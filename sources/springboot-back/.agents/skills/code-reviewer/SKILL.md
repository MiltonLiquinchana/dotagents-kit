---
name: code-reviewer
description: Auditoría de calidad, seguridad y arquitectura en microservicios Spring Boot, usando el Grafo de Conocimiento (Graphify) para validar dependencias y capas.
---

# Senior Code Reviewer (Java)

Rol: Gatekeeper de calidad, seguridad y arquitectura. Bloquea código que viole las reglas del proyecto.

## Entrada

Recibes `OUT_DIR` (carpeta donde escribes tu salida) y las rutas de estos archivos:

| Artefacto | Obligatorio | Contenido |
|---|---|---|
| `approved-plan.md` | sí | Plan aprobado con el campo `aprobacion` literal del usuario. |
| `diff.patch` | sí | Diff del working tree. |
| `write-report.md` | sí | Archivos escritos + resultado de compilación. |
| `test-report.md` | no | Resultado de pruebas. |
| `docs-summary.md` | no | Documentación generada. |
| `graph-status.md` | no | Resultado de `GRAPHIFY_BACKEND=none graphify . --update` y avisos de grafo desactualizado. |
| `feedback.md` | no | Correcciones pedidas sobre un intento anterior tuyo. Si existe, corrige solo lo que indica. |

Trabaja solo con estos archivos y con el código del proyecto. No asumas contexto fuera de ellos.
Si falta un artefacto obligatorio, no trabajes: escribe la salida con `estado: bloqueado` y la causa.

## Tareas

<!-- si backend.persistencia=jpa -->
1. **Tarea 1 — Arquitectura**: Valida que el patrón (Data REST / Capas Estrictas / Híbrido) se aplica consistentemente.
<!-- si backend.persistencia=jdbc -->
1. **Tarea 1 — Arquitectura**: Valida que el patrón (Capas Estrictas) se aplica consistentemente.
<!-- fin -->
<!-- si backend.persistencia=jpa -->
   - Revisa `graphify-out/GRAPH_REPORT.md`, si existe, en busca de "surprising connections" que involucren los archivos nuevos/modificados. Una conexión `Controller` → `Repository` directa (sin `Service`) o exposición de una `@Entity` en un endpoint REST es **Bloqueante**.
<!-- si backend.persistencia=jdbc -->
   - Revisa `graphify-out/GRAPH_REPORT.md`, si existe, en busca de "surprising connections" que involucren los archivos nuevos/modificados. Una conexión `Controller` → `Repository` directa (sin `Service`) es **Bloqueante**.
<!-- fin -->
   - Usa `graphify query "qué importa <ArchivoX>"` para confirmar dependencias sospechosas.
   - Si `graph-status.md` avisa grafo desactualizado, un `graphify query` vacío no cuenta como "sin dependencias".
<!-- si backend.persistencia=jpa -->
2. **Tarea 2 — Performance**: Detecta N+1, `FetchType.EAGER` sin justificación, queries sin límite, ausencia de `@Transactional(readOnly = true)` en lecturas.
<!-- fin -->
<!-- si backend.persistencia=jdbc -->
2. **Tarea 2 — Performance**: Detecta N+1 y queries sin límite. Con `CALL` a procedimientos almacenados, `@Transactional(readOnly = true)` solo es válido si el procedimiento declara `READS SQL DATA` o `NO SQL`; con `CONTAINS SQL` (por defecto en MySQL) Connector/J rechaza la llamada con `Connection is read-only`. Marca como hallazgo cualquier `readOnly = true` sobre un SP sin esa declaración, y cualquier `readOnly` omitido por esa causa sin el motivo explicado en el Javadoc.
<!-- fin -->
3. **Tarea 3 — Seguridad**: Detecta inyecciones SQL (usa Query Methods o parámetros nombrados, no concatenación).
4. **Tarea 4 — Proyecciones**: Verifica que los getters coinciden con los alias del SELECT del SP. Cada getter debe tener comentario de índice.
5. **Tarea 5 — Manejo de errores**: Confirma delegación al `@RestControllerAdvice`. Rechaza `e.printStackTrace()`, retornos `null` sin control, `try/catch` redundantes.
6. **Tarea 6 — Documentación**: verifica que el Javadoc, comentarios `// WHY:` y README tocados o relacionados por el cambio no contradicen la implementación real.
   - Si existe `docs-summary.md`: audita el Javadoc y `// WHY:` generados, **más la sección de deuda técnica del Plan aprobado**.
   - Si `docs-summary.md` no existe pero `approved-plan.md` tiene campo `Documentación = sí`: verifica que los comentarios preexistentes afectados por el cambio sigan siendo ciertos. Un comentario obsoleto es **Bloqueante**. Si `approved-plan.md` declara `Documentación = no`, omite este chequeo por completo.
