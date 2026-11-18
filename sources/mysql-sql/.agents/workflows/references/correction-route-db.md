# Ruta de Corrección (Base de Datos)

Cargado solo cuando el orquestador determinó Ruta de Corrección. El Paso 0 ya se ejecutó en el orquestador y `RUN_DIR` está inicializado.

## C1 — Consulta de contexto

El workflow localiza los objetos afectados en este orden:
1. Busca en `knowledge-base/` con `tgrep` el historial de correcciones y las notas del objeto. Si `tgrep` no responde, ejecuta `tgrep serve knowledge-base/` y vuelve a intentar; si sigue sin estar operativo, detén el flujo e informa al usuario.
2. Consulta el esquema real mediante MCP en modo lectura (`SHOW CREATE` y `schema_<conexión>`). Si MCP no responde, detén el flujo e informa al usuario; no sustituyas la fuente real por el grafo ni infieras el esquema.
3. Si `herramientas.graphify` es `true`, usa `GRAPHIFY_BACKEND=none graphify query` o `GRAPHIFY_BACKEND=none graphify path` como complemento, no como fuente de verdad del esquema; si es `false`, omite esas consultas.

**Historial de correcciones (vinculante)**: busca `<objeto>-fixes.md` con `tgrep --files knowledge-base/ | grep -E "/<objeto>-fixes\\.md$"` (ver `.agents/rules/tgrep.md`). Si existe, trátalo como restricción dura del Plan de Corrección: no propongas un enfoque ya registrado como fallido sin explicar por qué la condición cambió.

## C2 — Plan de Corrección y esperar aprobación

El workflow redacta el Plan de Corrección:
- ¿Qué se corrige?
- Objetos/scripts afectados
- Código actual vs propuesto con diff
- Capacidades de la versión usadas: una línea breve junto a cada bloque de código final, con qué aprovecha y desde qué versión existe.
- ¿Puede romper algo?
- ¿Cómo se verifica?
- Verificación con reglas del proyecto
- Documentación: ¿altera comportamiento ya documentado? (Sí/No)

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

- **Enmienda del plan aprobado**: vale aquí lo definido en la Ruta Completa (Paso 1e): una fase posterior que no pueda cumplir el plan devuelve `bloqueado` con la causa; el orquestador propone el cambio acotado con su diff, archiva el plan anterior en `history/approved-plan.<n>.md` con sus artefactos congelados si cambian, añade una fila al manifest con `enmienda <n>`, no consume iteraciones y respeta el tope de 2 enmiendas por feature.

- Si el usuario solicita cambios técnicos o incluye condiciones, aplícalos, presenta el Plan de Corrección actualizado y espera confirmación final. Cada vuelta requiere confirmación explícita, no tiene tope automático y no consume iteraciones.
- **Si el usuario aprueba**: el workflow escribe `RUN_DIR/approved-plan.md` con el contenido del plan y la cabecera:
  ```markdown
  ---
  aprobacion: "<texto literal del usuario>"
  fecha: <ISO-8601>
  Documentación: sí | no
  ---
  ```
  Avanza a C2.5.

## C2.5 — Auditoría previa del script

- **Skill**: `sql-code-reviewer` (modo `diseno`)
- **Ejecución**: subagente (ver `.agents/workflows/references/ejecutar-fase.md`)
- **Entrada**: `RUN_DIR/approved-plan.md`
- **Salida esperada**: `RUN_DIR/review.md`
- **Condición**: siempre
- **Según el resultado**:
  - `veredicto: APPROVED` o `APPROVED WITH RECOMMENDATIONS` → C3.
  - `veredicto: CHANGES REQUIRED` con `tipo_rechazo: IMPLEMENTACION`:
    - Escribir `RUN_DIR/feedback.md` y volver a C2 para ajustar el plan.
  - `veredicto: CHANGES REQUIRED` con `tipo_rechazo: ARQUITECTURA`:
    - Pausa de confirmación con el usuario antes de escalar a Ruta Completa. Antes de limpiar, consulta los `execution-report.md` del intento actual y de `history/`: restaurar los archivos con git no revierte el DDL ya ejecutado en la BD viva. Informa los objetos ejecutados y espera instrucciones del usuario antes de reiniciar. Si hay cambios previos del usuario en el notebook, muéstrale la celda rechazada y pide confirmación antes de eliminar solo esa celda; elimina notebooks nuevos con `git clean -fd <ruta>` y restaura los modificados con `git checkout -- <ruta>` solo cuando no haya cambios previos que preservar. Si confirma y no queda ninguna instrucción pendiente sobre la BD, mueve `RUN_DIR` a `history/attempt-<n>/` y escala a Ruta Completa (consume 1 reinicio).
  - `veredicto: BLOCKED (infraestructura)` → detener e informar al usuario.

