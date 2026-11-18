#!/usr/bin/env node
// Descarga oficial fijada; la IA debe obtener permiso antes de instalar fuera del proyecto.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { VERSION, SHA256, URL_BASE, TAMANO_ESPERADO, rutasKit, directoriosKit, comprobarJar, fallo } from './sonar-servidor.mjs';

async function main() {
  let temporal, archivo, timer;
  const abort = new AbortController();
  const interrumpir = () => abort.abort();
  process.once('SIGINT', interrumpir);
  process.once('SIGTERM', interrumpir);
  try {
    const args = process.argv.slice(2);
    if (args.length && (args.length !== 1 || args[0] !== '--comprobar')) throw fallo('Uso: instalar-sonar-mcp.mjs [--comprobar]');
    const rutas = rutasKit();
    directoriosKit(rutas, true);
    const estado = await comprobarJar(rutas.jar);
    if (estado === 'huella') throw fallo(`huella distinta ${rutas.jar}; no se modifica el archivo.`);
    if (args.length || estado === 'ok') {
      process.stdout.write(`${estado === 'ok' ? 'OK' : 'FALTA'} ${rutas.jar}\n`);
      process.exitCode = estado === 'ok' ? 0 : 1;
      return;
    }
    directoriosKit(rutas);
    temporal = path.join(rutas.versionDir, `.descarga-${crypto.randomUUID()}.tmp`);
    archivo = await fs.promises.open(temporal, 'wx', 0o600);
    const test = process.env.DOTAGENTSKIT_TEST_TIMEOUT_MS;
    const timeout = test && /^[1-9][0-9]*$/.test(test) && Number.isSafeInteger(Number(test)) ? Number(test) : 600000;
    timer = setTimeout(() => abort.abort(), timeout);
    let url = new URL(`sonarqube-mcp-server-${VERSION}.jar`, URL_BASE), respuesta;
    for (let saltos = 0; ; saltos++) {
      respuesta = await fetch(url, { redirect: 'manual', signal: abort.signal });
      if (![301, 302, 303, 307, 308].includes(respuesta.status)) break;
      await respuesta.body?.cancel();
      const location = respuesta.headers.get('location');
      if (!location || saltos >= 5) throw fallo('Redirección de descarga inválida.');
      url = new URL(location, url);
      if (url.origin !== 'https://binaries.sonarsource.com' || url.username || url.password) throw fallo('Redirección de descarga fuera del sitio oficial.');
    }
    if (respuesta.status !== 200) { await respuesta.body?.cancel(); throw fallo(`Descarga: HTTP ${respuesta.status}; se exige HTTP 200.`); }
    const hash = crypto.createHash('sha256');
    let bytes = 0;
    for await (const chunk of respuesta.body) {
      bytes += chunk.length;
      if (abort.signal.aborted) throw fallo('Descarga interrumpida o tiempo agotado.');
      if (bytes > 2 * TAMANO_ESPERADO) throw fallo('La descarga supera el tamaño máximo.');
      hash.update(chunk);
      let offset = 0;
      while (offset < chunk.length) {
        const { bytesWritten } = await archivo.write(chunk, offset, chunk.length - offset);
        if (!bytesWritten) throw fallo('No se pudo escribir la descarga.');
        offset += bytesWritten;
      }
    }
    if (abort.signal.aborted) throw fallo('Descarga interrumpida o tiempo agotado.');
    if (hash.digest('hex') !== SHA256) throw fallo('la descarga no coincide con la huella fijada');
    await archivo.sync();
    await archivo.close(); archivo = null;
    directoriosKit(rutas);
    const final = await comprobarJar(rutas.jar);
    if (final === 'huella') throw fallo('huella distinta en el archivo de destino; no se modifica.');
    if (abort.signal.aborted) throw fallo('Descarga interrumpida o tiempo agotado.');
    if (final === 'ok') { await fs.promises.unlink(temporal); temporal = null; }
    else { await fs.promises.rename(temporal, rutas.jar); temporal = null; }
    fs.chmodSync(rutas.jar, 0o600);
    process.stdout.write(`OK ${rutas.jar}\n`);
  } catch (e) {
    process.stderr.write(`BLOCKED: ${e.codigo ? e.message : 'No se pudo descargar el servidor MCP (red, disco, interrupción o tiempo agotado).'}\n`);
    process.exitCode = 2;
  } finally {
    clearTimeout(timer);
    try { await archivo?.close(); if (temporal) await fs.promises.unlink(temporal); }
    catch { process.stderr.write('BLOCKED: no se pudo retirar el temporal de descarga.\n'); process.exitCode = 2; }
    process.removeListener('SIGINT', interrumpir);
    process.removeListener('SIGTERM', interrumpir);
  }
}
await main();
