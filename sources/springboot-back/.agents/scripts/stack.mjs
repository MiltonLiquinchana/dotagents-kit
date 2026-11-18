#!/usr/bin/env node
// stack.mjs - Lector de .agents/stack.yaml (subconjunto de YAML, sin dependencias).
//
// Único punto del .agents que lee el archivo de parámetros del proyecto. Ningún otro script
// lee .agents/stack.yaml por su cuenta: importan este módulo o lo llaman por terminal.
//
// Subconjunto admitido:
//   - claves de primer nivel cuyo valor es un escalar (texto, número, true/false, null),
//     una lista de escalares ([a, b] o en bloque con `- `) o un mapa;
//   - mapas de hasta cuatro niveles, con sangría fija de dos espacios;
//   - comentarios con `#`. Sin anclas, sin bloques multilínea, sin tipos especiales.
//
// Uso:
//   node .agents/scripts/stack.mjs get <clave>    Imprime el valor (para listas, una por línea)
//   node .agents/scripts/stack.mjs validate       Comprueba claves obligatorias y formato
//   node .agents/scripts/stack.mjs --help
//
// Códigos de salida: 0 = OK, 2 = BLOCKED (infraestructura).
// ==============================================================================
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { pathToFileURL } from 'node:url';

// Stack que este .agents soporta: si `proyecto.stack` difiere, el archivo no es de este proyecto.
const STACK = 'springboot';

const REQUIRED = [
  'nomenclatura.clase_aplicacion',
  'devops.infraestructura', 'version_esquema', 'api_error.campo_mensaje', 'api_error.campo_codigo',
  'proyecto.nombre', 'proyecto.stack',
  'backend.group', 'backend.java', 'backend.spring_boot', 'backend.build', 'backend.gateway',
  'backend.persistencia', 'backend.lombok', 'backend.prueba_viva',
  'backend.jdk_ruta_desarrollo',
  'integraciones.autenticacion',
  'herramientas.codebase_memory', 'git.rama_base',

];

let contextoLectura = '.agents/stack.yaml';
function bloqueado(msg) {
  process.stderr.write(`BLOCKED (infraestructura): ${contextoLectura}: ${msg}\n`);
  process.exit(2);
}

function etc(arg) {
  process.stderr.write(`uso: node stack.mjs get <clave> | validate | huella | regenerar | registro-datos | --help\n${arg ? '   ' + arg + '\n' : ''}`);
  process.exit(2);
}

// ---- Lectura y análisis --------------------------------------------------------------
function rutaStack() {
  let root = process.cwd();
  try {
    root = execFileSync('git', ['rev-parse', '--show-toplevel'], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }).trim();
  } catch { /* se usa el directorio actual */ }
  return path.join(root, '.agents', 'stack.yaml');
}

function sinComentario(linea) {
  let enComillas = null;
  for (let i = 0; i < linea.length; i++) {
    const c = linea[i];
    if (enComillas) {
      if (c === '\\' && enComillas !== "'") i++;
      else if (c === enComillas) enComillas = null;
    } else if (c === '"' || c === "'") enComillas = c;
    else if (c === '#') return linea.slice(0, i);
  }
  return linea;
}

function escalar(bruto) {
  const s = bruto.trim();
  if (s === 'null' || s === '~') return null;
  if (s === 'true') return true;
  if (s === 'false') return false;
  if (/^-?\d+(?:\.\d+)?$/.test(s)) return Number(s);
  if (s.length >= 2 && ((s[0] === '"' && s.at(-1) === '"') || (s[0] === "'" && s.at(-1) === "'"))) {
    if (s[0] === '"') {
      try { return JSON.parse(s); } catch { return s.slice(1, -1); }
    }
    return s.slice(1, -1);
  }
  return s; // texto sin comillas
}

function listaEnLinea(texto) {
  const m = texto.trim().match(/^\[(.*)\]$/);
  if (!m) return null;
  const inner = m[1].trim();
  if (inner === '') return [];
  // parte por comas fuera de comillas
  const items = [];
  let cur = '', enComillas = null;
  for (const c of inner) {
    if (enComillas) {
      if (c === enComillas) enComillas = null;
      cur += c;
    } else if (c === '"' || c === "'") { enComillas = c; cur += c; }
    else if (c === ',') { items.push(cur); cur = ''; }
    else cur += c;
  }
  items.push(cur);
  return items.map(escalar);
}

