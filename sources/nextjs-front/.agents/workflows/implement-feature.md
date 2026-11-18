---
description: Orquestador del flujo de cambios de código en Next.js/TypeScript. Decide la ruta y despacha a la referencia correspondiente — no contiene los pasos de implementación. Inicializa RUN_DIR y coordina el ciclo de vida de los artefactos.
---

# Implement Feature — Orquestador

> **Ejecución obligatoria de fases:** aplica `.agents/workflows/references/ejecutar-fase.md` en cada paso que asigna una skill. Registra en `manifest.md` todas las revisiones repetidas y cada artefacto movido a `history/`.

## Precondición (Paso 0, una sola vez, sin importar la ruta — bloqueante, sin excepciones)

Ejecutar los siguientes puntos en orden. Si cualquiera falla, aplica el código, la clase y el remedio literales del preflight según `.agents/config/codigos.yaml`; un bloqueo detiene el workflow.

1. **Entorno determinista**: `bash .agents/scripts/preflight.sh --workflow implement-feature --fase entrada` continúa solo con exit 0; revisa avisos, partes del plan y omitidos según `.agents/config/codigos.yaml`.
   ```bash
   bash .agents/scripts/preflight.sh --workflow implement-feature --fase entrada
   ```
   Comprueba: árbol limpio (`git status --porcelain`), herramientas y dependencias del proyecto, configuración ESLint y su canario, el grafo solo si `herramientas.codebase_memory` es `true`, y `tgrep` independientemente de esa opción, además de SonarQube. Un grafo habilitado con 0 nodos es un aviso. Si el grafo falta o está corrupto, propone `.agents/workflows/codebase-memory.md`; el usuario decide o se incluye en el plan aprobado. No ejecutes una reparación automática para superar el preflight.
2. **Proyecto registrado en SonarQube (MCP)**: resuelve `projectKey` como el valor `sonarqube.project_key` de `.agents/stack.yaml` (`node .agents/scripts/stack.mjs get sonarqube.project_key`). Consulta con `node .agents/scripts/sonar-mcp.mjs search_my_sonarqube_projects --json '{"q":"<projectKey>"}'`. Si no existe, pide permiso al usuario para crear un proyecto privado. Tras aprobación, ejecuta `node .agents/scripts/sonar-diff-gate.mjs --registrar-proyecto <projectKey>`. No leas credenciales ni uses `curl -u`; el script resuelve la configuración internamente y no imprime el token.

3. **Canario SonarQube (MCP)**: `node .agents/scripts/sonar-diff-gate.mjs --canary` (exit 2 = `BLOCKED (infraestructura)`). Equivale a `analyze_code_snippet` con `fileContent` = contenido de `.agents/skills/code-reviewer/fixtures/canary-eval.ts`, `language: "ts"`, `scope: "MAIN"`, `projectKey: <projectKey>`. Pasa solo si aparece `typescript:S1523`.
4. **Inicialización de RUN_DIR**:
   - Crear carpeta de ejecución: `RUN_DIR=".agent-runs/$(date +%Y%m%d-%H%M)-<slug-feature>"`
   - Crear subdirectorio `RUN_DIR/history/`.
   - La carpeta vive en la raíz del proyecto, fuera de `.agents/`: los sandboxes de algunas herramientas montan `.agents/` en solo lectura, y los artefactos de la feature tendrían que pedir permiso por cada escritura.
   - Asegurar que `.agent-runs/` esté en `.gitignore`.
   - Inicializar `RUN_DIR/manifest.md` con las columnas: `| paso | skill o "workflow" | entradas | salida | estado | ejecución | iteración |`.
   - Escribir `RUN_DIR/request.md` con la solicitud literal del usuario.

## Selección de Ruta

| Criterio | Ruta Completa | Ruta de Corrección |
|----------|---------------|---------------------|
| Archivos nuevos | ≥ 1 | 0 |
| Capas nuevas | ≥ 1 capa | Solo capas existentes |
| Contratos, interfaces o DTOs en `domains/` | Sí (creación o cambio de firma) | No |
| Componentes de UI nuevos o cambios visuales | Sí | No, o cosméticos menores |
| Ejemplo típico | "Crear CRUD", "Agregar módulo", "Cambiar contrato público" | "Corregir import", "Cambiar patrón de ref", "Optimizar query", "Eliminar código en desuso" |

