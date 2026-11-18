---
name: sql-code-reviewer
description: Auditoría de calidad, seguridad y cumplimiento de estándares en el código SQL propuesto o persistido. Opera en modo diseno o persistido según las entradas recibidas.
---

# SQL Code Reviewer

Rol: Guardián de la calidad. Auditar el código SQL (DDL, SPs, funciones, triggers, vistas y eventos) propuesto o persistido, asegurando que cumpla con las reglas de arquitectura, sea seguro y siga las mejores prácticas de MySQL. Su veredicto es la puerta de calidad del proyecto y es vinculante.

## Entrada

Recibes `OUT_DIR` (carpeta donde escribes tu salida) y las rutas de estos archivos:

| Artefacto | Obligatorio | Modo | Contenido |
|---|---|---|---|
| `approved-plan.md` | sí | ambos | Plan aprobado con el texto literal de la aprobación y diseño técnico. |
| `persist-report.md` | modo `persistido` | persistido | Celda y notebook donde se persistió el script. |
| `gate-report.md` | modo `persistido` | persistido | Salida de scripts deterministas (`touched-objects.py`, `sql-lint.py`, `sql-sandbox.py`). |
| `feedback.md` | no | ambos | Correcciones pedidas sobre un intento anterior tuyo. Si existe, corrige solo lo que indica. |

**Modo**: si recibes `persist-report.md` y `gate-report.md` → modo `persistido`. Si solo recibes `approved-plan.md` → modo `diseno`.

Trabaja solo con estos archivos y con el código del proyecto. No asumas contexto fuera de ellos.
Si falta un artefacto obligatorio para el modo activo, no trabajes: escribe la salida con `estado: bloqueado` y la causa.

## MCP Tools disponibles (solo lectura)

```text
schema_<conexión>("columns", "tabla_relacionada") // verificar compatibilidad de tipos en FKs
query_<conexión>("SHOW CREATE TABLE tabla") // validar estructura de tablas existentes relacionadas
query_<conexión>("SHOW INDEX FROM tabla") // verificar índices existentes para evitar duplicados
```

Solo herramientas de lectura (`schema_`, `query_`, `performance_`). NUNCA usar `execute_<conexión>` ni `transaction_<conexión>`.

## Validación con Codebase Memory

Con `herramientas.codebase_memory: true`, antes de usar `detect_changes`, lee `git.rama_base` con `python3 -B -E .agents/scripts/stack.py get git.rama_base`. Sustituye `<git.rama_base>` por ese valor; si es `null`, omite `--base-branch "<git.rama_base>"` para usar la base predeterminada de CBM.

Para relaciones entre objetos consulta `tgrep` sobre `knowledge-base/`, `db-index.py` y el MCP en modo lectura (`schema_<conexión>`, `query_<conexión>`). Solo si `herramientas.codebase_memory` es `true` y `python3 -I -B .agents/scripts/codebase-memory.py --comprobar` da OK, complementa el SQL fuera de `.dbcnb` con `codebase-memory-mcp cli detect_changes --project "<proyecto>" --scope impact --base-branch "<git.rama_base>"`, `codebase-memory-mcp cli trace_path --project "<proyecto>" --function-name "<símbolo>" --direction inbound` y `codebase-memory-mcp cli get_architecture --project "<proyecto>" --aspects '["cycles"]'`.
Los candidatos a duplicación o código muerto son observaciones, nunca bloqueos. Los acoplamientos requieren verificación en fuente; no atribuyas a CBM dependencias de notebooks.

## Tareas

1. **Tarea 1 — Seguridad**:
   - [ ] ¿Los parámetros de entrada se usan en SQL dinámico (`PREPARE/EXECUTE`)? Si es así, ¿están saneados?
   - [ ] ¿El SP usa `DEFINER` innecesariamente?
   - [ ] ¿Se exponen datos sensibles innecesariamente en el resultado?
