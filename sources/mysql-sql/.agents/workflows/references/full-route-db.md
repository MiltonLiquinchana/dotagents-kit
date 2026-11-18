# Ruta Completa (Base de Datos)

Cargado solo cuando el orquestador determinó Ruta Completa. El Paso 0 ya se ejecutó en el orquestador y `RUN_DIR` está inicializado.

## Paso 1 — Análisis de contexto

- **Skill**: `sql-context-analyzer`
- **Ejecución**: subagente (ver `.agents/workflows/references/ejecutar-fase.md`)
- **Entrada**: `RUN_DIR/request.md`
- **Salida esperada**: `RUN_DIR/context.md`
- **Condición**: siempre
- **Según el resultado**:
  - `estado: ok` → Paso 2.
  - `estado: fallo` | `bloqueado` → detener e informar al usuario.

## Paso 2 — Diseño técnico

- **Skill**: `db-architect`
- **Ejecución**: subagente (ver `.agents/workflows/references/ejecutar-fase.md`)
- **Entrada**: `RUN_DIR/request.md`, `RUN_DIR/context.md`
- **Salida esperada**: `RUN_DIR/technical-design.md`
- **Condición**: siempre
- **Según el resultado**:
  - `estado: ok` → Paso 3.
  - `estado: fallo` | `bloqueado` → detener e informar al usuario.

## Paso 3 — Generar Plan de Implementación y esperar aprobación

El workflow integra los artefactos de diseño (`context.md` y `technical-design.md`) en un Plan estructurado que presenta al usuario:

- ¿Qué se quiere realizar?
- Objetos de BD involucrados (tablas, SPs, funciones, vistas, triggers)
- Reutilización de objetos existentes (vía MCP / tgrep)
- ¿Qué puede romperse?
- ¿Cómo se verifica que funcionó?
- ¿Genera o resuelve deuda técnica?
- DDL propuesto y SPs propuestos con pruebas propuestas
- Capacidades de la versión usadas: una línea breve junto a cada bloque de código final, con qué aprovecha y desde qué versión existe.
- Justificación de decisiones

Los contratos, las firmas y los bloques de código del artefacto de diseño (`technical-design.md`) **no se resumen**: el plan los cita por el nombre del artefacto (por ejemplo, "contratos: los de `technical-design.md`, sin cambios"). Si el plan cambia algo respecto al artefacto, lo copia entero en el plan y dice qué cambió.

Al aprobarse el plan, ese artefacto queda congelado con él: si después cambia, se archiva en `history/` como el plan (ver la enmienda del plan aprobado, más abajo).

El plan incluye literalmente estas secciones; cada ruta parte de la raíz del repositorio, igual que en `git status`:

```markdown
## Archivos a crear o modificar
Una viñeta por ruta, sin subencabezados ni tablas dentro de la sección.
- `ruta/desde/la/raíz/del/repo.ext` — crear | modificar | borrar: motivo

## Pruebas a crear o modificar
- `ruta/de/la/prueba.ext` — escenario que cubre
```

La primera sección lista los notebooks `.dbcnb` que se crean o modifican; los objetos de BD se mantienen en la lista de diseño.

Antes de presentar el plan para aprobación, guarda el borrador en `RUN_DIR/plan-draft.md` y ejecuta `python3 -I -B .agents/scripts/comparar-plan.py RUN_DIR/plan-draft.md --solo-plan`. Con exit 2, completa la sección y repite la comprobación antes de presentarlo; con otro error, detente e informa con la salida literal. Repite esta validación tras cualquier ajuste del plan antes de volver a pedir aprobación.

```text
⏸️ ESPERANDO APROBACIÓN — Responde "aprobado" para continuar o indica los cambios necesarios.
```

