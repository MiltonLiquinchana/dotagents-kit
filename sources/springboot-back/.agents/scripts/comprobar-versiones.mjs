#!/usr/bin/env node
// Comprobación estática, sin Gradle ni red: Spring Boot y Java declarados en builds del primer nivel.
import fs from 'node:fs';
import path from 'node:path';
import { get } from './stack.mjs';
import { analizarGradle, sinComentarios } from './gradle-estatico.mjs';
import { inventariar } from './inventario-versiones.mjs';

let tabla;
try {
  tabla = JSON.parse(fs.readFileSync(new URL('../config/gradle-java.json', import.meta.url), 'utf8'));
  if (!tabla || Array.isArray(tabla) || typeof tabla !== 'object' ||
      typeof tabla.fuente !== 'string' || new URL(tabla.fuente).protocol !== 'https:' ||
      typeof tabla.verificado !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(tabla.verificado) ||
      !Number.isFinite(Date.parse(tabla.verificado)) || new Date(tabla.verificado).toISOString().slice(0, 10) !== tabla.verificado ||
      !tabla.minimos || typeof tabla.minimos !== 'object' || Array.isArray(tabla.minimos) ||
      !Object.keys(tabla.minimos).length ||
      !Object.entries(tabla.minimos).every(([java, gradle]) => /^[1-9]\d*$/.test(java) && typeof gradle === 'string' && /^\d+(?:\.\d+)*$/.test(gradle))) throw new Error();
} catch {
  console.error('ERROR: .agents/config/gradle-java.json ausente o inválida; avisa al mantenedor de .agents para reparar la tabla de compatibilidad Gradle/Java.');
  process.exit(1);
}

function versionComparable(version) {
  const m = version.match(/^(\d+(?:\.\d+)*)(?:-(rc|milestone)-(\d+))?$/);
  return m ? {numeros: m[1].split('.').map(BigInt), etapa: m[2] === 'milestone' ? 0 : m[2] === 'rc' ? 1 : 2, previa: BigInt(m[3] || '0')} : null;
}
function comparar(a, b) {
  for (let i = 0; i < Math.max(a.numeros.length, b.numeros.length); i++) {
    const x = a.numeros[i] || 0n, y = b.numeros[i] || 0n;
    if (x !== y) return x < y ? -1 : 1;
  }
  if (a.etapa !== b.etapa) return a.etapa - b.etapa;
  return a.previa === b.previa ? 0 : a.previa < b.previa ? -1 : 1;
}

const esperadaBoot = String(get('backend.spring_boot'));
const esperadaJava = String(get('backend.java'));
const servicios = fs.readdirSync('.', { withFileTypes: true })
  .filter(e => e.isDirectory() && !e.name.startsWith('.') &&
    fs.existsSync(path.join(e.name, 'build.gradle')) &&
    fs.existsSync(path.join(e.name, 'settings.gradle')))
  .map(e => e.name).sort();
let fallos = 0;
if (!servicios.length) {
  console.error('BLOCKED: no hay servicios (build.gradle + settings.gradle); sigue .agents/skills/service-creator/references/servicio-initializr.md.');
  process.exit(1);
}

