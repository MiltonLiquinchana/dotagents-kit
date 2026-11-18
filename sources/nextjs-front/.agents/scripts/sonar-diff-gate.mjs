#!/usr/bin/env node
// ==============================================================================
// sonar-diff-gate.mjs - Gate diferencial de SonarQube (frontend), ejecutable.
//
// Implementa el algoritmo de .agents/skills/code-reviewer/references/sonarqube-gate.md ("Capa 2") para que el
// revisor no tenga que hacer a mano las llamadas A y B de cada fichero:
//   - lee la lista de touched-files.sh,
//   - arranca el servidor MCP de SonarQube como subproceso (stdio) y llama a su herramienta
//     analyze_code_snippet sobre la versión base (A) y la actual (B) de cada fichero,
//   - compara por clave (ruleKey, mensaje normalizado) con multiplicidad (B - A),
//   - bloquea ante cualquier issue nuevo, de cualquier severidad.
//
// Uso:
//   node .agents/scripts/sonar-diff-gate.mjs            Gate diferencial (JSON por stdout)
//   node .agents/scripts/sonar-diff-gate.mjs --canary   Canario del Paso 0 + proyecto registrado
//   node .agents/scripts/sonar-diff-gate.mjs --comprobar-recibo <ruta> [--base <ref>]
//   Opciones: --explain, --base <ref>, --resolver-config, --registrar-proyecto <projectKey>, --recibo <ruta>
//
// Códigos de salida: 0 = PASA, 1 = BLOQUEA (hay issues nuevos), 2 = BLOCKED (infraestructura).
//
// Servidor propio del kit: Java del PATH y jar instalado por instalar-sonar-mcp.mjs.
// URL y token solo por SONARQUBE_URL y SONARQUBE_TOKEN. Jar y storage opcionales
// por SONARQUBE_MCP_JAR y SONARQUBE_STORAGE_PATH; por defecto storage exclusivo.
// --resolver-config imprime únicamente nombres de orígenes y versión mayor de Java.
// Cualquier aparición del token en un mensaje de error se sustituye por ***.
// ==============================================================================
import { spawn, spawnSync, execFileSync } from 'node:child_process';
import crypto from 'node:crypto';
import fs from 'node:fs';
import { resolverServidor, cerrarServidor } from './sonar-servidor.mjs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { get as stackGet } from './stack.mjs';

// ---- Configuración propia de este repositorio (única parte que difiere del backend) ----
const CONFIG = {
  exclusiones: new Set([]),                       // reglas descartadas de A y B (ver el .md)
  canario: {
    fichero: '.agents/skills/code-reviewer/fixtures/canary-eval.ts',
    language: 'ts',
    regla: 'typescript:S1523',
    exigeProyecto: true,                          // el canario se analiza con projectKey
    impactsContiene: null,                        // texto que debe aparecer en `impacts`, o null
  },
  // projectKey de un fichero tocado: `sonarqube.project_key` del .agents/stack.yaml, si existe
  // en el servidor; si no, null (se omite)
  projectKeyDe: (_fichero, proyectos) => {
    const k = stackGet('sonarqube.project_key');
    return k && proyectos.has(k) ? k : null;
  },
  // projectKey para el canario (se exige que exista)
  projectKeyCanario: () => stackGet('sonarqube.project_key'),
  languageDe: (fichero) => fichero.language,
};

const CACHE_DIR = '.agents/.cache/sonar-base';
const REINTENTOS = 3;
const ESPERA_REINTENTO_MS = 5000;
const TIMEOUT_LLAMADA_MS = 120000;

// ---- Utilidades --------------------------------------------------------------------
let TOKEN_A_OCULTAR = '';
const limpiar = (t) => {
  let s = String(t ?? '');
  if (TOKEN_A_OCULTAR) s = s.split(TOKEN_A_OCULTAR).join('***');
  return s;
};

function infra(msg) {
  process.stderr.write(`BLOCKED (infraestructura): ${limpiar(msg)}\n`);
  limpiarYSalir(2);
}

let hijo = null, configuracion = null;
class Salida extends Error { constructor(code) { super('Fin del gate'); this.code = code; } }
function limpiarYSalir(code) { throw new Salida(code); }
async function cerrar() {
  await cerrarServidor(hijo);
  configuracion?.liberar();
}

const dormir = (ms) => new Promise((r) => setTimeout(r, ms));

