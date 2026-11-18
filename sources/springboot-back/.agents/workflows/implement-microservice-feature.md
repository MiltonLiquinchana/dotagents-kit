---
description: Orquestador del flujo de cambios de código en microservicios Spring Boot / Java (versiones de `.agents/stack.yaml`). Decide la ruta y gestiona la carpeta de ejecución y el ciclo de vida de los artefactos.
---

# Implement Microservice Feature — Orquestador

> **Ejecución obligatoria de fases:** aplica `.agents/workflows/references/ejecutar-fase.md` en cada paso que asigna una skill. Registra en `manifest.md` todas las revisiones repetidas y cada artefacto movido a `history/`.

## Precondición (Paso 0, una sola vez, sin importar la ruta)

Ejecutar los siguientes puntos en orden. Si cualquiera falla, aplica el código, la clase y el remedio literales del preflight según `.agents/config/codigos.yaml`; un bloqueo detiene el workflow.

1. **Entorno determinista**: `bash .agents/scripts/preflight.sh --workflow implement-microservice-feature --fase entrada` continúa solo con exit 0; revisa avisos, partes del plan y omitidos según `.agents/config/codigos.yaml`. Comprueba el árbol git limpio, `git`/`node`/`jq`/`curl`, el JDK que Gradle usa en todos los servicios con `build.gradle` (cada `<servicio>` es un build Gradle independiente), los `gradlew`, el índice real de CBM, la CLI `codebase-memory-mcp`, el servidor `tgrep` sobre `knowledge-base/` (bloqueante, sin fallback a `grep`/`rg`) y que SonarQube responda `UP`.
   - El árbol limpio aplica al inicio de la feature. En cambios multi-servicio, los commits intermedios del propio flujo no vuelven a pasar por este script.
   - Si falta el índice de CBM o no está listo, propone `.agents/workflows/codebase-memory.md`; el usuario decide o se incluye la reparación en un plan aprobado. No indexes solo para que pase el preflight.
   - Un `AVISO [CODIGO]` no bloquea ni autoriza reparar algo fuera del plan.
2. **Servidor de SonarQube (`<mcp.sonarqube>`) operativo**: `node .agents/scripts/sonar-mcp.mjs search_my_sonarqube_projects` responde con `estado: ok`.
3. **Canario SonarQube**: `node .agents/scripts/sonar-diff-gate.mjs --canary` (exit 2 = `BLOCKED (infraestructura)`). Equivale a `analyze_code_snippet` con `fileContent` = contenido de `.agents/skills/code-reviewer/fixtures/CanarySqli.java`, `language: "java"`, `scope: "MAIN"` y sin `projectKey`. Pasa solo si aparece `java:S2077`.
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
| Archivos nuevos de producción o nuevos artefactos estructurales | ≥ 1 (fuera de `src/test/` o que cambie la estructura) | 0 en producción; si el cambio **solo** crea o modifica archivos bajo `<servicio>/src/test/` (sin tocar `src/main/java` ni contratos), es Ruta de Corrección aunque cree archivos |
| Capas nuevas | ≥ 1 capa | Solo capas existentes |
| Contratos/interfaces nuevos | Sí | No |
| Cambio de patrón arquitectónico | Sí | No |
<!-- si backend.persistencia=jpa -->
| Ejemplo típico | "Crear CRUD de pedidos", "Agregar módulo de pedidos" | "Corregir import incorrecto", "Cambiar versión de dependencia", "Optimizar query JPA", "Eliminar código o clases en desuso", "Añadir pruebas unitarias de un servicio" |
<!-- si backend.persistencia=jdbc -->
| Ejemplo típico | "Crear CRUD de pedidos", "Agregar módulo de pedidos" | "Corregir import incorrecto", "Cambiar versión de dependencia", "Optimizar query JDBC", "Eliminar código o clases en desuso", "Añadir pruebas unitarias de un servicio" |
<!-- fin -->

