---
description: Orquestador del flujo de cambios de base de datos MySQL. Decide la ruta y gestiona la carpeta de ejecución y el ciclo de vida de los artefactos.
---

# Build Database Feature — Orquestador

> **Ejecución obligatoria de fases:** aplica `.agents/workflows/references/ejecutar-fase.md` en cada paso que asigna una skill. Registra en `manifest.md` todas las revisiones repetidas y cada artefacto movido a `history/`.

## Precondición (Paso 0, una sola vez, sin importar la ruta; bloqueante)

Ejecutar los siguientes puntos en orden. Si cualquiera falla, aplica el código, la clase y el remedio literales del preflight según `.agents/config/codigos.yaml`; un bloqueo detiene el workflow.

1. **MCP de base de datos (`<mcp.base_de_datos>`)**: resuelve la conexión con el mapa `conexiones` de
   `.agents/stack.yaml` (cada conexión declara el esquema al que apunta) según la tabla de casos:

   | `conexiones` tiene… | Comportamiento |
   |---|---|
   | **una** entrada | Se usa esa. La declaración en `stack.yaml` es la indicación del usuario: no hace falta preguntar. El agente la nombra en el plan que el usuario aprueba. |
   | **dos o más** | El agente pregunta cuál usar y nunca asume. |
   | **ninguna** (`{}`) | Ningún paso ejecuta en la base real: los pasos que lo necesitan se detienen e informan. |

   Nunca se usa una conexión que no esté en `conexiones`, aunque el servidor MCP la exponga. Solo si existe la conexión seleccionada, confirma que el
   MCP responde con `SELECT VERSION()` en solo lectura. Extrae la primera coincidencia `\d+\.\d+\.\d+`; no guardes ni pases el texto crudo. Si no es normalizable, avisa y omite el dato. Si no existe una herramienta de consulta de solo lectura para esa conexión, detente e identifica lo esperado, por ejemplo:
   "no encuentro una herramienta de consulta de solo lectura para la conexión declarada en el servidor MCP `<mcp.base_de_datos>`; revisa
   `mcp.base_de_datos` y `conexiones` en `.agents/stack.yaml`". Si no responde o falla, detén el workflow e
   informa: "El MCP de base de datos no está operativo. Verifica la conexión y reintenta."
2. **Entorno determinista (después de MCP)**: `bash .agents/scripts/preflight.sh --workflow build-database-feature --fase entrada --dato version_real=<V>` con la versión normalizada; sin conexión o sin versión normalizable usa `bash .agents/scripts/preflight.sh --workflow build-database-feature --fase entrada`. Continúa solo con exit 0; revisa avisos, partes del plan y omitidos según `.agents/config/codigos.yaml`. Comprueba árbol limpio, herramientas, notebooks, sandbox, tgrep y referencia base. Solo si `herramientas.codebase_memory` es `true`, comprueba también el grafo y la CLI; si es `false`, muestra `OMITIDO [GRAFO] (depende de herramientas.codebase_memory=false) servicio=*` y continúa. Un grafo habilitado con 0 nodos es `AVISO [GRAFO_AVISO]`.
3. **Codebase Memory (solo si herramientas.codebase_memory es true)**: verifica el índice real con `python3 -I -B .agents/scripts/codebase-memory.py --comprobar`. Si falta o no está listo, propone `.agents/workflows/codebase-memory.md`; el usuario decide o la reparación se incluye en un plan aprobado, sin ejecutarla solo para superar el preflight. Con `false`, omite este paso; el contexto SQL viene de MCP de lectura, `db-index.py` y `tgrep`.
4. **tgrep (bloqueante)**: verifica `tgrep status knowledge-base/`. Si no responde, arráncalo con `tgrep serve knowledge-base/` y vuelve a verificar. Si no está instalado o no arranca, detén el flujo e informa al usuario.
5. **Destino explícito**: el destino es la conexión del caso resuelto en el punto 1 y siempre una clave del
   mapa `conexiones` de `.agents/stack.yaml`: nunca una conexión fuera del mapa, aunque el servidor MCP la
   exponga. Si la tarea requiriera una base no declarada ahí, detente; es el usuario quien debe añadir esa
   conexión al mapa.
