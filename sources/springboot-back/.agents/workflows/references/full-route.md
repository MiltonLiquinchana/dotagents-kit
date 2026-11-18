# Ruta Completa (Backend)

Cargado solo cuando el orquestador determinó Ruta Completa. El Paso 0 ya se ejecutó en el orquestador y `RUN_DIR` está inicializado.

## Paso 1a — Analizar contexto

- **Skill**: `context-analyzer`
- **Ejecución**: subagente (ver `.agents/workflows/references/ejecutar-fase.md`)
- **Entrada**: `RUN_DIR/request.md`
- **Salida esperada**: `RUN_DIR/context.md`
- **Condición**: siempre
- **Según el resultado**:
  - `estado: ok` → Paso 1b.
  - `estado: fallo` | `bloqueado` → detener e informar al usuario.

## Paso 1b — Decidir patrón arquitectónico

- **Skill**: `spring-architect`
- **Ejecución**: subagente (ver `.agents/workflows/references/ejecutar-fase.md`)
- **Entrada**: `RUN_DIR/request.md`, `RUN_DIR/context.md`
- **Salida esperada**: `RUN_DIR/architecture-decision.md`
- **Condición**: siempre
- **Según el resultado**:
  - `estado: ok` → si la feature implica comunicación entre servicios, Paso 1c; si no, Paso 1d.
  - `estado: fallo` | `bloqueado` → detener e informar al usuario.

## Paso 1c — Diseñar comunicación entre servicios

- **Skill**: `microservices-architect`
- **Ejecución**: subagente (ver `.agents/workflows/references/ejecutar-fase.md`)
- **Entrada**: `RUN_DIR/request.md`, `RUN_DIR/context.md`, `RUN_DIR/architecture-decision.md`
- **Salida esperada**: `RUN_DIR/inter-service-design.md`
- **Condición**: solo si la feature requiere comunicación entre microservicios (Feign / RabbitMQ)
- **Según el resultado**:
  - `estado: ok` → Paso 1d.
  - `estado: fallo` | `bloqueado` → detener e informar al usuario.

## Paso 1d — Diseñar capa de datos

<!-- si backend.persistencia=jpa -->
- **Skill**: `jpa-data-expert`
- **Ejecución**: subagente (ver `.agents/workflows/references/ejecutar-fase.md`)
- **Entrada**: `RUN_DIR/context.md`, `RUN_DIR/architecture-decision.md`
- **Salida esperada**: `RUN_DIR/data-design.md`
- **Condición**: siempre
- **Según el resultado**:
  - `estado: ok` → Paso 1e.
  - `estado: fallo` | `bloqueado` → detener e informar al usuario.
<!-- fin -->
<!-- si backend.persistencia=jdbc -->
- En `jdbc` no hay paso de diseño de datos aparte: el diseño de la capa de datos lo incluye
  `spring-architect` en `architecture-decision.md` (Tarea 4, `JdbcTemplate`/`CallableStatement` y
  contratos de los SP). Este paso no se ejecuta; avanza directamente al Paso 1e.
<!-- fin -->

## Paso 1e — Integrar Plan de Implementación y esperar aprobación

<!-- si backend.persistencia=jpa -->
El workflow integra los artefactos de diseño (`context.md`, `architecture-decision.md`, `inter-service-design.md` si aplica y `data-design.md`) en un Plan estructurado que presenta al usuario:
<!-- fin -->
<!-- si backend.persistencia=jdbc -->
El workflow integra los artefactos de diseño (`context.md`, `architecture-decision.md` y `inter-service-design.md` si aplica) en un Plan estructurado que presenta al usuario:
<!-- fin -->

- ¿Qué se quiere realizar?
- Patrón elegido y justificación
- Capas involucradas (Controller → Service → Repository)
- Scripts de migración (si aplica)
- Reutilización de Componentes Base (con query del grafo)
- ¿Qué puede romperse? (Gateway, servicios dependientes, contratos)
- ¿Cómo se verifica? (Escenarios que `qa-engineer` debe cubrir)
- ¿Genera o resuelve deuda técnica?
- Borradores de código por archivo, con firma, anotaciones, métodos y dependencias inyectadas.
- Capacidades de la versión usadas: una línea breve junto a cada bloque de código final, con qué aprovecha y desde qué versión existe.