// ---- Cliente MCP por stdio ---------------------------------------------------------
class ClienteMcp {
  constructor(cfg) {
    this.cfg = cfg;
    this.id = 0;
    this.pend = new Map();
    this.buffer = '';
  }

  async iniciar() {
    hijo = spawn(this.cfg.command, this.cfg.args, {
      env: { ...process.env, ...this.cfg.env },
      stdio: ['pipe', 'pipe', 'ignore'],
    });
    hijo.once('close', () => { hijo._sonarCerrado = true; });
    hijo.on('error', () => {
      for (const p of this.pend.values()) { clearTimeout(p.timer); p.reject(new Error('No se pudo arrancar el servidor MCP.')); }
      this.pend.clear();
    });
    hijo.stdin.on('error', () => { /* el proceso terminó: el rechazo llega por 'exit' */ });
    hijo.on('exit', (code) => {
      for (const { reject, timer } of this.pend.values()) { clearTimeout(timer); reject(new Error(hintInfraSonar(`el servidor MCP terminó (código ${code})`))); }
      this.pend.clear();
    });
    hijo.stdout.on('data', (d) => this.alRecibir(d));
    const init = await this.pedir('initialize', {
      protocolVersion: '2025-06-18', capabilities: {}, clientInfo: { name: 'sonar-diff-gate', version: '1' },
    });
    this.versionJar = init?.serverInfo?.version ?? 'desconocida';
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
      try { msg = JSON.parse(linea); } catch { continue; }        // ruido que no es JSON-RPC
      const p = this.pend.get(msg.id);
      if (!p) continue;
      this.pend.delete(msg.id);
      clearTimeout(p.timer);
      if (msg.error) p.reject(new Error(msg.error.message ?? 'error JSON-RPC'));
      else p.resolve(msg.result);
    }
  }

  enviar(obj) { hijo.stdin.write(JSON.stringify(obj) + '\n'); }

  pedir(method, params) {
    return new Promise((resolve, reject) => {
      const id = ++this.id;
      const timer = setTimeout(() => {
        this.pend.delete(id);
        reject(new Error(`tiempo agotado esperando '${method}' (${TIMEOUT_LLAMADA_MS / 1000}s)`));
      }, TIMEOUT_LLAMADA_MS);
      this.pend.set(id, { resolve, reject, timer });
      this.enviar({ jsonrpc: '2.0', id, method, params });
    });
  }

  // Llama a una herramienta con reintentos: los analizadores se descargan en segundo plano al arrancar.
  async herramienta(nombre, argumentos) {
    let ultimo;
    for (let intento = 1; intento <= REINTENTOS; intento++) {
      try {
        const res = await this.pedir('tools/call', { name: nombre, arguments: argumentos });
        const texto = (res?.content ?? []).map((c) => c.text ?? '').join('\n');
        if (res?.isError) throw new Error(texto || 'la herramienta devolvió error');
        if (res?.structuredContent) return res.structuredContent;
        try { return JSON.parse(texto); } catch { return { texto }; }
      } catch (e) {
    if (e instanceof Salida) throw e;
        ultimo = e;
        if (intento < REINTENTOS) await dormir(ESPERA_REINTENTO_MS);
      }
    }
    throw ultimo;
  }
}

// ---- Algoritmo diferencial ---------------------------------------------------------
const clave = (i) => `${i.ruleKey}\u0000${String(i.primaryMessage ?? '').replace(/"[^"]*"/g, '"_"')}`;

function contar(issues) {
  const m = new Map();
  for (const i of issues) {
    if (CONFIG.exclusiones.has(i.ruleKey)) continue;
    const k = clave(i);
    m.set(k, (m.get(k) ?? 0) + 1);
  }
  return m;
}

function restar(a, b) {
  const out = new Map();
  for (const [k, n] of a) {
    const d = n - (b.get(k) ?? 0);
    if (d > 0) out.set(k, d);
  }
  return out;
}

const total = (m) => [...m.values()].reduce((s, n) => s + n, 0);

async function versionServidor(url) {
  try {
    const r = await fetch(`${url.replace(/\/$/, '')}/api/system/status`, { signal: AbortSignal.timeout(5000) });
    return (await r.json()).version ?? 'desconocida';
  } catch { return 'desconocida'; }
}