6. **Inicialización de RUN_DIR**:
   - Crear carpeta de ejecución: `RUN_DIR=".agent-runs/$(date +%Y%m%d-%H%M)-<slug-feature>"`
   - Crear subdirectorio `RUN_DIR/history/`.
   - La carpeta vive en la raíz del proyecto, fuera de `.agents/`: los sandboxes de algunas herramientas montan `.agents/` en solo lectura, y los artefactos de la feature tendrían que pedir permiso por cada escritura.
   - Asegurar que `.agent-runs/` esté en `.gitignore`.
   - Inicializar `RUN_DIR/manifest.md` con las columnas: `| paso | skill o "workflow" | entradas | salida | estado | ejecución | iteración |`.
   - Escribir `RUN_DIR/request.md` con la solicitud literal del usuario.

## Selección de Ruta

| Criterio | Ruta Completa | Ruta de Corrección |
|----------|---------------|---------------------|
| Objetos de BD nuevos (tablas, SPs, funciones, vistas, triggers, eventos) | ≥ 1 | 0 |
| Cambio estructural en tablas existentes (ALTER con nuevas columnas, cambios de tipo) | Sí | No |
| Nuevos parámetros o cambio en el conjunto de resultados de un SP existente | Sí | No |
| Solo modificaciones de lógica interna sin cambiar firma ni estructura | No | Sí |
| Optimización de consulta sin alterar esquema | No | Sí |
| Corrección de error de manejo de errores o nomenclatura | No | Sí |
| Ejemplo típico | "Crear tabla de pedidos", "Nuevo SP de pedidos" | "Corregir división por cero en SP", "Optimizar consulta" |

Si cumple **≥ 1 criterio** de Ruta Completa → Ruta Completa.
Si cumple **todos** los de Ruta de Corrección → Ruta de Corrección.
En caso de duda, pregunta: "¿Esto es una feature nueva o un ajuste puntual sobre objetos existentes?"

Si la respuesta a la pregunta de desambiguación cambia la ruta, vuelve a evaluar la tabla antes de cargar una referencia; no cargues ambas por precaución.

## Despacho

- Si aplica Ruta Completa → carga **únicamente** `workflows/references/full-route-db.md`.
- Si aplica Ruta de Corrección → carga **únicamente** `workflows/references/correction-route-db.md`.

## Cambios multi-objeto o multi-BD

Si la solicitud afecta varios objetos interdependientes o más de una base de datos:

1. `db-architect` determina el orden de dependencia (por ejemplo, tablas antes de SPs que las usan, y primero la BD que expone datos y luego la consumidora).
2. Crea `RUN_DIR/<objeto>/` para cada objeto y úsalo como `RUN_DIR` aislado de su subflujo, de modo que sus artefactos no colisionen. Ejecuta su Ruta Completa o de Corrección por separado hasta que cada `sql-code-reviewer` emita `APPROVED` o `APPROVED WITH RECOMMENDATIONS`; difiere la ejecución en BD viva y los pasos posteriores. No ejecutes ningún objeto antes de que todos estén aprobados.
3. Persiste y valida todos los scripts con el gate y sandbox desechable. Luego ejecuta en BD viva en orden de dependencia y completa las pruebas de cada objeto. Si un DDL falla y hay que cambiar el script, considéralo un cambio nuevo: vuelve a persistirlo y auditarlo antes de re-ejecutarlo.
4. Cuando todos se hayan ejecutado y probado, cierra en este orden: documentación técnica y de objeto, notas de conocimiento, verificación de vinculación, un único commit atómico de notebooks y notas, y una actualización del grafo al final. Si la cadena falla a mitad, detente e informa qué objetos se ejecutaron y cuáles no; DDL no es transaccional.

