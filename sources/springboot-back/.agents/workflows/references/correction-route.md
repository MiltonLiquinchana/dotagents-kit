# Ruta de Corrección (Backend)

Cargado solo cuando el orquestador determinó Ruta de Corrección. El Paso 0 ya se ejecutó en el orquestador y `RUN_DIR` está inicializado.

**La Ruta de Corrección no crea servicios**: ni el esqueleto de un servicio nuevo ni un gateway. Si la corrección necesita uno, detente y propón al usuario reiniciar con la Ruta Completa (Paso 1), donde la fase de diseño lo propuso en `## Servicio nuevo` y el plan lo autoriza.

## C1 — Consulta al Grafo

El workflow ejecuta `codebase-memory-mcp cli search_graph --project "<proyecto>" --name-pattern ".*<símbolo>.*"` / `codebase-memory-mcp cli trace_path --project "<proyecto>" --function-name "<símbolo>"` antes de abrir archivos, y comprueba el historial de correcciones en `knowledge-base/` con `tgrep`.

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
Una viñeta por ruta, sin subencabezados ni tablas dentro de la sección.
- `ruta/desde/la/raíz/del/repo.ext` — crear | modificar | borrar: motivo
(incluye aquí también las pruebas nuevas o modificadas; así las escriben `backend-developer`/`file-writer` y `comparar-plan.py` las exige)

## Pruebas a crear o modificar
- `ruta/de/la/prueba.ext` — escenario que cubre
```

La documentación (README) va en la primera sección: la escribe `file-writer`. Las pruebas nuevas o modificadas se listan en ambas secciones.

Antes de presentar el plan para aprobación, guarda el borrador en `RUN_DIR/plan-draft.md` y ejecuta `python3 -I -B .agents/scripts/comparar-plan.py RUN_DIR/plan-draft.md --solo-plan`. Con exit 2, completa la sección y repite la comprobación antes de presentarlo; con otro error, detente e informa con la salida literal. Repite esta validación tras cualquier ajuste del plan antes de volver a pedir aprobación.

```text
⏸️ ESPERANDO APROBACIÓN — Responde "aprobado" para continuar o indica los cambios necesarios.
```

- **Enmienda del plan aprobado**: vale aquí lo definido en la Ruta Completa (Paso 1e): una fase posterior que no pueda cumplir el plan devuelve `bloqueado` con la causa; el orquestador propone el cambio acotado con su diff, archiva el plan anterior en `history/approved-plan.<n>.md` con sus artefactos congelados si cambian, añade una fila al manifest con `enmienda <n>`, no consume iteraciones y respeta el tope de 2 enmiendas por feature.

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

- **Skill**: `backend-developer`
- **Ejecución**: subagente (ver `.agents/workflows/references/ejecutar-fase.md`)
- **Entrada**: `RUN_DIR/approved-plan.md`, `RUN_DIR/architecture-decision.md`, `RUN_DIR/inter-service-design.md` (si existe), `RUN_DIR/data-design.md` (si existe)
- **Salida esperada**: `RUN_DIR/code-changes.md`
- **Condición**: siempre
- **Según el resultado**:
  - `estado: ok` → C4.
  - `estado: fallo` | `bloqueado` → detener e informar al usuario.

## C4 — Persistir corrección

- **Skill**: `file-writer`
- **Ejecución**: subagente (ver `.agents/workflows/references/ejecutar-fase.md`)
- **Entrada**: `RUN_DIR/approved-plan.md`, `RUN_DIR/code-changes.md`
- **Salida esperada**: `RUN_DIR/write-report.md`
- **Condición**: siempre
- **Según el resultado**:
  - `estado: ok` → completar la secuencia de escritura descrita a continuación, antes de avanzar.
  - `estado: fallo` (error de compilación Gradle):
    - Mover `code-changes.md` a `history/code-changes.<n>.md`.
    - Escribir `RUN_DIR/feedback.md` con el error de compilación.
    - Volver a C3 (consume 1 iteración del ciclo de corrección).
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
  - `estado: fallo`, `causa: codigo_diff` → escribir feedback y volver a C3; consume la iteración de DevOps y, al repetir pruebas/revisión, la del ciclo principal.
  - `estado: bloqueado` → detener e informar; infraestructura o enmienda no consume iteración de corrección.

<!-- fin -->
### Comparación completa y diff

el workflow compara el plan con el working tree con `python3 -I -B .agents/scripts/comparar-plan.py RUN_DIR/approved-plan.md`: si falta alguno o sobra alguno no declarado (exit 1), detiene el workflow e informa; un archivo extra solo vale si una enmienda lo añadió, en cuyo caso re-ejecuta el script con el plan ya enmendado. Con exit 2 o mayor, detiene el workflow e informa con la salida literal. Solo con exit 0 genera `RUN_DIR/diff.patch` con `git add -N -- <archivos tocados>` y `git diff HEAD`, y avanza a C4.5.

La lista completa del plan se compara antes de pruebas, gate y revisión. El diff incluye los archivos nuevos de todas las fases de escritura; usa la unión de sus listas `## Archivos tocados` para `git add -N -- <archivos tocados>` y luego `git diff HEAD`. Ninguna fase posterior audita un diff anterior a esta escritura.