## C3 — Persistir la corrección en notebook

- **Skill**: `sql-writer`
- **Ejecución**: subagente (ver `.agents/workflows/references/ejecutar-fase.md`)
- **Entrada**: `RUN_DIR/approved-plan.md`, `RUN_DIR/technical-design.md` (si existe), `RUN_DIR/review.md`
- **Salida esperada**: `RUN_DIR/persist-report.md`
- **Condición**: requiere `review.md` con `veredicto: APPROVED` o `APPROVED WITH RECOMMENDATIONS`
- **Según el resultado**:
  - `estado: ok` → el workflow compara el plan con el working tree con `python3 -I -B .agents/scripts/comparar-plan.py RUN_DIR/approved-plan.md`: si falta alguno o sobra alguno no declarado (exit 1), detiene el workflow e informa; un archivo extra solo vale si una enmienda lo añadió, en cuyo caso re-ejecuta el script con el plan ya enmendado. Con exit 2 o mayor, detiene el workflow e informa con la salida literal. Solo con exit 0 genera `RUN_DIR/diff.patch` con `git add -N -- <notebooks tocados>` y `git diff HEAD`, y avanza a C3.5.
  - `estado: fallo` | `bloqueado` → detener e informar al usuario.

## C3.5 — Gate determinista y sandbox

El workflow ejecuta:
```bash
python3 -B -E .agents/scripts/touched-objects.py --compact
python3 -B -E .agents/scripts/sql-lint.py
python3 -B -E .agents/scripts/sql-sandbox.py run --base HEAD
```
El workflow escribe `RUN_DIR/gate-report.md`.
- **Según el resultado**:
  - Sin fallos nuevos → C4.
  - Con fallos o hallazgos nuevos:
    - Escribir `RUN_DIR/feedback.md` y volver a C3 (consume 1 iteración).

## C4 — Re-auditar la corrección persistida

- **Skill**: `sql-code-reviewer` (modo `persistido`)
- **Ejecución**: subagente (ver `.agents/workflows/references/ejecutar-fase.md`)
- **Entrada**: `RUN_DIR/approved-plan.md`, `RUN_DIR/persist-report.md`, `RUN_DIR/gate-report.md`
- **Salida esperada**: `RUN_DIR/review.md`
- **Condición**: siempre
- **Según el resultado**:
  - `veredicto: APPROVED` o `APPROVED WITH RECOMMENDATIONS` → C5.
  - `veredicto: CHANGES REQUIRED` con `tipo_rechazo: IMPLEMENTACION`:
    - Escribir `RUN_DIR/feedback.md` y volver a C3 (consume 1 iteración).
  - `veredicto: CHANGES REQUIRED` con `tipo_rechazo: ARQUITECTURA`:
    - Pausa de confirmación con el usuario antes de reiniciar por Ruta Completa (Paso 1). Antes de limpiar, consulta los `execution-report.md` del intento actual y de `history/`: restaurar los archivos con git no revierte el DDL ya ejecutado en la BD viva. Informa los objetos ejecutados y espera instrucciones del usuario antes de reiniciar. Aplica las precauciones de cambios previos y notebooks nuevos descritas en la regla de limpieza de `build-database-feature.md`.
  - `veredicto: BLOCKED (infraestructura)` → detener e informar al usuario.

## C5 — Ejecutar en BD viva

