#!/usr/bin/env node
// Resolución del MCP propio del kit; importar no lee configuración ni inicia procesos.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import crypto from 'node:crypto';
import { spawnSync } from 'node:child_process';
import { pathToFileURL } from 'node:url';

export const VERSION = '1.32.0.5118';
export const SHA256 = 'f64f79bb8ccde5f05ee37d6aa24ab505225c38bc35f051fae665bba6ea0bd421';
export const URL_BASE = 'https://binaries.sonarsource.com/Distribution/sonarqube-mcp-server/';
export const TAMANO_ESPERADO = 81308785;
export function fallo(mensaje, codigo = 'SONAR_SERVIDOR') {
  return Object.assign(new Error(mensaje), { codigo });
}
export function rutasKit(entorno = process.env) {
  const base = entorno.DOTAGENTSKIT_HOME === undefined ? path.join(os.homedir(), '.dotagentskit') : entorno.DOTAGENTSKIT_HOME;
  if (!base || !path.isAbsolute(base)) throw fallo('DOTAGENTSKIT_HOME debe ser una ruta absoluta no vacía.');
  const servidor = path.join(base, 'sonarqube-mcp');
  const versionDir = path.join(servidor, VERSION);
  return { base, servidor, versionDir, jar: path.join(versionDir, `sonarqube-mcp-server-${VERSION}.jar`), storageDir: path.join(servidor, 'storage') };
}
// Sin seguir enlaces en los directorios gestionados. comprobar=true no escribe.
export function directorio(ruta, comprobar = false) {
  let st;
  try { st = fs.lstatSync(ruta); }
  catch (e) {
    if (e.code !== 'ENOENT') throw fallo('No se pudo comprobar el directorio del MCP.');
    if (comprobar) return;
    try { fs.mkdirSync(ruta, { recursive: true, mode: 0o700 }); st = fs.lstatSync(ruta); }
    catch { throw fallo('No se pudo crear el directorio del MCP.'); }
  }
  if (!st.isDirectory() || st.isSymbolicLink() || (process.getuid && st.uid !== process.getuid())) {
    throw fallo('Directorio del MCP inseguro: enlace simbólico, tipo o propietario incorrecto.');
  }
  if (!comprobar) fs.chmodSync(ruta, 0o700);
  try { fs.accessSync(ruta, fs.constants.W_OK | fs.constants.X_OK); }
  catch { throw fallo('Directorio del MCP no escribible.'); }
}
export function directoriosKit(rutas, comprobar = false) {
  for (const ruta of [rutas.base, rutas.servidor, rutas.versionDir]) directorio(ruta, comprobar);
}
export async function comprobarJar(ruta) {
  let st;
  try { st = fs.lstatSync(ruta); }
  catch (e) { if (e.code === 'ENOENT') return 'falta'; throw fallo('No se pudo comprobar el jar del MCP.'); }
  if (!st.isFile() || st.isSymbolicLink()) throw fallo('El jar del kit debe ser un archivo regular, sin enlace simbólico.');
  try {
    const hash = crypto.createHash('sha256');
    for await (const chunk of fs.createReadStream(ruta)) hash.update(chunk);
    return hash.digest('hex') === SHA256 ? 'ok' : 'huella';
  } catch { throw fallo('No se pudo leer el jar del MCP.'); }
}
function legible(ruta, propio) {
  try {
    const st = propio ? fs.statSync(ruta) : fs.lstatSync(ruta);
    fs.accessSync(ruta, fs.constants.R_OK);
    if (!st.isFile() || (!propio && st.isSymbolicLink())) throw new Error();
    if (!propio && st.size !== TAMANO_ESPERADO) throw fallo('El jar del kit tiene otro tamaño; ejecuta instalar-sonar-mcp.mjs --comprobar para comprobar su huella.');
  } catch (e) {
    if (e.codigo) throw e;
    throw fallo(propio ? 'SONARQUBE_MCP_JAR debe indicar un archivo existente y legible (jar propio).' : 'Falta el servidor MCP del kit o no es legible; autoriza instalar-sonar-mcp.mjs.');
  }
}
function borrarArbol(ruta) {
  for (const entry of fs.readdirSync(ruta, { withFileTypes: true })) {
    const child = path.join(ruta, entry.name);
    if (entry.isDirectory()) borrarArbol(child); else fs.unlinkSync(child);
  }
  fs.rmdirSync(ruta);
}
export async function resolverServidor({ entorno = process.env, stackGet, comprobarHuella = false, crearStorage = true } = {}) {
  // stackGet se admite por contrato; ninguna variable de conexión procede del stack.
  for (const [nombre, descripcion] of [['SONARQUBE_URL', 'dirección del servidor SonarQube'], ['SONARQUBE_TOKEN', 'token de usuario de SonarQube']]) {
    if (!entorno[nombre]?.trim()) throw fallo(`Falta ${nombre} (${descripcion}); expórtala en el entorno de tu herramienta y repite. No se muestra su valor.`, 'SONAR_CREDENCIALES');
  }
  const rutas = rutasKit(entorno);
  const propio = entorno.SONARQUBE_MCP_JAR !== undefined;
  const jar = propio ? entorno.SONARQUBE_MCP_JAR : rutas.jar;
  if (!propio) directoriosKit(rutas, true);
  legible(jar, propio);
  if (!propio && comprobarHuella && await comprobarJar(jar) !== 'ok') throw fallo('huella distinta en el jar del kit; no se modifica el archivo.');
  const java = spawnSync('java', ['-version'], { env: entorno, encoding: 'utf8', timeout: 10000, stdio: ['ignore', 'pipe', 'pipe'] });
  const m = /version "(\d+)(?:\.(\d+))?/.exec(java.stderr ?? '');
  const mayor = m ? Number(m[1] === '1' ? m[2] : m[1]) : NaN;
  if (java.error || java.status !== 0 || !(mayor >= 21)) throw fallo('SonarQube MCP necesita Java 21 o superior.');
  const compartido = entorno.SONARQUBE_STORAGE_PATH !== undefined;
  let storage, exclusivo = false;
  if (compartido) {
    storage = entorno.SONARQUBE_STORAGE_PATH;
    try {
      if (!storage || !path.isAbsolute(storage) || !fs.statSync(storage).isDirectory()) throw new Error();
      fs.accessSync(storage, fs.constants.W_OK | fs.constants.X_OK);
    } catch { throw fallo('SONARQUBE_STORAGE_PATH debe ser una carpeta absoluta existente y escribible.'); }
  } else {
    for (const ruta of [rutas.base, rutas.servidor, rutas.storageDir]) directorio(ruta, !crearStorage);
    if (crearStorage) {
      storage = fs.mkdtempSync(path.join(rutas.storageDir, 'ejecucion-'));
      fs.chmodSync(storage, 0o700);
      exclusivo = true;
    }
  }
  return { command: 'java', args: ['-jar', jar],
    env: { SONARQUBE_URL: entorno.SONARQUBE_URL, SONARQUBE_TOKEN: entorno.SONARQUBE_TOKEN, ...(storage ? { STORAGE_PATH: storage } : {}) },
    origen: { jar: propio ? 'SONARQUBE_MCP_JAR' : 'kit', url: 'SONARQUBE_URL', token: 'SONARQUBE_TOKEN', storage: compartido ? 'SONARQUBE_STORAGE_PATH' : 'por ejecución', java: mayor },
    liberar() { if (exclusivo) { borrarArbol(storage); exclusivo = false; } },
  };
}
// Esperar close asegura que el hijo ya no escribe antes de borrar su storage.
export async function cerrarServidor(hijo) {
  if (!hijo || hijo._sonarCerrado) return;
  await new Promise((resolve) => {
    let timer;
    const fin = () => { clearTimeout(timer); hijo._sonarCerrado = true; resolve(); };
    hijo.once('close', fin);
    try { hijo.stdin?.end(); hijo.kill(); } catch { /* close informa el final */ }
    timer = setTimeout(() => { try { hijo.kill('SIGKILL'); } catch { /* ya terminó */ } }, 2000);
  });
}
async function main() {
  try {
    if (process.argv.slice(2).join(' ') !== '--comprobar') throw fallo('Uso: sonar-servidor.mjs --comprobar');
    const cfg = await resolverServidor({ comprobarHuella: true, crearStorage: false });
    process.stdout.write(`OK SonarQube MCP (${cfg.origen.jar === 'kit' ? 'kit' : 'jar propio'}); Java ${cfg.origen.java}; variables definidas.\n`);
  } catch (e) {
    process.stderr.write(`BLOCKED: ${e.codigo ? e.message : 'No se pudo comprobar el servidor MCP.'}\n`);
    process.exitCode = 2;
  }
}
if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) await main();
