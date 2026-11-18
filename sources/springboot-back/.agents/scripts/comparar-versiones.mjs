#!/usr/bin/env node
import { inventariar } from './inventario-versiones.mjs';
const salidas='Alinea las versiones de librerías, plugins o BOM mediante .agents/workflows/change-version.md (plan aprobado), incluidas las claves de stack.yaml si corresponden. Ningún agente edita stack.yaml; esas líneas las edita el usuario.';
try {
  const inv=inventariar(), grupos=new Map(); let fallos=0;
  for (const warning of inv.avisos) console.log('AVISO: '+warning);
  for (const service of inv.servicios) {
    for (const [tipo,items] of [['plugin',service.plugins],['dependencia',service.dependencias],['bom',service.boms]]) for (const item of items) {
      if (item.estado!=='literal') continue;
      const key=tipo+':'+(item.id || item.coordenada);
      if (!grupos.has(key)) grupos.set(key,[]);
      grupos.get(key).push({servicio:service.nombre,version:item.version,origen:item.origen});
    }
  }
  for (const [key,items] of grupos) if (new Set(items.map(i=>i.servicio)).size>1 && new Set(items.map(i=>i.version)).size>1) {
    console.error('BLOCKED: '+key+' difiere: '+items.map(i=>`${i.servicio}=${i.version} (${i.origen.archivo}:${i.origen.linea})`).join('; ')); fallos++;
  }
  if (!inv.servicios.length) { console.error('BLOCKED: no hay servicios con build.gradle y settings.gradle.'); fallos++; }
  if (fallos) console.error(salidas); else console.log('OK: versiones literales compartidas coinciden; dependencias del BOM no se comparan.');
  process.exitCode=fallos ? 1:0;
} catch { console.error('BLOCKED: no se pudo comparar el inventario de servicios.'); process.exitCode=1; }