export function parsear(texto, nombre = '.agents/stack.yaml') {
  const rows = [];
  function bad(row, msg) { throw new Error(`${nombre}:${row[2]}: ${msg}`); }
  texto.split(/\r?\n/).forEach((raw, i) => {
    const line = sinComentario(raw);
    if (!line.trim()) return;
    const prefix = line.slice(0, line.length - line.trimStart().length);
    if (prefix.includes('\t') || prefix.length % 2) bad([0, '', i + 1], 'sangría incoherente; usa dos espacios por nivel, sin tabuladores');
    rows.push([prefix.length, line.trim(), i + 1]);
  });
  function value(raw, row, list = true) {
    if (raw.startsWith('[')) {
      if (!list || !raw.endsWith(']')) bad(row, 'lista inválida o no escalar');
      const inner = raw.slice(1, -1).trim();
      if (!inner) return [];
      const parts = []; let cur = '', quote = '', escape = false;
      for (const c of inner) {
        if (quote) {
          cur += c;
          if (escape) escape = false;
          else if (c === '\\' && quote === '"') escape = true;
          else if (c === quote) quote = '';
        } else if (c === '"' || c === "'") { quote = c; cur += c; }
        else if (c === ',') { parts.push(cur.trim()); cur = ''; }
        else cur += c;
      }
      parts.push(cur.trim());
      if (quote || parts.some(p => !p)) bad(row, 'lista inválida o comillas sin cerrar');
      return parts.map(p => value(p, row, false));
    }
    if (raw.startsWith('"') || raw.startsWith("'")) {
      if (raw.length < 2 || raw.at(-1) !== raw[0]) bad(row, 'comillas sin cerrar');
    } else if (/^[{}&*!|>]/.test(raw) || ['---', '...'].includes(raw)) bad(row, 'formato no admitido: sin mapas en línea, anclas, tags ni multilínea');
    else if (/^[\w.-]+:\s/.test(raw)) bad(row, 'solo se admiten elementos escalares');
    return escalar(raw);
  }
  function read(index, indent, depth) {
    const list = rows[index][1].startsWith('- '), result = list ? [] : {};
    while (index < rows.length) {
      const row = rows[index];
      if (row[0] < indent) break;
      if (row[0] !== indent) bad(row, 'sangría incoherente o hijos de un escalar');
      if (list) {
        if (!row[1].startsWith('- ')) bad(row, 'no se pueden mezclar listas y mapas');
        result.push(value(row[1].slice(2).trim(), row, false)); index++; continue;
      }
      if (depth >= 4) bad(row, 'máximo cuatro niveles de claves');
      const match = row[1].match(/^([\w.-]+):\s*(.*)$/);
      if (!match) bad(row, 'se esperaba clave: valor; sin listas de objetos ni documentos múltiples');
      const key = match[1], raw = match[2].trim();
      if (Object.hasOwn(result, key)) bad(row, 'clave repetida ' + key);
      Object.defineProperty(result, key, { value: null, enumerable: true, writable: true, configurable: true });
      index++;
      if (raw) result[key] = value(raw, row);
      else if (index < rows.length && rows[index][0] > indent) {
        if (rows[index][0] !== indent + 2) bad(rows[index], 'cada nivel añade exactamente dos espacios');
        [result[key], index] = read(index, indent + 2, depth + 1);
      } else result[key] = {};
    }
    return [result, index];
  }
  if (!rows.length) return {};
  if (rows[0][0] !== 0 || rows[0][1].startsWith('- ')) bad(rows[0], 'el documento debe empezar con un mapa sin sangría');
  const [root, end] = read(0, 0, 0);
  if (end !== rows.length) bad(rows[end], 'sangría incoherente');
  return root;
}


function validarEntornos(data) {
  if (obtener(data, 'devops.infraestructura') !== 'jenkins-kubernetes') return;
  const all = obtener(data, 'devops.entornos');
  if (!all || typeof all !== 'object' || Array.isArray(all) || !Object.keys(all).length) bloqueado('falta devops.entornos no vacío; sustituye rama_despliegue/entorno con el formato de la plantilla');
  const suffixes = new Set(), explicit = new Set(), patterns = []; let builders = 0;
  const fields = ['rama','sufijo','credencial_kubeconfig','imagen','desplegar'];
  for (const [name, cfg] of Object.entries(all)) {
    const key = `devops.entornos.${name}`;
    const fail = msg => bloqueado(`${key}: ${msg}`);
    if (!/^[a-z][a-z0-9]*$/.test(name) || name.length > 63 || name.endsWith('-')) fail('nombre de carpeta no válido');
    if (!cfg || typeof cfg !== 'object' || Array.isArray(cfg)) fail('debe ser un mapa');
    for (const f of fields) if (!Object.hasOwn(cfg, f)) fail(`falta ${f}`);
    if (typeof cfg.rama !== 'string' || !/^[A-Za-z0-9][A-Za-z0-9._/-]*(?:\/\*)?$/.test(cfg.rama) || cfg.rama.includes('..') || cfg.rama.includes('//') || cfg.rama.endsWith('/')) fail('rama debe ser exacta o un prefijo terminado en /*');
    const branch = cfg.rama.endsWith('/*') ? cfg.rama.slice(0, -2) : cfg.rama;
    if (branch.split('/').some(part => part.startsWith('.') || part.endsWith('.') || part.endsWith('.lock'))) fail('rama contiene un segmento no válido para Git');
    const prefix = cfg.rama.endsWith('/*') ? cfg.rama.slice(0, -1) : null;
    for (const [other, pre] of patterns) {
      if (cfg.rama === other || (pre && (prefix ? prefix.startsWith(pre) || pre.startsWith(prefix) : cfg.rama.startsWith(pre))) || (prefix && !pre && other.startsWith(prefix))) fail('rama se solapa con otro entorno');
    }
    patterns.push([cfg.rama, prefix]);
    if (typeof cfg.sufijo !== 'string' || !/^[a-z][a-z0-9]*$/.test(cfg.sufijo) || suffixes.has(cfg.sufijo)) fail('sufijo debe ser alfanumérico minúsculo y único');
    suffixes.add(cfg.sufijo);
    if (typeof cfg.credencial_kubeconfig !== 'string' || !/^[A-Za-z0-9_.-]+$/.test(cfg.credencial_kubeconfig)) fail('credencial_kubeconfig debe ser solo el ID de Jenkins');
    if (!['construir','promover'].includes(cfg.imagen)) fail('imagen debe valer construir | promover; si esta rama solo necesita compilar y analizar, elimina su entrada de devops.entornos (la compilación y Sonar se ejecutan sin ella).');
    if (cfg.imagen === 'construir') builders++;
    if (typeof cfg.desplegar !== 'boolean') fail('desplegar debe ser true | false');
    if (cfg.imagen === 'promover' && !cfg.desplegar) fail('imagen promover exige desplegar true');
    if (!cfg.desplegar) continue;
    if (!Number.isInteger(cfg.replicas) || cfg.replicas < 1) fail('replicas debe ser un entero positivo');
    for (const f of ['cpu_peticion','cpu_limite']) if (typeof cfg[f] !== 'string' || !/^[1-9][0-9]*m$/.test(cfg[f])) fail(`${f} necesita unidad m y cantidad positiva`);
    const memory = v => {
      const m = typeof v === 'string' && v.match(/^([1-9][0-9]*)(Ki|Mi|Gi|Ti)$/);
      return m ? BigInt(m[1]) * (1024n ** BigInt(['Ki','Mi','Gi','Ti'].indexOf(m[2]) + 1)) : null;
    };
    const req = memory(cfg.memoria_peticion), lim = memory(cfg.memoria_limite);
    if (req === null || lim === null || req > lim || BigInt(cfg.cpu_peticion.slice(0,-1)) > BigInt(cfg.cpu_limite.slice(0,-1))) fail('recursos inválidos: memoria con Ki/Mi/Gi/Ti y petición no mayor que límite');
    if (!Number.isInteger(cfg.nodo_puerto_base) || cfg.nodo_puerto_base < 30000 || cfg.nodo_puerto_base > 32767) fail('nodo_puerto_base fuera de 30000–32767');
    if (obtener(data,'backend.gateway') !== null) {
      if (!Number.isInteger(cfg.gateway_nodo_puerto) || cfg.gateway_nodo_puerto < 30000 || cfg.gateway_nodo_puerto > 32767 || explicit.has(cfg.gateway_nodo_puerto)) fail('gateway_nodo_puerto inválido o repetido');
      explicit.add(cfg.gateway_nodo_puerto);
    }
    if (obtener(data,'backend.gateway') !== null) {
    if (!Array.isArray(cfg.cors_origenes) || !cfg.cors_origenes.length) fail('cors_origenes debe ser lista no vacía');
    for (const v of cfg.cors_origenes) {
      let u; try { u = new URL(v); } catch { fail('origen CORS no válido'); }
      if (typeof v !== 'string' || v !== v.trim() || v.endsWith('/') || !['http:','https:'].includes(u.protocol) || !u.hostname || u.username || u.password || u.search || u.hash || u.pathname !== '/') fail('origen CORS debe ser HTTP(S), sin ruta, barra final ni credenciales');
    }
    }
    if (obtener(data,'integraciones.autenticacion') === 'clerk') {
      let u; try { u = new URL(cfg.clerk_issuer_uri); } catch { fail('falta clerk_issuer_uri HTTPS con Clerk'); }
      if (typeof cfg.clerk_issuer_uri !== 'string' || cfg.clerk_issuer_uri.endsWith('/') || u.protocol !== 'https:' || !u.hostname || u.username || u.password || u.search || u.hash) fail('clerk_issuer_uri debe ser HTTPS sin credenciales, parámetros ni barra final');
    }
  }
  if (builders > 1) bloqueado('devops.entornos: solo un entorno puede tener imagen construir');
}