Los contratos, las firmas y los bloques de código de los artefactos de diseño (`architecture-decision.md`, `inter-service-design.md` si existe y `data-design.md` si existe) **no se resumen**: el plan los cita por el nombre del artefacto (por ejemplo, "contratos: los de `architecture-decision.md`, sin cambios"). Si el plan cambia algo respecto a un artefacto, lo copia entero en el plan y dice qué cambió.

Al aprobarse el plan, esos artefactos quedan congelados con él: si después cambian, se archivan en `history/` como el plan (ver la enmienda del plan aprobado, más abajo).

El plan incluye literalmente estas secciones; cada ruta parte de la raíz del repositorio, igual que en `git status`:

```markdown
## Archivos a crear o modificar
Una viñeta por ruta, sin subencabezados ni tablas dentro de la sección.
- `ruta/desde/la/raíz/del/repo.ext` — crear | modificar | borrar: motivo

## Pruebas a crear o modificar
- `ruta/de/la/prueba.ext` — escenario que cubre
```

La documentación (README) va en la primera sección: la escribe `file-writer`.

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
- **Si el usuario indica cambios**:
  - De formato/redacción: el workflow edita el Plan directamente y vuelve a presentarlo.
  - De contenido técnico: reinvoca la skill de diseño correspondiente con `RUN_DIR/feedback.md` y regenera en cascada.
- **Si el usuario aprueba**: el workflow escribe `RUN_DIR/approved-plan.md` con el contenido del plan y la cabecera:
  ```markdown
  ---
  aprobacion: "<texto literal del usuario>"
  fecha: <ISO-8601>
  ---
  ```
  Avanza al Paso 1f.

## Paso 1f — Crear servicio

- **Skill**: `service-creator`
- **Ejecución**: subagente (ver `.agents/workflows/references/ejecutar-fase.md`)
- **Entrada**: `RUN_DIR/approved-plan.md`
- **Salida esperada**: `RUN_DIR/service-report.md`
- **Condición**: solo si `approved-plan.md` tiene la sección `## Servicio nuevo`; si no, pasa al Paso 2a con exposición o al Paso 2b con Capas Estrictas (anota "Creación de servicio: omitida, sin sección" en el manifest).
- **Según el resultado**:
<!-- si devops.infraestructura=jenkins-kubernetes -->
  - `estado: ok` → si se creó un gateway, confirma que su carpeta coincide con `backend.gateway`, declarado antes de crearlo junto con `gateway_nodo_puerto` y `cors_origenes` de cada entorno desplegable; no pidas declararlo después ni regenerar por esas claves. La propuesta con gateway null debió terminar bloqueada en Paso 1c con `## Antes de crear el gateway` en inter-service-design.md y el remedio «edita `stack.yaml` con esos valores y relanza el workflow», sin aprobación ni escritura de archivos del proyecto; registra ese estado en el manifest al recibirlo. Repite `python3 -I -B .agents/scripts/servicios.py validar-entornos` tras sembrarlo y antes del modo generar; si bloquea, detente. Prevé `preparar-documentacion` para el tren de Spring Cloud y las versiones de módulo de Gateway y, cuando se use, de Kubernetes que resuelve `resolver-bom` tras crear el gateway. Después avanza al Paso 2a con exposición o al Paso 2b con Capas Estrictas (multiservicio si aplica, ya con el servicio creado); el compilado y las pruebas cubren también el servicio nuevo. Los artefactos del servicio nuevo se generan en modo `generar` en Paso 2c y el plan debe listarlos. En el paso de pruebas, `test-engineer`, con permiso de Gradle, ejecuta en el gateway `./gradlew dependencyInsight --dependency io.grpc:grpc-api` si la versión grpc fue aprobada como provisional; si difiere, vuelve a `file-writer` con feedback.md para cambiar solo esa versión, sin enmienda, y repite comparación y pruebas.
