# Ruta Completa (Frontend)

Cargado solo cuando el orquestador determinó Ruta Completa. El Paso 0 ya se ejecutó en el orquestador y `RUN_DIR` está inicializado.

## Paso 1 — Analizar contexto

- **Skill**: `context-analyzer`
- **Ejecución**: subagente (ver `.agents/workflows/references/ejecutar-fase.md`)
- **Entrada**: `RUN_DIR/request.md`
- **Salida esperada**: `RUN_DIR/context.md`
- **Condición**: siempre
<!-- si frontend.llamadas_api=navegador -->
- **Núcleo compartido**: comprueba si existen en `utils/` `Logger`, `ExceptionHandler`, `apiClient`, los errores y los contextos base. Si falta alguno, propone ejecutar `.agents/workflows/bootstrap-project.md` y espera la respuesta del usuario; no escribas un núcleo propio ni continúes hasta resolverlo.
<!-- si frontend.llamadas_api=servidor -->
- **Núcleo compartido**: comprueba si existen en `utils/` `Logger`, `apiClient`, los errores y los contextos base. Si falta alguno, propone ejecutar `.agents/workflows/bootstrap-project.md` y espera la respuesta del usuario; no escribas un núcleo propio ni continúes hasta resolverlo.
<!-- fin -->
- **Según el resultado**:
  - `estado: ok` → Paso 2.
  - `estado: fallo` | `bloqueado` → detener e informar al usuario.

## Paso 2 — Definir contratos de datos

- **Skill**: `api-integration-architect` (modo `contratos`)
- **Ejecución**: subagente (ver `.agents/workflows/references/ejecutar-fase.md`)
- **Entrada**: `RUN_DIR/request.md`, `RUN_DIR/context.md`
- **Salida esperada**: `RUN_DIR/data-contracts.md`
- **Condición**: siempre
- **Según el resultado**:
  - `estado: ok` → si la feature requiere diseño visual / cambios UI, Paso 3; si no, Paso 4.
  - `estado: fallo` | `bloqueado` → detener e informar al usuario.

## Paso 3 — Diseñar UX/UI

- **Skill**: `ux-designer`
- **Ejecución**: subagente (ver `.agents/workflows/references/ejecutar-fase.md`)
- **Entrada**: `RUN_DIR/request.md`, `RUN_DIR/context.md`, `RUN_DIR/data-contracts.md`
- **Salida esperada**: `RUN_DIR/ux-spec.md`
- **Condición**: solo si la feature incluye cambios visuales o componentes de UI nuevos
- **Según el resultado**:
  - `estado: ok` → Paso 4.
  - `estado: fallo` | `bloqueado` → detener e informar al usuario.

## Paso 4 — Definir arquitectura de componentes

- **Skill**: `frontend-architect`
- **Ejecución**: subagente (ver `.agents/workflows/references/ejecutar-fase.md`)
- **Entrada**: `RUN_DIR/context.md`, `RUN_DIR/data-contracts.md`, `RUN_DIR/ux-spec.md` (si existe)
- **Salida esperada**: `RUN_DIR/component-architecture.md`
- **Condición**: siempre
- **Según el resultado**:
  - `estado: ok` → Paso 5.
  - `estado: fallo` | `bloqueado` → detener e informar al usuario.

## Paso 5 — Generar Plan de Implementación y esperar aprobación

El workflow integra los artefactos generados (`context.md`, `data-contracts.md`, `ux-spec.md` y `component-architecture.md`) en un Plan estructurado que presenta al usuario:

- ¿Qué se quiere realizar?
- Reutilización de Componentes Base (citando queries del grafo)
- Especificación UX (si aplicó)
- ¿Qué puede romperse?
- ¿Cómo se verifica?
- ¿Genera o resuelve deuda técnica?
- Borradores de código, con los imports y las dependencias que usará cada archivo (ahí se ven las dependencias nuevas).
- Capacidades de la versión usadas: una línea breve junto a cada bloque de código final, con qué aprovecha y desde qué versión existe.

Los contratos, las firmas y los bloques de código de los artefactos de diseño (`data-contracts.md`, `component-architecture.md` y `ux-spec.md`) **no se resumen**: el plan los cita por el nombre del artefacto (por ejemplo, "contratos: los de `data-contracts.md`, sin cambios"). Si el plan cambia algo respecto a un artefacto, lo copia entero en el plan y dice qué cambió.