// Contrato generado: contiene rutas y condiciones, nunca valores del proyecto.
function terminosCondicion(expr, meta, opciones = {}) {
  if (typeof expr !== 'string' || !expr.trim()) bloqueado('config/condiciones.yaml: condición vacía');
  return expr.split('&&').map(term => {
    const m = term.match(/^\s*([\w.{}-]+)\s*(!=|=)\s*(null|true|false|[\w-]+)\s*$/);
    if (!m || !meta.claves.includes(m[1])) bloqueado('config/condiciones.yaml: condición inválida o clave desconocida');
    const [,key,op,raw] = m, value = escalar(raw);
    if (key.includes('{nombre}') && !meta.claves.some(p => p.endsWith('.{nombre}') && key.startsWith(p + '.'))) bloqueado('config/condiciones.yaml: comodín fuera de un mapa libre');
    if (opciones[key] && !opciones[key].some(v => v === value)) bloqueado('config/condiciones.yaml: valor fuera de config/opciones.yaml');
    return [key,op,value];
  });
}
function validarMetadata(meta, opciones) {
  if (!meta || typeof meta !== 'object' || Object.keys(meta).sort().join(',') !== 'claves,reglas,version' || meta.version !== 1 || !Array.isArray(meta.claves) || !meta.claves.length || meta.claves.some(k => typeof k !== 'string' || !/^[\w.{}-]+$/.test(k)) || new Set(meta.claves).size !== meta.claves.length || !Array.isArray(meta.reglas)) bloqueado('config/condiciones.yaml inválido; regenera el .agents');
  const seen = new Set();
  for (const regla of meta.reglas) {
    if (typeof regla !== 'string' || regla.split(' :: ').length !== 2) bloqueado('config/condiciones.yaml: regla inválida');
    const [key,expr] = regla.split(' :: ');
    if (!meta.claves.includes(key) || seen.has(key)) bloqueado('config/condiciones.yaml: clave de regla desconocida o repetida');
    seen.add(key);
    for (const [ref] of terminosCondicion(expr,meta,opciones)) if (ref.includes('{nombre}') && !key.includes('{nombre}')) bloqueado('config/condiciones.yaml: comodín sin contexto');
  }
  return meta;
}
function cargarCondiciones() {
  const ruta = path.join(path.dirname(rutaStack()), 'config/condiciones.yaml');
  if (!fs.existsSync(ruta)) bloqueado('falta config/condiciones.yaml generado; regenera el .agents con actualizar.py');
  let meta;
  contextoLectura = 'config/condiciones.yaml generado';
  try { meta = parsear(fs.readFileSync(ruta,'utf8')); }
  catch { bloqueado('contenido inválido; regenera el .agents'); }
  finally { contextoLectura = '.agents/stack.yaml'; }
  return validarMetadata(meta,cargarOpciones());
}
function normalCondicion(key, meta) {
  const partes = key.split('.');
  return meta.claves.find(candidate => {
    const pattern = candidate.split('.');
    return pattern.length === partes.length && pattern.every((p,i) => p === '{nombre}' || p === partes[i]);
  }) || key;
}
function activaCondicion(meta, key, data) {
  const normal = normalCondicion(key, meta), name = normal.includes('{nombre}') ? key.split('.')[normal.split('.').indexOf('{nombre}')] : null;
  for (const regla of meta.reglas) {
    const [target,expr] = regla.split(' :: ');
    if (normal !== target && !normal.startsWith(target + '.')) continue;
    for (const [ref,op,value] of terminosCondicion(expr,meta)) {
      const actual = obtener(data, ref.replace('{nombre}', name));
      if (actual === undefined || (op === '=' ? actual !== value : actual === value)) return false;
    }
  }
  return true;
}
function rutasCondicion(data, key) {
  let paths = [''];
  for (const part of key.split('.')) {
    paths = paths.flatMap(p => part === '{nombre}' ? Object.keys(obtener(data,p) || {}).map(k => p + '.' + k) : [(p ? p + '.' : '') + part]);
  }
  return paths;
}
function ayudaCondicion(meta, key) {
  const normal = normalCondicion(key, meta), frases = [];
  for (const regla of meta.reglas) {
    const [target,expr] = regla.split(' :: ');
    if (normal !== target && !normal.startsWith(target + '.')) continue;
    for (const [ref,op,value] of terminosCondicion(expr,meta)) {
      const frase = ref.split('.').at(-1) + (op === '=' ? ': ' : ' distinto de ') + String(value);
      if (!frases.includes(frase)) frases.push(frase);
    }
  }
  return frases.length ? ' (solo con ' + frases.join(' y ') + ')' : '';
}
function validarCondicionales(data, meta) {
  for (const regla of meta.reglas) for (const key of rutasCondicion(data,regla.split(' :: ')[0])) {
    if (activaCondicion(meta,key,data) && obtener(data,key) === undefined) bloqueado('falta en tu stack.yaml: ' + key + ayudaCondicion(meta,key));
  }
}