// Spring Boot
for (const servicio of servicios) {
  const texto = sinComentarios(fs.readFileSync(path.join(servicio, 'build.gradle'), 'utf8'));
  const declaraciones = [...texto.matchAll(/\bid\s*(?:\(\s*(['"])org\.springframework\.boot\1\s*\)|(['"])org\.springframework\.boot\2)\s+version\s+(['"])([^'"\n]+)\3(?=\s*(?:\r?\n|;|\}|apply\b|$))/g)];
  const literal = declaraciones.length === 1 ? declaraciones[0][4] : null;
  const observada = literal && /^[0-9]+(?:\.[0-9]+)+(?:[-.][A-Za-z0-9.-]+)?$/.test(literal) ? literal : null;
  if (observada !== esperadaBoot) {
    console.error(`BLOCKED: ${servicio}/build.gradle: Spring Boot observado ${observada ?? 'ausente, ambiguo o no resoluble'}; backend.spring_boot esperado ${esperadaBoot}. Lanza .agents/workflows/change-version.md para alinearlos, o vuelve backend.spring_boot en .agents/stack.yaml a la versión del código. No cambies stack.yaml automáticamente.`);
    fallos++;
  } else console.log(`OK: ${servicio}: Spring Boot ${observada} = backend.spring_boot ${esperadaBoot}`);
}

// Java en builds (mismo criterio que el inventario: gradle-estatico.mjs/analizarGradle)
const javaPorServicio = [];
for (const servicio of servicios) {
  const archivo = path.join(servicio, 'build.gradle');
  const analisis = analizarGradle(fs.readFileSync(archivo, 'utf8'), archivo);
  const version = analisis.java?.estado === 'literal' ? String(analisis.java.version) : null;
  javaPorServicio.push({ servicio, version });
}
const sinJava = javaPorServicio.filter(x => !x.version).map(x => x.servicio);
if (sinJava.length) {
  for (const servicio of sinJava) {
    console.error(`BLOCKED: ${servicio}/build.gradle no declara JavaLanguageVersion.of(N); añade JavaLanguageVersion.of(${esperadaJava}) mediante .agents/workflows/incorporate-service.md (o un plan aprobado).`);
  }
  fallos++;
} else {
  const distintas = [...new Set(javaPorServicio.map(x => x.version))];
  if (distintas.length > 1) {
    console.error('BLOCKED: Los servicios declaran versiones de Java distintas entre sí; alinea todos con .agents/workflows/change-version.md (o con .agents/workflows/incorporate-service.md si el distinto es un servicio recién traído).');
    for (const x of javaPorServicio) console.error(`${x.servicio}=${x.version}`);
    fallos++;
  } else if (distintas[0] !== esperadaJava) {
    console.error(`BLOCKED: backend.java de .agents/stack.yaml (${esperadaJava}) no coincide con lo declarado en los build.gradle (${distintas[0]}); lanza .agents/workflows/change-version.md, o vuelve backend.java en .agents/stack.yaml a la versión del código. No edites los build.gradle a mano.`);
    fallos++;
  } else {
    console.log(`OK: Java ${distintas[0]} = backend.java ${esperadaJava} en ${servicios.length} servicios`);
  }
}

// installations.paths (formato .properties: espacios, key=value/:, continuaciones con \)
function leerPropiedades(contenido) {
  const props = {};
  const lineas = contenido.split(/\r?\n/);
  let actual = '';
  for (const linea of lineas) {
    const recortada = linea.replace(/\r$/, '');
    if (actual) {
      actual += recortada.replace(/^\s*/, '');
    } else {
      if (/^\s*(#|!|$)/.test(recortada)) continue;
      actual = recortada.replace(/^\s*/, '');
    }
    let barras = 0;
    for (let i = actual.length - 1; i >= 0 && actual[i] === '\\'; i--) barras++;
    if (barras % 2 === 1) {
      actual = actual.slice(0, -1);
      continue;
    }
    const m = actual.match(/^([^:=\s]+)\s*[:=]?\s*(.*)$/);
    if (m) props[m[1]] = m[2];
    actual = '';
  }
  return props;
}
function esJavacEjecutable(rutaJavac) {
  try {
    const st = fs.statSync(rutaJavac);
    if (!st.isFile()) return false;
    fs.accessSync(rutaJavac, fs.constants.X_OK);
    return true;
  } catch {
    return false;
  }
}

let instalacionesComprobadas = 0;
let instalacionesFallos = 0;
for (const servicio of servicios) {
  const propsPath = path.join(servicio, 'gradle.properties');
  if (!fs.existsSync(propsPath)) continue;
  const contenido = fs.readFileSync(propsPath, 'utf8');
  const props = leerPropiedades(contenido);
  const valor = props['org.gradle.java.installations.paths'];
  if (valor == null || valor.trim() === '') continue;
  const paths = valor.split(',').map(x => x.trim()).filter(Boolean);
  for (const installPath of paths) {
    instalacionesComprobadas++;
    const javac = path.join(installPath, 'bin', 'javac');
    if (!esJavacEjecutable(javac)) {
      console.error(`BLOCKED: ${servicio}/gradle.properties apunta a '${installPath}', que no contiene bin/javac (¿JDK movido o desinstalado?).`);
      instalacionesFallos++;
      fallos++;
    }
  }
}
if (instalacionesComprobadas > 0 && instalacionesFallos === 0) {
  console.log('OK: instalaciones JDK declaradas en gradle.properties contienen bin/javac');
}

const minimo = tabla.minimos[esperadaJava];
if (!minimo) {
  console.log(`AVISO: backend.java ${esperadaJava} fuera de la tabla .agents/config/gradle-java.json; no se comprueba la compatibilidad del wrapper de Gradle.`);
} else {
  for (const servicio of inventariar().servicios) {
    const wrapper = servicio.gradle_wrapper;
    if (wrapper.estado !== 'literal') continue;
    const actual = versionComparable(wrapper.version);
    if (!actual) {
      console.log(`AVISO: ${wrapper.origen.archivo}: versión del wrapper de Gradle ${wrapper.version} no comparable; no se comprueba su compatibilidad con Java ${esperadaJava}.`);
    } else if (comparar(actual, versionComparable(minimo)) < 0) {
      console.error(`BLOCKED: ${wrapper.origen.archivo}: el wrapper de Gradle ${wrapper.version} no ejecuta Java ${esperadaJava} (mínimo ${minimo} según .agents/config/gradle-java.json); lanza .agents/workflows/change-version.md para subir el wrapper.`);
      fallos++;
    } else {
      console.log(`OK: ${servicio.nombre}: wrapper de Gradle ${wrapper.version} ejecuta Java ${esperadaJava} (mínimo ${minimo} según .agents/config/gradle-java.json)`);
    }
  }
}
process.exitCode = fallos ? 1 : 0;
