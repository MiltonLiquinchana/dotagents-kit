---
description: Planificar y aprobar un cambio de versión del front y su documentación.
---

# Cambiar una versión del front

1. **Preflight y diagnóstico inicial.**
   - Ejecuta `bash .agents/scripts/preflight.sh --workflow change-version --fase entrada`. Conserva salida y exit: los códigos y clases están en `.agents/config/codigos.yaml`. Exit 1 detiene; PREPARACION solo permite proponer el comando con permiso y repetir, nunca seguir como pendiente. Exit 2 es error de uso. Exit 0 permite elaborar el plan, sin dar por pasados controles omitidos.
   - Ejecuta `node .agents/scripts/inventario-versiones.mjs` y conserva su JSON para la tabla de cambios. No ejecutes Groovy ni resuelvas expresiones fuera del enlace literal local admitido.

2. **Destino desde `stack.yaml` y alcance.**
   - Compara `frontend.version` de `.agents/stack.yaml` con `next` del inventario/código.
   - Si difieren, propone por sí solo el cambio hacia lo que dice `stack.yaml` (tabla antes/después) y pide confirmación.
   - Solo pregunta la versión cuando el usuario quiere cambiar algo que `stack.yaml` no fija (otra dependencia) o cuando `stack.yaml` y el código ya coinciden. En ese caso el plan enumera las líneas de `.agents/stack.yaml` que edita el usuario y la escritura espera a que lo haga.
   - Si el usuario no quiere subir el código, la alternativa es que él vuelva `frontend.version` en `.agents/stack.yaml` a la versión del código.
   - `frontend-architect` prepara un único plan con tabla antes/después, motivo, `package.json` y lock afectados, compatibilidad y pruebas. No confundas Next, React y TypeScript.

3. **Documentación y citas antes de escribir.**
   - Prepara/carga documentación de las versiones literales de destino aprobadas con `.agents/workflows/preparar-documentacion.md`, usando la excepción de change-version solo para `preparar` y `cargar` (nunca `asociar`). URL, asociaciones y archivos con aprobación explícita.
   - Citas de compatibilidad obtenidas con `documentacion.py preguntar ... --version V` entran al plan como `datos_verificados`. Si falta concretar una URL, se aprueba como enmienda del mismo plan.
   - Si no hay fuente en catálogo para una compatibilidad, el plan lo dice y propone ampliar catálogo o seguir sin cita; decide el usuario.

4. **Plan de cambios.**
   - Si cambia Next y `stack.yaml` y el código ya coinciden pero el usuario quiere otra versión, el plan enumera `frontend.version` como línea que edita el usuario en `.agents/stack.yaml`. Si `stack.yaml` ya trae el destino, no hay líneas que editar. Las versiones no resolubles se muestran y se pide decisión; no se instalan dependencias para adivinarlas.
   - Incluye fuentes de la nueva versión, vínculos del servicio raíz (`.`) y notebooks anteriores archivables sin usuarios.

5. **Aprobación.** Pide aprobación del plan completo. Si el usuario debe editar `stack.yaml`, espera sus ediciones antes de escribir.

6. **Escritura.** Tras las ediciones del stack por el usuario (si tocan), `file-writer` cambia solo los manifiestos y lock aprobados. La actualización del lock y sus comandos deben constar en el plan; pide permiso para instalaciones o descargas. No aceptes rangos para Next.

7. **Asociación y archivo de documentación.** Ejecuta preparación/asociaciones aprobadas; archiva la versión anterior solo sin usuarios y con confirmación. Si se vuelve atrás, propone reactivar el notebook existente, sin duplicarlo. Conserva JSON, Markdown y salidas literales.

8. **Verificación propia.**
   - `node .agents/scripts/comprobar-versiones.mjs`
   - `tsc --noEmit` con el gestor de `frontend.gestor_paquetes` (`npx tsc --noEmit`, `pnpm exec tsc --noEmit` o `yarn tsc --noEmit`), con permiso del usuario; el ruido de `.next/types` se trata como dice `skills/file-writer/SKILL.md:44`.
   - `python3 -I -B .agents/scripts/comprobar-documentacion.py` (estricto, sin argumentos). Para el éxito de change-version solo cuentan las tecnologías/versiones cambiadas; el resto va a pendientes (una línea que no encaje en el formato se trata como pendiente, nunca como éxito).
   - Pruebas completas: opcionales; fallos por entorno se informan aparte y el workflow no falla por ello.

9. **Cierre (sin `preflight.sh`).**
   - No ejecutes `bash .agents/scripts/preflight.sh`.
   - Indica al usuario: «Haz commit de los cambios y ejecuta `bash .agents/scripts/preflight.sh`» como paso suyo.
   - Muestra versiones finales, comprobaciones propias y pendientes con remedio. Nunca muestres credenciales.

Antes de aprobar cualquier plan, sigue `.agents/workflows/references/decisiones-stack.md`; consulta clases, remedios y códigos que resuelve este workflow en `.agents/config/codigos.yaml`.