function cargar() {
  const ruta = rutaStack();
  let texto;
  try {
    texto = fs.readFileSync(ruta, 'utf8');
  } catch {
    bloqueado('no se encontró .agents/stack.yaml en la raíz del repositorio.');
  }
  let data;
  try {
    data = parsear(texto);
  } catch (e) {
    if (e instanceof Error && e.message.startsWith('BLOCKED (infraestructura): ')) bloqueado(e.message.replace('BLOCKED (infraestructura): ', ''));
    bloqueado(`formato inválido: ${e.message}`);
  }
  return validarDatos(data, cargarCondiciones());
}
function validarDatos(data, meta, opciones = cargarOpciones()) {
  if (data === null || typeof data !== 'object' || Array.isArray(data)) bloqueado('el documento no es un mapa de claves');
  const herramientas = data.herramientas;
  if (herramientas && typeof herramientas === 'object' && !Array.isArray(herramientas) &&
      !Object.hasOwn(herramientas, 'codebase_memory') && Object.hasOwn(herramientas, 'graphify')) {
    herramientas.codebase_memory = herramientas.graphify;
  }
  const desarrollo = obtener(data, 'backend.jdk_ruta_desarrollo');
  if (desarrollo === undefined) bloqueado('falta la clave obligatoria backend.jdk_ruta_desarrollo; declara una sola ruta POSIX absoluta del JDK de desarrollo, sin comas, o null para no gestionar esa línea');
  if (desarrollo !== null && (typeof desarrollo !== 'string' || !desarrollo.startsWith('/') || !desarrollo.trim() || desarrollo.includes(',') || /[\r\n\0]/.test(desarrollo))) bloqueado('backend.jdk_ruta_desarrollo debe ser una sola ruta POSIX absoluta no vacía, sin comas, o null');
  if (obtener(data, 'devops.infraestructura') === 'jenkins-kubernetes') {
    const jf = obtener(data, 'devops.jenkinsfile');
    if (jf === undefined) bloqueado('falta la clave obligatoria devops.jenkinsfile con infraestructura jenkins-kubernetes; declara la ruta relativa de tu pipeline, por ejemplo devops/Jenkinsfile');
    if (typeof jf !== 'string' || !jf.trim() || jf.startsWith('/') || jf.includes('..') || jf.split('/').some(p => !p || p === 'account' || p.startsWith('.env')) || jf.includes(String.fromCharCode(92)) || /^[A-Za-z]+:/.test(jf) || /[\r\n\0]/.test(jf)) bloqueado('devops.jenkinsfile debe ser una ruta relativa no vacía dentro del repositorio, sin .., barra inicial ni contrabarras; sin segmentos vacíos, account/ ni nombres .env*');
    for (const [name, ejemplo] of [['general', 'principal'], ['compilacion', 'compilador'], ['docker', 'docker']]) {
      const key = 'devops.nodos.' + name, value = obtener(data, key);
      if (value === undefined) bloqueado('falta la clave obligatoria ' + key + ' con infraestructura jenkins-kubernetes; declara una etiqueta, por ejemplo ' + ejemplo);
      if (typeof value !== 'string' || !/^[A-Za-z0-9][A-Za-z0-9_.-]*$/.test(value)) bloqueado(key + ' debe ser una sola etiqueta con formato ^[A-Za-z0-9][A-Za-z0-9_.-]*$');
    }
  }
  validarCondicionales(data, meta);
  if (!('proyecto' in data) || data.proyecto === null || typeof data.proyecto !== 'object' || data.proyecto === undefined) {
    bloqueado("falta la clave 'proyecto'");
  }
  if (!('stack' in data.proyecto)) bloqueado("falta la clave 'proyecto.stack'");
  if (data.proyecto.stack !== STACK) {
    bloqueado(`proyecto.stack es ${JSON.stringify(data.proyecto.stack)}, este .agents corresponde al stack '${STACK}'`);
  }
  if (!('version_esquema' in data)) bloqueado('falta la clave obligatoria version_esquema');
  for (const clave of ['api_error.campo_mensaje', 'api_error.campo_codigo']) {
    const valor = obtener(data, clave);
    const permiteNull = clave === 'api_error.campo_codigo';
    const ayuda = permiteNull ? 'texto con el campo del código de negocio, o null si la API no lo manda' : 'texto con el campo del mensaje de la API';
    if (valor === undefined) bloqueado(`falta la clave obligatoria ${clave}; declara ${ayuda}`);
    if (!(permiteNull && valor === null) && (typeof valor !== 'string' || valor.trim() === '')) {
      bloqueado(`${clave} debe ser ${ayuda}`);
    }
  }
  const config = data.documentacion;
  if (!config || typeof config !== 'object') bloqueado('falta documentacion');
  for (const clave of ['url_api', 'variable_password', 'modelo_chat', 'modelo_contexto_grande', 'modelo_transformacion', 'timeout_chat']) {
    if (!(clave in config)) bloqueado(`falta documentacion.${clave}; declara esta clave según la plantilla y regenera.`);
    if (!['url_api', 'timeout_chat'].includes(clave) && config[clave] !== null && (typeof config[clave] !== 'string' || !config[clave].trim())) bloqueado(`documentacion.${clave} debe ser texto o null`);
  }
  if (!Number.isInteger(config.timeout_chat) || config.timeout_chat < 1 || config.timeout_chat > 3600) bloqueado('documentacion.timeout_chat debe ser un entero entre 1 y 3600 segundos');
  let url;
  try { url = new URL(config.url_api); } catch { bloqueado('documentacion.url_api debe ser HTTP(S)'); }
  if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password || url.search || url.hash) bloqueado('documentacion.url_api no admite credenciales ni parámetros');
  if (config.variable_password !== null && !/^[A-Za-z_][A-Za-z0-9_]*$/.test(config.variable_password)) bloqueado('documentacion.variable_password solo admite el nombre de una variable');
  for (const clave of REQUIRED) {
    if (obtener(data, clave) === undefined) bloqueado(`falta la clave obligatoria ${clave}${clave === 'backend.prueba_viva' ? ' (valores válidos: true | false)' : ''}`);
  }
  const group = obtener(data, 'backend.group');
  const reservadas = new Set(('abstract assert boolean break byte case catch char class const continue default do double else enum extends final finally float for goto if implements import instanceof int interface long native new package private protected public return short static strictfp super switch synchronized this throw throws transient try void volatile while true false null _').split(' '));
  if (typeof group !== 'string' || !group.split('.').every(segmento =>
    /^[$_\p{ID_Start}][$_\p{ID_Continue}]*$/u.test(segmento) && !reservadas.has(segmento))) {
    bloqueado('backend.group debe ser un paquete Java: identificadores separados por puntos, sin segmentos vacíos ni palabras reservadas');
  }
  if (typeof obtener(data, 'backend.prueba_viva') !== 'boolean') {
    bloqueado('backend.prueba_viva debe valer true | false');
  }
  const configuradoLocal = obtener(data, 'backend.perfil_local');
  const perfilLocal = configuradoLocal === undefined ? 'feature' : configuradoLocal;
  if (perfilLocal !== undefined) {
    if (typeof perfilLocal !== 'string' || !/^[a-z][a-z0-9]*$/.test(perfilLocal)) {
      bloqueado('backend.perfil_local debe ser un identificador de perfil en minúsculas (letras y números)');
    }
    if (obtener(data, 'devops.infraestructura') === 'jenkins-kubernetes') {
      const sufijos = Object.values(obtener(data, 'devops.entornos') || {}).map(e => e && e.sufijo).filter(Boolean);
      if (sufijos.includes(perfilLocal)) {
        bloqueado('backend.perfil_local no puede coincidir con el sufijo de un entorno: ' + perfilLocal);
      }
    }
  }
  if (obtener(data, 'devops.infraestructura') === 'jenkins-kubernetes') {
    for (const nombre of ['registry',
      'java_home_nodo', 'java_home_contenedor', 'jdk_url', 'slack_canal',
      'credencial_bd_pruebas']) {
      const clave = `devops.${nombre}`;
      const valor = obtener(data, clave);
      if (valor === undefined) bloqueado(`falta la clave obligatoria ${clave} con infraestructura jenkins-kubernetes`);
      if ((nombre === 'slack_canal' || nombre === 'credencial_bd_pruebas') && valor === null) continue;
      if (nombre === 'credencial_bd_pruebas') {
        if (typeof valor !== 'string' || !/^[A-Za-z0-9_.-]+$/.test(valor)) {
          bloqueado(`${clave} debe ser null o un ID de credencial Jenkins (solo letras, números, _, . y -)`);
        }
        continue;
      }
      if (typeof valor !== 'string' || valor.trim() === '') {
        bloqueado(`${clave} debe ser texto no vacío${nombre === 'slack_canal' ? ' o null (sin aviso)' : ''}`);
      }
    }
  }
  validarEntornos(data);
  // Clerk: el issuer y los NOMBRES de las variables de autenticación (nunca valores).
  if (obtener(data, 'integraciones.autenticacion') === 'clerk') {
    for (const clave of ['integraciones.clerk_issuer_uri']) {
      if (obtener(data, clave) === undefined) {
        bloqueado(`falta la clave obligatoria ${clave} con autenticacion: clerk`);
      }
    }
  }
  const issuer = obtener(data, 'integraciones.clerk_issuer_uri');
  if (issuer !== undefined && (typeof issuer !== 'string' || issuer.trim() === '')) {
    bloqueado('integraciones.clerk_issuer_uri debe ser texto no vacío; si no usas Clerk, quita la clave');
  }
  const variables = obtener(data, 'integraciones.variables_autenticacion');
  if (activaCondicion(meta, 'integraciones.variables_autenticacion', data) && variables !== undefined) {
    if (!Array.isArray(variables) || variables.length === 0) {
      bloqueado('integraciones.variables_autenticacion debe valer una lista de nombres de variables');
    }
    for (const nombre of variables) {
      if (typeof nombre !== 'string') {
        bloqueado("integraciones.variables_autenticacion contiene un elemento que no es un nombre de variable");
      }
      if (/_(test|live)_/.test(nombre) || nombre.includes('whsec_') || nombre.includes('=') || nombre.length > 64) {
        bloqueado("integraciones.variables_autenticacion contiene un elemento que parece un valor; declara solo NOMBRES");
      }
      if (!/^[A-Z][A-Z0-9_]*$/.test(nombre)) {
        bloqueado("integraciones.variables_autenticacion contiene un nombre que no respeta MAYÚSCULAS_CON_GUIONES_BAJOS");
      }
    }
  }
  if (activaCondicion(meta, 'nomenclatura.estrategia_fisica_jpa', data) && (typeof obtener(data, 'nomenclatura.estrategia_fisica_jpa') !== 'string' || !obtener(data, 'nomenclatura.estrategia_fisica_jpa').trim())) bloqueado('nomenclatura.estrategia_fisica_jpa debe ser texto no vacío');
  const patrones = {"clase_aplicacion": "{AliasPascal}"};
  for (const [key, comodin] of Object.entries(patrones)) {
    const value = obtener(data, 'nomenclatura.' + key);
    if (typeof value !== 'string' || !value.includes(comodin)) bloqueado(`nomenclatura.${key} debe contener ${comodin}`);
  }
  return data;
}