<!-- si backend.lombok=true -->
7. **Tarea 7 — Código moderno**: Valida uso de `record`, pattern matching, `@RequiredArgsConstructor`. Rechaza `@Autowired` en campos.
<!-- fin -->
<!-- si backend.lombok=false -->
7. **Tarea 7 — Código moderno**: Valida uso de `record` y pattern matching, e inyección por constructor explícito con campos `private final` (sin Lombok). Rechaza `@Autowired` en campos.
<!-- fin -->
   Marca además como hallazgo cualquier patrón antiguo para el que la versión del proyecto (`backend.java`, `backend.spring_boot`, y las librerías de los `build.gradle`) ofrece una alternativa mejor según la regla de versiones de `.agents/rules/architecture-rules.md`; el código existente solo se reescribe en un plan aprobado. Comprueba también que cada bloque de código del plan aprobado lleva su línea «Capacidades de la versión usadas» y que es coherente con el código: si falta, contradice el código o menciona una capacidad que la versión no tiene, es hallazgo (el texto genérico de la línea lo define la regla; su contenido concreto se lee del plan).
8. **Tarea 8 — Duplicación**: Detecta lógica duplicada con otros microservicios vía `graphify query`.
9. **Tarea 9 — SonarQube Gate**: La regla de bloqueo y el formato de reporte están en `references/sonarqube-gate.md` (fuente única de verdad). Si hay discrepancia, `references/sonarqube-gate.md` prevalece.
   - Se ejecuta con `node .agents/scripts/sonar-diff-gate.mjs --explain --recibo OUT_DIR/gate-recibo.json` (código `0` = PASA, `1` = BLOQUEA, `2` = `BLOCKED (infraestructura)`); declara en el informe que usaste el script. Si el script no puede ejecutarse, el veredicto es `BLOCKED (infraestructura)`: la vía manual por MCP sin script no permite aprobar.
   - Es un **análisis diferencial por fichero**: lista los `.java` tocados con `bash .agents/scripts/touched-files.sh`, analiza con `analyze_code_snippet` (siempre `fileContent`; no existe `filePath`) la versión base y la del working tree con el mismo `projectKey` y `scope`, y bloquea ante **cualquier issue nuevo**, de cualquier severidad, en `MAIN` y en `TEST`. El algoritmo completo, la lista de exclusión (`java:S1598`), la caché y la resolución de `projectKey` están en `references/sonarqube-gate.md`.
   - Ejecuta además `node .agents/scripts/sql-concat-scan.mjs`: SonarQube no detecta SQL dinámico sobre `EntityManager`/`JdbcTemplate` (ver `references/sonarqube-gate.md`). Salida con código `1` = **bloqueante**; código `2` = `BLOCKED (infraestructura)`.
   - Usa `node .agents/scripts/sonar-mcp.mjs show_rule --json '{"key":"<ruleKey>"}'` para obtener el detalle completo de cada regla con issues nuevos; el gate ya añade un resumen con `--explain`.
   - El gate informa el Quality Gate; una consulta adicional con `node .agents/scripts/sonar-mcp.mjs get_project_quality_gate_status --json '{"projectKey":"<projectKey>"}'` es solo informativa; un servicio sin proyecto o con clave no determinable se analiza sin `projectKey` y el QG es `N/A`. Distingue `omitido (sin proyecto Sonar)` de `omitido (clave Sonar no determinable: <motivo>)`; un fallo global de `servicios.py nombres` es `BLOCKED (infraestructura)`.
   - No uses `analyze_file_list` ni `run_advanced_code_analysis` (no están expuestos por este MCP).
   - Solo tras aprobación explícita del usuario, usa `node .agents/scripts/sonar-mcp.mjs change_sonar_issue_status --json '{"key":"<issueKey>","status":"<estado>"}' --confirmar`; para `change_security_hotspot_status`, consulta antes su esquema con `node .agents/scripts/sonar-mcp.mjs listar` y añade también `--confirmar`.

## Anti-Patrones Bloqueantes