## C4.5 — Actualizar Grafo de Código

El workflow ejecuta:
```bash
if [ "$(node .agents/scripts/stack.mjs get herramientas.codebase_memory)" = true ]; then
  python3 -I -B .agents/scripts/codebase-memory.py --indexar > "$RUN_DIR/graph-status.md" 2>&1
else
  printf '%s\n' 'OMITIDO: herramientas.codebase_memory=false' > "$RUN_DIR/graph-status.md"
fi
```
Genera `RUN_DIR/graph-status.md`. Si falla, avisa y continúa a C5.

## C5 — Pruebas condicionales

- **Skill**: `qa-engineer`
- **Ejecución**: subagente (ver `.agents/workflows/references/ejecutar-fase.md`)
- **Entrada**: `RUN_DIR/approved-plan.md`, `RUN_DIR/diff.patch`
- **Salida esperada**: `RUN_DIR/test-report.md`
- **Condición**: solo si la corrección toca `Service`, `Repository` u otra lógica de negocio, o si el plan crea o modifica archivos bajo `<servicio>/src/test/`
- **Según el resultado**:
  - `estado: ok` → C6.
  - `estado: fallo`:
    - Mover `code-changes.md` a `history/code-changes.<n>.md`.
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
<!-- si devops.infraestructura=jenkins-kubernetes -->
  - `veredicto: APPROVED` o `APPROVED WITH RECOMMENDATIONS` → antes de avanzar, ejecuta `node .agents/scripts/sonar-diff-gate.mjs --comprobar-recibo RUN_DIR/gate-recibo.json`; si falla, repite la revisión sin consumir iteración. Si pasa y el diff toca `build.gradle` (versión o nombre), `application*.yaml` (puerto, context-path o variables de base), un `Dockerfile`, `devops/` o el archivo de `devops.jenkinsfile`, C6.5; si no, C7.
<!-- si devops.infraestructura=ninguna -->
  - `veredicto: APPROVED` o `APPROVED WITH RECOMMENDATIONS` → antes de avanzar, ejecuta `node .agents/scripts/sonar-diff-gate.mjs --comprobar-recibo RUN_DIR/gate-recibo.json`; si falla, repite la revisión sin consumir iteración. Si pasa, C7; registra en el manifest "DevOps: omitido, sin infraestructura declarada".
<!-- fin -->
  - `veredicto: CHANGES REQUIRED` con `tipo_rechazo: IMPLEMENTACION`:
    - Mover `code-changes.md` a `history/code-changes.<n>.md`.
    - Escribir `RUN_DIR/feedback.md` con los hallazgos de `review.md`.
    - Volver a C3 (consume 1 iteración del ciclo de corrección).
  - `veredicto: CHANGES REQUIRED` con `tipo_rechazo: ARQUITECTURA`:
    - Pausa de confirmación con el usuario antes de escalar a Ruta Completa. Si el usuario confirma: ejecutar limpieza git con las rutas de `## Archivos tocados`, mover `RUN_DIR` a `history/attempt-<n>/`, ejecutar `python3 -I -B .agents/scripts/codebase-memory.py --indexar` e iniciar Ruta Completa desde el Paso 1a (consume 1 reinicio).
  - `veredicto: BLOCKED (infraestructura)` → detener e informar al usuario sin consumir iteraciones.

<!-- si devops.infraestructura=jenkins-kubernetes -->
## C6.5 — DevOps condicional (validar)

