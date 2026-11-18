#!/usr/bin/env node
// ==============================================================================
// sql-concat-scan.mjs - Complemento determinista del gate de SonarQube.
//
// Por qué existe: el análisis por fichero de SonarQube (analyze_code_snippet) solo
// detecta SQL dinámico (java:S2077) sobre tipos del JDK como java.sql.Statement. No
// lo detecta sobre EntityManager.createNativeQuery/createQuery ni JdbcTemplate, que
// son los tipos de librería que usaría este proyecto (comprobado, ver
// .agents/skills/code-reviewer/references/sonarqube-gate.md). Este escáner cubre ese hueco con una heurística
// léxica: una cadena con forma de SQL construida por concatenación o formato.
//
// Qué hace: para cada .java tocado (lista de touched-files.sh) compara el contenido
// base con el actual y reporta las líneas SQL-con-concatenación NUEVAS (multiconjunto
// actual - base, por texto normalizado, sin número de línea).
//
// Heurística (deliberadamente simple, ver "Límites"). Marca una línea nueva si:
//   (a) tiene un literal de forma SQL completa (select..from, insert into, update..set,
//       delete from, call x(, where col =) Y, en esa línea o en las 2 siguientes, un literal
//       unido con "+" a una expresión no literal, o String.format / .formatted; o
//   (b) tiene un literal de fragmento SQL (" AND ...", " ORDER BY ", " LIMIT ", ...) unido
//       con "+" a una expresión no literal EN ESA MISMA LÍNEA.
//   Las constantes UPPER_SNAKE no cuentan como expresión no literal. Cubre también text
//   blocks (""") cuyo cierre llama a .formatted(...).
//
// Límites (NO se detecta):
//   - SQL montado con StringBuilder.append(...) o StringJoiner.
//   - Un fragmento que no empieza por una cláusula SQL (p. ej. `q += col + " = " + valor`).
//   - Un literal SQL completo y la concatenación separados por MÁS de 2 líneas, salvo que
//     la línea de concatenación contenga además un fragmento de cláusula (caso b).
//   - Variables que se unen en una sentencia distinta de la del literal (la variable
//     tainted se sigue solo si el literal SQL y el "+" están en la ventana de 3 líneas).
// Falsos positivos posibles: un mensaje que contenga texto con forma de SQL y se concatene,
// o una constante que no siga la convención UPPER_SNAKE.
//
// Salida: JSON por stdout. Códigos: 0 = nada nuevo, 1 = hallazgos, 2 = infraestructura.
// ==============================================================================
import { execFileSync, spawnSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';

const SQL = /"[^"]*\b(select\s.+\sfrom|insert\s+into|update\s+\w+\s+set|delete\s+from|call\s+\w+\s*\(|where\s+\w+(\.\w+)?\s*(=|<|>|like\b|in\b))[^"]*"/i;
const CONCAT = /"\s*\+\s*[A-Za-z_(]|[A-Za-z0-9_)\]]\s*\+\s*"|String\.format\s*\(|"\s*\.formatted\s*\(/;
const COMMENT = /^\s*(\/\/|\*|\/\*)/;

function die(msg) {
  process.stderr.write(`BLOCKED (infraestructura): ${msg}\n`);
  process.exit(2);
}

const SQL_BLOCK = /\b(select\s.+\sfrom|insert\s+into|update\s+\w+\s+set|delete\s+from|call\s+\w+\s*\(|where\s+\w+(\.\w+)?\s*(=|<|>|like\b|in\b))/is;
const FORMATTED = /"{3}\s*\.formatted\s*\(|String\.format\s*\(/;

// Text blocks: el SQL no lleva comillas por línea y el formato llega en la línea de cierre.
function textBlockFindings(lines) {
  const out = [];
  let start = -1;
  lines.forEach((line, i) => {
    const marks = (line.match(/"{3}/g) || []).length;
    if (start < 0 && marks % 2 === 1) { start = i; return; }
    if (start >= 0 && marks % 2 === 1) {
      const body = lines.slice(start, i + 1).join('\n');
      if (SQL_BLOCK.test(body) && FORMATTED.test(lines[i])) {
        out.push({ linea: start + 1, texto: lines[start].trim().replace(/\s+/g, ' ') + ' ... ' + lines[i].trim() });
      }
      start = -1;
    }
  });
  return out;
}

// Fragmento SQL (cláusula suelta) unido por "+" en la MISMA línea: `" AND estado = " + x`, `base + " ORDER BY " + col`.
// Exige estructura SQL para no marcar mensajes en lenguaje natural ("Where is the invoice " + x):
// operador tras la columna (and/or/where col =), o espacio inicial en ORDER BY / GROUP BY / HAVING / LIMIT.
const FRAGMENT = /"(?:\s+(?:order\s+by|group\s+by|having|limit)\s|\s*(?:and|or|where)\s+\w+(?:\.\w+)?\s*(?:=|<|>|like\b|in\b|is\b)|\s*set\s+\w+\s*=|\s*values\s*\()[^"]*"/i;

// Las constantes UPPER_SNAKE (static final) no cuentan como operando variable. Se sustituyen por "" solo FUERA
// de los literales, para que `"SELECT ..." + TABLE_SUFFIX` no se marque.
const LITERAL_OR_CONST = /"(?:[^"\\]|\\.)*"|\b[A-Z][A-Z0-9_]{2,}\b(?!\s*[.(\[])/g;
const withoutConstants = (text) => text.replace(LITERAL_OR_CONST, (m) => (m.startsWith('"') ? m : '""'));

function findings(content) {
  const lines = content.replace(/\r/g, '').split('\n');
  const out = textBlockFindings(lines);
  lines.forEach((line, i) => {
    if (COMMENT.test(line)) return;
    const esSql = SQL.test(line);
    const esFragmento = !esSql && FRAGMENT.test(line);
    if (!esSql && !esFragmento) return;
    const alcance = esSql ? lines.slice(i, i + 3).join(' ') : line;
    if (CONCAT.test(withoutConstants(alcance))) out.push({ linea: i + 1, texto: line.trim().replace(/\s+/g, ' ') });
  });
  return out;
}

const args = process.argv.slice(2);
let base = null;
for (let i = 0; i < args.length; i++) {
  if (args[i] === '--base' && args[i + 1]) base = args[++i];
  else die(`argumento desconocido o incompleto: ${args[i]}`);
}
let root;
try { root = execFileSync('git', ['rev-parse', '--show-toplevel'], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }).trim(); }
catch { die('no se ejecuta dentro de un repositorio git.'); }
process.chdir(root);

const touchedArgs = ['.agents/scripts/touched-files.sh'];
if (base) touchedArgs.push('--base', base);
const touched = spawnSync('bash', touchedArgs, { encoding: 'utf8' });
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
  const previos = new Map();
  for (const h of findings(base)) previos.set(h.texto, (previos.get(h.texto) ?? 0) + 1);
  for (const h of findings(actual)) {
    const n = previos.get(h.texto) ?? 0;
    if (n > 0) previos.set(h.texto, n - 1);
    else nuevos.push({ servicio: f.servicio, ruta: f.ruta, estado: f.estado, linea: h.linea, texto: h.texto });
  }
}

process.stdout.write(JSON.stringify(nuevos, null, 2) + '\n');
if (nuevos.length > 0) {
  process.stderr.write(`sql-concat-scan: ${nuevos.length} línea(s) nueva(s) con SQL construido por concatenación o formato.\n`);
  process.exit(1);
}
process.stderr.write('sql-concat-scan: sin hallazgos nuevos.\n');