Si cumple **≥ 1 criterio** de Ruta Completa → Ruta Completa.
Si cumple **todos** los de Ruta de Corrección → Ruta de Corrección.
En caso de duda, pregunta: "¿Esto es un ajuste puntual o involucra estructura nueva?"

## Despacho

- Si aplica Ruta Completa → carga **únicamente** `workflows/references/full-route.md`.
- Si aplica Ruta de Corrección → carga **únicamente** `workflows/references/correction-route.md`.

## Notas operativas y gestión de artefactos

- **Comunicación por archivos**: Cada paso se comunica exclusivamente a través de archivos en `RUN_DIR`. No se pasa texto copiado en el prompt. El workflow valida que el frontmatter de salida contenga `entradas_leidas` completas y `estado: ok` antes de avanzar.
- **Validación de salida**: después de cada skill, comprueba que existe en `RUN_DIR` el archivo esperado y que su frontmatter es válido. Si no existe (timeout, error de herramienta o aborto) o una skill informa un fallo de escritura/persistencia, informa al usuario y detén el workflow: no reintentes ni consumas iteraciones. Distingue estos fallos de `estado: fallo` por una comprobación de código, que sí sigue las rutas de corrección descritas abajo.
- **Aprobación del usuario**: "aprobado", "dale", "sí, procede", "ok" cuentan como confirmación. Tras la aprobación en el Paso 5 / C2, el workflow genera `RUN_DIR/approved-plan.md` con el texto íntegro del plan y el campo `aprobacion: "<texto literal del usuario>"`.
- Si la aprobación incluye condiciones, aplícalas, presenta el plan actualizado y espera una confirmación final. Los ajustes al Plan durante su aprobación requieren aprobación explícita en cada vuelta, no tienen tope automático y no consumen iteraciones del ciclo de corrección.
- **Reinvocación en cascada del diseño**: ante un cambio técnico solicitado al Plan, reinvoca la primera skill cuyo resultado cambia y todas las posteriores que dependan de ella: Paso 1 → 2 → 3 (si aplica) → 4. Un ajuste limitado a una salida posterior no invalida las anteriores.
- **Ciclos de corrección**: Máximo 3 iteraciones combinadas en el ciclo Construcción ↔ Persistencia ↔ Grafo ↔ Documentación ↔ Pruebas ↔ Revisión. Cada reintento consume 1 iteración.
  - **Comprobaciones completas**: en el ciclo de corrección, las comprobaciones que no escriben código (verificación de la documentación, pruebas, gate, revisión) se ejecutan **todas**, aunque falle una: el orquestador junta sus fallos en un único `feedback.md` y pide **una** iteración para corregirlos todos. Solo se para antes si falla la compilación o el build, porque entonces lo demás no tiene sentido.
  - **Enmiendas**: las enmiendas del plan aprobadas por el usuario no cuentan como iteraciones de corrección; tienen su propio tope de 2 por feature (ver la enmienda del plan aprobado en la Ruta Completa).
  - Antes de re-invocar una skill para corrección, el workflow mueve el artefacto previo a `history/<artefacto>.<n>.md` y escribe `RUN_DIR/feedback.md` con los errores o correcciones requeridas.
  - Tras el reintento exitoso, borra `feedback.md`.
  - Cada vez que cambie el código se vuelve a ejecutar el tramo aplicable completo: persistencia, actualización del grafo, documentación y pruebas. Los resultados de una vuelta anterior no son válidos para el código actualizado.
  - Al agotar las 3 iteraciones sin aprobación, detén el flujo sin reintentar automáticamente e informa al usuario del estado del working tree.
- **Rechazo por implementación (`CHANGES REQUIRED` + `IMPLEMENTACION`)**:
  - Si viene de compilación (`write-report.md`), pruebas (`test-report.md`) o revisión (`review.md`), el workflow escribe `feedback.md` y vuelve al paso de desarrollo.