async function registrarProyecto(cfg, projectKey) {
  if (!/^[A-Za-z0-9_.:-]+$/.test(projectKey)) infra('projectKey inválido.');
  const url = cfg.env?.SONARQUBE_URL;
  const token = cfg.env?.SONARQUBE_TOKEN;
  if (!url || !token) infra('la configuración resuelta no contiene URL y token de SonarQube.');
  TOKEN_A_OCULTAR = token;
  const auth = `Basic ${Buffer.from(`${token}:`).toString('base64')}`;
  const base = url.replace(/\/$/, '');
  try {
    const search = await fetch(`${base}/api/projects/search?projects=${encodeURIComponent(projectKey)}`, {
      headers: { Authorization: auth }, signal: AbortSignal.timeout(10000),
    });
    if (!search.ok) infra(`no se pudo consultar el proyecto: HTTP ${search.status}.`);
    const data = await search.json();
    if ((data.components ?? []).some((p) => p.key === projectKey)) {
      process.stdout.write(`proyecto ya existía (HTTP ${search.status}).\n`);
      limpiarYSalir(0);
    }
    const body = new URLSearchParams({ name: projectKey, project: projectKey, visibility: 'private' });
    const created = await fetch(`${base}/api/projects/create`, {
      method: 'POST', headers: { Authorization: auth, 'Content-Type': 'application/x-www-form-urlencoded' },
      body, signal: AbortSignal.timeout(10000),
    });
    if (!created.ok) infra(`no se pudo crear el proyecto: HTTP ${created.status}.`);
    process.stdout.write(`proyecto privado creado (HTTP ${created.status}).\n`);
    limpiarYSalir(0);
  } catch (e) {
    if (e instanceof Salida) throw e;
    if (e?.message?.startsWith('BLOCKED')) throw e;
    infra(`no se pudo registrar el proyecto: sin respuesta HTTP (${e.name ?? 'Error'}).`);
  }
}

function cacheDir() {
  const r = spawnSync('bash', ['.agents/scripts/touched-files.sh', '--ensure-cache'], { encoding: 'utf8' });
  return r.status === 0 ? r.stdout.trim() : null;
}

function claveCache(parts) {
  return crypto.createHash('sha256').update(parts.join('|')).digest('hex').slice(0, 20);
}


function hintInfraSonar(msg) {
  const t = String(msg ?? '');
  const early = t.includes('el servidor MCP terminó');
  if (t.includes('CancellationException') || early) {
    return t + ' el servidor MCP de SonarQube no pudo iniciar su análisis; revisa <SONARQUBE_STORAGE_PATH o la carpeta de almacenamiento del MCP>/logs/mcp.log; si muestra `90028` o `MVStoreException` en `h2/sq-ide.mv.db`, si defines SONARQUBE_STORAGE_PATH compartida, evita usarla a la vez desde varios procesos y vuelve a intentarlo.';
  }
  return t;
}

function sha256Archivo(ruta) {
  return crypto.createHash('sha256').update(fs.readFileSync(ruta)).digest('hex');
}

function leerFicherosTocados(opciones) {
  const args = ['.agents/scripts/touched-files.sh'];
  if (opciones.base) args.push('--base', opciones.base);
  const t = spawnSync('bash', args, { encoding: 'utf8' });
  if (t.status !== 0) throw new Error('touched-files.sh no pudo seleccionar los ficheros tocados');
  let ficheros;
  try { ficheros = JSON.parse(t.stdout); } catch { throw new Error('la salida de touched-files.sh no es JSON'); }
  if (!Array.isArray(ficheros)) throw new Error('touched-files.sh no devolvió una lista');
  return { ficheros, diagnostico: t.stderr ?? '' };
}

function escribirRecibo(rutaRecibo, code, base, ficheros) {
  if (!rutaRecibo || (code !== 0 && code !== 1)) return;
  const archivos = ficheros.map((f) => ({ ruta: f.ruta, sha256: sha256Archivo(f.ruta) }));
  const recibo = { exit: code, fecha: new Date().toISOString(), base: base || null, archivos };
  fs.writeFileSync(rutaRecibo, JSON.stringify(recibo, null, 2) + '\n');
}

