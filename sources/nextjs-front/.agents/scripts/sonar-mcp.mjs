#!/usr/bin/env node
// Cliente MCP de SonarQube: lista blanca local y una sola línea JSON por stdout.
// Resolver y transporte derivados del gate; revisar ambas copias al evolucionar el protocolo.
import { spawn, spawnSync, execFileSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const DIR = path.dirname(fileURLToPath(import.meta.url));
const MAX_INTENTOS_LECTURA = 3;
const USO = `uso: node .agents/scripts/sonar-mcp.mjs <herramienta> [--json '<objeto JSON>'] [--confirmar] | listar | ayuda`;
// Overrides exclusivamente para pruebas aisladas; no son parámetros del proyecto.
function tiempo(nombre, defecto) {
  const v = process.env[nombre];
  return v && /^[1-9][0-9]*$/.test(v) && Number.isSafeInteger(Number(v)) ? Number(v) : defecto;
}
const TIMEOUT_LLAMADA_MS = tiempo('SONAR_MCP_TEST_TIMEOUT_MS', 120000);
const ESPERA_REINTENTO_MS = tiempo('SONAR_MCP_TEST_ESPERA_MS', 5000);
let token = '';
let almacenamiento = null;
let servidor = '';
class Bloqueo extends Error {
  constructor(codigo, mensaje) { super(mensaje); this.codigo = codigo; }
}
class ErrorHerramienta extends Error {}
function bloquear(codigo, mensaje) { throw new Bloqueo(codigo, mensaje); }
function infra(mensaje) { bloquear('SONAR_SERVIDOR', mensaje); }
function nombreServidor() { return servidor; }
function crearAlmacenamiento() {
  almacenamiento = fs.mkdtempSync(path.join(os.tmpdir(), 'sonar-mcp-'));
  return almacenamiento;
}
// El lector de parámetros y git no reciben variables de conexión, tampoco en pruebas.
// El MCP recibe únicamente las variables de conexión resueltas, sobre ese entorno limpio.
function entornoBase() {
  return Object.fromEntries(Object.entries(process.env).filter(([k]) => !k.startsWith('SONARQUBE_')));
}
function argumentos(argv) {
  const herramienta = argv.shift();
  if (!herramienta || herramienta.startsWith('-')) bloquear('SONAR_ARGUMENTOS', 'Indica una herramienta o listar; ' + USO + '.');
  let datos = {}, confirmar = false, json = false;
  while (argv.length) {
    const a = argv.shift();
    if (a === '--confirmar' && !confirmar) confirmar = true;
    else if (a === '--json' && !json && argv.length) {
      json = true;
      try { datos = JSON.parse(argv.shift()); }
      catch { bloquear('SONAR_ARGUMENTOS', '--json requiere un objeto JSON válido; ' + USO + '.'); }
      if (!datos || typeof datos !== 'object' || Array.isArray(datos)) bloquear('SONAR_ARGUMENTOS', '--json requiere un objeto JSON; ' + USO + '.');
    } else if (a.startsWith('{')) bloquear('SONAR_ARGUMENTOS', "Los argumentos van con --json '<objeto>'; " + USO + '.');
    else bloquear('SONAR_ARGUMENTOS', 'Argumentos desconocidos, duplicados o incompletos; ' + USO + '.');
  }
  if (herramienta === 'listar' && (json || confirmar)) bloquear('SONAR_ARGUMENTOS', 'listar no admite opciones; ' + USO + '.');
  return { herramienta, datos, confirmar };
}
function listaBlanca() {
  try {
    const v = JSON.parse(fs.readFileSync(path.join(DIR, '../config/sonar-mcp.json'), 'utf8'));
    if (!v || typeof v !== 'object' || Object.keys(v).sort().join(',') !== 'escritura,lectura') throw new Error();
    if (![v.lectura, v.escritura].every((l) => Array.isArray(l) && l.every((n) => typeof n === 'string' && /^[a-z][a-z0-9_]*$/.test(n)))) throw new Error();
    const todas = [...v.lectura, ...v.escritura];
    if (!todas.length || new Set(todas).size !== todas.length) throw new Error();
    if (todas.includes('ayuda') || todas.includes('listar')) throw new Error();
    // Una configuración equivocada no puede convertir las escrituras conocidas en lecturas.
    if (v.lectura.some((n) => n.startsWith('change_'))) throw new Error();
    return { permitidas: new Set(todas), escritura: new Set(v.escritura) };
  } catch { bloquear('SONAR_LISTA_BLANCA', 'Lista blanca ausente o inválida: config/sonar-mcp.json.'); }
}
function leerServidor() {
  try {
    const root = execFileSync('git', ['rev-parse', '--show-toplevel'], { encoding: 'utf8', env: entornoBase(), stdio: ['ignore', 'pipe', 'ignore'] }).trim();
    process.chdir(root);
  } catch { bloquear('SONAR_REPOSITORIO', 'No se ejecuta dentro de un repositorio git.'); }
  const r = spawnSync(process.execPath, [path.join(DIR, 'stack.mjs'), 'get', 'mcp.sonarqube'], {
    env: entornoBase(), encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'], timeout: TIMEOUT_LLAMADA_MS,
  });
  if (r.error || r.status !== 0 || !r.stdout?.trim()) bloquear('SONAR_STACK', 'No se pudo leer mcp.sonarqube de .agents/stack.yaml; comprueba su formato y el nombre del servidor.');
  servidor = r.stdout.trim();
}
function hintInfraSonar(msg) {
  const t = String(msg ?? '');
  if (t.includes('Revisa el almacenamiento del MCP')) return t;
  if (/CancellationException|90028|MVStoreException/.test(t) || t.includes('el servidor MCP terminó')) {
    return t + ' Revisa el almacenamiento del MCP; ante 90028 o MVStoreException no ejecutes a la vez el MCP activo y el script si comparten STORAGE_PATH.';
  }
  return t;
}
function normalizar(e, formato) {
  if (!e || typeof e !== 'object') return null;
  if (formato === 'opencode') {
    if (!Array.isArray(e.command) || e.command.length === 0 || typeof e.command[0] !== 'string' || !e.command[0]) return null;
    const env = {};
    if (e.environment && typeof e.environment === 'object') {
      for (const [k, v] of Object.entries(e.environment)) if (typeof v === 'string') env[k] = v;
    }
    return { command: e.command[0], args: e.command.slice(1).map(String), env };
  }
  if (typeof e.command !== 'string' || !e.command) return null;
  const env = {};
  if (e.env && typeof e.env === 'object') {
    for (const [k, v] of Object.entries(e.env)) if (typeof v === 'string') env[k] = v;
  }
  return { command: e.command, args: Array.isArray(e.args) ? e.args.map(String) : [], env };
}

// Codex (~/.codex/config.toml): lector TOML mínimo, solo para las tablas del servidor MCP:
// `[mcp_servers.<nombre>]` (claves `command` y `args`: texto y listas de texto) y
// `[mcp_servers.<nombre>.env]` (valores de texto). Ignora el resto del archivo y cualquier
// otra sintaxis: si la hubiese, la búsqueda con Codex no resuelve y sigue el orden habitual.
function entradaToml(texto, nombre) {
  const quitarComentario = (linea) => {
    let s = '';
    let enCadena = false;
    for (let i = 0; i < linea.length; i++) {
      const c = linea[i];
      if (enCadena) {
        s += c;
        if (c === '\\' && i + 1 < linea.length) s += linea[++i];
        else if (c === '"') enCadena = false;
      } else if (c === '"') { enCadena = true; s += c; }
      else if (c === '#') break;
      else s += c;
    }
    return s;
  };
  const valor = (bruto) => {
    try {
      const v = JSON.parse(bruto.replace(/,\s*\]/g, ']'));      // tolera coma final en listas
      if (typeof v === 'string') return v;
      if (Array.isArray(v) && v.every((x) => typeof x === 'string')) return v;
    } catch { return null; }
    return null;
  };
  let en = null;
  const base = {};
  const entorno = {};
  for (const cruda of texto.split(/\r?\n/)) {
    const linea = quitarComentario(cruda).trim();
    if (!linea) continue;
    const mT = linea.match(/^\[\s*mcp_servers\.([A-Za-z0-9_-]+)\.env\s*\]$/);
    const mS = mT ? null : linea.match(/^\[\s*mcp_servers\.([A-Za-z0-9_-]+)\s*\]$/);
    if (mT) { en = `${mT[1]}.env`; continue; }
    if (mS) { en = mS[1]; continue; }
    if (en === null) continue;
    const m = linea.match(/^([A-Za-z0-9_-]+)\s*=\s*(.+?)\s*$/);
    if (!m) continue;
    const v = valor(m[2]);
    if (v === null) continue;
    if (en === nombre) {
      if (m[1] === 'command' || m[1] === 'args') base[m[1]] = v;
    } else if (en === `${nombre}.env` && typeof v === 'string') {
      entorno[m[1]] = v;
    }
  }
  if (typeof base.command !== 'string' || !base.command) return null;
  return normalizar({ command: base.command, args: base.args, env: entorno }, 'json');
}