Al aprobarse el plan, esos artefactos quedan congelados con él: si después cambian, se archivan en `history/` como el plan (ver la enmienda del plan aprobado, más abajo).

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

- **Enmienda del plan aprobado**: si una fase posterior descubre que el plan no se puede cumplir tal cual (falta una dependencia, una regla que el plan no contempló o un contrato que no encaja):
  - la fase devuelve `bloqueado` con la causa;
  - el orquestador propone el cambio acotado, con un diff del plan, y espera la aprobación literal del usuario;
  - el plan anterior pasa a `history/approved-plan.<n>.md` y, con él, los artefactos de diseño congelados que cambien;
  - se añade una fila al manifest con `enmienda <n>`;
  - la enmienda no consume iteraciones de corrección. Tope: 2 enmiendas por feature; con la tercera, se para y se propone reiniciar desde el diseño.
- **Si el usuario pide ajustes**:
  - De redacción/formato: el workflow ajusta el texto y vuelve a presentar.
  - De contenido técnico: el workflow reinvoca la primera skill cuyo resultado cambie y todas las posteriores que dependan de ella, con `RUN_DIR/feedback.md`, en esta cadena: Paso 1 → 2 → 3 (si aplica) → 4. Los ajustes no consumen iteraciones y cada nueva versión del Plan requiere aprobación explícita.
  - Si la aprobación incluye condiciones, aplícalas, presenta el Plan actualizado y espera confirmación final.
- **Si el usuario aprueba**: el workflow escribe `RUN_DIR/approved-plan.md` con el contenido del plan y la cabecera:
  ```markdown
  ---
  aprobacion: "<texto literal del usuario>"
  fecha: <ISO-8601>
  ---
  ```
  Avanza al Paso 6.

## Paso 6 — Implementar código

Una skill por invocación según las capas requeridas:

- **Paso 6a — Capas de integración**:
  - Si la feature toca `domains/`, `repository/`, `services/` o `controllers/`:
    - **Skill**: `api-integration-architect` (modo `implementacion`)
- **Ejecución**: subagente (ver `.agents/workflows/references/ejecutar-fase.md`)
    - **Entrada**: `RUN_DIR/approved-plan.md`, `RUN_DIR/data-contracts.md`, `RUN_DIR/component-architecture.md`, `RUN_DIR/ux-spec.md` (si existe)
    - **Salida de la skill**: `code-changes.integration.md`. El mensaje fijo a la fase nombra esta salida exacta con `OUT_DIR` igual a `RUN_DIR`; no hay renombrado posterior.
- **Paso 6b — Capa de UI y hooks**:
  - Si la feature incluye componentes UI o hooks:
    - **Skill**: `frontend-developer`
- **Ejecución**: subagente (ver `.agents/workflows/references/ejecutar-fase.md`)
    - **Entrada**: `RUN_DIR/approved-plan.md`, `RUN_DIR/data-contracts.md`, `RUN_DIR/component-architecture.md`, `RUN_DIR/ux-spec.md` (si existe)
    - **Salida de la skill**: `code-changes.ui.md`. El mensaje fijo a la fase nombra esta salida exacta con `OUT_DIR` igual a `RUN_DIR`; no hay renombrado posterior.
- **Según el resultado**:
  - Si se ejecutó una capa, su salida queda con el nombre exacto que se le pasó. Si ambas se ejecutaron, deben quedar ambos archivos; no combines ni sobrescribas su contenido.
  - `estado: ok` → Paso 7.
  - `estado: fallo` | `bloqueado` → detener e informar al usuario.

## Paso 7 — Persistir cambios