Si cumple **≥ 1 criterio** de Ruta Completa → Ruta Completa.
Si cumple **todos** los de Ruta de Corrección → Ruta de Corrección. Los perfiles que falten y que la regla de `references/decisiones-stack.md` obliga a incluir siguen entrando en el plan y **no cuentan** como tocar `src/main` a efectos de la ruta. Si una prueba necesita cambiar código de producción, se aplica la tabla normal.
En caso de duda, pregunta: "¿Esto es un ajuste puntual o involucra estructura nueva?"

## Despacho

- Si aplica Ruta Completa → carga **únicamente** `workflows/references/full-route.md`.
- Si aplica Ruta de Corrección → carga **únicamente** `workflows/references/correction-route.md`.
- Si la respuesta a la pregunta de desambiguación cambia la ruta, vuelve a evaluar la tabla antes de cargar una referencia; no cargues ambas por precaución.

## Cambios multi-servicio

Si la solicitud modifica más de un microservicio:

1. **Plan maestro**: el orquestador reúne la solicitud completa y presenta `RUN_DIR/master-plan.md`, con endpoints, esquema de mensajes, dependencias y patrón de resiliencia. Espera aprobación explícita antes de construir cualquier servicio. Si la aprobación incluye condiciones, aplícalas, presenta el Plan maestro actualizado y espera confirmación final. Cada ajuste requiere aprobación y no tiene tope automático ni consume iteraciones de corrección.
2. **Construcción de todos los servicios**: por orden de dependencia, crea `RUN_DIR/<servicio>/` con el juego de artefactos propio de ese servicio y ejecuta las etapas de contexto, diseño, aprobación, construcción, persistencia, documentación y pruebas de su Ruta Completa o de Corrección. Cada servicio aplica el contrato aprobado y no lo redefine localmente. En el Paso 1a de cada Ruta Completa, incluye `RUN_DIR/master-plan.md` como entrada obligatoria. En esta fase difiere la actualización del grafo, QA/revisión, validación de infraestructura, conocimiento/vinculación y commit; no revises ni comitees ningún servicio hasta que todos estén construidos.
3. **Actualización única del grafo**: cuando terminen todas las construcciones, ejecuta `python3 -I -B .agents/scripts/codebase-memory.py --indexar` una sola vez sobre el monorepo completo antes de revisar servicios. Registra su resultado en el manifest y en el `graph-status.md` de la raíz.
4. **Revisión por servicio**: ejecuta `qa-engineer` cuando corresponda y `code-reviewer` por servicio, en el orden de dependencia, usando el grafo completo. El orquestador acepta `APPROVED` o `APPROVED WITH RECOMMENDATIONS` de `review.md` solo tras `node .agents/scripts/sonar-diff-gate.mjs --comprobar-recibo <RUN_DIR del servicio>/gate-recibo.json`; si falla, repite la revisión sin consumir iteración. Si un servicio falla la revisión por implementación, reconstruye solo ese servicio y vuelve a actualizar el grafo compartido antes de revisarlo de nuevo; esta actualización forma parte de la misma iteración. No reinicies el Plan maestro.
   - El revisor compara siempre con el Plan maestro y valida el contrato cruzado.
   - Si la reconstrucción rompe el contrato aprobado, es rechazo arquitectónico: pausa para confirmación y, si se aprueba, reinicia con un Plan maestro revisado, aplicando la limpieza y el tope global de reinicios.
   - Si el cambio es aditivo y retrocompatible, invalida temporalmente el `APPROVED` de los consumidores dependientes: re-revisa solo esos consumidores, en orden de dependencia, sin reconstruir salvo que su revisor lo pida. Los no dependientes conservan su aprobación. Si no cambia el contrato, vuelve a revisar solo el servicio reconstruido.