export function obtener(data, clavePunteada) {
  let cur = data;
  for (const part of clavePunteada.split('.')) {
    if (cur === null || typeof cur !== 'object' || !(part in cur)) return undefined;
    cur = cur[part];
  }
  return cur;
}

export function get(clave) {
  const valor = obtener(cargar(), clave);
  if (clave === 'backend.perfil_local' && valor === undefined) return 'feature';
  if (valor === undefined) bloqueado(`falta la clave ${clave}`);
  return valor;
}

function avisosValidacion(data) {
  const avisos = [];
  if (obtener(data, 'backend.perfil_local') === undefined) {
    avisos.push('AVISO PERFIL_LOCAL: falta backend.perfil_local; se usará "feature" como perfil local por defecto. Decláralo en .agents/stack.yaml para evitar esta advertencia.');
  }
  const n = String(obtener(data, 'backend.java') ?? '').trim();
  if (!/^[0-9]+$/.test(n)) return avisos;
  const claves = ['backend.jdk_ruta_desarrollo'];
  if (obtener(data, 'devops.infraestructura') === 'jenkins-kubernetes') claves.push('devops.java_home_nodo', 'devops.java_home_contenedor', 'devops.jdk_url');
  const reN = new RegExp(`(^|[^0-9])${n}([^0-9]|$)`);
  for (const clave of claves) {
    const valor = obtener(data, clave);
    if (valor === undefined || valor === null) continue;
    const texto = String(valor);
    if (!reN.test(texto)) {
      avisos.push(`AVISO JDK_STACK: ${clave} no contiene el número ${n} de backend.java (${texto}); revisa la clave o lánzalo con change-version.`);
    }
  }
  return avisos;
}

