#!/usr/bin/env node
// ==============================================================================
// security-scan.mjs - Complemento determinista del gate de SonarQube (frontend).
//
// Por qué existe: ni ESLint (reglas core) ni analyze_code_snippet detectan secretos
// hardcodeados (ver .agents/skills/code-reviewer/references/sonarqube-gate.md, "Hueco comprobado"). Tampoco marcan
// toda inyección de HTML en el cliente. Este escáner cubre ese hueco con una heurística
// léxica sobre los .ts/.tsx tocados.
//
// Qué hace: para cada fichero tocado (lista de touched-files.sh) compara el contenido
// base con el actual y reporta los hallazgos NUEVOS (multiconjunto actual - base, por
// regla + texto normalizado, sin número de línea).
//
// Reglas (cada hallazgo lleva su id):
//   secret-aws-key       clave de acceso AWS (AKIA + 16 caracteres)
//   secret-private-key   cabecera de clave privada PEM
//   secret-token-prefix  prefijos de token conocidos (ghp_, sk_live_, sk-…, xox*-, AIza…)
//   secret-jwt           JWT literal (eyJ….eyJ….)
//   secret-assignment    password/secret/apiKey/token = "valor literal de 8+ caracteres sin espacios"
//   public-env-secret    variable NEXT_PUBLIC_* cuyo nombre contiene SECRET/PRIVATE/PASSWORD/CREDENTIAL
//   html-injection       dangerouslySetInnerHTML, .innerHTML =, .outerHTML =, document.write(
//
// Límites (NO se detecta):
//   - Secretos fuera de .ts/.tsx (.env, .json, .yaml): el alcance es el de touched-files.sh.
//   - Secretos de formato libre (una contraseña con espacios, un valor construido por
//     concatenación o leído de un literal en otra línea).
//   - NEXT_PUBLIC_*_TOKEN y NEXT_PUBLIC_*_KEY: pueden ser públicos legítimos (p. ej. la clave
//     publicable de Clerk), así que no se marcan por nombre.
//   - html-injection marca todo uso nuevo, también el saneado: es un aviso para revisar,
//     no un veredicto de vulnerabilidad.
// Falsos positivos posibles: un valor de prueba o un literal de ejemplo con forma de secreto.
//
// Salida: JSON por stdout. Códigos: 0 = nada nuevo, 1 = hallazgos, 2 = infraestructura.
// ==============================================================================
import { execFileSync, spawnSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';

const COMMENT = /^\s*(\/\/|\*|\/\*)/;

// Se aplican a todas las líneas, comentadas o no: un secreto comentado sigue filtrado.
const SECRET_RULES = [
  ['secret-aws-key', /\bAKIA[0-9A-Z]{16}\b/],
  ['secret-private-key', /-----BEGIN [A-Z ]*PRIVATE KEY-----/],
  ['secret-token-prefix', /\b(?:ghp_[A-Za-z0-9]{36}|gho_[A-Za-z0-9]{36}|sk_live_[A-Za-z0-9]{16,}|sk-[A-Za-z0-9_-]{24,}|xox[baprs]-[A-Za-z0-9-]{10,}|AIza[0-9A-Za-z_-]{35})/],
  ['secret-jwt', /\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\./],
  ['secret-assignment', /\b(?:password|passwd|pwd|secret|api[_-]?key|access[_-]?key|private[_-]?key|auth[_-]?token|client[_-]?secret|token)["']?\s*[:=]\s*(["'`])(?![^"'`]*\$\{)[^"'`\s]{8,}\1/i],
];

// Solo líneas de código (no comentarios).
const CODE_RULES = [
  ['public-env-secret', /\bNEXT_PUBLIC_[A-Z0-9_]*(?:SECRET|PRIVATE|PASSWORD|PASSWD|CREDENTIAL)[A-Z0-9_]*\b/],
  ['html-injection', /\bdangerouslySetInnerHTML\b|\.(?:inner|outer)HTML\s*=(?!=)|\bdocument\.write\s*\(/],
];

// Un valor que solo hace referencia a una variable de entorno o a un marcador no es un secreto.
const PLACEHOLDER = /process\.env|import\.meta\.env|<[^>]*>|\*{4,}|x{6,}|•{3,}/i;

function die(msg) {
  process.stderr.write(`BLOCKED (infraestructura): ${msg}\n`);
  process.exit(2);
}

function findings(content) {
  const lines = content.replace(/\r/g, '').split('\n');
  const out = [];
  lines.forEach((line, i) => {
    const texto = line.trim().replace(/\s+/g, ' ');
    for (const [regla, re] of SECRET_RULES) {
      if (re.test(line) && !PLACEHOLDER.test(line)) out.push({ regla, linea: i + 1, texto });
    }
    if (COMMENT.test(line)) return;
    for (const [regla, re] of CODE_RULES) {
      if (re.test(line)) out.push({ regla, linea: i + 1, texto });
    }
  });
  return out;
}

const root = execFileSync('git', ['rev-parse', '--show-toplevel'], { encoding: 'utf8' }).trim();
process.chdir(root);

const touched = spawnSync('bash', ['.agents/scripts/touched-files.sh'], { encoding: 'utf8' });
if (touched.status !== 0) die(`touched-files.sh terminó con código ${touched.status}: ${touched.stderr.trim()}`);

let files;
try { files = JSON.parse(touched.stdout); } catch { die('la salida de touched-files.sh no es JSON.'); }

const nuevos = [];
for (const f of files) {
  let actual;
  try { actual = fs.readFileSync(path.join(root, f.ruta), 'utf8'); } catch { die(`no se pudo leer ${f.ruta}.`); }
  let base = '';
  if (f.estado !== 'nuevo') {
    try { base = execFileSync('git', ['cat-file', '-p', f.blobBase], { encoding: 'utf8' }); }
    catch { die(`no se pudo leer el blob base de ${f.ruta}.`); }
  }
  const clave = (h) => `${h.regla}|${h.texto}`;
  const previos = new Map();
  for (const h of findings(base)) previos.set(clave(h), (previos.get(clave(h)) ?? 0) + 1);
  for (const h of findings(actual)) {
    const n = previos.get(clave(h)) ?? 0;
    if (n > 0) previos.set(clave(h), n - 1);
    else nuevos.push({ ruta: f.ruta, estado: f.estado, regla: h.regla, linea: h.linea, texto: h.texto });
  }
}

process.stdout.write(JSON.stringify(nuevos, null, 2) + '\n');
if (nuevos.length > 0) {
  process.stderr.write(`security-scan: ${nuevos.length} hallazgo(s) nuevo(s).\n`);
  process.exit(1);
}
process.stderr.write('security-scan: sin hallazgos nuevos.\n');