- **Skill**: `devops-engineer`
- **Ejecución**: subagente (ver `.agents/workflows/references/ejecutar-fase.md`)
- **Entrada**: `RUN_DIR/approved-plan.md`, `RUN_DIR/diff.patch`, `RUN_DIR/devops-generate-report.md` (si existe); `modo: validar`, `salida: devops-report.md`.
- **Salida esperada**: `RUN_DIR/devops-report.md`
- **Condición**: solo si el diff toca `build.gradle` (versión o nombre), `application*.yaml` (puerto, context-path o variables de base), un `Dockerfile`, `devops/` o el archivo de `devops.jenkinsfile`. Los artefactos autorizados en modo generar ya se escribieron antes del comparador y fueron incluidos en pruebas, gate y revisión; aquí no se generan de nuevo.
- **Según el resultado**:
  - `estado: ok` → C7; conservar las observaciones sobre incoherencias preexistentes. Mostrar al usuario en el resumen final los servicios «no incorporados» del informe e indicar que se incorporan con `.agents/workflows/incorporate-service.md`.
  - `estado: fallo`, `causa: codigo_diff` → escribir `RUN_DIR/feedback.md` y volver a C3 (consume iteración de DevOps; máximo 2).
  - Si faltan artefactos de un servicio en alcance, `estado: bloqueado` → proponer enmienda del plan para modo generar, sin atribuirlo al código ni consumir iteración de corrección.
  - `estado: bloqueado` por infraestructura → detener e informar sin consumir iteración de corrección.
<!-- fin -->

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

## C8.5 — Prueba en vivo

- **Condición**: `backend.prueba_viva` de `.agents/stack.yaml` es `true`. El orquestador lo lee con `node .agents/scripts/stack.mjs get backend.prueba_viva`; si es `false`, escribe `RUN_DIR/live-test.md` con `estado: omitido` y el motivo, y avanza a C9. Un cambio de solo pruebas (sin tocar `src/main` ni contratos) deja C8.5 con `estado: omitido`, motivo `sin cambio de producción`, y avanza a C9.
- **Ejecución**: la hace el propio workflow (orquestador), no un subagente. Registra el resultado en `RUN_DIR/live-test.md` con: servicio, arranque usado, petición, status y cuerpo literal de cada respuesta.

Con `backend.prueba_viva` en `true`, tras la revisión:

1. Arranca el servicio de la corrección **con su perfil local**, como lo arrancaría el usuario; no pases valores de configuración por la línea de comandos y no escribas ni leas credenciales: las aporta el entorno (ver la regla de credenciales de `.agents/rules/architecture-rules.md`).
2. Espera a que el puerto del servicio acepte conexiones. Haz una petición `GET` a la ruta corregida y comprueba que responde lo esperado. Si la corrección escribe, haz como máximo un `POST` de prueba con un código reconocible, y nada más.
3. Para el servicio y comprueba que el puerto queda libre.

- **Según el resultado**:
  - `estado: ok` → C9.
  - `estado: fallo` (la respuesta no es la esperada, incluida una respuesta fuera del contrato de error declarado en `api_error.campo_mensaje` y `api_error.campo_codigo` de `.agents/stack.yaml` (con código `null`, solo mensaje)): registra la respuesta literal en `RUN_DIR/live-test.md`, escribe `RUN_DIR/feedback.md` con la diferencia observada vs esperada y vuelve a C3 (consume 1 iteración del ciclo de corrección).
  - `estado: bloqueado` (el servicio no arranca o no alcanza la base de pruebas): detener e informar al usuario con la causa literal del arranque; normalmente nombra la variable de entorno que falta. No consume iteraciones.

## C9 — Confirmar cambios atómicamente en Git

El workflow ejecuta:
```bash
git status --porcelain
git add -- <rutas explícitas>
git commit -m "fix: <descripcion-de-la-correccion>"
```
En un cambio de solo pruebas (sin tocar `src/main` ni contratos), el commit usa el prefijo `test:` en lugar de `fix:`. La nota de conocimiento registrada en C7 usa `tipo: fix`.
La lista de rutas es la unión de `## Archivos tocados` de todas las salidas del intento aprobado y las notas listadas en `knowledge-report.md`. Antes de añadir, compara `git status --porcelain` con esa lista; si queda cualquier archivo modificado o sin seguimiento fuera de ella, detente e informa al usuario sin añadirlo ni descartarlo. Inmediatamente tras el commit, invoca `python3 -I -B .agents/scripts/codebase-memory.py --indexar`.

Antes de aprobar o enmendar el plan, aplica `.agents/workflows/references/decisiones-stack.md`; incluye el registro entre los archivos aprobados si cambia.

Antes de aprobar el plan de esta ruta, aplica el párrafo común de perfiles y DevOps de `.agents/workflows/references/decisiones-stack.md`.

Solo con `herramientas.codebase_memory: true`, resuelve `<proyecto>` con `python3 -I -B .agents/scripts/codebase-memory.py --resolver` (exit 0) antes de las consultas. Un resultado vacío requiere comprobar cobertura con `check_index_coverage` y, si hay duda, buscar en fuente.