<!-- si devops.infraestructura=ninguna -->
  - `estado: ok` → si se creó un gateway, confirma que su carpeta coincide con `backend.gateway`, declarado antes de crearlo; no pidas declararlo después ni regenerar por esa clave. La propuesta con gateway null debió terminar bloqueada en Paso 1c con `## Antes de crear el gateway` en inter-service-design.md y el remedio «edita `stack.yaml` con esos valores y relanza el workflow», sin aprobación ni escritura de archivos del proyecto; registra ese estado en el manifest al recibirlo. Prevé `preparar-documentacion` para el tren de Spring Cloud y las versiones de módulo de Gateway que resuelve `resolver-bom` tras crear el gateway. Después avanza al Paso 2a con exposición o al Paso 2b con Capas Estrictas (multiservicio si aplica, ya con el servicio creado); el compilado y las pruebas cubren también el servicio nuevo.
<!-- fin -->
  - `estado: fallo` | `bloqueado` → detener e informar al usuario: la creación del servicio no se improvisa fuera del plan.

## Paso 2a — Esqueleto de exposición

- **Skill**: `api-integration-architect`
- **Ejecución**: subagente (ver `.agents/workflows/references/ejecutar-fase.md`)
- **Entrada**: `RUN_DIR/approved-plan.md`
- **Salida esperada**: `RUN_DIR/exposure-code.md`
- **Condición**: solo si el patrón en `approved-plan.md` es Data REST o Híbrido. En Capas Estrictas se omite directamente o emite "No aplica".
- **Según el resultado**:
  - `estado: ok` → Paso 2b.
  - `estado: fallo` | `bloqueado` → detener e informar al usuario.

## Paso 2b — Implementar lógica de negocio

- **Skill**: `backend-developer`
- **Ejecución**: subagente (ver `.agents/workflows/references/ejecutar-fase.md`)
- **Entrada**: `RUN_DIR/approved-plan.md`, `RUN_DIR/exposure-code.md` (si existe), `RUN_DIR/architecture-decision.md`, `RUN_DIR/inter-service-design.md` (si existe), `RUN_DIR/data-design.md` (si existe)
- **Salida esperada**: `RUN_DIR/code-changes.md`
- **Condición**: siempre
- **Según el resultado**:
  - `estado: ok` → Paso 2c.
  - `estado: fallo` | `bloqueado` → detener e informar al usuario.

## Paso 2c — Persistir cambios

- **Skill**: `file-writer`
- **Ejecución**: subagente (ver `.agents/workflows/references/ejecutar-fase.md`)
- **Entrada**: `RUN_DIR/approved-plan.md`, `RUN_DIR/code-changes.md`, `RUN_DIR/exposure-code.md` (si existe)
- **Salida esperada**: `RUN_DIR/write-report.md`
- **Condición**: siempre
- **Según el resultado**:
  - `estado: ok` → completar la secuencia de escritura descrita a continuación, antes de avanzar.
  - `estado: fallo` (error de compilación Gradle):
    - Mover `code-changes.md` a `history/code-changes.<n>.md`.
    - Escribir `RUN_DIR/feedback.md` con el error literal de compilación.
    - Volver al Paso 2b (consume 1 iteración del ciclo de corrección).
  - `estado: bloqueado` → detener e informar al usuario.

<!-- si devops.infraestructura=jenkins-kubernetes -->
### Generación DevOps previa a la comparación

- **Skill**: `devops-engineer`
- **Ejecución**: subagente (ver `.agents/workflows/references/ejecutar-fase.md`)
- **Entrada**: `RUN_DIR/approved-plan.md`, `RUN_DIR/write-report.md`, `RUN_DIR/feedback.md` (si existe); `modo: generar`, `salida: devops-generate-report.md`.
- **Salida esperada**: `RUN_DIR/devops-generate-report.md`
- **Alcance por entorno**: el plan enumera cada carpeta de devops.entornos, su sufijo, sus perfiles y sus destinos. Genera todos los aprobados; no solo la rama del momento. Los entornos existentes y la migración del pipeline requieren sus cambios expresamente aprobados. Las cuentas existentes solo se comprueban por presencia, sin lectura.
- **Condición**: inmediatamente después de escritura exitosa, solo si el plan aprobado dice `modo: generar` y lista los artefactos DevOps. Se activa por el plan aunque el diff previo no los toque. Si no lo pide, pasa directamente a la comparación.
- **Según el resultado**:
  - `estado: ok` → comparación completa y generación de diff, más abajo.
  - `estado: fallo`, `causa: artefactos` → escribir `RUN_DIR/feedback.md` y repetir esta misma fase DevOps (consume iteración del ciclo DevOps, máximo 2); al alcanzar el tope, detener e informar.
  - `estado: fallo`, `causa: codigo_diff` → escribir feedback y volver a Paso 2b; consume la iteración de DevOps y, al repetir pruebas/revisión, la del ciclo principal.
  - `estado: bloqueado` → detener e informar; infraestructura o enmienda no consume iteración de corrección.