- **Skill**: `file-writer`
- **Ejecución**: subagente (ver `.agents/workflows/references/ejecutar-fase.md`)
- **Entrada**: `RUN_DIR/approved-plan.md` y todos los archivos `RUN_DIR/code-changes*.md` presentes.
- **Salida esperada**: `RUN_DIR/write-report.md`
- **Condición**: siempre
- **Según el resultado**:
  - `estado: ok` → el workflow compara el plan con el working tree con `python3 -I -B .agents/scripts/comparar-plan.py RUN_DIR/approved-plan.md --ignorar LOCKFILE`, sustituyendo LOCKFILE según `frontend.gestor_paquetes` por `package-lock.json` (npm), `pnpm-lock.yaml` (pnpm) o `yarn.lock` (yarn): si falta alguno o sobra alguno no declarado (exit 1), detiene el workflow e informa; un archivo extra solo vale si una enmienda lo añadió, en cuyo caso re-ejecuta el script con el plan ya enmendado. Con exit 2 o mayor, detiene el workflow e informa con la salida literal. Solo con exit 0 genera `RUN_DIR/diff.patch` con `git add -N -- <archivos tocados>` y `git diff HEAD`, y avanza al Paso 7.5.
  - `estado: fallo` (errores de `tsc --noEmit` o el build del gestor de `frontend.gestor_paquetes` (`npm run build`, `pnpm build` o `yarn build`) en el código del proyecto):
    - Identificar las capas que deben corregirse según `feedback.md`; si no está claro, reintentar ambas. Antes de cada re-invocación, mover solo el artefacto activo de esa capa a `history/code-changes.<capa>.<n>.md`.
    - Escribir `RUN_DIR/feedback.md` con el error literal de compilación.
    - Volver al Paso 6 (consume 1 iteración del ciclo de corrección).
  - `estado: bloqueado` → detener e informar al usuario.

## Paso 7.5 — Actualizar Grafo de Código

El workflow ejecuta:
```bash
if [ "$(node .agents/scripts/stack.mjs get herramientas.codebase_memory)" = true ]; then
  python3 -I -B .agents/scripts/codebase-memory.py --indexar > "$RUN_DIR/graph-status.md" 2>&1
else
  printf '%s\n' 'OMITIDO: herramientas.codebase_memory=false' > "$RUN_DIR/graph-status.md"
fi
```
Genera `RUN_DIR/graph-status.md` con el resultado. Si falla, se anota la advertencia en `graph-status.md` y el flujo continúa al Paso 8 sin detenerse.

## Paso 8 — Documentar

- **Skill**: `tech-writer`
- **Ejecución**: subagente (ver `.agents/workflows/references/ejecutar-fase.md`)
- **Entrada**: `RUN_DIR/approved-plan.md`, `RUN_DIR/diff.patch`
- **Salida esperada**: `RUN_DIR/docs-summary.md`
- **Condición**: siempre que haya código nuevo o modificado con API pública (exports, endpoints o interfaces). Si se omite, registra en `manifest.md` un motivo concreto.
- **Según el resultado**:
  - `estado: ok` → avanzar al Paso 9.
  - `estado: fallo` (falta JSDoc o la actualización del README según la skill): pedir autorización al usuario para gastar una iteración, escribir `RUN_DIR/feedback.md` con los archivos que faltan documentar, mover el artefacto activo de esa capa a `history/code-changes.<capa>.<n>.md` y volver al Paso 6 (consume 1 iteración del ciclo de corrección).
  - `estado: bloqueado` → detener e informar al usuario.

## Paso 9 — Ejecutar pruebas

- **Skill**: `test-engineer`
- **Ejecución**: subagente (ver `.agents/workflows/references/ejecutar-fase.md`)
- **Entrada**: `RUN_DIR/approved-plan.md`, `RUN_DIR/diff.patch`
- **Salida esperada**: `RUN_DIR/test-report.md`
- **Condición**: solo si la feature toca `services/` o `controllers/` y existe script `"test"` en `package.json`
- **Según el resultado**:
  - `estado: ok` → Paso 10.
  - `estado: fallo` (alguna prueba fallida):
    - Identificar las capas que deben corregirse según `feedback.md`; si no está claro, reintentar ambas. Antes de cada re-invocación, mover solo el artefacto activo de esa capa a `history/code-changes.<capa>.<n>.md`.
    - Escribir `RUN_DIR/feedback.md` con la sección "Correcciones requeridas" de `test-report.md`.
    - Volver al Paso 6 (consume 1 iteración del ciclo de corrección).
  - `estado: bloqueado` → detener e informar al usuario.

## Paso 10 — Revisión de calidad y Static Analysis Gate