export function validar(avisarRetirada = false) {
  const data = cargar();
  validarOpciones(data);
  for (const aviso of avisosValidacion(data)) process.stderr.write(aviso + '\n');
  if (avisarRetirada && Object.hasOwn(data.herramientas ?? {}, 'graphify')) {
    process.stderr.write('aviso: herramientas.graphify está retirada; renómbrala a herramientas.codebase_memory en tu stack.yaml\n');
  }
  return true;
}

// ---- Opciones condicionales (`si clave=valor`) -----------------------------------------
// .agents/config/opciones.yaml declara, para cada marca condicional del .agents, la lista de
// valores permitidos. `validate` comprueba aquí que cada clave existe en stack.yaml y que su
// valor está en su lista. Si el archivo falta, no hay nada que validar.
function cargarOpciones() {
  const ruta = path.join(path.dirname(rutaStack()), 'config', 'opciones.yaml');
  let texto;
  try { texto = fs.readFileSync(ruta, 'utf8'); } catch { return null; }
  let ops;
  try { ops = parsear(texto); } catch (e) {
    if (e instanceof Error && e.message.startsWith('BLOCKED (infraestructura): ')) bloqueado(e.message.replace('BLOCKED (infraestructura): ', '').replace('.agents/stack.yaml: ', ''));
    bloqueado(`config/opciones.yaml: formato inválido: ${e.message}`);
  }
  return ops;
}