function comprobarRecibo(rutaRecibo, baseOverride) {
  let recibo;
  try {
    recibo = JSON.parse(fs.readFileSync(rutaRecibo, 'utf8'));
  } catch {
    process.stderr.write('recibo ausente o ilegible\n');
    return 2;
  }
  if (!recibo || !Array.isArray(recibo.archivos) || typeof recibo.exit !== 'number') {
    process.stderr.write('recibo ausente o ilegible\n');
    return 2;
  }
  const base = baseOverride ?? (recibo.base ? String(recibo.base).split(' ')[0] : null);
  let seleccion;
  try {
    seleccion = leerFicherosTocados({ base });
  } catch (e) {
    if (e instanceof Salida) throw e;
    process.stderr.write(`recibo no verificable: ${e.message}\n`);
    return 1;
  }
  const actuales = new Map();
  for (const f of seleccion.ficheros) actuales.set(f.ruta, sha256Archivo(f.ruta));
  const esperados = new Map(recibo.archivos.map((a) => [a.ruta, a.sha256]));
  const diffs = [];
  for (const [ruta, sha] of esperados) {
    if (!actuales.has(ruta)) diffs.push(`falta: ${ruta}`);
    else if (actuales.get(ruta) !== sha) diffs.push(`cambiado: ${ruta}`);
  }
  for (const ruta of actuales.keys()) {
    if (!esperados.has(ruta)) diffs.push(`nuevo: ${ruta}`);
  }
  if (recibo.exit !== 0) diffs.unshift(`exit_recibo: ${recibo.exit}`);
  if (diffs.length === 0) {
    process.stdout.write(JSON.stringify({ ok: true, base }, null, 2) + '\n');
    return 0;
  }
  process.stdout.write(JSON.stringify({ ok: false, base, diferencias: diffs }, null, 2) + '\n');
  return 1;
}

// ---- Modos -------------------------------------------------------------------------
async function modoCanario(mcp, projectKeys) {
  const c = CONFIG.canario;
  const projectKey = c.exigeProyecto ? CONFIG.projectKeyCanario() : null;
  if (c.exigeProyecto) {
    if (!projectKey || !projectKeys.has(projectKey)) {
      infra(`el proyecto '${projectKey}' no existe en SonarQube. Solicita permiso y, tras aprobación, ejecuta ` +
        `node .agents/scripts/sonar-diff-gate.mjs --registrar-proyecto ${projectKey}.`);
    }
  }
  const contenido = fs.readFileSync(c.fichero, 'utf8');
  const args = { fileContent: contenido, language: c.language, scope: 'MAIN' };
  if (c.exigeProyecto) args.projectKey = projectKey;
  const res = await mcp.herramienta('analyze_code_snippet', args);
  const hallazgo = (res.issues ?? []).find((i) => i.ruleKey === c.regla);
  if (!hallazgo) infra(`regla canario ${c.regla} no detectada (el MCP responde pero la regla no aparece).`);
  if (c.impactsContiene && !String(hallazgo.impacts ?? '').includes(c.impactsContiene)) {
    infra(`regla canario ${c.regla} detectada pero sin ${c.impactsContiene} en impacts (${hallazgo.impacts}).`);
  }
  process.stdout.write(JSON.stringify({ canario: 'OK', regla: c.regla, impacts: hallazgo.impacts ?? null, proyecto: projectKey ?? 'omitido' }, null, 2) + '\n');
  process.stderr.write(`sonar-diff-gate: canario OK (${c.regla}).\n`);
  limpiarYSalir(0);
}