- **Skill**: `code-reviewer`
- **Ejecución**: subagente (ver `.agents/workflows/references/ejecutar-fase.md`)
- **Entrada**: `RUN_DIR/approved-plan.md`, `RUN_DIR/diff.patch`, `RUN_DIR/write-report.md`, `RUN_DIR/test-report.md` (si existe), `RUN_DIR/docs-summary.md` (si existe), `RUN_DIR/graph-status.md` (si existe)
- **Salida esperada**: `RUN_DIR/review.md`
- **Condición**: siempre
- **Según el resultado**:
  - `veredicto: APPROVED` o `APPROVED WITH RECOMMENDATIONS` → antes de avanzar, ejecuta `node .agents/scripts/sonar-diff-gate.mjs --comprobar-recibo RUN_DIR/gate-recibo.json`; si falla, repite la revisión sin consumir iteración. Si pasa, Paso 11.
  - `veredicto: CHANGES REQUIRED` con `tipo_rechazo: IMPLEMENTACION`:
    - Identificar las capas que deben corregirse según `feedback.md`; si no está claro, reintentar ambas. Antes de cada re-invocación, mover solo el artefacto activo de esa capa a `history/code-changes.<capa>.<n>.md`.
    - Escribir `RUN_DIR/feedback.md` con los hallazgos y sugerencias de `review.md`.
    - Volver al Paso 6 (consume 1 iteración del ciclo de corrección).
  - `veredicto: CHANGES REQUIRED` con `tipo_rechazo: ARQUITECTURA`:
    - Pausa de confirmación con el usuario. Si el usuario confirma: ejecutar limpieza git con las rutas de `## Archivos tocados`, mover contenido de `RUN_DIR` a `history/attempt-<n>/`, ejecutar `python3 -I -B .agents/scripts/codebase-memory.py --indexar` y reiniciar desde el Paso 1 (consume 1 de los 2 reinicios permitidos).
  - `veredicto: BLOCKED (infraestructura)` → detener e informar al usuario sin consumir iteraciones.

## Paso 11 — Actualizar Base de Conocimiento

- **Skill**: `knowledge-writer` (modo `escribir`)
- **Ejecución**: subagente (ver `.agents/workflows/references/ejecutar-fase.md`)
- **Entrada**: `RUN_DIR/approved-plan.md`, `RUN_DIR/diff.patch`, `tipo: feature`, `RUN_DIR/docs-summary.md` (si existe)
- **Salida esperada**: `RUN_DIR/knowledge-report.md`
- **Condición**: siempre
- **Según el resultado**:
  - `estado: ok` → Paso 12.
  - `estado: fallo` → registrar advertencia y continuar al Paso 12.

## Paso 12 — Verificar vinculación de Base de Conocimiento

- **Skill**: `knowledge-writer` (modo `verificar`)
- **Ejecución**: subagente (ver `.agents/workflows/references/ejecutar-fase.md`)
- **Entrada**: `RUN_DIR/knowledge-report.md`
- **Salida esperada**: `RUN_DIR/link-check.md`
- **Condición**: siempre
- **Según el resultado**:
  - `estado: ok` → Paso 12.5.
  - `estado: fallo` | `bloqueado` → bloquear el commit; invocar inmediatamente `knowledge-writer` para autocorregir el frontmatter de las notas con `estado_vinculacion: pendiente` y repetir la verificación hasta obtener `estado: ok`.

## Paso 12.5 — Prueba de humo

- **Ejecución**: la hace el propio workflow (orquestador), no un subagente. Registra el resultado en `RUN_DIR/smoke-test.md` con la ruta pedida, el status y los fragmentos del HTML comprobados.

Tras la revisión y antes del commit:

1. Arranca la app **como la arrancaría el usuario**: build de producción (si el Paso 7 no lo dejó hecho) y el arranque del gestor de `frontend.gestor_paquetes` (`npm run start`, `pnpm start` o `yarn start`), con su `.env.local`; no pases variables de configuración por la línea de comandos.
2. Pide la ruta nueva de la feature y comprueba en el HTML el estado esperado (contenido de la feature, mensajes o estados de carga cuando apliquen).
3. Para el proceso y comprueba que el puerto queda libre.

- **Según el resultado**:
  - `estado: ok` → Paso 12.6.
  - `estado: fallo` (la API responde conforme a su contrato y el HTML no muestra el estado esperado): registra la respuesta literal en `RUN_DIR/smoke-test.md`, escribe `RUN_DIR/feedback.md` con lo observado vs lo esperado y vuelve al Paso 6 (consume 1 iteración del ciclo de corrección).
  - `estado: bloqueado` (conexión a la API rechazada, tiempo agotado o respuesta ajena al contrato de la API, por ejemplo otro servidor en ese puerto): registra la causa literal y la URL que usó la app en `RUN_DIR/smoke-test.md`, detente e informa sin consumir iteración.
  - `estado: bloqueado` (falta la configuración local): detente con el mensaje exacto "copia `.env.example` a `.env.local`".

