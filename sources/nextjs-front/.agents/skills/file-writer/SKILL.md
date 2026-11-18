---
name: file-writer
description: Persiste cambios de código aprobados en el working tree del proyecto Next.js y valida tipos con TypeScript y el build de producción.
---

# File Writer (Next.js/TypeScript)

Rol: Persiste código aprobado en el working tree y valida tipos con TypeScript.

## Entrada

Recibes `OUT_DIR` (carpeta donde escribes tu salida) y las rutas de estos archivos:

| Artefacto | Obligatorio | Contenido |
|---|---|---|
| `approved-plan.md` | sí | Plan aprobado con el campo `aprobacion` con el texto literal del usuario. |
| `code-changes*.md` | sí | Uno o varios archivos de código propuesto por capa, con ruta + contenido completo por archivo. |
| `feedback.md` | no | Correcciones pedidas sobre un intento anterior tuyo. Si existe, corrige solo lo que indica. |

Trabaja solo con estos archivos y con el código del proyecto. No asumas contexto fuera de ellos.
Si falta `approved-plan.md` o si el campo `aprobacion` no contiene el texto literal del usuario, **no escribas ningún archivo**: escribe la salida con `estado: bloqueado` y la causa. No reconstruyas la aprobación a partir de contexto implícito.
Si no hay ningún `code-changes*.md`, escribe la salida con `estado: bloqueado` y la causa.

## Tareas

1. **Tarea 1 — Gestión de Dependencias (si aplica)**: Si `approved-plan.md` declara nuevas dependencias en `package.json`:
   - La instalación con el gestor de `frontend.gestor_paquetes` (`npm install`, `pnpm install` o `yarn install`) se ejecuta **antes** de escribir el código y antes de `tsc`, para que los módulos estén disponibles.
   - *Nota de residuo*: Si la feature sufriera un reinicio posterior, `git clean` revierte `package.json` y el lockfile, pero no desinstala automáticamente los paquetes de `node_modules`.

2. **Tarea 2 — Escritura y eliminación**: Guarda o elimina archivos exclusivamente en las siguientes rutas permitidas:
   - `app/`
   - `controllers/`
   - `services/`
   - `repository/`
   - `domains/`
   - `utils/`
   - `lib/`
   - `hooks/`
   - `__tests__/`
   No commitees a git.

3. **Tarea 3 — Atomicidad**: Escribe cada archivo completo. Si alguno falla por error de I/O, detén el lote. Reporta qué archivos se escribieron y cuáles fallaron.

4. **Tarea 4 — Validación de tipos (Post-escritura)**: Una vez escritos los archivos en disco, ejecuta `tsc --noEmit`.
   - *Ruido de entorno en `.next/`*: Si los únicos errores de `tsc` provienen de `.next/types/` o `.next/dev/types/` (rutas obsoletas de compilaciones anteriores), limpia esas carpetas (`rm -rf .next/types .next/dev/types`) y re-ejecuta `tsc --noEmit`.
   - Si `tsc --noEmit` pasa exitosamente, reporta éxito con la lista de archivos escritos.
   - Si `tsc --noEmit` falla por errores en el código del proyecto, **no hagas rollback**: deja los archivos en el working tree y emite `estado: fallo` con el error literal.

5. **Tarea 5 — Build de producción (Post-tipos, bloqueante)**: si `tsc --noEmit` pasó, ejecuta el build del gestor de `frontend.gestor_paquetes` (`npm run build`, `pnpm build` o `yarn build`). Es lo que valida Vercel: compila la app, comprueba tipos y genera las rutas. Tarda más que `tsc`, por eso va después y solo si `tsc` pasó.
   - Si el build pasa, reporta éxito y las rutas afectadas que aparecen en la tabla `Route (app)`.
   - Si falla por errores del código del proyecto, **no hagas rollback**: deja los archivos y emite `estado: fallo` con el error literal.
   - Si falla por entorno (variables de entorno ausentes, `node_modules` incompleto, red), no lo presentes como fallo del código: reporta `estado: bloqueado` con la causa `BLOCKED (infraestructura)`.
   - `.next/` está en `.gitignore`: el build no ensucia el árbol de git.

6. **Tarea 6 — Gate de SonarQube (Post-build)**: si el build pasó, ejecuta `node .agents/scripts/sonar-diff-gate.mjs` y añade sus resultados a la sección "Gate de SonarQube" del reporte. No corrijas ni evalúes sus avisos: los juntan la documentación, las pruebas y la revisión. Si el script falla por infraestructura, reporta `estado: bloqueado` con la causa `BLOCKED (infraestructura)`.

## Reglas

- Aplica `.agents/rules/architecture-rules.md` y `.agents/rules/project.md`.
- No hagas chequeos de estilo manuales: el único SonarQube que ejecutas es el gate de la Tarea 6; evaluar y corregir sus avisos no es cosa tuya.
- Escribe exactamente lo que traen los `code-changes*.md`: si `tsc --noEmit` o el build fallan, devuelve `fallo` con el error literal y **no edites nada más**; no corrijas ni reescribas código por tu cuenta.
- No sobreescribas `next.config.ts`, `package.json`, `tailwind.config.ts`, `.env` ni `tsconfig.json` sin confirmación explícita del usuario en `approved-plan.md` o en una enmienda aprobada del plan.
- No hagas `git commit`. El working tree queda listo sin commitear.
- Crea carpetas solo dentro de las rutas permitidas enumeradas en la Tarea 2.

## Salida

Escribe **un único archivo**: `OUT_DIR/write-report.md`, con este formato:

```markdown
---
artefacto: write-report.md
skill: file-writer
estado: ok | fallo | bloqueado
entradas_leidas: [approved-plan.md, code-changes.integration.md, code-changes.ui.md]   # solo los artefactos realmente leídos
fecha: <ISO-8601>
---

## Resultado

- `tsc --noEmit`: ✅ sin errores | ❌ errores (ver detalles)
- el build del gestor de `frontend.gestor_paquetes` (`npm run build`, `pnpm build` o `yarn build`): ✅ éxito | ❌ error | ⚠️ BLOCKED (infraestructura)
- Gate de SonarQube: ✅ sin avisos | ⚠️ avisos (ver detalles) | ⚠️ BLOCKED (infraestructura)

## Archivos tocados
| Archivo | Estado |
|---------|--------|
| ruta/archivo1.ts | ✅ Escrito |
| ruta/archivo2.ts | ❌ Fallido |

## Detalles de error
(si aplica: output literal de `tsc --noEmit` o `npm run build`)
```