- **Skill**: `sql-developer`
- **Ejecución**: subagente (ver `.agents/workflows/references/ejecutar-fase.md`)
- **Entrada**: `RUN_DIR/approved-plan.md`, `RUN_DIR/technical-design.md` (si existe), `RUN_DIR/review.md`, `RUN_DIR/persist-report.md`, `RUN_DIR/gate-report.md`, `conexión: <conexión>`
- **Salida esperada**: `RUN_DIR/execution-report.md`
- **Condición**: siempre
- **Según el resultado**:
  - `estado: ok` → si toca lógica de negocio (SPs, funciones, triggers, vistas, eventos), C6; si no, C6.5.
  - `estado: fallo`:
    - Detener e informar estado parcial de la BD.
  - `estado: bloqueado` → detener e informar al usuario.

## C6 — Pruebas condicionales

- **Skill**: `sql-test-engineer`
- **Ejecución**: subagente (ver `.agents/workflows/references/ejecutar-fase.md`)
- **Entrada**: `RUN_DIR/approved-plan.md`, `RUN_DIR/execution-report.md`, `conexión: <conexión>`
- **Salida esperada**: `RUN_DIR/test-report.md`
- **Condición**: solo si la corrección modifica lógica de negocio
- **Según el resultado**:
  - `estado: ok` → C6.5.
  - `estado: fallo`:
    - Escribir `RUN_DIR/feedback.md` y volver a C3 (consume 1 iteración).
  - `estado: bloqueado` → detener e informar al usuario.

## C6.5 — Actualizar documentación del objeto

- **Skill**: `sql-object-analyzer` (modo `creacion`)
- **Ejecución**: subagente (ver `.agents/workflows/references/ejecutar-fase.md`)
- **Entrada**: `RUN_DIR/persist-report.md`
- **Salida esperada**: `RUN_DIR/object-doc-report.md`
- **Condición**: siempre
- **Según el resultado**:
  - `estado: ok` → C7.
  - `estado: fallo` | `bloqueado` → registrar advertencia y avanzar a C7.

## C7 — Actualizar Base de Conocimiento

- **Skill**: `knowledge-writer` (modo `escribir`)
- **Ejecución**: subagente (ver `.agents/workflows/references/ejecutar-fase.md`)
- **Entrada**: `RUN_DIR/approved-plan.md`, `RUN_DIR/diff.patch`, `tipo: fix`
- **Salida esperada**: `RUN_DIR/knowledge-report.md`
- **Condición**: siempre
- **Según el resultado**:
  - `estado: ok` → C7.5.
  - `estado: fallo` → registrar advertencia y avanzar a C7.5.

## C7.5 — Verificar vinculación de Base de Conocimiento

- **Skill**: `knowledge-writer` (modo `verificar`)
- **Ejecución**: subagente (ver `.agents/workflows/references/ejecutar-fase.md`)
- **Entrada**: `RUN_DIR/knowledge-report.md`
- **Salida esperada**: `RUN_DIR/link-check.md`
- **Condición**: siempre
- **Según el resultado**:
  - `estado: ok` → C8.
  - `estado: fallo` | `bloqueado` → bloquear el commit; invocar inmediatamente `knowledge-writer` para autocorregir el frontmatter de las notas con `estado_vinculacion: pendiente` y repetir la verificación hasta obtener `estado: ok`.

## C8 — Confirmar cambios atómicamente en Git

El workflow ejecuta:
```bash
git status --porcelain
git add -- <rutas explícitas>
git commit -m "fix: <descripcion-de-la-correccion>"
```
La lista de rutas es la unión de `## Archivos tocados` de todas las salidas del intento aprobado y las notas listadas en `knowledge-report.md`. Antes de añadir, compara `git status --porcelain` con esa lista; si queda cualquier archivo modificado o sin seguimiento fuera de ella, detente e informa al usuario sin añadirlo ni descartarlo. Si el commit falla, detén e informa al usuario.

## C8.5 — Actualizar el grafo

El workflow ejecuta:
```bash
Solo si `herramientas.graphify` es `true`, ejecuta `GRAPHIFY_BACKEND=none graphify . --update`; con `false`, registra el paso como omitido en `manifest.md`.
```

Antes de aprobar o enmendar el plan, aplica `.agents/workflows/references/decisiones-stack.md`; incluye el registro entre los archivos aprobados si cambia.