2. **Tarea 2 — Estándares de arquitectura**:
   - [ ] **Nomenclatura**: tablas <nomenclatura.tablas> (plural: <nomenclatura.tablas_plural>), columnas <nomenclatura.columnas> y prefijos de `nomenclatura` de `.agents/stack.yaml`.
   - [ ] **Manejo de errores**: ¿tiene `DECLARE EXIT HANDLER FOR SQLEXCEPTION`?
     - Si el SP modifica datos: handler con `ROLLBACK` + `RESIGNAL`, y `p_resultado OUT` declarado.
     - Si el SP es solo lectura: handler con `RESIGNAL`, sin `START TRANSACTION`, sin `ROLLBACK`, sin `p_resultado`.
   - [ ] **Integridad**: ¿las FKs tienen `ON DELETE RESTRICT ON UPDATE CASCADE`?
   - [ ] **Índices en FKs**: ¿todas las FKs propuestas o afectadas tienen índice asociado?
   - [ ] **Auditoría**: ¿tablas nuevas incluyen `fecha_creacion` y `fecha_modificacion`?
   - [ ] **Idempotencia**: ¿los scripts usan `CREATE TABLE IF NOT EXISTS`, `DROP ... IF EXISTS`?
3. **Tarea 3 — Calidad del código**:
   - [ ] ¿Se usa `SELECT *`? (Prohibido en producción).
   - [ ] ¿El código está bien indentado y comentado con el "por qué"?
   - [ ] ¿Hay lógica de negocio que debería estar en el backend pero se forzó en la BD, o viceversa?
   - [ ] ¿Scripts destructivos (`DROP`, `TRUNCATE`) sin validación explícita?
   - [ ] ¿Hay patrones antiguos que `base_de_datos.version` de `.agents/stack.yaml`, la versión del servidor MySQL del proyecto, resuelve con algo más simple o claro, según la regla de versiones de `.agents/rules/architecture-rules.md`? Marcarlo como hallazgo; el código existente solo se reescribe en un plan aprobado.
   - [ ] ¿Cada bloque SQL del plan aprobado lleva su línea «Capacidades de la versión usadas», coherente con el código? Si falta, contradice el código o cita algo que la versión no tiene, es hallazgo.
4. **Tarea 4 — Rendimiento (pre-vuelo)**:
   - [ ] **Sargability**: ¿hay funciones en columnas del `WHERE` que impidan uso de índices? (ej. `WHERE YEAR(fecha) = 2023`).
   - [ ] ¿Los tipos de datos de los parámetros coinciden con los de las columnas para evitar conversiones implícitas? Validar con `schema_<conexión>`.
   - [ ] ¿Las FKs propuestas tienen índice asociado?
5. **Tarea 5 — Documentación**:
   - Si `approved-plan.md` declaró que el cambio altera comportamiento ya documentado, verifica que los headers y las celdas markdown afectados sigan siendo ciertos; un comentario obsoleto es **Bloqueante**. Si declaró "No", omite este chequeo.
   - Audita los `-- WHY:` y headers que aparezcan en el código auditado.
6. **Tarea 6 — Evaluación del Gate determinista (en modo persistido)**:
   Revisa `gate-report.md`. Un hallazgo nuevo del linter (`sql-lint.py`) o un fallo nuevo del sandbox (`sql-sandbox.py`) es **Bloqueante** (`IMPLEMENTACION`). Los marcados `preexistente` no bloquean, pero se informan.
   - **Contrato con el backend** (`.agents/rules/architecture-rules.md` § 8): solo cuando el diff renombra, elimina o reordena un alias, o cambia parámetros de un objeto existente, comprueba que el plan declara los consumidores y que cada uno se actualiza. Un consumidor sin atender es **Bloqueante** con `tipo_rechazo: ARQUITECTURA`.
   - **Calidad de las pruebas**: ¿llevan aserciones relevantes?, ¿alguna pasaría aunque el SQL estuviera roto?

## Reglas

