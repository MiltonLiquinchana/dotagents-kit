#!/usr/bin/env node
// stack.mjs - Lector de .agents/stack.yaml (subconjunto de YAML, sin dependencias).
//
// Único punto del .agents que lee el archivo de parámetros del proyecto. Ningún otro script
// lee .agents/stack.yaml por su cuenta: importan este módulo o lo llaman por terminal.
//
// Subconjunto admitido:
//   - claves de primer nivel cuyo valor es un escalar (texto, número, true/false, null),
//     una lista de escalares ([a, b] o en bloque con `- `) o un mapa;
//   - los mapas solo contienen escalares o listas de escalares (máximo dos niveles);
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
const STACK = 'nextjs';

const REQUIRED = [
  'nomenclatura.controlador_interfaz', 'nomenclatura.controlador_implementacion', 'nomenclatura.servicio_interfaz', 'nomenclatura.servicio_implementacion', 'nomenclatura.repositorio_interfaz', 'nomenclatura.repositorio_implementacion', 'nomenclatura.modelo', 'nomenclatura.request', 'nomenclatura.response', 'nomenclatura.archivo_seccion_ui',
  'version_esquema', 'api_error.campo_mensaje', 'api_error.campo_codigo',
  'proyecto.nombre', 'proyecto.stack',
  'frontend.framework', 'frontend.version', 'frontend.gestor_paquetes', 'frontend.eslint_config',
  'frontend.notificaciones', 'frontend.llamadas_api',
  'sonarqube.project_key',
  'integraciones.autenticacion',
  'herramientas.codebase_memory', 'herramientas.agent_browser', 'git.rama_base',

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

function parsear(texto) {
  const raiz = {};
  let pendiente = null;   // { nombre, lista|mapa } de la clave de primer nivel aún sin valor
  const cerrar = () => {
    if (!pendiente) return;
    if (Object.keys(pendiente.mapa).length > 0) raiz[pendiente.nombre] = pendiente.mapa;
    else if (pendiente.lista.trim() !== '') {
      const items = pendiente.lista.split('\n').filter((l) => l.trim() !== '').map(escalar);
      if (items.some((x) => x !== null && typeof x === 'object')) {
        bloqueado(`\`${pendiente.nombre}\` es una lista con elementos no escalares`);
      }
      raiz[pendiente.nombre] = items;
    } else raiz[pendiente.nombre] = pendiente.mapa;
    pendiente = null;
  };
  for (const [i, cruda] of texto.split(/\r?\n/).entries()) {
    const linea = sinComentario(cruda);
    if (linea.trim() === '') continue;
    const recorte = linea.trimStart();
    // elemento de lista en bloque (solo en un nivel: `- <escalar>`)
    const mlista = recorte.match(/^-\s+(.*)$/);
    if (mlista) {
      if (!pendiente) bloqueado(`línea ${i + 1} es un elemento de lista pero la clave anterior no tiene lista`);
      pendiente.lista = pendiente.lista + '\n' + mlista[1];
      continue;
    }
    const m = recorte.match(/^([\w.-]+):\s*(.*)$/);
    if (!m) bloqueado(`línea ${i + 1} no respeta el formato: se admite \`clave: valor\`, \`clave:\` con mapa anidado, \`- item\` o comentario`);
    const clave = m[1];
    const valor = m[2].trim();
    if (linea === recorte) { // primer nivel
      cerrar();
      if (Object.hasOwn(raiz, clave)) bloqueado(`clave repetida ${clave} (línea ${i + 1})`);
      if (valor === '') { pendiente = { nombre: clave, lista: '', mapa: {} }; continue; }
      const lista = listaEnLinea(valor);
      if (lista) {
        if (lista.some((x) => x !== null && typeof x === 'object')) bloqueado(`\`${clave}\` es una lista con elementos no escalares`);
        raiz[clave] = lista;
      } else raiz[clave] = escalar(valor);
    } else { // nivel anidado (2.º y último)
      if (!pendiente) bloqueado(`línea ${i + 1} está sangrada pero la clave de primer nivel anterior ya cerró`);
      if (valor === '') bloqueado(`\`${clave}\` anida más de dos niveles o mezcla tipos`);
      if (Object.hasOwn(pendiente.mapa, clave)) bloqueado(`clave repetida ${clave} (línea ${i + 1})`);
      const lista = listaEnLinea(valor);
      if (lista) pendiente.mapa[clave] = lista;
      else {
        const esc = escalar(valor);
        if (esc !== null && typeof esc === 'object') bloqueado(`\`${clave}\` anida más de dos niveles o mezcla tipos`);
        pendiente.mapa[clave] = esc;
      }
    }
  }
  cerrar();
  return raiz;
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
  if (herramientas && typeof herramientas === 'object' && !Array.isArray(herramientas)) {
    if (!Object.hasOwn(herramientas, 'agent_browser')) herramientas.agent_browser = false;
    else if (typeof herramientas.agent_browser !== 'boolean') bloqueado('herramientas.agent_browser debe ser true o false');
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
  const modosApi = opciones?.['frontend.llamadas_api'];
  if (!Array.isArray(modosApi) || modosApi.length === 0) {
    bloqueado('config/opciones.yaml debe declarar los valores válidos de frontend.llamadas_api');
  }
  if (!modosApi.includes(obtener(data, 'frontend.llamadas_api'))) {
    bloqueado(`frontend.llamadas_api falta o tiene un valor inválido; valores válidos: ${modosApi.join(' | ')} (config/opciones.yaml)`);
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
    if (obtener(data, clave) === undefined) bloqueado(`falta la clave obligatoria ${clave}`);
  }
  const patrones = {"controlador_interfaz": "{Entidad}", "controlador_implementacion": "{Entidad}", "servicio_interfaz": "{Entidad}", "servicio_implementacion": "{Entidad}", "repositorio_interfaz": "{Entidad}", "repositorio_implementacion": "{Entidad}", "modelo": "{Entidad}", "request": "{Entidad}", "response": "{Entidad}", "archivo_seccion_ui": "{nombre}"};
  for (const [key, comodin] of Object.entries(patrones)) {
    const value = obtener(data, 'nomenclatura.' + key);
    if (typeof value !== 'string' || !value.includes(comodin)) bloqueado(`nomenclatura.${key} debe contener ${comodin}`);
  }
  if (obtener(data, 'integraciones.autenticacion') === 'clerk') {
    const variables = obtener(data, 'integraciones.variables_autenticacion');
    if (!Array.isArray(variables) || !variables.length || variables.some(n => typeof n !== 'string' || !/^[A-Z][A-Z0-9_]{0,63}$/.test(n) || /_test_|_live_|whsec_|=/.test(n))) {
      bloqueado('integraciones.variables_autenticacion debe contener solo NOMBRES con autenticacion clerk');
    }
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
  if (valor === undefined) bloqueado(`falta la clave ${clave}`);
  return valor;
}

export function validar(avisarRetirada = false) {
  const data = cargar();
  validarOpciones(data);
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
  const keys = ["integraciones.autenticacion", "integraciones.gestion_usuarios", "frontend.llamadas_api", "frontend.notificaciones", "frontend.gestor_paquetes", "nomenclatura.controlador_interfaz", "nomenclatura.controlador_implementacion", "nomenclatura.servicio_interfaz", "nomenclatura.servicio_implementacion", "nomenclatura.repositorio_interfaz", "nomenclatura.repositorio_implementacion", "nomenclatura.modelo", "nomenclatura.request", "nomenclatura.response", "nomenclatura.archivo_seccion_ui", "api_error.campo_mensaje", "api_error.campo_codigo"];
  return {stack: STACK, servicios: ['.'], gateway: null, valores: Object.fromEntries(keys.map(k => [k, obtener(data,k)]))};
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