// Archivos de las herramientas (gana el primero que exista y tenga el servidor buscado).
const FORMATOS_HERRAMIENTA = [
  { nombre: 'Claude Code', donde: 'mcpServers.<nombre> (y si no, projects.<repo>.mcpServers.<nombre>)',
    archivo: () => path.join(os.homedir(), '.claude.json'),
    entrar: (texto, nombre) => {
      let e = texto?.mcpServers?.[nombre];
      if (!e) {
        const proys = texto?.projects ?? {};
        if (proys[process.cwd()]?.mcpServers?.[nombre]) e = proys[process.cwd()].mcpServers[nombre];
        else {
          for (const cfg2 of Object.values(proys)) {
            if (cfg2 && typeof cfg2 === 'object' && cfg2.mcpServers?.[nombre]) { e = cfg2.mcpServers[nombre]; break; }
          }
        }
      }
      return normalizar(e, 'json');
    } },
  { nombre: 'Gemini CLI', donde: 'mcpServers.<nombre>', archivo: () => path.join(os.homedir(), '.gemini', 'config', 'mcp_config.json'),
    entrar: (texto, nombre) => normalizar(texto?.mcpServers?.[nombre], 'json') },
  { nombre: 'Antigravity', donde: 'mcpServers.<nombre>', archivo: () => path.join(os.homedir(), '.gemini', 'antigravity', 'mcp_config.json'),
    entrar: (texto, nombre) => normalizar(texto?.mcpServers?.[nombre], 'json') },
  { nombre: 'OpenCode', donde: 'mcp.<nombre>', archivo: () => path.join(os.homedir(), '.config', 'opencode', 'opencode.json'),
    entrar: (texto, nombre) => normalizar(texto?.mcp?.[nombre], 'opencode') },
  { nombre: 'VS Code', donde: 'servers.<nombre>', archivo: () => path.join(os.homedir(), '.config', 'Code', 'User', 'mcp.json'),
    entrar: (texto, nombre) => normalizar(texto?.servers?.[nombre], 'json') },
  { nombre: 'Codex', donde: 'mcp_servers.<nombre> (y su tabla .env)', archivo: () => path.join(os.homedir(), '.codex', 'config.toml'),
    entrar: entradaToml },
];

