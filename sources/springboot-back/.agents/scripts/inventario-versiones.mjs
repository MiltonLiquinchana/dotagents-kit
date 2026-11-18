#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { get } from './stack.mjs';
import { analizarGradle } from './gradle-estatico.mjs';
export function leerGradleWrapper(servicio) {
  const archivo = `${servicio}/gradle/wrapper/gradle-wrapper.properties`;
  const resultado = {nombre: 'gradle-wrapper', version: null, estado: 'no_resoluble', origen: {archivo, linea: null}};
  let texto;
  try { texto = fs.readFileSync(archivo, 'utf8'); } catch { return resultado; }
  let actual = '', inicio = null, valor = null;
  for (const [indice, linea] of texto.split(/\r?\n/).entries()) {
    if (inicio === null) {
      if (/^\s*(?:[#!]|$)/.test(linea)) continue;
      inicio = indice + 1;
    }
    actual += linea.trimStart();
    const barras = actual.match(/\\+$/)?.[0].length || 0;
    if (barras % 2) { actual = actual.slice(0, -1); continue; }
    const m = actual.match(/^distributionUrl(?:\s*[:=]\s*|\s+|$)(.*)$/);
    if (m) { valor = m[1].replace(/\\:/g, ':').trim(); resultado.origen.linea = inicio; }
    actual = ''; inicio = null;
  }
  if (valor === null) return resultado;
  try {
    const segmento = new URL(valor).pathname.split('/').at(-1);
    const m = segmento.match(/^gradle-(\d+(?:\.\d+)*(?:[-+][A-Za-z0-9][A-Za-z0-9.+-]*)?)-(?:bin|all)\.zip$/);
    if (m) { resultado.version = m[1]; resultado.estado = 'literal'; }
  } catch { /* URL no resoluble: conservar archivo y línea para el aviso. */ }
  return resultado;
}
export function inventariar() {
  const servicios = fs.readdirSync('.', {withFileTypes:true}).filter(e => e.isDirectory() && !e.name.startsWith('.') && fs.existsSync(path.join(e.name,'build.gradle')) && fs.existsSync(path.join(e.name,'settings.gradle'))).map(e=>e.name).sort().map(nombre=>({nombre,ruta:nombre,...analizarGradle(fs.readFileSync(path.join(nombre,'build.gradle'),'utf8'),nombre+'/build.gradle'),gradle_wrapper:leerGradleWrapper(nombre)}));
  const avisos=[];
  for (const s of servicios) for (const item of [s.java,s.gradle_wrapper,...s.plugins,...s.dependencias,...s.boms,...s.propiedades_version]) if (item.estado==='no_resoluble') avisos.push(`${s.nombre}: ${item.coordenada || item.id || item.nombre || 'Java'} no_resoluble (${item.origen.archivo}:${item.origen.linea || '?'})`);
  return {formato:1,stack:'springboot',base:{jdk:String(get('backend.java')),'spring-boot':String(get('backend.spring_boot'))},servicios,avisos};
}
if (process.argv[1] && path.resolve(process.argv[1])===fileURLToPath(import.meta.url)) {
  try { console.log(JSON.stringify(inventariar(),null,2)); }
  catch { console.error('BLOCKED: no se pudo leer el inventario de los builds; revisa los archivos declarados.'); process.exitCode=1; }
}