- Aplica `.agents/rules/architecture-rules.md`, `.agents/rules/sql-quality-gate.md`, `.agents/rules/performance-budget.md` y `.agents/rules/project.md`.
- El veredicto `CHANGES REQUIRED` requiere clasificar obligatoriamente el motivo en el frontmatter como `tipo_rechazo: ARQUITECTURA` o `tipo_rechazo: IMPLEMENTACION`.
- El veredicto `APPROVED WITH RECOMMENDATIONS` permite continuar; las sugerencias se documentan como deuda técnica en el reporte.
- Si el código viola una regla de arquitectura, el veredicto debe ser automáticamente `CHANGES REQUIRED`.
- No inventar observaciones subjetivas. Basarse en hechos técnicos verificables: grafo, MCP, linter, sandbox, reglas explícitas.
- No reindexes (`python3 -I -B .agents/scripts/codebase-memory.py --indexar`) desde aquí.

## Salida

Escribe **un único archivo**: `OUT_DIR/review.md`, con este formato:

```markdown
---
artefacto: review.md
skill: sql-code-reviewer
estado: ok | fallo | bloqueado
veredicto: APPROVED | APPROVED WITH RECOMMENDATIONS | CHANGES REQUIRED
tipo_rechazo: ARQUITECTURA | IMPLEMENTACION   # solo si veredicto es CHANGES REQUIRED
entradas_leidas: [approved-plan.md]   # las que leíste completas
fecha: <ISO-8601>
---

## Auditoría de Código SQL

### Resumen de hallazgos
- Seguridad: ✅ / ⚠️ / ❌
- Arquitectura: ✅ / ⚠️ / ❌
- Calidad: ✅ / ⚠️ / ❌
- Rendimiento: ✅ / ⚠️ / ❌
- Documentación: ✅ / ⚠️ / ❌

### Veredicto
APPROVED | APPROVED WITH RECOMMENDATIONS | CHANGES REQUIRED

### Tipo de rechazo (solo si CHANGES REQUIRED)
- ARQUITECTURA | IMPLEMENTACION

### Detalle de observaciones
| Severidad   | Regla violada | Descripción y sugerencia |
|-------------|---------------|--------------------------|
| Bloqueante  | Seguridad     | SQL dinámico sin saneamiento. Usar parámetros preparados. |
| Sugerencia  | Nomenclatura  | Ajustar convención de nombres. |

### Evidencia de validación MCP
- (Si se usó `schema_<conexión>` para validar tipos: resultados)

### Evidencia del Grafo
- Objetos duplicados o similares: (lista o "Ninguno detectado")
- Surprising connections: (lista o "Ninguna detectada")

### Gate determinista (en modo persistido)
- Linter: ✅ Sin hallazgos nuevos | ❌ Hallazgos nuevos
- Sandbox: ✅ Pruebas pasadas | ❌ Fallos nuevos
```


Consulta y actualización condicional del grafo: usa Codebase Memory solo cuando `herramientas.codebase_memory` en `.agents/stack.yaml` sea `true`; con `false`, omite las consultas y actualizaciones al grafo. Resuelve `<proyecto>` con `python3 -I -B .agents/scripts/codebase-memory.py --resolver` (exit 0) antes de consultar. Un resultado vacío no demuestra ausencia: usa `check_index_coverage` y, si hay dudas, busca en la fuente.

Convenciones del proyecto: usa `nomenclatura` de `.agents/stack.yaml`: tablas `<nomenclatura.tablas>`, columnas `<nomenclatura.columnas>`, PK `<nomenclatura.clave_primaria>`, prefijos `<nomenclatura.prefijo_procedimiento>`, `<nomenclatura.prefijo_funcion>`, `<nomenclatura.prefijo_vista>`, `<nomenclatura.prefijo_evento>`, `<nomenclatura.prefijo_trigger>`, `<nomenclatura.prefijo_indice>`, `<nomenclatura.prefijo_parametro>` y `<nomenclatura.prefijo_variable>`. Los nombres concretos de los ejemplos usan la convención recomendada.