## Paso 12.6 — Verificación en el navegador

- **Ejecución**: la hace el propio workflow, no un subagente. Sigue `.agents/rules/agent-browser.md`. Registra el resultado en `RUN_DIR/browser-check.md`: estado, URL, acciones hechas, resultado observado frente al esperado, salida literal de `console`, `errors` y peticiones fallidas, y hosts afectados si los hay. Guarda la captura en `RUN_DIR/browser-check.png`.
- **Condición**: solo si `[ "$(node .agents/scripts/stack.mjs get herramientas.agent_browser)" = true ]`. Si no, registra en `RUN_DIR/manifest.md` la fila de este paso con `estado: omitido` y motivo `herramientas.agent_browser≠true`; no crees `browser-check.*` y pasa a Paso 13.

1. Arranca la app como en la prueba de humo, con el mismo build y arranque de producción del gestor declarado, sin pasar variables de configuración por la línea de comandos.
2. Usa la sesión `kit-<nombre de RUN_DIR>`: toma el nombre de la carpeta de ejecución y sustituye los caracteres distintos de letras, números, `-` y `_` por `-`. Exporta `AGENT_BROWSER_NO_VERSION_CHECK=1`, limita cada orden a 60 s y abre la URL local con `--allowed-domains localhost,127.0.0.1`; incluye `--session <nombre>` en cada orden. Recorre el flujo principal de la feature descrito en `RUN_DIR/ux-spec.md` (estados de éxito, carga, vacío y error que apliquen) o, si no existe, en `RUN_DIR/approved-plan.md`. Usa `snapshot -i`, interacciones y esperas conforme a la regla; renueva las referencias tras cada navegación o cambio del DOM. Con autenticación activa solo recorre rutas públicas.
3. Comprueba la consola, las excepciones y las peticiones fallidas con `console`, `errors`, `network requests --status 400-499` y `network requests --status 500-599`. Conserva sus salidas literales y aplica el orden de decisión de la regla.
4. Obtén `screenshot --full RUN_DIR/browser-check.png`, usando la ruta concreta de la carpeta de ejecución. Si un bloqueo impide la captura o alguna consulta, registra la causa literal en `RUN_DIR/browser-check.md` y conserva lo disponible.
5. Ejecuta `close` de la sesión, para la app y comprueba que el puerto queda libre. En cualquier salida, también si una orden falla a mitad, ejecuta este cierre y detén la app; registra cualquier fallo de cierre. Registra la fila del paso en `RUN_DIR/manifest.md`.

- **Según el resultado** (primero `bloqueado`, después `fallo`, finalmente `ok`, conforme a la regla):
  - `estado: ok` → Paso 13.
  - `estado: bloqueado` → registra la causa literal y los hosts afectados en `RUN_DIR/browser-check.md`, cierra la sesión, para la app, detente e informa sin consumir iteración. Si requiere sesión real, registra «requiere sesión real; verificación manual».
  - `estado: fallo` → escribe `RUN_DIR/feedback.md` con lo observado frente a lo esperado y vuelve a Paso 6 (consume 1 iteración del ciclo de corrección), tras cerrar la sesión y parar la app.

## Paso 13 — Confirmar cambios atómicamente en Git

El workflow ejecuta:
```bash
git status --porcelain
git add -- <rutas explícitas>
git commit -m "feat: <descripcion-de-la-feature>"
```
La lista de rutas es la unión de `## Archivos tocados` de todas las salidas del intento aprobado y las notas listadas en `knowledge-report.md`. Incluye `package.json` y el lockfile del gestor si se instalaron dependencias. Antes de añadir, compara `git status --porcelain` con esa lista; si queda cualquier archivo modificado o sin seguimiento fuera de ella, detente e informa al usuario sin añadirlo ni descartarlo. Si el commit falla, detén e informa al usuario con el error literal.

Antes de aprobar o enmendar el plan, aplica `.agents/workflows/references/decisiones-stack.md`; incluye el registro entre los archivos aprobados si cambia.
