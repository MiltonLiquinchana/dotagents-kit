# Ruta de Corrección (Frontend)

Cargado solo cuando el orquestador determinó Ruta de Corrección. El Paso 0 ya se ejecutó en el orquestador y `RUN_DIR` está inicializado.

## C1 — Consulta al Grafo

Antes de implementar, comprueba el núcleo compartido en `utils/`. Si falta, propone ejecutar `.agents/workflows/bootstrap-project.md` y espera la respuesta del usuario; no escribas un núcleo propio.

El workflow ejecuta `GRAPHIFY_BACKEND=none graphify query` o `GRAPHIFY_BACKEND=none graphify path` antes de tocar archivos, y verifica historial de correcciones en `knowledge-base/` con `tgrep`.

## C2 — Plan de Corrección y esperar aprobación

El workflow redacta el Plan de Corrección:
- ¿Qué se corrige?
- Código actual vs propuesto con diff
- Capacidades de la versión usadas: una línea breve junto a cada bloque de código final, con qué aprovecha y desde qué versión existe.
- ¿Puede romper algo?
- ¿Cómo se verifica?
- Verificación con reglas del proyecto
- Documentación: ¿el cambio altera comportamiento ya documentado? (Sí/No)

El plan incluye literalmente estas secciones; cada ruta parte de la raíz del repositorio, igual que en `git status`:

```markdown
## Archivos a crear o modificar
Una viñeta por ruta, sin subencabezados ni tablas dentro de la sección. Si `ux-spec.md` propone tokens nuevos, incluye aquí el archivo de tokens del proyecto (`app/globals.css` o su fuente de estilos, según corresponda).
- `ruta/desde/la/raíz/del/repo.ext` — crear | modificar | borrar: motivo

## Pruebas a crear o modificar
- `ruta/de/la/prueba.ext` — escenario que cubre
```

Antes de presentar el plan para aprobación, guarda el borrador en `RUN_DIR/plan-draft.md` y ejecuta `python3 -I -B .agents/scripts/comparar-plan.py RUN_DIR/plan-draft.md --solo-plan`. Con exit 2, completa la sección y repite la comprobación antes de presentarlo; con otro error, detente e informa con la salida literal. Repite esta validación tras cualquier ajuste del plan antes de volver a pedir aprobación.

```text
ESPERANDO APROBACIÓN — Responde "aprobado" para continuar o indica los cambios necesarios.
```

- **Enmienda del plan aprobado**: vale aquí lo definido en la Ruta Completa (Paso 5): una fase posterior que no pueda cumplir el plan devuelve `bloqueado` con la causa; el orquestador propone el cambio acotado con su diff, archiva el plan anterior en `history/approved-plan.<n>.md` con sus artefactos congelados si cambian, añade una fila al manifest con `enmienda <n>`, no consume iteraciones y respeta el tope de 2 enmiendas por feature.

- Si el usuario pide un cambio técnico, reinvoca la primera skill de diseño cuyo resultado cambia y todas las posteriores dependientes: Paso 1 → 2 → 3 → 4. Aplica las condiciones, vuelve a presentar el Plan actualizado y espera confirmación final. Cada ajuste requiere confirmación explícita y no consume iteraciones.
- **Si el usuario aprueba**: el workflow escribe `RUN_DIR/approved-plan.md` con el contenido del plan y la cabecera:
  ```markdown
  ---
  aprobacion: "<texto literal del usuario>"
  fecha: <ISO-8601>
  Documentación: sí | no
  ---
  ```
  Avanza a C3.

## C3 — Desarrollar corrección

- Invoca por separado cada skill de la capa afectada, pasándole en el mensaje fijo el nombre exacto de su salida con `OUT_DIR` igual a `RUN_DIR` (no hay renombrado posterior):
  - **Integración** (`api-integration-architect`, modo `implementacion`): escribe `code-changes.integration.md`.
  - **UI/hooks** (`frontend-developer`): escribe `code-changes.ui.md`.
  - Si el cambio afecta ambas capas, ejecuta ambas en ese orden y conserva ambos artefactos. Si un reintento no identifica claramente la capa, reintenta ambas.
- **Entrada**: `RUN_DIR/approved-plan.md`, `RUN_DIR/data-contracts.md`, `RUN_DIR/component-architecture.md`, `RUN_DIR/ux-spec.md` (si existe)
- **Salida esperada**: un archivo por capa afectada, con nombre `RUN_DIR/code-changes.<capa>.md`.
- **Condición**: siempre
- **Según el resultado**:
  - `estado: ok` → C4.
  - `estado: fallo` | `bloqueado` → detener e informar al usuario.

