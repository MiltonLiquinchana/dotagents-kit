#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { get } from './stack.mjs';
const literal = v => typeof v==='string' && /^\d+(?:\.\d+)+(?:[-+][A-Za-z0-9][A-Za-z0-9.-]*)?$/.test(v);
export function inventariar() {
  const pkg=JSON.parse(fs.readFileSync('package.json','utf8'));
  const hasLock=fs.existsSync('package-lock.json');
  const lock=hasLock ? JSON.parse(fs.readFileSync('package-lock.json','utf8')) : null;
  const dependencias=[], avisos=[];
  for (const section of ['dependencies','devDependencies','optionalDependencies']) for (const [nombre,declarada] of Object.entries(pkg[section] || {})) {
    const entry=lock?.packages?.['node_modules/'+nombre];
    const observed=hasLock ? entry?.version : declarada;
    const version=literal(observed) ? observed : null;
    const item={nombre,declarada,version,estado:version ? 'literal':'no_resoluble',procedencia:hasLock?'lock':'declaracion',configuraciones:[section],archivo:hasLock?'package-lock.json':'package.json',puntero:hasLock?'/packages/'+('node_modules/'+nombre).replaceAll('~','~0').replaceAll('/','~1')+'/version':'/'+section+'/'+nombre.replaceAll('~','~0').replaceAll('/','~1')};
    dependencias.push(item);
    if (!version) avisos.push(`${nombre}: no_resoluble (${item.archivo}${item.puntero}); ${hasLock?'falta una versión instalada literal':'sin lock y declaración no literal'}`);
  }
  return {formato:1,stack:'nextjs',base:{nextjs:String(get('frontend.version'))},servicios:[{nombre:'.',ruta:'.',dependencias}],avisos};
}
if (process.argv[1] && path.resolve(process.argv[1])===fileURLToPath(import.meta.url)) {
  try { console.log(JSON.stringify(inventariar(),null,2)); }
  catch { console.error('BLOCKED: package.json o package-lock.json ilegible; no se adivina el inventario.'); process.exitCode=1; }
}