- **Enmienda del plan aprobado**: si una fase posterior descubre que el plan no se puede cumplir tal cual (falta una dependencia, una regla que el plan no contempló o un contrato que no encaja):
  - la fase devuelve `bloqueado` con la causa;
  - el orquestador propone el cambio acotado, con un diff del plan, y espera la aprobación literal del usuario;
  - el plan anterior pasa a `history/approved-plan.<n>.md` y, con él, los artefactos de diseño congelados que cambien;
  - se añade una fila al manifest con `enmienda <n>`;
  - la enmienda no consume iteraciones de corrección. Tope: 2 enmiendas por feature; con la tercera, se para y se propone reiniciar desde el diseño.
- **Si el usuario indica cambios**: para cambios de redacción/formato, ajusta el Plan directamente; para cambios técnicos, reinvoca `sql-context-analyzer` si cambia el contexto y luego `db-architect` con `RUN_DIR/feedback.md`. Aplica condiciones, vuelve a presentar el Plan actualizado y espera confirmación explícita en cada vuelta. Estos ajustes no consumen iteraciones y no tienen tope automático.
- **Si el usuario aprueba**: el workflow escribe `RUN_DIR/approved-plan.md` con el contenido del plan y la cabecera:
  ```markdown
  ---
  aprobacion: "<texto literal del usuario>"
  fecha: <ISO-8601>
  ---
  ```
  Avanza al Paso 4.

## Paso 4 — Auditoría de diseño

- **Skill**: `sql-code-reviewer` (modo `diseno`)
- **Ejecución**: subagente (ver `.agents/workflows/references/ejecutar-fase.md`)
- **Entrada**: `RUN_DIR/approved-plan.md`
- **Salida esperada**: `RUN_DIR/review.md`
- **Condición**: siempre
- **Según el resultado**:
  - `veredicto: APPROVED` o `APPROVED WITH RECOMMENDATIONS` → Paso 5a.
  - `veredicto: CHANGES REQUIRED` con `tipo_rechazo: IMPLEMENTACION`:
    - Escribir `RUN_DIR/feedback.md` y volver al Paso 3 para ajustar el plan.
  - `veredicto: CHANGES REQUIRED` con `tipo_rechazo: ARQUITECTURA`:
    - Pausa de confirmación con el usuario antes de reiniciar desde el Paso 1. Antes de limpiar, consulta los `execution-report.md` del intento actual y de `history/`: restaurar los archivos con git no revierte el DDL ya ejecutado en la BD viva. Informa los objetos ejecutados y espera instrucciones del usuario antes de reiniciar. Si hay cambios previos del usuario en el notebook, muéstrale la celda rechazada y pide confirmación antes de eliminar solo esa celda; elimina notebooks nuevos con `git clean -fd <ruta>` y restaura los modificados con `git checkout -- <ruta>` solo cuando no haya cambios previos que preservar. Si confirma y no queda ninguna instrucción pendiente sobre la BD, mueve `RUN_DIR` a `history/attempt-<n>/` y reinicia desde el Paso 1 (consume 1 reinicio).
  - `veredicto: BLOCKED (infraestructura)` → detener e informar al usuario.

## Paso 5a — Persistir en el notebook

- **Skill**: `sql-writer`
- **Ejecución**: subagente (ver `.agents/workflows/references/ejecutar-fase.md`)
- **Entrada**: `RUN_DIR/approved-plan.md`, `RUN_DIR/technical-design.md`, `RUN_DIR/review.md`
- **Salida esperada**: `RUN_DIR/persist-report.md`
- **Condición**: requiere `review.md` con `veredicto: APPROVED` o `APPROVED WITH RECOMMENDATIONS`
- **Según el resultado**:
  - `estado: ok` → el workflow compara el plan con el working tree con `python3 -I -B .agents/scripts/comparar-plan.py RUN_DIR/approved-plan.md`: si falta alguno o sobra alguno no declarado (exit 1), detiene el workflow e informa; un archivo extra solo vale si una enmienda lo añadió, en cuyo caso re-ejecuta el script con el plan ya enmendado. Con exit 2 o mayor, detiene el workflow e informa con la salida literal. Solo con exit 0 genera `RUN_DIR/diff.patch` con `git add -N -- <notebooks tocados>` y `git diff HEAD`, y avanza al Paso 5a.5.
  - `estado: fallo` | `bloqueado` → detener e informar al usuario.