## C4 — Persistir corrección

- **Skill**: `file-writer`
- **Ejecución**: subagente (ver `.agents/workflows/references/ejecutar-fase.md`)
- **Entrada**: `RUN_DIR/approved-plan.md` y todos los archivos `RUN_DIR/code-changes*.md` presentes.
- **Salida esperada**: `RUN_DIR/write-report.md`
- **Condición**: siempre
- **Según el resultado**:
  - `estado: ok` → el workflow compara el plan con el working tree con `python3 -I -B .agents/scripts/comparar-plan.py RUN_DIR/approved-plan.md --ignorar LOCKFILE`, sustituyendo LOCKFILE según `frontend.gestor_paquetes` por `package-lock.json` (npm), `pnpm-lock.yaml` (pnpm) o `yarn.lock` (yarn): si falta alguno o sobra alguno no declarado (exit 1), detiene el workflow e informa; un archivo extra solo vale si una enmienda lo añadió, en cuyo caso re-ejecuta el script con el plan ya enmendado. Con exit 2 o mayor, detiene el workflow e informa con la salida literal. Solo con exit 0 genera `RUN_DIR/diff.patch` con `git add -N -- <archivos tocados>` y `git diff HEAD`, y avanza a C4.5.
  - `estado: fallo` (fallo de compilación `tsc --noEmit` o el build del gestor de `frontend.gestor_paquetes` (`npm run build`, `pnpm build` o `yarn build`)):
    - Identificar las capas que deben corregirse según `feedback.md`; si no está claro, reintentar ambas. Antes de cada re-invocación, mover solo el artefacto activo de esa capa a `history/code-changes.<capa>.<n>.md`.
    - Escribir `RUN_DIR/feedback.md` con el error de tipos literal.
    - Volver a C3 (consume 1 iteración del ciclo de corrección).
  - `estado: bloqueado` → detener e informar al usuario.

## C4.5 — Actualizar Grafo de Código

El workflow ejecuta:
```bash
GRAPHIFY_BACKEND=none graphify . --update
```
Genera `RUN_DIR/graph-status.md`. Si falla, avisa y continúa a C5.

## C5 — Pruebas condicionales

- **Skill**: `test-engineer`
- **Ejecución**: subagente (ver `.agents/workflows/references/ejecutar-fase.md`)
- **Entrada**: `RUN_DIR/approved-plan.md`, `RUN_DIR/diff.patch`
- **Salida esperada**: `RUN_DIR/test-report.md`
- **Condición**: solo si la corrección toca `services/` o `controllers/` y existe script `"test"` en `package.json`
- **Según el resultado**:
  - `estado: ok` → C6.
  - `estado: fallo`:
    - Identificar las capas que deben corregirse según `feedback.md`; si no está claro, reintentar ambas. Antes de cada re-invocación, mover solo el artefacto activo de esa capa a `history/code-changes.<capa>.<n>.md`.
    - Escribir `RUN_DIR/feedback.md` con las correcciones requeridas de `test-report.md`.
    - Volver a C3 (consume 1 iteración del ciclo de corrección).
  - `estado: bloqueado` → detener e informar al usuario.

## C6 — Revisión de calidad y Static Analysis Gate

- **Skill**: `code-reviewer`
- **Ejecución**: subagente (ver `.agents/workflows/references/ejecutar-fase.md`)
- **Entrada**: `RUN_DIR/approved-plan.md`, `RUN_DIR/diff.patch`, `RUN_DIR/write-report.md`, `RUN_DIR/test-report.md` (si existe), `RUN_DIR/graph-status.md` (si existe)
- **Salida esperada**: `RUN_DIR/review.md`
- **Condición**: siempre
- **Según el resultado**:
  - `veredicto: APPROVED` o `APPROVED WITH RECOMMENDATIONS` → antes de avanzar, ejecuta `node .agents/scripts/sonar-diff-gate.mjs --comprobar-recibo RUN_DIR/gate-recibo.json`; si falla, repite la revisión sin consumir iteración. Si pasa, C7.
  - `veredicto: CHANGES REQUIRED` con `tipo_rechazo: IMPLEMENTACION`:
    - Identificar las capas que deben corregirse según `feedback.md`; si no está claro, reintentar ambas. Antes de cada re-invocación, mover solo el artefacto activo de esa capa a `history/code-changes.<capa>.<n>.md`.
    - Escribir `RUN_DIR/feedback.md` con los hallazgos de `review.md`.
    - Volver a C3 (consume 1 iteración del ciclo de corrección).
  - `veredicto: CHANGES REQUIRED` con `tipo_rechazo: ARQUITECTURA`:
    - Pausa de confirmación con el usuario antes de escalar a Ruta Completa. Si el usuario confirma: ejecutar limpieza git con las rutas de `## Archivos tocados`, mover `RUN_DIR` a `history/attempt-<n>/`, ejecutar `GRAPHIFY_BACKEND=none graphify . --update` e iniciar Ruta Completa desde el Paso 1 (consume 1 reinicio).
  - `veredicto: BLOCKED (infraestructura)` → detener e informar al usuario sin consumir iteraciones.