function validarRequisitos(data, ops) {
  const ruta = path.join(path.dirname(rutaStack()), 'config', 'requisitos.yaml');
  if (!fs.existsSync(ruta)) return;
  const vistos = new Set();
  const condicion = (texto) => {
    if (typeof texto !== 'string' || !texto.includes('=')) bloqueado('config/requisitos.yaml: se esperaba clave=valor');
    const pos = texto.indexOf('=');
    const clave = texto.slice(0, pos), literal = texto.slice(pos + 1);
    const valores = (ops?.[clave] ?? []).filter(v => formatoEscalarHuella(v) === literal);
    if (valores.length !== 1) bloqueado(`config/requisitos.yaml: ${texto} no está en config/opciones.yaml`);
    return [clave, valores[0]];
  };
  const reglas = [];
  for (const cruda of fs.readFileSync(ruta, 'utf8').split(/\r?\n/)) {
    const linea = sinComentario(cruda);
    if (!linea.trim()) continue;
    const m = linea.match(/^([^\s:]+):\s*(\[.*\])\s*$/);
    if (!m || vistos.has(m[1])) bloqueado('config/requisitos.yaml: mapa plano de condiciones no válido');
    vistos.add(m[1]);
    const lista = listaEnLinea(m[2]);
    if (!lista?.length) bloqueado('config/requisitos.yaml: lista de requisitos vacía');
    reglas.push([condicion(m[1]), lista.map(condicion)]);
  }
  for (const [[clave, valor], requisitos] of reglas) {
    if (obtener(data, clave) !== valor) continue;
    for (const [requerida, esperado] of requisitos) {
      if (obtener(data, requerida) !== esperado) bloqueado(`${clave}=${formatoEscalarHuella(valor)} exige ${requerida}=${formatoEscalarHuella(esperado)}`);
    }
  }
}

function validarOpciones(data) {
  const ops = cargarOpciones();
  if (ops === null) { validarRequisitos(data, {}); return true; }
  for (const [clave, lista] of Object.entries(ops)) {
    if (!Array.isArray(lista) || lista.length === 0 || lista.some((x) => x === null || typeof x === 'object')) {
      bloqueado(`config/opciones.yaml: \`${clave}\` debe valer una lista de escalares`);
    }
    const valor = obtener(data, clave);
    if (valor === undefined) bloqueado(`falta la clave obligatoria ${clave} (config/opciones.yaml; valores válidos: ${lista.join(', ')})`);
    if (!lista.includes(valor)) bloqueado(`valor de ${clave} no está en config/opciones.yaml; valores válidos: ${lista.join(', ')}`);
  }
  validarRequisitos(data, ops);
  return true;
}

// ---- Huella de la configuración -------------------------------------------------------
// sha256 (hex) de las líneas `<clave>=<valor>\n`, para cada clave de
// config/opciones.yaml resuelta en .agents/stack.yaml, en orden alfabético.
// Es la misma fórmula que aplica actualizar.py al escribir .generado.json:
// si cambia stack.yaml sin regenerar, la huella del preflight ya no coincide.
function formatoEscalarHuella(valor) {
  if (typeof valor === 'string') return valor;
  if (valor === true) return 'true';
  if (valor === false) return 'false';
  return String(valor);
}

function huellaConfiguracion(data) {
  const ops = cargarOpciones();
  const claves = ops === null ? [] : Object.keys(ops).sort();
  const lineas = claves.map((clave) => {
    const valor = obtener(data, clave);
    if (valor === undefined || valor === null || Array.isArray(valor) || typeof valor === 'object') {
      bloqueado(`falta la clave ${clave} (huella de la configuración; lista de valores en config/opciones.yaml)`);
    }
    return `${clave}=${formatoEscalarHuella(valor)}\n`;
  });
  return crypto.createHash('sha256').update(lineas.join('')).digest('hex');
}