function resolverServidor() {
  const nombre = nombreServidor();
  const env = process.env;
  if (env.SONARQUBE_MCP_JAR && env.SONARQUBE_URL && env.SONARQUBE_TOKEN) {
    return {
      command: 'java',
      args: ['-jar', env.SONARQUBE_MCP_JAR],
      env: {
        SONARQUBE_URL: env.SONARQUBE_URL,
        SONARQUBE_TOKEN: env.SONARQUBE_TOKEN,
        STORAGE_PATH: env.SONARQUBE_STORAGE_PATH ?? crearAlmacenamiento(),
      },
      servidor: nombre,
      origen: 'variables de entorno (SONARQUBE_MCP_JAR + SONARQUBE_URL + SONARQUBE_TOKEN)',
    };
  }
  if (env.SONARQUBE_MCP_CONFIG) {
    try {
      const json = JSON.parse(fs.readFileSync(env.SONARQUBE_MCP_CONFIG, 'utf8'));
      const e = normalizar(json?.mcpServers?.[nombre], 'json');
      if (e) return { ...e, servidor: nombre, origen: `SONARQUBE_MCP_CONFIG (${env.SONARQUBE_MCP_CONFIG}) > mcpServers.${nombre}` };
    } catch { /* sin entrada válida se sigue con los archivos de las herramientas */ }
  }
  const revisados = [];
  for (const f of FORMATOS_HERRAMIENTA) {
    const ruta = f.archivo();
    if (!fs.existsSync(ruta)) continue;
    revisados.push(ruta);
    try {
      let datos = fs.readFileSync(ruta, 'utf8');
      if (ruta.endsWith('.json')) datos = JSON.parse(datos);
      const e = f.entrar(datos, nombre);
      if (e) return { ...e, servidor: nombre, origen: `${f.nombre} (${ruta}) > ${f.donde.replace('<nombre>', nombre)}` };
    } catch { /* ilegible o con formato no esperado: se sigue con el archivo siguiente */ }
  }
  const lista = revisados.length
    ? revisados.join(', ')
    : 'ninguno existe: ' + FORMATOS_HERRAMIENTA.map((f) => f.archivo()).join(', ');
  infra(`no se encontró el servidor MCP de SonarQube '${nombre}' (valor de mcp.sonarqube de .agents/stack.yaml). Archivos revisados: ${lista}. Alternativas: registra el servidor ${nombre} en alguno de esos archivos, deja un JSON con la entrada mcpServers.${nombre} apuntado por SONARQUBE_MCP_CONFIG, o fija las variables SONARQUBE_MCP_JAR + SONARQUBE_URL + SONARQUBE_TOKEN. No se imprime el contenido de esos archivos.`);
  return null;   // no se llega: infra termina el proceso
}