<!-- fin -->
### Comparación completa y diff

el workflow compara el plan con el working tree con `python3 -I -B .agents/scripts/comparar-plan.py RUN_DIR/approved-plan.md`: si falta alguno o sobra alguno no declarado (exit 1), detiene el workflow e informa; un archivo extra solo vale si una enmienda lo añadió, en cuyo caso re-ejecuta el script con el plan ya enmendado. Con exit 2 o mayor, detiene el workflow e informa con la salida literal. Solo con exit 0 genera `RUN_DIR/diff.patch` con `git add -N -- <archivos tocados>` y `git diff HEAD`, y avanza al Paso 2.5.

La lista completa del plan se compara antes de pruebas, gate y revisión. El diff incluye los archivos nuevos de todas las fases de escritura; usa la unión de sus listas `## Archivos tocados` para `git add -N -- <archivos tocados>` y luego `git diff HEAD`. Ninguna fase posterior audita un diff anterior a esta escritura.

## Paso 2.5 — Actualizar Grafo de Código

El workflow ejecuta:
```bash
GRAPHIFY_BACKEND=none graphify . --update
```
Genera `RUN_DIR/graph-status.md`. Si falla, avisa en el output y avanza al Paso 2d.

## Paso 2d — Documentar

- **Skill**: `tech-writer`
- **Ejecución**: subagente (ver `.agents/workflows/references/ejecutar-fase.md`)
- **Entrada**: `RUN_DIR/approved-plan.md`, `RUN_DIR/diff.patch`
- **Salida esperada**: `RUN_DIR/docs-summary.md`
- **Condición**: siempre que haya código nuevo o modificado con API pública (exports, endpoints o interfaces). Si se omite, registra en `manifest.md` un motivo concreto.
- **Según el resultado**:
  - `estado: ok` → avanzar al Paso 3.
  - `estado: fallo` (falta Javadoc o la actualización del README según la skill): pedir autorización al usuario para gastar una iteración, escribir `RUN_DIR/feedback.md` con los archivos que faltan documentar, mover `code-changes.md` a `history/code-changes.<n>.md` y volver al Paso 2b (consume 1 iteración del ciclo de corrección).
  - `estado: bloqueado` → detener e informar al usuario.

## Paso 3 — Pruebas

- **Skill**: `qa-engineer`
- **Ejecución**: subagente (ver `.agents/workflows/references/ejecutar-fase.md`)
- **Entrada**: `RUN_DIR/approved-plan.md`, `RUN_DIR/diff.patch`
- **Salida esperada**: `RUN_DIR/test-report.md`
- **Condición**: siempre
- **Según el resultado**:
  - `estado: ok` → Paso 4.
  - `estado: fallo` (alguna prueba fallida):
    - Mover `code-changes.md` a `history/code-changes.<n>.md`.
    - Escribir `RUN_DIR/feedback.md` con las correcciones requeridas de `test-report.md`.
    - Volver al Paso 2b (consume 1 iteración del ciclo de corrección).
  - `estado: bloqueado` → detener e informar al usuario (si es por infraestructura Docker/BD, no consume iteraciones).

## Paso 4 — Revisión de calidad y Static Analysis Gate