async function modoGate(mcp, projectKeys, opciones, versionSrv) {
  const args = ['.agents/scripts/touched-files.sh'];
  if (opciones.base) args.push('--base', opciones.base);
  const t = spawnSync('bash', args, { encoding: 'utf8' });
  if (t.status !== 0) infra(`touched-files.sh terminó con código ${t.status}: ${t.stderr.trim()}`);
  let ficheros;
  try { ficheros = JSON.parse(t.stdout); } catch { infra('la salida de touched-files.sh no es JSON.'); }
  const base = (t.stderr.match(/BASE=(\S+) \(([^)]*)\)/) ?? []).slice(1, 3).join(' ');

  const dirCache = cacheDir();
  const resumen = [];
  const reglas = new Map();
  let llamadas = 0;
  let aciertos = 0;
  const proyectosUsados = new Set();
  const clavesReales = new Set();

  const analizar = async (contenido, scope, language, pk) => {
    const a = { fileContent: contenido, language, scope };
    if (pk) a.projectKey = pk;
    llamadas++;
    return (await mcp.herramienta('analyze_code_snippet', a)).issues ?? [];
  };

  for (const f of ficheros) {
    const language = CONFIG.languageDe(f);
    const pk = CONFIG.projectKeyDe(f, projectKeys);
    proyectosUsados.add(pk ?? 'omitido (sin proyecto Sonar)');
    if (pk) clavesReales.add(pk);
    let issuesA = [];
    let estadoCache = '-';
    if (f.estado !== 'nuevo') {
      const fuente = execFileSync('git', ['cat-file', '-p', f.blobBase], { encoding: 'utf8', maxBuffer: 64 * 1024 * 1024 });
      const archivo = dirCache
        ? path.join(dirCache, claveCache([f.blobBase, f.scope, language, pk ?? '-', versionSrv, mcp.versionJar]) + '.json')
        : null;
      if (archivo && fs.existsSync(archivo)) {
        issuesA = JSON.parse(fs.readFileSync(archivo, 'utf8'));
        estadoCache = 'HIT';
        aciertos++;
      } else {
        issuesA = await analizar(fuente, f.scope, language, pk);
        estadoCache = 'MISS';
        if (archivo) fs.writeFileSync(archivo, JSON.stringify(issuesA));
      }
    }
    const issuesB = await analizar(fs.readFileSync(f.ruta, 'utf8'), f.scope, language, pk);
    const A = contar(issuesA);
    const B = contar(issuesB);
    const nuevos = restar(B, A);
    const resueltos = restar(A, B);

    const detalleNuevos = [];
    for (const [k, n] of nuevos) {
      const [ruleKey, mensaje] = k.split('\u0000');
      const origen = issuesB.filter((i) => clave(i) === k);
      const muestra = origen[origen.length - 1] ?? {};
      detalleNuevos.push({
        ruleKey, mensaje, mas: n, impacts: muestra.impacts ?? null, severity: muestra.severity ?? null,
        lineas: origen.map((i) => i.textRange?.startLine ?? null).filter((x) => x !== null),
      });
      const r = reglas.get(ruleKey) ?? { ruleKey, antes: 0, ahora: 0, mas: 0 };
      r.antes += [...A].filter(([kk]) => kk.startsWith(ruleKey + '\u0000')).reduce((s, [, c]) => s + c, 0);
      r.ahora += [...B].filter(([kk]) => kk.startsWith(ruleKey + '\u0000')).reduce((s, [, c]) => s + c, 0);
      r.mas += n;
      reglas.set(ruleKey, r);
    }
    resumen.push({
      ruta: f.ruta, rutaBase: f.rutaBase, estado: f.estado, scope: f.scope, language, projectKey: pk ?? 'omitido',
      A: total(A), B: total(B), cache: estadoCache,
      nuevos: detalleNuevos,
      resueltos: [...resueltos].map(([k, n]) => ({ ruleKey: k.split('\u0000')[0], mensaje: k.split('\u0000')[1], menos: n })),
    });
  }

  let explicaciones = {};
  if (opciones.explain) {
    for (const ruleKey of reglas.keys()) {
      try {
        const r = await mcp.herramienta('show_rule', { key: ruleKey });
        explicaciones[ruleKey] = String(r.texto ?? JSON.stringify(r)).replace(/\s+/g, ' ').slice(0, 400);
      } catch (e) {
    if (e instanceof Salida) throw e;
        explicaciones[ruleKey] = `no disponible: ${limpiar(e.message)}`;
      }
    }
  }

  // Quality Gate del servidor: solo informativo (no sustituye al diferencial)
  const qualityGate = {};
  for (const pk of clavesReales) {
    try {
      const r = await mcp.herramienta('get_project_quality_gate_status', { projectKey: pk });
      qualityGate[pk] = r.status ?? 'desconocido';
    } catch (e) {
    if (e instanceof Salida) throw e;
      qualityGate[pk] = `no disponible: ${limpiar(e.message)}`;
    }
  }

  const bloquea = reglas.size > 0;
  const salida = {
    base, proyectos: [...proyectosUsados], servidor: versionSrv, jar: mcp.versionJar,
    archivos: resumen,
    reglasNuevas: [...reglas.values()],
    ...(opciones.explain ? { explicaciones } : {}),
    qualityGate: Object.keys(qualityGate).length ? qualityGate : 'N/A (sin proyecto Sonar)',
    llamadas, aciertosCache: aciertos,
    veredicto: bloquea ? 'BLOQUEA' : 'PASA',
  };
  process.stdout.write(JSON.stringify(salida, null, 2) + '\n');
  const exitCode = bloquea ? 1 : 0;
  try { escribirRecibo(opciones.recibo, exitCode, opciones.base ?? (base.split(' ')[0] || null), ficheros); } catch (e) {
    if (e instanceof Salida) throw e;
    infra(`no se pudo escribir el recibo: ${e.message}`);
  }
  process.stderr.write(`sonar-diff-gate: ${salida.veredicto} (${ficheros.length} fichero(s), ${llamadas} llamada(s), ${aciertos} acierto(s) de caché).\n`);
  limpiarYSalir(exitCode);
}

