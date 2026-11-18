---
trigger: model_decision
description: Gate de calidad SQL, linter diferencial (sql-lint.py), sandbox en contenedor y aserciones de prueba.
---

# SQL Quality Gate

- La puerta de calidad del proyecto para objetos de base de datos es la revisión técnica de código.
- **Todo cambio que cree o modifique tablas, vistas, procedimientos, funciones o triggers debe superar la auditoría de calidad antes de ejecutarse en la BD viva.**
- El veredicto de revisión es vinculante y **debe incluir un campo `tipo_rechazo`** cuando sea `CHANGES REQUIRED`:
  - `ARQUITECTURA`: indica que el diseño o contrato requiere reiniciar la fase de análisis y diseño.
  - `IMPLEMENTACION`: permite volver a la fase de persistencia y ajuste del script sin rediseñar.
- Se considera bloqueante cualquier violación de `.agents/rules/architecture-rules.md` o de las comprobaciones de seguridad.
- No se permite introducir objetos sin:
  - manejo de errores (`DECLARE EXIT HANDLER` en SPs: con `ROLLBACK` + `RESIGNAL` para SPs que modifican datos, y `RESIGNAL` sin transacción para SPs de solo lectura),
  - índices en FKs,
  - script persistido en el notebook correspondiente antes de ejecutar en BD viva,
  - idempotencia (`IF NOT EXISTS` / `IF EXISTS` según corresponda),
  - ausencia de `SELECT *` en producción.

## Gate determinista

Antes de ejecutar cambios en la BD viva, se aplica un gate mecánico y reproducible:

1. **Linter diferencial** — `python3 -B -E .agents/scripts/sql-lint.py`. Compara, por objeto tocado, los hallazgos de la versión base (A) con los de la actual (B) por `(regla, texto normalizado)`. **Cualquier hallazgo nuevo bloquea** (exit 1); uno preexistente no. Exit 2 = `BLOCKED (infraestructura)`. Reglas: `select-star`, `dynamic-sql` (`PREPARE` con `CONCAT` o variables de usuario), `destructive` (`DROP TABLE/DATABASE`, `TRUNCATE`, `DELETE`/`UPDATE` sin `WHERE`), `exit-handler` (todo procedimiento lleva `EXIT HANDLER`; si escribe, además `START TRANSACTION` y `ROLLBACK`; con `RESIGNAL`), `sql-data-access` (todo procedimiento declara su característica de acceso a datos: `READS SQL DATA` si el cuerpo solo lee y `MODIFIES SQL DATA` si escribe; con `CONTAINS SQL` (el valor por defecto de MySQL) Connector/J rechaza las llamadas con conexión `readOnly`), `non-idempotent`, `missing-use`, `naming` (prefijos declarados en `nomenclatura` de `.agents/stack.yaml`), `list-order` (`sp_listar_*` sin `ORDER BY`), `sargable` (función sobre una columna en `WHERE`/`ON`), `audit-columns` (tabla nueva sin `fecha_creacion`/`fecha_modificacion`), `comment-syntax` (`--Texto` sin espacio: MySQL lo rechaza), `definer`, `credentials` y `hardcoded-secret`.
2. **Sandbox** — `python3 -B -E .agents/scripts/sql-sandbox.py run --base HEAD`: un MySQL **desechable** en contenedor (docker o podman; imagen `mysql:9.5.0` por defecto, configurable con `SQL_SANDBOX_IMAGE`) construye el esquema completo desde los notebooks y ejecuta las pruebas. Con `--base HEAD` construye y prueba antes la versión base: un fallo preexistente no bloquea. Sirve también `sql-sandbox.py explain <fichero.sql>` para evaluar planes de ejecución.
3. **Índice de dependencias** — `python3 -B -E .agents/scripts/db-index.py`: objetos, parámetros, tablas que usa cada objeto, alias del resultado y quién usa una tabla, calculado a partir de los notebooks.

## Formato de prueba con aserciones

Las pruebas en el sandbox se estructuran con directivas sobre la sentencia SQL:
- `-- @test <descripción>`
- `-- @expect-rows N`
- `-- @expect-rows-min N`
- `-- @expect-columns a,b,c`
- `-- @expect-error <SQLSTATE> <fragmento>`

Sin directivas, la prueba opera en modo humo (valida ejecución sin error de sintaxis ni runtime).

## Alcance del gate local

*(Declararlo siempre en el informe de revisión)*: *"El gate valida sintaxis, dependencias y comportamiento en un MySQL desechable de versión <X> con los datos de prueba del repositorio, y aplica un linter heurístico. No cubre diferencias con la versión de MySQL de las bases reales (el MCP maneja dos), volumen y concurrencia reales, la semántica del negocio ni consumidores fuera de este repositorio y del backend hermano."*


## Identificación y aislamiento de pruebas

Cada celda de prueba puede identificarse con `-- @test: <id>` en su primera línea y actualizarse de forma idempotente con `python3 .agents/scripts/nb-edit.py upsert-test --book "<libro>" --id <id> --sql-file <f>`. El sandbox ejecuta cada celda en una sesión independiente: las variables `@x` no pasan a otra celda; calcula cualquier valor previo dentro de la misma celda. `@expect-columns` no se puede comprobar cuando el resultado tiene 0 filas; para ese caso usa solo `@expect-rows 0`.