<!-- si devops.infraestructura=jenkins-kubernetes -->
5. **DevOps por servicio**: la generación aprobada ocurre en la escritura de cada servicio antes de su comparación y diff; la validación posterior sigue la condición de la Ruta activa, en orden de dependencia y antes del commit.
<!-- si devops.infraestructura=ninguna -->
5. Registra en el manifest "DevOps: omitido, sin infraestructura declarada" por servicio; continúa sin invocar una fase de infraestructura.
<!-- fin -->
6. **Commits secuenciales**: cuando todos los servicios tengan aprobación, actualiza la base de conocimiento y verifica la vinculación para cada servicio; después confirma un commit atómico por servicio (código y notas) en orden de dependencia. Si falla un commit, detén la secuencia e informa qué servicios ya se commitearon y cuál falló; no continúes con los demás.
7. **Actualización final consolidada**: después de los commits, ejecuta otra vez `python3 -I -B .agents/scripts/codebase-memory.py --indexar` sobre el monorepo completo como red de seguridad post-commit.

El tope de 2 reinicios arquitectónicos aplica a la feature multi-servicio completa, no a cada servicio por separado.

## Notas operativas y gestión de artefactos

- **Comunicación por archivos**: Cada paso se comunica exclusivamente a través de archivos en `RUN_DIR`. No se pasa texto copiado en el prompt. El workflow valida que el frontmatter de salida contenga `entradas_leidas` completas y `estado: ok` antes de avanzar.
- **Validación de salida**: después de cada skill, comprueba que existe en el directorio del servicio el archivo esperado y que su frontmatter es válido. Si no existe (timeout, error de herramienta o aborto) o una skill informa un fallo de escritura/persistencia, informa al usuario y detén el workflow: no reintentes ni consumas iteraciones. Distingue estos fallos de un rechazo de implementación.
- **Aprobación del usuario**: "aprobado", "dale", "sí, procede", "ok" cuentan como confirmación. Tras la aprobación en el Paso 1e / C2, el workflow genera `RUN_DIR/approved-plan.md` con el contenido del plan y la cabecera `aprobacion: "<texto literal del usuario>"`.
- Si la aprobación incluye condiciones, aplícalas, presenta el plan actualizado y espera confirmación final. Los ajustes al Plan durante la aprobación requieren aprobación explícita en cada vuelta, no tienen tope automático y no consumen iteraciones del ciclo de corrección.
- **Reinvocación en cascada del diseño**: ante un cambio técnico solicitado al Plan, reinvoca la primera skill cuyo resultado cambia y todas las posteriores que dependan de ella: Paso 1a → 1b → 1c (si aplica) → 1d. Un ajuste limitado a una salida posterior no invalida las anteriores.
- **Ciclos de corrección**: Máximo 3 iteraciones combinadas en el ciclo Construcción ↔ Persistencia ↔ Grafo ↔ Documentación ↔ Pruebas ↔ Revisión. Cada reintento consume 1 iteración.
  - **Comprobaciones completas**: en el ciclo de corrección, las comprobaciones que no escriben código (verificación de la documentación, pruebas, gate, revisión) se ejecutan **todas**, aunque falle una: el orquestador junta sus fallos en un único `feedback.md` y pide **una** iteración para corregirlos todos. Solo se para antes si falla la compilación, porque entonces lo demás no tiene sentido.
  - **Enmiendas**: las enmiendas del plan aprobadas por el usuario no cuentan como iteraciones de corrección; tienen su propio tope de 2 por feature (ver la enmienda del plan aprobado en la Ruta Completa).
  - Antes de re-invocar una skill para corrección, el workflow mueve el artefacto previo a `history/<artefacto>.<n>.md` y escribe `RUN_DIR/feedback.md` con los errores o correcciones requeridas.
  - Tras el reintento exitoso, borra `feedback.md`.
  - Cada vez que cambie el código se vuelve a ejecutar el tramo aplicable completo: persistencia, actualización del grafo, documentación, pruebas y revisión. Los resultados de una vuelta anterior no son válidos para el código actualizado.
  - Al agotar las 3 iteraciones del ciclo principal, detén el flujo sin reintentos automáticos, informa del working tree sin commitear y pregunta si el usuario quiere descartarlo. No escales automáticamente a un reinicio arquitectónico.