- **Rechazo por arquitectura (`CHANGES REQUIRED` + `ARQUITECTURA`)**:
  - El workflow nunca reinicia automáticamente: pausa y pide confirmación explícita al usuario.
  - En Ruta de Corrección pregunta: "El cambio fue rechazado por code-reviewer por una violación arquitectónica. Se requiere rediseñar la solución mediante Ruta Completa. ¿Procedemos?" En Ruta Completa pregunta: "El cambio fue rechazado por code-reviewer por una violación arquitectónica. Se requiere rediseñar desde el Paso 1 (contexto, contratos y arquitectura). ¿Procedemos?"
  - Si el usuario aprueba el reinicio: el workflow ejecuta limpieza git (`git checkout -- <rutas>`, `git clean -fd <rutas>`) usando la unión de las listas `## Archivos tocados` de los reportes del intento fallido. Incluye `package.json` y el lockfile del gestor si se instalaron dependencias; `node_modules` permanece como residuo documentado.
  - Mueve todos los archivos de `RUN_DIR` (salvo `request.md` y `manifest.md`) a `history/attempt-<n>/`.
  - Si el grafo está habilitado, ejecuta `python3 -I -B .agents/scripts/codebase-memory.py --indexar`; la reindexación aplica `.cbmignore`.
  - Reinicia desde el Paso 1 (en Ruta Completa) o escala a Ruta Completa (en Ruta de Corrección).
  - Límite global: máximo 2 reinicios arquitectónicos por feature. Al 3er rechazo arquitectónico, detén el flujo sin reiniciar.
- **Bloqueo del preflight (`BLOCKED [CODIGO]`)**: aplica el remedio y el alcance del catálogo. Para los gates propios se conserva su veredicto de infraestructura:
  - Si SonarQube, el linter o el entorno fallan, detén el flujo e informa al usuario. No consume iteraciones del ciclo de corrección.
- Cada fase recibe íntegros los artefactos de entrada, en especial el Plan aprobado completo con su sección de deuda técnica; no los sustituyas por resúmenes del orquestador.
- No se instalan hooks de CBM; el índice se actualiza explícitamente desde la raíz.
- **Manifest obligatorio**: tras cada paso, skill o acción del workflow, añade una fila a `RUN_DIR/manifest.md` con `| paso | skill o "workflow" | entradas | salida | estado | ejecución | iteración |`. Registra también reintentos, reinicios y pasos omitidos; para estos últimos usa `estado: omitido` e indica el motivo. Registra desde el Paso 0: preflight, inicialización de RUN_DIR y análisis de contexto o de solicitud. Mantén el historial, sin sobrescribir filas anteriores.
- **Intervenciones del orquestador**: Si el orquestador edita o ajusta un archivo directamente, debe declararlo en el informe final con su motivo.


- **Codebase Memory opcional**: solo actualiza el grafo y ejecuta consultas `codebase-memory-mcp cli search_graph --project "<proyecto>" --name-pattern ".*<símbolo>.*"` si `herramientas.codebase_memory` de `.agents/stack.yaml` es `true`. Con `false`, omite esas acciones y en SQL usa MCP en lectura, `db-index.py` y `tgrep` como fuentes de contexto.

- **Preparación del Paso 0**: si preflight informa PREPARACION, propone y, solo con permiso del usuario, ejecuta `bash .agents/scripts/preparar-proyecto.sh`, revisa los archivos que cambió, pide al usuario el commit `chore: preparar el proyecto para .agents` o hazlo únicamente con su permiso y vuelve a ejecutar preflight. Después propone iniciar/verificar tgrep, como parte de PREPARACION antes del plan y solo con permiso del usuario, con `bash .agents/scripts/preparar-proyecto.sh --arrancar-tgrep`; espera `Indexing: complete`. No improvises infraestructura en otro paso.

Antes de aprobar cualquier plan, sigue `.agents/workflows/references/decisiones-stack.md`; consulta clases, remedios y códigos que resuelve este workflow en `.agents/config/codigos.yaml`.

Solo con `herramientas.codebase_memory: true`, resuelve `<proyecto>` con `python3 -I -B .agents/scripts/codebase-memory.py --resolver` (exit 0) antes de las consultas. Un resultado vacío requiere comprobar cobertura con `check_index_coverage` y, si hay duda, buscar en fuente.