## Paso 5a.5 — Gate determinista y sandbox

El workflow ejecuta directamente las herramientas deterministas y captura la salida:
```bash
python3 -B -E .agents/scripts/touched-objects.py --compact
python3 -B -E .agents/scripts/sql-lint.py
python3 -B -E .agents/scripts/sql-sandbox.py run --base HEAD
```
El workflow escribe `RUN_DIR/gate-report.md` con el resultado y códigos de salida.
- **Según el resultado**:
  - Si linter y sandbox terminan sin errores nuevos → Paso 5b.
  - Si hay hallazgos o fallos nuevos:
    - Escribir `RUN_DIR/feedback.md` con el reporte del gate.
    - Volver al Paso 5a (o Paso 3 si requiere cambiar el diseño). Consume 1 iteración.

## Paso 5b — Ejecutar en la BD viva

- **Skill**: `sql-developer`
- **Ejecución**: subagente (ver `.agents/workflows/references/ejecutar-fase.md`)
- **Entrada**: `RUN_DIR/approved-plan.md`, `RUN_DIR/technical-design.md`, `RUN_DIR/review.md`, `RUN_DIR/persist-report.md`, `RUN_DIR/gate-report.md`, `conexión: <conexión>`
- **Salida esperada**: `RUN_DIR/execution-report.md`
- **Condición**: siempre tras pasar el gate determinista
- **Según el resultado**:
  - `estado: ok` → Paso 6.
  - `estado: fallo`:
    - Detener e informar al usuario el estado parcial de la BD devuelto por `execution-report.md`. No reintentar automáticamente sobre DDL.
  - `estado: bloqueado` → detener e informar al usuario.

## Paso 6 — Validar lógica

- **Skill**: `sql-test-engineer`
- **Ejecución**: subagente (ver `.agents/workflows/references/ejecutar-fase.md`)
- **Entrada**: `RUN_DIR/approved-plan.md`, `RUN_DIR/execution-report.md`, `conexión: <conexión>`
- **Salida esperada**: `RUN_DIR/test-report.md`
- **Condición**: siempre
- **Según el resultado**:
  - `estado: ok` → Paso 7.
  - `estado: fallo`:
    - Escribir `RUN_DIR/feedback.md` con las correcciones requeridas de `test-report.md`.
    - Volver al Paso 5a si es ajuste de script o al Paso 3 si requiere rediseño (consume 1 iteración).
  - `estado: bloqueado` → detener e informar al usuario.

## Paso 7 — Optimizar rendimiento

- **Skill**: `performance-optimizer`
- **Ejecución**: subagente (ver `.agents/workflows/references/ejecutar-fase.md`)
- **Entrada**: `RUN_DIR/execution-report.md`, `RUN_DIR/test-report.md`, `conexión: <conexión>`
- **Salida esperada**: `RUN_DIR/performance-report.md`
- **Condición**: requiere `test-report.md` con `estado: ok`
- **Según el resultado**:
  - `estado: ok` → si no propone cambios o el plan ya es óptimo, Paso 8a. Si propone optimizaciones que el usuario desea aplicar, se incorporan al plan y se re-auditan (Paso 4).
  - `estado: bloqueado` → registrar causa y avanzar al Paso 8a.

## Paso 8a — Documentación técnica

- **Skill**: `sql-tech-writer`
- **Ejecución**: subagente (ver `.agents/workflows/references/ejecutar-fase.md`)
- **Entrada**: `RUN_DIR/approved-plan.md`, `RUN_DIR/diff.patch`
- **Salida esperada**: `RUN_DIR/docs-summary.md`
- **Condición**: siempre
- **Según el resultado**:
  - `estado: ok` → Paso 8b.
  - `estado: fallo` | `bloqueado` → registrar advertencia y continuar al Paso 8b.