<!-- si devops.infraestructura=jenkins-kubernetes -->
- **Ciclo de DevOps (contador separado)**: Límite de 2 iteraciones de validación DevOps (`devops-report.md`).
<!-- fin -->
- **Rechazo por implementación (`CHANGES REQUIRED` + `IMPLEMENTACION`)**:
  - Si viene de compilación (`write-report.md`), pruebas (`test-report.md`) o revisión (`review.md`), el workflow escribe `feedback.md` y vuelve al paso de desarrollo (Paso 2b / C3).
- **Rechazo por arquitectura (`CHANGES REQUIRED` + `ARQUITECTURA`)**:
  - El workflow nunca reinicia automáticamente: pausa y pide confirmación explícita al usuario.
  - En Ruta de Corrección pregunta: "El cambio fue rechazado por code-reviewer por una violación arquitectónica. Se requiere rediseñar la solución mediante Ruta Completa. ¿Procedemos?" En Ruta Completa pregunta: "El cambio fue rechazado por code-reviewer por una violación arquitectónica. Se requiere rediseñar desde el Paso 1 (contexto, patrón, contratos). ¿Procedemos?"
  - Si el usuario aprueba el reinicio: el workflow ejecuta limpieza git (`git checkout -- <rutas>`, `git clean -fd <rutas>`) usando la unión de las listas `## Archivos tocados` de los reportes del intento fallido.
  - Mueve todos los archivos de `RUN_DIR` (salvo `request.md` y `manifest.md`) a `history/attempt-<n>/`.
  - Si el grafo está habilitado, ejecuta `python3 -I -B .agents/scripts/codebase-memory.py --indexar`; la reindexación aplica `.cbmignore`.
  - Reinicia desde el Paso 1a (en Ruta Completa) o escala a Ruta Completa (en Ruta de Corrección).
  - Límite global: máximo 2 reinicios arquitectónicos por feature. Al 3er rechazo arquitectónico, detén el flujo sin reiniciar.
  - El tope de reinicios es compartido entre ambas rutas; al alcanzarlo, no limpies automáticamente. Informa que el working tree conserva el intento rechazado y pregunta al usuario si quiere descartarlo.
- **Bloqueo del preflight (`BLOCKED [CODIGO]`)**: aplica el remedio y el alcance del catálogo. Para los gates propios se conserva su veredicto de infraestructura:
  - Si SonarQube o el entorno fallan, detén el flujo e informa al usuario. No consume iteraciones del ciclo de corrección.
<!-- si devops.infraestructura=jenkins-kubernetes -->
- El ciclo de DevOps tiene un contador independiente de máximo 2 invocaciones. Si un reintento DevOps obliga además a repetir pruebas o revisión, consume también una iteración del ciclo principal al volver a pasar por esos gates.
<!-- fin -->
- No se instalan hooks de CBM; el índice se actualiza explícitamente desde la raíz.
- Cada fase recibe íntegros los artefactos de entrada, en especial el Plan aprobado completo con su sección de deuda técnica; no los sustituyas por resúmenes del orquestador.
- **Manifest obligatorio**: tras cada paso, skill o acción del workflow, añade una fila a `RUN_DIR/manifest.md` con `| paso | skill o "workflow" | entradas | salida | estado | ejecución | iteración |`. Registra también reintentos, reinicios y pasos omitidos; para estos últimos usa `estado: omitido` e indica el motivo. Registra desde el Paso 0: preflight, inicialización de RUN_DIR y análisis de contexto o de solicitud. En cambios multi-servicio, registra además cada operación en el manifest del servicio correspondiente; conserva el historial sin sobrescribir filas.
- **Intervenciones del orquestador**: si el orquestador escribe o corrige directamente código, documentación o un artefacto que corresponde a una fase aislada, decláralo en el informe final con el motivo.
- **Coherencia del Gateway**: si la feature modifica o añade un `context-path` en un microservicio, ejecuta `python3 -I -B .agents/scripts/servicios.py validar-gateway` e incluye en el diff del plan la actualización de `GatewayConfig.java` (path, uri y X-Gateway), sustituyendo la ruta desfasada sin duplicarla.


