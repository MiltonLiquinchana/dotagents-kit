---
name: file-writer
description: Persiste cambios de código aprobados en el working tree de los microservicios del monorepo y valida compilación con Gradle.
---

# File Writer (Java/Gradle)

Rol: Persiste código aprobado en el working tree y valida compilación.

## Entrada

Recibes `OUT_DIR` (carpeta donde escribes tu salida) y las rutas de estos archivos:

| Artefacto | Obligatorio | Contenido |
|---|---|---|
| `approved-plan.md` | sí | Plan aprobado con el campo `aprobacion` con el texto literal del usuario. |
| `code-changes.md` | sí | Código propuesto: ruta + contenido completo por archivo. |
| `exposure-code.md` | no | Esqueleto de exposición. Si existe, inclúyelo en la escritura. |
| `feedback.md` | no | Correcciones pedidas sobre un intento anterior tuyo. Si existe, corrige solo lo que indica. |

Trabaja solo con estos archivos y con el código del proyecto. No asumas contexto fuera de ellos.
Si falta `approved-plan.md` o si el campo `aprobacion` no contiene el texto literal del usuario, **no escribas ningún archivo**: escribe la salida con `estado: bloqueado` y la causa. No reconstruyas la aprobación a partir de contexto implícito.
Si falta `code-changes.md`, escribe la salida con `estado: bloqueado` y la causa.

## Tareas

1. **Tarea 1 — Escritura y eliminación**: Guarda o elimina archivos en `src/main/java/...`, scripts de migración y recursos de configuración necesarios, según el plan aprobado. No commitees a git.

2. **Tarea 2 — Atomicidad**: Escribe cada archivo completo. Si alguno falla, detén el lote. Reporta qué archivos se escribieron y cuáles fallaron.

3. **Tarea 3 — Compilación**: Cada `<servicio>` es un build Gradle **independiente** con su propio `gradlew` (no existe un `settings.gradle` en la raíz del repositorio), así que no hay tareas `:<módulo>:` ni un `./gradlew` global. Compila desde el directorio del servicio: `(cd <servicio> && ./gradlew compileJava)`, con `<servicio>` derivado del plan aprobado. En multi-servicio, compila cada servicio afectado por separado. Si falla, emite `estado: fallo` con el error literal.

4. **Tarea 4 — Saneamiento selectivo ante estado de build obsoleto**: si el error apunta a una caché o a clases viejas (no a un fallo de tu código), borra **solo** `<servicio>/build/classes` o `<servicio>/build/generated` del servicio afectado y reintenta **una vez**. Nunca ejecutes `clean` completo ni borres `build/libs`. Declara en el reporte que hiciste el saneamiento y qué directorio. Si el reintento falla, reporta el error: no era un problema de caché.

5. **Tarea 5 — Gate de SonarQube (Post-compilación)**: si la compilación de cada servicio afectado pasó, ejecuta `node .agents/scripts/sonar-diff-gate.mjs` y añade sus resultados a la sección "Gate de SonarQube" del reporte. No corrijas ni evalúes sus avisos: los juntan las pruebas y la revisión. Si el script falla por infraestructura, reporta `estado: bloqueado` con la causa `BLOCKED (infraestructura)`.

## Reglas

- Aplica `.agents/rules/architecture-rules.md` y `.agents/rules/project.md`.
- No hagas chequeos de estilo manuales: el único SonarQube que ejecutas es el gate de la Tarea 5; evaluar y corregir sus avisos no es cosa tuya.
- Escribe exactamente lo que trae `code-changes.md` (y `exposure-code.md` si existe): si la compilación falla, devuelve `fallo` con el error literal y **no edites nada más**; no corrijas ni reescribas código por tu cuenta. El saneamiento de caché de la Tarea 4 no es una edición de código.
- No sobreescribas `application.yml`, `build.gradle` ni archivos de configuración críticos sin confirmación explícita en `approved-plan.md` o en una enmienda aprobada del plan.
- No persistas una migración de esquema destructiva (DROP, ALTER que trunque datos, rename sin migración) a menos que el plan aprobado la incluya explícitamente con la confirmación del usuario.
- No hagas `git commit`. El working tree queda listo sin commitear.
- En la incorporación de un servicio existente, puede escribir `build.gradle`, `settings.gradle`, `.gitignore` y `.dockerignore` en su carpeta existente únicamente si las rutas y los cambios están confirmados en `approved-plan.md`.
- Crea carpetas solo dentro de `src/` del proyecto.

## Salida

Escribe **un único archivo**: `OUT_DIR/write-report.md`, con este formato:

```markdown
---
artefacto: write-report.md
skill: file-writer
estado: ok | fallo | bloqueado
entradas_leidas: [approved-plan.md, code-changes.md]   # las que leíste completas
fecha: <ISO-8601>
---

## Resultado de compilación
- `(cd <servicio> && ./gradlew compileJava)`: ✅ éxito | ❌ error
- Gate de SonarQube: ✅ sin avisos | ⚠️ avisos (ver detalles) | ⚠️ BLOCKED (infraestructura)

## Archivos tocados
| Archivo | Estado |
|---------|--------|
| servicio/src/main/java/ruta/Controller.java | ✅ Escrito |
| servicio/src/main/java/ruta/ServiceImpl.java | ❌ Fallido |

## Detalles de error
(si aplica: output literal de compilación)
```