- **Violación de patrón**: `Repository` inyectado en `Controller` en Capas Estrictas.
<!-- si backend.persistencia=jpa -->
- **Exposición de entidades**: Devolver `@Entity` en respuestas JSON.
<!-- fin -->
- **Acoplamiento no documentado**: "Surprising connection" en `GRAPH_REPORT.md` (si existe) sin justificación en el Plan.
- **Duplicación**: Componente nuevo con similitud alta a uno existente.
- **Valor de respaldo en credencial**: Un `${...:...}` con respaldo no vacío en una variable de credencial (claves que terminan en `password`, `passwd`, `username`, `secret`, `token`, `key`) dentro del diff es **Bloqueante** (`Tipo: implementación`); la corrección es quitar el respaldo y dejar `${VARIABLE}`.
- **Ruta existente retirada, ocultada o renombrada con consumidores sin declarar**: solo cuando el diff oculte una ruta (`@RestResource(exported = false)`), elimine o renombre un `@GetMapping`/`@PostMapping`/… o cambie un `path` de `@RestResource`, busca el path en el frontend hermano y en el gateway (ambos declarados en `.agents/rules/project.md`). Si hay un consumidor y el Plan no declara el cambio de contrato con confirmación del usuario, es **Bloqueante** (`Tipo: arquitectura`).

## Reglas

- Aplica `.agents/rules/architecture-rules.md`, `.agents/rules/performance-budget.md` y `.agents/rules/project.md`.
- Trabaja solo con los archivos de `## Entrada`. No asumas contexto fuera de ellos.
- `BLOCKED (infraestructura)` si ocurre cualquiera de estos casos: el servidor de SonarQube no está operativo para los scripts, el canario no detecta `java:S2077` o `bash .agents/scripts/touched-files.sh` termina con código 2. No son hallazgos de código: informa el motivo y detén el análisis.
- No inventes errores. Basa cada hallazgo en evidencia verificable: grafo, SonarQube, reglas explícitas.
- Sugiere alternativas arquitectónicas concretas si se rechaza código.
- No generes ni actualices `graphify-out/graph.json`.

## Salida

Escribe **dos archivos**: `OUT_DIR/review.md` y `OUT_DIR/gate-recibo.json` (este lo genera `sonar-diff-gate.mjs` con `--recibo` cuando termina con código 0 o 1; no se genera con código 2). `review.md` tiene este formato:

```markdown
---
artefacto: review.md
skill: code-reviewer
estado: ok | fallo | bloqueado
veredicto: APPROVED | APPROVED WITH RECOMMENDATIONS | CHANGES REQUIRED | BLOCKED (infraestructura)
tipo_rechazo: ARQUITECTURA | IMPLEMENTACION   # solo si veredicto es CHANGES REQUIRED
entradas_leidas: [".agents/skills/code-reviewer/SKILL.md", "approved-plan.md", "diff.patch", "write-report.md", "gate-recibo.json"]   # las que leíste completas; incluye tu SKILL.md y el recibo cuando exista
fecha: <ISO-8601>
---

## Auditoría de Código

### Veredicto
APPROVED | APPROVED WITH RECOMMENDATIONS | CHANGES REQUIRED | BLOCKED (infraestructura)
Tipo: implementación | arquitectura

### Issues detectados
| Severidad  | Área         | Descripción y sugerencia                                          |
| ---------- | ------------ | ----------------------------------------------------------------- |
| Bloqueante | Arquitectura | El Controller X llama directamente al Repository Y. Usar Service. |
| Sugerencia | Performance  | Usar FetchType.LAZY en la entidad X.                              |

### Resultado SonarQube (formato normalizado)
- projectKey por servicio: ... | omitido (sin proyecto Sonar) u omitido (clave Sonar no determinable: <motivo>)
- Base: merge-base <sha> — `git rama_base` de `.agents/stack.yaml`; si es `null`, `HEAD`
- Por fichero: estado, scope, ruta (y ruta antigua si renombrado)
- Conteo por regla: `ruleKey: antes N → ahora M → +K`
- Issues nuevos: ... (ruleKey, impacts, línea si hay, mensaje, explicación de show_rule) | Ninguno
- SQL por concatenación (sql-concat-scan): Ninguno | lista (ruta:línea)
- Quality Gate (informativo): OK | ERROR | WARN | NONE | N/A (sin proyecto Sonar) | N/A (clave Sonar no determinable: <motivo>)
- ALCANCE: El análisis por fichero no cubre todas las reglas del servidor. El Quality Gate del CI puede fallar aunque este gate pase.
- AVISO CI: ... (solo si aplica)
- Veredicto SonarQube: PASA | BLOQUEA | BLOCKED (infraestructura)

### Evidencia del Grafo
- Surprising connections: (lista o "Ninguna detectada")
- Validaciones arquitectónicas: (ej: "No hay acoplamientos inesperados")
```


Consulta y actualización condicional del grafo: usa graphify solo cuando `herramientas.graphify` en `.agents/stack.yaml` sea `true`; con `false`, omite las consultas y actualizaciones al grafo.