- **Codebase Memory opcional**: solo actualiza el grafo y ejecuta consultas `codebase-memory-mcp cli search_graph --project "<proyecto>" --name-pattern ".*<símbolo>.*"` si `herramientas.codebase_memory` de `.agents/stack.yaml` es `true`. Con `false`, omite esas acciones y en SQL usa MCP en lectura, `db-index.py` y `tgrep` como fuentes de contexto.

- **Preparación del Paso 0**: si preflight informa PREPARACION, propone y, solo con permiso del usuario, ejecuta `bash .agents/scripts/preparar-proyecto.sh`, revisa los archivos que cambió, pide al usuario el commit `chore: preparar el proyecto para .agents` o hazlo únicamente con su permiso y vuelve a ejecutar preflight. Después propone iniciar/verificar tgrep, como parte de PREPARACION antes del plan y solo con permiso del usuario, con `bash .agents/scripts/preparar-proyecto.sh --arrancar-tgrep`; espera `Indexing: complete`. No improvises infraestructura en otro paso.

Ejemplos de clientes y pedidos: ejemplo con la convención recomendada; las convenciones efectivas se leen de `.agents/stack.yaml`.
<!-- si devops.infraestructura=jenkins-kubernetes -->
## Entornos del plan aprobado

Antes de pedir aprobación, ejecuta `python3 -I -B .agents/scripts/servicios.py entornos` y `validar-entornos`. Enumera la tabla completa de `devops.entornos` para el pipeline. Solo para entradas con `desplegar: true`, enumera los datos de destino: carpeta, rama, sufijo, credencial_kubeconfig (solo ID), imagen, desplegar, puerto efectivo, nodePort, réplicas, recursos y los perfiles y artefactos que se crearán o modificarán. Los nombres de carpeta son libres y no se obtienen de la rama. El gateway usa gateway_nodo_puerto; sus perfiles llevan sufijo, CORS e issuer públicos de cada entorno y mantienen los valores globales en local.

Si el proyecto solo tiene una carpeta, lista las que faltan para aprobación; no alteres un entorno existente fuera del plan. Para migrar el Jenkinsfile existente, incluye su diff aprobado de lógica y mapa de entornos; no lo reemplaces automáticamente. RBAC y cuentas de Jenkins mantienen nombres fijos y contenido idéntico si comparten clúster; nunca leas los archivos existentes de account/. Las nuevas cuentas y Secrets vacíos requieren sus rutas aprobadas por carpeta y las comprobaciones de ausencia e ignore vigentes. Tú rellenas el Secret, lo compruebas con `python3 -B -E .agents/scripts/servicios.py comprobar-secreto <ruta>` y lo aplicas con `kubectl apply -f <ruta>` antes del primer despliegue; la IA no lo abre.

Con modo generar, DevOps corre después de la escritura exitosa y antes de comparar-plan.py, git add -N, git diff HEAD, pruebas, gate y revisión. Lo activa el plan aunque el diff previo no tocara DevOps. Un fallo de artefactos vuelve a DevOps con feedback.md (máximo dos intentos); solo codigo_diff vuelve a escritura. En la revisión posterior se invoca modo validar. Con modo validar inicial se conservan la comparación temprana y la condición posterior del diff.
<!-- fin -->

Antes de aprobar cualquier plan, sigue `.agents/workflows/references/decisiones-stack.md`; consulta clases, remedios y códigos que resuelve este workflow en `.agents/config/codigos.yaml`.

Solo con `herramientas.codebase_memory: true`, resuelve `<proyecto>` con `python3 -I -B .agents/scripts/codebase-memory.py --resolver` (exit 0) antes de las consultas. Un resultado vacío requiere comprobar cobertura con `check_index_coverage` y, si hay duda, buscar en fuente.