class ClienteMcp {
  constructor(cfg) {
    this.cfg = cfg;
    this.id = 0;
    this.pend = new Map();
    this.buffer = '';
    this.terminal = null;
    this.hijo = null;
    this.esperas = new Set();
  }
  terminar(error) {
    this.terminal ??= error;
    for (const p of this.pend.values()) { clearTimeout(p.timer); p.reject(this.terminal); }
    this.pend.clear();
    for (const p of this.esperas) { clearTimeout(p.timer); p.reject(this.terminal); }
    this.esperas.clear();
  }
  async iniciar() {
    try {
      this.hijo = spawn(this.cfg.command, this.cfg.args, {
        env: { ...entornoBase(), ...this.cfg.env }, stdio: ['pipe', 'pipe', 'ignore'],
      });
    } catch { bloquear('SONAR_ARRANQUE', 'No se pudo arrancar el servidor MCP.'); }
    this.hijo.on('error', () => this.terminar(new Bloqueo('SONAR_ARRANQUE', 'No se pudo arrancar el servidor MCP.')));
    this.hijo.stdin.on('error', () => this.terminar(new Bloqueo('SONAR_SALIDA', hintInfraSonar('el servidor MCP terminó o cerró su entrada.'))));
    this.hijo.on('exit', () => this.terminar(new Bloqueo('SONAR_SALIDA', hintInfraSonar('el servidor MCP terminó.'))));
    this.hijo.stdout.on('data', (d) => this.alRecibir(d));
    await this.pedir('initialize', {
      protocolVersion: '2025-06-18', capabilities: {}, clientInfo: { name: 'sonar-mcp', version: '1' },
    });
    this.enviar({ jsonrpc: '2.0', method: 'notifications/initialized', params: {} });
  }
  alRecibir(chunk) {
    this.buffer += chunk.toString('utf8');
    let i;
    while ((i = this.buffer.indexOf('\n')) >= 0) {
      const linea = this.buffer.slice(0, i).trim();
      this.buffer = this.buffer.slice(i + 1);
      if (!linea) continue;
      let msg;
      try { msg = JSON.parse(linea); } catch { continue; }
      const p = this.pend.get(msg?.id);
      if (!p) continue;
      this.pend.delete(msg.id);
      clearTimeout(p.timer);
      if (msg.error) p.reject(new ErrorHerramienta(String(msg.error.message ?? 'Error JSON-RPC.')));
      else p.resolve(msg.result);
    }
  }
  enviar(obj) {
    if (this.terminal) throw this.terminal;
    this.hijo.stdin.write(JSON.stringify(obj) + '\n');
  }
  pedir(method, params) {
    if (this.terminal) return Promise.reject(this.terminal);
    return new Promise((resolve, reject) => {
      const id = ++this.id;
      const timer = setTimeout(() => {
        this.pend.delete(id);
        reject(new Bloqueo('SONAR_TIEMPO', `Tiempo agotado esperando ${method}.`));
      }, TIMEOUT_LLAMADA_MS);
      this.pend.set(id, { resolve, reject, timer });
      try { this.enviar({ jsonrpc: '2.0', id, method, params }); }
      catch (e) { clearTimeout(timer); this.pend.delete(id); reject(e); }
    });
  }
  esperar() {
    if (this.terminal) return Promise.reject(this.terminal);
    return new Promise((resolve, reject) => {
      const p = { reject, timer: null };
      p.timer = setTimeout(() => { this.esperas.delete(p); resolve(); }, ESPERA_REINTENTO_MS);
      this.esperas.add(p);
    });
  }
  async llamar(method, params, escritura) {
    for (let intento = 1; ; intento++) {
      try {
        const res = await this.pedir(method, params);
        if (res?.isError) throw new ErrorHerramienta((res.content ?? []).map((c) => c.text ?? '').join('\n') || 'La herramienta devolvió error.');
        return res;
      } catch (e) {
        if (escritura && e.codigo === 'SONAR_TIEMPO') {
          e.message += ' La escritura pudo aplicarse; comprueba su estado antes de repetir.';
        }
        if (this.terminal) throw this.terminal;
        if (escritura || e.codigo !== 'SONAR_TIEMPO' || intento >= MAX_INTENTOS_LECTURA) throw e;
        await this.esperar();
      }
    }
  }
  cerrar() {
    this.terminar(new Bloqueo('SONAR_SALIDA', 'Cliente cerrado.'));
    try { this.hijo?.stdin.end(); this.hijo?.kill(); } catch { /* ya terminó */ }
  }
}
function limpiar(serializado) {
  if (!token) return serializado;
  const formas = new Set([JSON.stringify(token).slice(1, -1), token]);
  // Primero las representaciones más largas para no dejar fragmentos de una forma escapada.
  let s = serializado;
  for (const forma of [...formas].sort((a, b) => b.length - a.length)) s = s.split(forma).join('***');
  return s;
}
function salidaOk(herramienta, resultado) {
  const serializado = limpiar(JSON.stringify(resultado));
  if (serializado.length > 20000) {
    return { estado: 'ok', herramienta, resultado_truncado: serializado.slice(0, 20000), truncado: true,
      aviso: 'Resultado truncado; usa pageIndex/pageSize de la herramienta cuando su esquema los admita.' };
  }
  return { estado: 'ok', herramienta, resultado: JSON.parse(serializado) };
}
async function main() {
  let mcp, herramienta;
  let salida, code = 0;
  try {
    const argv = process.argv.slice(2);
    if (argv[0] === 'ayuda' || argv[0] === '--help' || argv[0] === '-h') {
      if (argv.length !== 1) bloquear('SONAR_ARGUMENTOS', 'ayuda no admite opciones; ' + USO + '.');
      salida = { estado: 'ok', herramienta: 'ayuda', uso: USO,
        nota: 'listar muestra las herramientas permitidas y sus parámetros; las de escritura exigen --confirmar y aprobación explícita del usuario.' };
    } else {
      const args = argumentos(argv);
      herramienta = args.herramienta;
      const lista = listaBlanca();
      if (herramienta !== 'listar' && !lista.permitidas.has(herramienta)) bloquear('SONAR_NO_PERMITIDA', 'Herramienta fuera de la lista blanca.');
      const escritura = lista.escritura.has(herramienta);
      if (escritura && !args.confirmar) bloquear('SONAR_APROBACION', 'Escritura: requiere aprobación explícita del usuario y --confirmar.');
      leerServidor();
      const cfg = resolverServidor();
      token = cfg.env?.SONARQUBE_TOKEN ?? '';
      if (!cfg.env?.SONARQUBE_URL) bloquear('SONAR_SERVIDOR', 'La configuración del servidor no define SONARQUBE_URL.');
      mcp = new ClienteMcp(cfg);
      await mcp.iniciar();
      let resultado;
      if (herramienta === 'listar') {
        const tools = [], cursores = new Set();
        let cursor;
        do {
          const pagina = await mcp.llamar('tools/list', cursor === undefined ? {} : { cursor }, false);
          if (!Array.isArray(pagina?.tools)) bloquear('SONAR_PROTOCOLO', 'tools/list no devolvió una lista de herramientas.');
          tools.push(...pagina.tools.filter((t) => lista.permitidas.has(t.name)));
          cursor = pagina.nextCursor;
          if (cursor !== undefined && cursor !== null && cursor !== '') {
            if (typeof cursor !== 'string' || cursores.has(cursor)) bloquear('SONAR_PROTOCOLO', 'Cursor inválido o repetido en tools/list.');
            cursores.add(cursor);
          }
        } while (cursor !== undefined && cursor !== null && cursor !== '');
        resultado = { tools };
      } else {
        const res = await mcp.llamar('tools/call', { name: herramienta, arguments: args.datos }, escritura);
        const texto = (res?.content ?? []).map((c) => c.text ?? '').join('\n');
        if (res && Object.hasOwn(res, 'structuredContent')) resultado = res.structuredContent;
        else { try { resultado = JSON.parse(texto); } catch { resultado = { texto }; } }
      }
      salida = salidaOk(herramienta, resultado);
    }
  } catch (e) {
    if (e instanceof ErrorHerramienta) {
      salida = { estado: 'error', herramienta, error: hintInfraSonar(e.message) }; code = 1;
    } else {
      salida = { estado: 'bloqueado', codigo: e.codigo ?? 'SONAR_INFRAESTRUCTURA',
        mensaje: hintInfraSonar(e instanceof Bloqueo ? e.message : 'Fallo de infraestructura del cliente.') + ' Código propio de sonar-mcp.mjs; no del preflight.' }; code = 2;
    }
  } finally {
    mcp?.cerrar();
    if (almacenamiento) {
      try { fs.rmSync(almacenamiento, { recursive: true, force: true }); }
      catch { salida = { estado: 'bloqueado', codigo: 'SONAR_ALMACENAMIENTO', mensaje: 'No se pudo borrar el almacenamiento temporal. Código propio del cliente; no del preflight.' }; code = 2; }
    }
  }
  process.stdout.write(limpiar(JSON.stringify(salida)) + '\n');
  process.exitCode = code;
}
await main();