## C7 — Actualizar Base de Conocimiento

- **Skill**: `knowledge-writer` (modo `escribir`)
- **Ejecución**: subagente (ver `.agents/workflows/references/ejecutar-fase.md`)
- **Entrada**: `RUN_DIR/approved-plan.md`, `RUN_DIR/diff.patch`, `tipo: fix`
- **Salida esperada**: `RUN_DIR/knowledge-report.md`
- **Condición**: siempre
- **Según el resultado**:
  - `estado: ok` → C8.
  - `estado: fallo` → registrar advertencia y continuar a C8.

## C8 — Verificar vinculación de Base de Conocimiento

- **Skill**: `knowledge-writer` (modo `verificar`)
- **Ejecución**: subagente (ver `.agents/workflows/references/ejecutar-fase.md`)
- **Entrada**: `RUN_DIR/knowledge-report.md`
- **Salida esperada**: `RUN_DIR/link-check.md`
- **Condición**: siempre
- **Según el resultado**:
  - `estado: ok` → C8.5.
  - `estado: fallo` | `bloqueado` → bloquear el commit; invocar inmediatamente `knowledge-writer` para autocorregir el frontmatter de las notas con `estado_vinculacion: pendiente` y repetir la verificación hasta obtener `estado: ok`.

## C8.5 — Prueba de humo

- **Ejecución**: la hace el propio workflow (orquestador), no un subagente. Registra el resultado en `RUN_DIR/smoke-test.md` con la ruta pedida, el status y los fragmentos del HTML comprobados.

Tras la revisión y antes del commit:

1. Arranca la app **como la arrancaría el usuario**: build de producción (si la corrección lo tocó) y el arranque del gestor de `frontend.gestor_paquetes` (`npm run start`, `pnpm start` o `yarn start`), con su `.env.local`; no pases variables de configuración por la línea de comandos.
2. Pide la ruta corregida y comprueba en el HTML el estado esperado.
3. Para el proceso y comprueba que el puerto queda libre.

- **Según el resultado**:
  - `estado: ok` → C9.
  - `estado: fallo` (la API responde conforme a su contrato y el HTML no muestra el estado esperado): registra la respuesta literal en `RUN_DIR/smoke-test.md`, escribe `RUN_DIR/feedback.md` con lo observado vs lo esperado y vuelve a C3 (consume 1 iteración del ciclo de corrección).
  - `estado: bloqueado` (conexión a la API rechazada, tiempo agotado o respuesta ajena al contrato de la API, por ejemplo otro servidor en ese puerto): registra la causa literal y la URL que usó la app en `RUN_DIR/smoke-test.md`, detente e informa sin consumir iteración.
  - `estado: bloqueado` (falta la configuración local): detente con el mensaje exacto "copia `.env.example` a `.env.local`".

## C9 — Confirmar cambios atómicamente en Git

El workflow ejecuta:
```bash
git status --porcelain
git add -- <rutas explícitas>
git commit -m "fix: <descripcion-de-la-correccion>"
```
La lista de rutas es la unión de `## Archivos tocados` de todas las salidas del intento aprobado y las notas listadas en `knowledge-report.md`. Incluye `package.json` y el lockfile del gestor si se instalaron dependencias. Antes de añadir, compara `git status --porcelain` con esa lista; si queda cualquier archivo modificado o sin seguimiento fuera de ella, detente e informa al usuario sin añadirlo ni descartarlo. Si el commit falla, detén e informa al usuario con el error literal; no reintentes ni asumas que el working tree sigue igual que el aprobado.

Antes de aprobar o enmendar el plan, aplica `.agents/workflows/references/decisiones-stack.md`; incluye el registro entre los archivos aprobados si cambia.