- **Skill**: `code-reviewer`
- **Ejecución**: subagente (ver `.agents/workflows/references/ejecutar-fase.md`)
- **Entrada**: `RUN_DIR/approved-plan.md`, `RUN_DIR/diff.patch`, `RUN_DIR/write-report.md`, `RUN_DIR/test-report.md` (si existe), `RUN_DIR/docs-summary.md` (si existe), `RUN_DIR/graph-status.md` (si existe)
- **Salida esperada**: `RUN_DIR/review.md`
- **Condición**: siempre
- **Según el resultado**:
<!-- si devops.infraestructura=jenkins-kubernetes -->
  - `veredicto: APPROVED` o `APPROVED WITH RECOMMENDATIONS` → antes de avanzar, ejecuta `node .agents/scripts/sonar-diff-gate.mjs --comprobar-recibo RUN_DIR/gate-recibo.json`; si falla, repite la revisión sin consumir iteración. Si pasa y el diff toca `build.gradle` (versión o nombre), `application*.yaml` (puerto, context-path o variables de base), un `Dockerfile` o `devops/`, Paso 5; si no, Paso 6.
<!-- si devops.infraestructura=ninguna -->
  - `veredicto: APPROVED` o `APPROVED WITH RECOMMENDATIONS` → antes de avanzar, ejecuta `node .agents/scripts/sonar-diff-gate.mjs --comprobar-recibo RUN_DIR/gate-recibo.json`; si falla, repite la revisión sin consumir iteración. Si pasa, Paso 6; registra en el manifest "DevOps: omitido, sin infraestructura declarada".
<!-- fin -->
  - `veredicto: CHANGES REQUIRED` con `tipo_rechazo: IMPLEMENTACION`:
    - Mover `code-changes.md` a `history/code-changes.<n>.md`.
    - Escribir `RUN_DIR/feedback.md` con los hallazgos de `review.md`.
    - Volver al Paso 2b (consume 1 iteración del ciclo de corrección).
  - `veredicto: CHANGES REQUIRED` con `tipo_rechazo: ARQUITECTURA`:
    - Pausa de confirmación con el usuario antes de reiniciar desde el Paso 1a. Si el usuario confirma: ejecutar limpieza git con las rutas de `## Archivos tocados`, mover `RUN_DIR` a `history/attempt-<n>/`, ejecutar `GRAPHIFY_BACKEND=none graphify . --update` e iniciar desde el Paso 1a (consume 1 reinicio).
  - `veredicto: BLOCKED (infraestructura)` → detener e informar al usuario sin consumir iteraciones.

<!-- si devops.infraestructura=jenkins-kubernetes -->
## Paso 5 — DevOps condicional (validar)

- **Skill**: `devops-engineer`
- **Ejecución**: subagente (ver `.agents/workflows/references/ejecutar-fase.md`)
- **Entrada**: `RUN_DIR/approved-plan.md`, `RUN_DIR/diff.patch`, `RUN_DIR/devops-generate-report.md` (si existe); `modo: validar`, `salida: devops-report.md`.
- **Salida esperada**: `RUN_DIR/devops-report.md`
- **Condición**: solo si el diff toca `build.gradle` (versión o nombre), `application*.yaml` (puerto, context-path o variables de base), un `Dockerfile`, `devops/` o el archivo de `devops.jenkinsfile`. Los artefactos autorizados en modo generar ya se escribieron antes del comparador y fueron incluidos en pruebas, gate y revisión; aquí no se generan de nuevo.
- **Según el resultado**:
  - `estado: ok` → Paso 6; conservar las observaciones sobre incoherencias preexistentes. Mostrar al usuario en el resumen final los servicios «no incorporados» del informe e indicar que se incorporan con `.agents/workflows/incorporate-service.md`.
  - `estado: fallo`, `causa: codigo_diff` → escribir `RUN_DIR/feedback.md` y volver a Paso 2b (consume iteración de DevOps; máximo 2).
  - Si faltan artefactos de un servicio en alcance, `estado: bloqueado` → proponer enmienda del plan para modo generar, sin atribuirlo al código ni consumir iteración de corrección.
  - `estado: bloqueado` por infraestructura → detener e informar sin consumir iteración de corrección.
<!-- fin -->

## Paso 6 — Actualizar Base de Conocimiento