## Notas operativas y gestión de artefactos

- **Comunicación por archivos**: Cada paso se comunica exclusivamente a través de archivos en `RUN_DIR`. No se pasa texto copiado en el prompt. El workflow valida que el frontmatter de salida contenga `entradas_leidas` completas y `estado: ok` antes de avanzar.
- **Validación de salida**: después de cada skill, comprueba que existe en `RUN_DIR` el archivo esperado y que su frontmatter es válido. Si no existe (timeout, error de herramienta o aborto) o una skill informa un fallo de escritura/persistencia, informa al usuario con el estado por objeto y detén el workflow: no reintentes ni consumas iteraciones. Distingue estos fallos de los rechazos de código y del fallo parcial de DDL.
- **Aprobación del usuario**: "aprobado", "dale", "sí, procede", "ok" cuentan como confirmación. Tras la aprobación en el Paso 3 / C2, el workflow genera `RUN_DIR/approved-plan.md` con el contenido del plan y la cabecera `aprobacion: "<texto literal del usuario>"`.
- Si la aprobación incluye condiciones, aplícalas, presenta el plan actualizado y espera una confirmación final. Los ajustes al Plan durante la aprobación requieren aprobación explícita en cada vuelta, no tienen tope automático y no consumen iteraciones del ciclo de corrección.
- **Reinvocación en cascada del diseño**: ante un cambio técnico solicitado al Plan, reinvoca la primera skill cuyo resultado cambia y todas las posteriores que dependan de ella: Paso 1 → 2. Un ajuste limitado a una salida posterior no invalida las anteriores.
- Cada fase recibe íntegros los artefactos de entrada, en especial el Plan aprobado completo con su sección de deuda técnica; no los sustituyas por resúmenes del orquestador.
- **Ciclos de corrección**: Máximo 3 iteraciones combinadas en el ciclo Persistencia ↔ Gate determinista ↔ Auditoría ↔ Ejecución ↔ Pruebas.
  - **Comprobaciones completas**: en el ciclo de corrección, las comprobaciones que no escriben código (gate determinista, auditoría, pruebas) se ejecutan **todas**, aunque falle una: el orquestador junta sus fallos en un único `feedback.md` y pide **una** iteración para corregirlos todos. Solo se para antes si falla una celda de datos al ejecutarse en la BD viva, porque entonces lo demás no tiene sentido.
  - **Enmiendas**: las enmiendas del plan aprobadas por el usuario no cuentan como iteraciones de corrección; tienen su propio tope de 2 por feature (ver la enmienda del plan aprobado en la Ruta Completa).
  - Antes de re-invocar una skill para corrección, el workflow mueve el artefacto previo a `history/<artefacto>.<n>.md` y escribe `RUN_DIR/feedback.md`.
  - Tras el reintento exitoso, borra `feedback.md`.
  - Al agotar el ciclo, detén el flujo e informa si quedan celdas persistidas sin ejecutar o si hay objetos ya ejecutados en la BD viva.
- **Precondiciones de orden en SQL**:
  - `sql-writer` se invoca únicamente tras `review.md` con veredicto `APPROVED` o `APPROVED WITH RECOMMENDATIONS`.
  - `sql-developer` requiere `conexión`, `approved-plan.md`, `review.md`, `persist-report.md` y `gate-report.md` sin fallos.
  - `performance-optimizer` se invoca solo si `test-report.md` tiene `estado: ok`.
- **Rechazo por implementación (`CHANGES REQUIRED` + `IMPLEMENTACION`)**:
  - El workflow escribe `RUN_DIR/feedback.md` y vuelve a persistencia/diseño según el paso.
