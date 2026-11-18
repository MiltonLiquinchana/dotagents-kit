# Referencia: herramientas MCP `db-mcp-server`

Carga este archivo solo cuando haya ambigüedad sobre el nombre o los parámetros de una herramienta. `SKILL.md` y `.agents/rules/sql-quality-gate.md` contienen el flujo normal.

## Herramientas disponibles (por conexión `<conexión>`)

### Schema
- `schema_<conexión>("tables")` – lista todas las tablas.
- `schema_<conexión>("columns", "nombre_tabla")` – lista columnas de una tabla.
- `schema_<conexión>("constraints", "nombre_tabla")` – lista restricciones (PK, FK, etc.).
- `schema_<conexión>("indexes", "nombre_tabla")` – lista índices.

### Query (solo lectura)
- `query_<conexión>("SELECT ...")` – ejecuta consultas SELECT (no modifica datos).

### Performance
- `performance_<conexión>("EXPLAIN SELECT ...")` – obtiene plan de ejecución.
- `performance_<conexión>("EXPLAIN FORMAT=JSON SELECT ...")` – plan en JSON.

### Execute
- `execute_<conexión>("DDL statement")` – ejecuta DDL (CREATE, ALTER, DROP).

### Transaction (solo DML, no DDL)
- `transaction_<conexión>("BEGIN")`, `transaction_<conexión>("ROLLBACK")` – para pruebas con datos sintéticos. **No usar en DDL.**

## Notas
- Las conexiones permitidas están en el mapa `conexiones` de `.agents/stack.yaml`. Nunca uses una conexión que no esté en ese mapa, aunque el servidor MCP la exponga.
- Para tareas de análisis o auditoría de solo lectura se usan exclusivamente herramientas de lectura (`schema_`, `query_`, `performance_`).