- **Skill**: `knowledge-writer` (modo `escribir`)
- **Ejecución**: subagente (ver `.agents/workflows/references/ejecutar-fase.md`)
- **Entrada**: `RUN_DIR/approved-plan.md`, `RUN_DIR/diff.patch`, `tipo: feature`, `RUN_DIR/docs-summary.md` (si existe)
- **Salida esperada**: `RUN_DIR/knowledge-report.md`
- **Condición**: siempre
- **Según el resultado**:
  - `estado: ok` → Paso 7.
  - `estado: fallo` → registrar advertencia y continuar al Paso 7.

## Paso 7 — Verificar vinculación de Base de Conocimiento

- **Skill**: `knowledge-writer` (modo `verificar`)
- **Ejecución**: subagente (ver `.agents/workflows/references/ejecutar-fase.md`)
- **Entrada**: `RUN_DIR/knowledge-report.md`
- **Salida esperada**: `RUN_DIR/link-check.md`
- **Condición**: siempre
- **Según el resultado**:
  - `estado: ok` → Paso 7.5.
  - `estado: fallo` | `bloqueado` → bloquear el commit; invocar inmediatamente `knowledge-writer` para autocorregir el frontmatter de las notas con `estado_vinculacion: pendiente` y repetir la verificación hasta obtener `estado: ok`.

## Paso 7.5 — Prueba en vivo

- **Condición**: `backend.prueba_viva` de `.agents/stack.yaml` es `true`. El orquestador lo lee con `node .agents/scripts/stack.mjs get backend.prueba_viva`; si es `false`, escribe `RUN_DIR/live-test.md` con `estado: omitido` y el motivo, y avanza al Paso 8.
- **Ejecución**: la hace el propio workflow (orquestador), no un subagente. Registra el resultado en `RUN_DIR/live-test.md` con: servicio, arranque usado, petición, status y cuerpo literal de cada respuesta.

Con `backend.prueba_viva` en `true`, tras la revisión:

1. Arranca el servicio de la feature **con su perfil local**, como lo arrancaría el usuario; no pases valores de configuración por la línea de comandos y no escribas ni leas credenciales: las aporta el entorno (ver la regla de credenciales de `.agents/rules/architecture-rules.md`).
2. Espera a que el puerto del servicio acepte conexiones. Haz una petición `GET` a la ruta de la feature y comprueba que responde lo esperado. Si la feature escribe, haz como máximo un `POST` de prueba con un código reconocible, y nada más.
3. Para el servicio y comprueba que el puerto queda libre.

- **Según el resultado**:
  - `estado: ok` → Paso 8.
  - `estado: fallo` (la respuesta no es la esperada, incluida una respuesta fuera del contrato de error declarado en `api_error.campo_mensaje` y `api_error.campo_codigo` de `.agents/stack.yaml` (con código `null`, solo mensaje)): registra la respuesta literal en `RUN_DIR/live-test.md`, escribe `RUN_DIR/feedback.md` con la diferencia observada vs esperada y vuelve al Paso 2b (consume 1 iteración del ciclo de corrección).
  - `estado: bloqueado` (el servicio no arranca o no alcanza la base de pruebas): detener e informar al usuario con la causa literal del arranque; normalmente nombra la variable de entorno que falta. No consume iteraciones.

## Paso 8 — Confirmar cambios atómicamente en Git

El workflow ejecuta:
```bash
git status --porcelain
git add -- <rutas explícitas>
git commit -m "feat: <descripcion-de-la-feature>"
```
La lista de rutas es la unión de `## Archivos tocados` de todas las salidas del intento aprobado y las notas listadas en `knowledge-report.md`. Antes de añadir, compara `git status --porcelain` con esa lista; si queda cualquier archivo modificado o sin seguimiento fuera de ella, detente e informa al usuario sin añadirlo ni descartarlo. Inmediatamente tras el commit, invoca `GRAPHIFY_BACKEND=none graphify . --update` como red de seguridad post-commit.

Antes de aprobar o enmendar el plan, aplica `.agents/workflows/references/decisiones-stack.md`; incluye el registro entre los archivos aprobados si cambia.

Antes de aprobar el plan de esta ruta, aplica el párrafo común de perfiles y DevOps de `.agents/workflows/references/decisiones-stack.md`.