- **Rechazo por arquitectura (`CHANGES REQUIRED` + `ARQUITECTURA`)**:
  - El workflow nunca reinicia automáticamente: pausa y pide confirmación explícita al usuario.
  - En Ruta de Corrección pregunta: "El cambio fue rechazado por sql-code-reviewer por una violación arquitectónica. Se requiere rediseñar la solución mediante Ruta Completa. ¿Procedemos?" En Ruta Completa pregunta: "El cambio fue rechazado por sql-code-reviewer por una violación arquitectónica. Se requiere rediseñar desde el Paso 1 (contexto y diseño). ¿Procedemos?"
  - Antes de limpiar, consulta los `execution-report.md` del intento actual y de `history/`. Restaurar el repositorio con git no revierte DDL ya ejecutado en la BD viva: informa qué objetos quedaron ejecutados y espera instrucciones del usuario antes de reiniciar.
  - Si un notebook contiene cambios previos del usuario que deben conservarse, muéstrale la celda rechazada y pide confirmación antes de eliminar solo esa celda. Elimina notebooks nuevos del intento con `git clean -fd <ruta>` y restaura notebooks modificados con `git checkout -- <ruta>` solo si no contienen cambios previos que preservar.
  - Una vez autorizada la limpieza y confirmado que no se requiere instrucción adicional sobre la BD viva, mueve el contenido de `RUN_DIR` a `history/attempt-<n>/` y reinicia desde el Paso 1 (o escala a Ruta Completa desde C4).
  - Límite global: máximo 2 reinicios arquitectónicos por feature. Al 3er rechazo arquitectónico, detén el flujo, informa del estado del working tree y de la BD viva, y pregunta si el usuario desea descartar el intento.
- **Orden de cierre**: documentación técnica y de objeto → nota de conocimiento → verificación de vinculación → commit atómico (notebooks y notas) → actualización del grafo.
- No se instalan hooks de CBM; el índice se actualiza explícitamente desde la raíz.
- **Intervenciones del orquestador**: si el orquestador corrige directamente SQL, un notebook o una nota que corresponde a una fase aislada, decláralo en el informe final con el motivo.
- **Manifest obligatorio**: tras cada paso, skill o acción del workflow, añade una fila a `RUN_DIR/manifest.md` con `| paso | skill o "workflow" | entradas | salida | estado | ejecución | iteración |`. Registra también reintentos, reinicios y pasos omitidos; para estos últimos usa `estado: omitido` e indica el motivo. Registra desde el Paso 0: preflight, inicialización de RUN_DIR y análisis de contexto. Conserva las filas anteriores.


- **Codebase Memory opcional**: solo actualiza el grafo y ejecuta consultas `codebase-memory-mcp cli search_graph --project "<proyecto>" --name-pattern ".*<símbolo>.*"` si `herramientas.codebase_memory` de `.agents/stack.yaml` es `true`. Con `false`, omite esas acciones y en SQL usa MCP en lectura, `db-index.py` y `tgrep` como fuentes de contexto.

- **Preparación del Paso 0**: si preflight informa PREPARACION, propone y, solo con permiso del usuario, ejecuta `bash .agents/scripts/preparar-proyecto.sh`, revisa los archivos que cambió, pide al usuario el commit `chore: preparar el proyecto para .agents` o hazlo únicamente con su permiso y vuelve a ejecutar preflight. Después propone iniciar/verificar tgrep, como parte de PREPARACION antes del plan y solo con permiso del usuario, con `bash .agents/scripts/preparar-proyecto.sh --arrancar-tgrep`; espera `Indexing: complete`. No improvises infraestructura en otro paso.

Ejemplos de clientes y pedidos: ejemplo con la convención recomendada; las convenciones efectivas se leen de `.agents/stack.yaml`.

Antes de aprobar cualquier plan, sigue `.agents/workflows/references/decisiones-stack.md`; consulta clases, remedios y códigos que resuelve este workflow en `.agents/config/codigos.yaml`.

Solo con `herramientas.codebase_memory: true`, resuelve `<proyecto>` con `python3 -I -B .agents/scripts/codebase-memory.py --resolver` (exit 0) antes de las consultas. Un resultado vacío requiere comprobar cobertura con `check_index_coverage` y, si hay duda, buscar en fuente.