## Paso 8b — Documentación de objeto

- **Skill**: `sql-object-analyzer` (modo `creacion`)
- **Ejecución**: subagente (ver `.agents/workflows/references/ejecutar-fase.md`)
- **Entrada**: `RUN_DIR/persist-report.md`, `RUN_DIR/docs-summary.md`
- **Salida esperada**: `RUN_DIR/object-doc-report.md`
- **Condición**: siempre
- **Según el resultado**:
  - `estado: ok` → actualizar `RUN_DIR/diff.patch` con `git add -N -- <notebooks tocados>` y `git diff HEAD` y avanzar al Paso 9.
  - `estado: fallo` | `bloqueado` → registrar advertencia y avanzar al Paso 9.

## Paso 9 — Actualizar Base de Conocimiento

- **Skill**: `knowledge-writer` (modo `escribir`)
- **Ejecución**: subagente (ver `.agents/workflows/references/ejecutar-fase.md`)
- **Entrada**: `RUN_DIR/approved-plan.md`, `RUN_DIR/diff.patch`, `tipo: feature`, `RUN_DIR/docs-summary.md` (si existe)
- **Salida esperada**: `RUN_DIR/knowledge-report.md`
- **Condición**: siempre
- **Según el resultado**:
  - `estado: ok` → Paso 9.5.
  - `estado: fallo` → registrar advertencia y avanzar al Paso 9.5.

## Paso 9.5 — Verificar vinculación de Base de Conocimiento

- **Skill**: `knowledge-writer` (modo `verificar`)
- **Ejecución**: subagente (ver `.agents/workflows/references/ejecutar-fase.md`)
- **Entrada**: `RUN_DIR/knowledge-report.md`
- **Salida esperada**: `RUN_DIR/link-check.md`
- **Condición**: siempre
- **Según el resultado**:
  - `estado: ok` → Paso 10.
  - `estado: fallo` | `bloqueado` → bloquear el commit; invocar inmediatamente `knowledge-writer` para autocorregir el frontmatter de las notas con `estado_vinculacion: pendiente` y repetir la verificación hasta obtener `estado: ok`.

## Paso 10 — Confirmar cambios atómicamente en Git

El workflow ejecuta:
```bash
git status --porcelain
git add -- <rutas explícitas>
git commit -m "feat: <descripcion-de-la-feature>"
```
La lista de rutas es la unión de `## Archivos tocados` de todas las salidas del intento aprobado y las notas listadas en `knowledge-report.md`. Antes de añadir, compara `git status --porcelain` con esa lista; si queda cualquier archivo modificado o sin seguimiento fuera de ella, detente e informa al usuario sin añadirlo ni descartarlo. Si el commit falla, detén e informa al usuario.

## Paso 10.5 — Actualizar el grafo (solo si herramientas.codebase_memory es true)

El workflow ejecuta:
Solo si `herramientas.codebase_memory` es `true`, ejecuta `python3 -I -B .agents/scripts/codebase-memory.py --indexar`; con `false`, registra el paso como omitido en `manifest.md`.

```bash
if [ "$(python3 -B -E .agents/scripts/stack.py get herramientas.codebase_memory)" = true ]; then
  python3 -I -B .agents/scripts/codebase-memory.py --indexar > "$RUN_DIR/graph-status.md" 2>&1
else
  printf '%s\n' 'OMITIDO: herramientas.codebase_memory=false' > "$RUN_DIR/graph-status.md"
fi
```
Genera `RUN_DIR/graph-status.md`.

Antes de aprobar o enmendar el plan, aplica `.agents/workflows/references/decisiones-stack.md`; incluye el registro entre los archivos aprobados si cambia.
