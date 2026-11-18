#!/usr/bin/env node
// Comprobación estática, sin instalación ni red. Solo lee package.json de la raíz,
// del mismo modo que el back compara los build.gradle: la comparación con
// `frontend.version` es literal exacta; un rango (^, ~, >, <, *, x) bloquea.
import fs from 'node:fs';
import { get } from './stack.mjs';
import { inventariar } from './inventario-versiones.mjs';

function literal(declarada) {
  return typeof declarada === 'string' && /^[0-9]+(?:\.[0-9]+)+(?:[-.][A-Za-z0-9.-]+)?$/.test(declarada.trim());
}

const esperada = String(get('frontend.version'));
let packageJson;
try {
  packageJson = JSON.parse(fs.readFileSync('package.json', 'utf8'));
} catch {
  console.error(`BLOCKED: no existe package.json en la raíz; no puedo comparar next con frontend.version ${esperada}.`);
  process.exit(1);
}
const declarada = (packageJson.dependencies && packageJson.dependencies.next !== undefined)
  ? packageJson.dependencies.next
  : packageJson.devDependencies?.next;

if (declarada === undefined) {
  console.error(`BLOCKED: package.json no declara la dependencia next; frontend.version esperado ${esperada}. Lanza .agents/workflows/change-version.md para alinearlos, o vuelve frontend.version en .agents/stack.yaml a la versión del código. No cambies stack.yaml automáticamente.`);
  process.exit(1);
}
const valor = String(declarada).trim();
if (!literal(valor)) {
  console.error(`BLOCKED: package.json: next declarado ${declarada} no es una versión literal (rango ^, ~, >, <, *, x); fija la versión exacta mediante .agents/workflows/change-version.md (plan aprobado).`);
  process.exit(1);
}
if (valor !== esperada) {
  console.error(`BLOCKED: package.json: next observado ${valor}; frontend.version esperado ${esperada}. Lanza .agents/workflows/change-version.md para alinearlos, o vuelve frontend.version en .agents/stack.yaml a la versión del código. No cambies stack.yaml automáticamente.`);
  process.exit(1);
}
console.log(`OK: next ${valor} = frontend.version ${esperada}`);

try {
  const inv = inventariar();
  for (const aviso of inv.avisos) console.log('AVISO: ' + aviso);
  const instalada = inv.servicios[0].dependencias.find(d => d.nombre === 'next');
  if (instalada?.procedencia === 'lock' && instalada.version && instalada.version !== esperada) {
    console.error(`BLOCKED: next del lock ${instalada.version}; frontend.version ${esperada}. Alinea la librería y la documentación mediante .agents/workflows/change-version.md (plan aprobado), o vuelve frontend.version en .agents/stack.yaml a la versión del código. No edites stack.yaml automáticamente.`);
    process.exitCode = 1;
  }
} catch {
  console.error('BLOCKED: no se pudo comprobar package-lock.json; revisa el inventario.');
  process.exitCode = 1;
}