export function valorCanonico(valor) {
  if (valor === null || valor === undefined) return '';
  if (typeof valor !== 'object') return formatoEscalarHuella(valor);
  const orden = v => Array.isArray(v) ? v.map(orden) : v && typeof v === 'object'
    ? Object.fromEntries(Object.keys(v).sort().map(k => [k, orden(v[k])])) : v;
  return JSON.stringify(orden(valor));
}
export function mapaRegenerar(data, opciones) {
  const result = {};
  for (const k of Object.keys(opciones).sort()) result[k] = valorCanonico(obtener(data, k));
  const hojas = (v, k) => {
    if (v && !Array.isArray(v) && typeof v === 'object' && Object.keys(v).length)
      for (const n of Object.keys(v).sort()) hojas(v[n], k + '.' + n);
    else result[k] = valorCanonico(v);
  };
  hojas(Object.hasOwn(data, 'nomenclatura') ? data.nomenclatura : {}, 'nomenclatura');
  return Object.fromEntries(Object.entries(result).sort(([a],[b]) => a < b ? -1 : a > b ? 1 : 0));
}
export function regenerar() {
  const data = cargar(); validarOpciones(data);
  return mapaRegenerar(data, cargarOpciones() || {});
}
export function registroDatos() {
  const data = cargar();
  const servicios = fs.readdirSync('.').filter(n => !n.startsWith('.') &&
    fs.existsSync(path.join(n, 'build.gradle')) && fs.existsSync(path.join(n, 'settings.gradle'))).sort();
  const gw = obtener(data, 'backend.gateway');
  let perfilLocal = obtener(data, 'backend.perfil_local');
  if (perfilLocal === undefined || perfilLocal === null || perfilLocal === '') perfilLocal = 'feature';
  const valores = {
    'backend.lombok': valorCanonico(obtener(data, 'backend.lombok')),
    'backend.persistencia': valorCanonico(obtener(data, 'backend.persistencia')),
    'backend.group': valorCanonico(obtener(data, 'backend.group')),
    'backend.gateway': valorCanonico(gw),
    'backend.cors_origenes': valorCanonico(obtener(data, 'backend.cors_origenes')),
    'backend.perfil_local': valorCanonico([...new Set([perfilLocal, ...(obtener(data, 'devops.infraestructura') === 'jenkins-kubernetes' ? Object.values(obtener(data, 'devops.entornos') || {}).map(e => e.sufijo).filter(Boolean) : [])])]),
    'integraciones.autenticacion': valorCanonico(obtener(data, 'integraciones.autenticacion')),
    'integraciones.gestion_usuarios': valorCanonico(obtener(data, 'integraciones.gestion_usuarios')),
    'integraciones.clerk_issuer_uri': valorCanonico(obtener(data, 'integraciones.clerk_issuer_uri')),
    'integraciones.variables_autenticacion': valorCanonico(obtener(data, 'integraciones.variables_autenticacion')),
    'nomenclatura.clase_aplicacion': valorCanonico(obtener(data, 'nomenclatura.clase_aplicacion')),
    'nomenclatura.estrategia_fisica_jpa': valorCanonico(obtener(data, 'nomenclatura.estrategia_fisica_jpa')),
    'api_error.campo_mensaje': valorCanonico(obtener(data, 'api_error.campo_mensaje')),
    'api_error.campo_codigo': valorCanonico(obtener(data, 'api_error.campo_codigo')),
    'devops.infraestructura': valorCanonico(obtener(data, 'devops.infraestructura')),
    'devops.slack_canal': valorCanonico(obtener(data, 'devops.slack_canal')),
    'devops.credencial_bd_pruebas': valorCanonico(obtener(data, 'devops.credencial_bd_pruebas')),
    'devops.registry': valorCanonico(obtener(data, 'devops.registry')),
    'backend.jdk_ruta_desarrollo': valorCanonico(obtener(data, 'backend.jdk_ruta_desarrollo')),
    'devops.jenkinsfile': valorCanonico(obtener(data, 'devops.jenkinsfile')),
    'devops.nodos.general': valorCanonico(obtener(data, 'devops.nodos.general')),
    'devops.nodos.compilacion': valorCanonico(obtener(data, 'devops.nodos.compilacion')),
    'devops.nodos.docker': valorCanonico(obtener(data, 'devops.nodos.docker')),
  };
  const entornos = (obtener(data, 'devops.entornos') && typeof obtener(data, 'devops.entornos') === 'object') ? obtener(data, 'devops.entornos') : {};
  const campos = ['rama','sufijo','credencial_kubeconfig','imagen','desplegar','replicas','cpu_peticion','cpu_limite','memoria_peticion','memoria_limite','nodo_puerto_base','gateway_nodo_puerto','cors_origenes','clerk_issuer_uri'];
  for (const [env, cfg] of Object.entries(entornos || {})) {
    if (!cfg || typeof cfg !== 'object') continue;
    for (const campo of campos) {
      if (Object.hasOwn(cfg, campo)) valores[`devops.entornos.${env}.${campo}`] = valorCanonico(cfg[campo]);
    }
  }
  return {stack: STACK, servicios, gateway: gw, valores};
}

export function huella() {
  const data = cargar();
  validarOpciones(data);
  return huellaConfiguracion(data);
}

// ---- CLI ------------------------------------------------------------------------------
function imprimir(valor) {
  if (valor === null) { process.stdout.write('\n'); return; }
  if (Array.isArray(valor)) {
    for (const x of valor) process.stdout.write(String(x) + '\n');
    return;
  }
  if (typeof valor === 'object') bloqueado('la clave solicitada es un mapa; pide una clave concreta dentro de él');
  process.stdout.write(String(valor) + '\n');
}

function main(argv) {
  if (argv[0] === '--validar-generacion') {
    const {data,meta,opciones} = JSON.parse(fs.readFileSync(0,'utf8'));
    validarDatos(data,validarMetadata(meta,opciones),opciones);
    return 0;
  }
  if (argv.length === 0 || argv[0] === '--help' || argv[0] === '-h') {
    process.stdout.write(
      `Uso: node .agents/scripts/stack.mjs get <clave> | validate | huella | regenerar | registro-datos | --help\n` +
      `  get <clave>   imprime el valor de la clave punteada (p. ej. proyecto.nombre);\n` +
      `                salida: booleanos true/false; null línea vacía; números sin decimales añadidos;\n` +
      `                textos tal cual; listas, un elemento por línea\n` +
      `  validate      comprueba que .agents/stack.yaml existe, respeta el subconjunto\n` +
      `                y tiene las claves obligatorias del stack '${STACK}'\n` +
      `  huella        imprime el sha256 de la configuración (claves de config/opciones.yaml\n` +
      `                resueltas en stack.yaml): misma fórmula que usa actualizar.py en .generado.json\n` +
      `Códigos de salida: 0 = OK, 2 = BLOCKED (infraestructura).\n`);
    return 0;
  }
  if (argv[0] === 'validate') {
    validar(true);
    process.stdout.write(`OK: .agents/stack.yaml es válido para el stack '${STACK}'.\n`);
    return 0;
  }
  if (['regenerar','registro-datos'].includes(argv[0]) && argv.length === 1) {
    process.stdout.write(JSON.stringify(argv[0] === 'regenerar' ? regenerar() : registroDatos()) + '\n');
    return 0;
  }
  if (argv[0] === 'huella') {
    process.stdout.write(huella() + '\n');
    return 0;
  }
  if (argv[0] === 'get') {
    if (argv.length !== 2) etc('get necesita exactamente una clave punteada');
    imprimir(get(argv[1]));
    return 0;
  }
  etc(`argumento desconocido: ${argv[0]}`);
}

const esCLI = process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href;
if (esCLI) { process.exit(main(process.argv.slice(2))); }