// ---- Entrada -----------------------------------------------------------------------
async function main() {
const opciones = { canary: false, explain: false, base: null, resolverConfig: false, registrarProyecto: null, recibo: null, comprobarRecibo: null };
const argv = process.argv.slice(2);
for (let i = 0; i < argv.length; i++) {
  if (argv[i] === '--canary') opciones.canary = true;
  else if (argv[i] === '--explain') opciones.explain = true;
  else if (argv[i] === '--base') opciones.base = argv[++i];
  else if (argv[i] === '--resolver-config') opciones.resolverConfig = true;
  else if (argv[i] === '--registrar-proyecto') {
    opciones.registrarProyecto = argv[++i];
    if (!opciones.registrarProyecto) infra('--registrar-proyecto requiere un projectKey.');
  }
  else if (argv[i] === '--recibo') {
    opciones.recibo = argv[++i];
    if (!opciones.recibo) infra('--recibo requiere una ruta.');
  }
  else if (argv[i] === '--comprobar-recibo') {
    opciones.comprobarRecibo = argv[++i];
    if (!opciones.comprobarRecibo) infra('--comprobar-recibo requiere una ruta.');
  }
  else infra(`argumento desconocido: ${argv[i]}`);
}

let root;
try { root = execFileSync('git', ['rev-parse', '--show-toplevel'], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }).trim(); }
catch { infra('no se ejecuta dentro de un repositorio git.'); }
process.chdir(root);

if (opciones.comprobarRecibo) {
  limpiarYSalir(comprobarRecibo(opciones.comprobarRecibo, opciones.base));
}

const cfg = configuracion = await resolverServidor({ crearStorage: !opciones.resolverConfig && !opciones.registrarProyecto });
TOKEN_A_OCULTAR = cfg.env.SONARQUBE_TOKEN;
if (opciones.resolverConfig) {
  process.stdout.write(JSON.stringify(cfg.origen, null, 2) + '\n');
  limpiarYSalir(0);
}
if (opciones.registrarProyecto) await registrarProyecto(cfg, opciones.registrarProyecto);

const mcp = new ClienteMcp(cfg);
try {
  await mcp.iniciar();
  const proyectos = await mcp.herramienta('search_my_sonarqube_projects', {});
  const projectKeys = new Set((proyectos.projects ?? []).map((p) => p.key));
  const versionSrv = await versionServidor(cfg.env.SONARQUBE_URL);
  if (opciones.canary) await modoCanario(mcp, projectKeys);
  else await modoGate(mcp, projectKeys, opciones, versionSrv);
} catch (e) {
    if (e instanceof Salida) throw e;
  infra(hintInfraSonar(`MCP SonarQube no responde o falló: ${e.message}`));
}

}

async function ejecutar() {
  const interrumpir = () => { cerrar().finally(() => process.exit(2)); };
  process.once('SIGINT', interrumpir);
  process.once('SIGTERM', interrumpir);
  try { await main(); }
  catch (e) {
    if (e instanceof Salida) process.exitCode = e.code;
    else {
      process.stderr.write(`BLOCKED (infraestructura): ${e.codigo ? e.message : 'Fallo del servidor MCP.'}\n`);
      process.exitCode = 2;
    }
  } finally {
    try { await cerrar(); }
    catch { process.stderr.write('BLOCKED (infraestructura): no se pudo limpiar el almacenamiento temporal.\n'); process.exitCode = 2; }
    process.removeListener('SIGINT', interrumpir);
    process.removeListener('SIGTERM', interrumpir);
  }
}
if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) await ejecutar();
