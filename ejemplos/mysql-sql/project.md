---
trigger: always_on
---

# Datos del proyecto

## Stack y estructura
- Motor, versión, esquema y carpeta de notebooks se leen de `base_de_datos.*` en `.agents/stack.yaml`. En este proyecto el esquema es `Pedidos` y los notebooks están en `pedidos-db/`.
- Los objetos y scripts de la base se guardan solo en notebooks `.dbcnb` versionados (no hay migraciones Flyway ni Liquibase).
- El sandbox usa la imagen `mysql:<base_de_datos.version>` (la variable `SQL_SANDBOX_IMAGE` tiene prioridad).

## Notebooks canónicos por tipo de objeto
La lista vigente es el mapa `notebooks` de `.agents/stack.yaml`: un notebook por tipo de objeto (tablas, procedimientos, funciones, vistas, triggers, eventos, datos de prueba y libros de pruebas). Si el de un tipo aún no existe, se crea al guardar el primer objeto.

## Integraciones y conexiones
- **db-mcp-server**: registrado en las herramientas con el nombre de `mcp.base_de_datos`; expone herramientas por conexión (`schema_<conexión>`, `query_<conexión>`, …).
- **Conexiones**: la única permitida es la del mapa `conexiones` de `.agents/stack.yaml`, que apunta a una base de **desarrollo**, no a la de producción. Nunca se ejecutan escrituras sin sandbox y confirmación.
- **Graphify y tgrep**: `knowledge-base/` y `.agents/` están excluidos vía `.graphifyignore`; `tgrep` consulta `knowledge-base/`.

## Grafo de conocimiento: estado actual
- Los notebooks `.dbcnb` no entran en el grafo: un resultado vacío de `graphify query` sobre un objeto SQL significa «el grafo no cubre notebooks», no «sin dependencias». Las relaciones reales se comprueban por MCP en modo lectura y con `db-index.py`.

## Nomenclatura del esquema
La convención se declara en `nomenclatura` de `.agents/stack.yaml`.
- Excepción: la tabla heredada `log_auditoria` conserva su nombre en minúsculas porque la lee un proceso externo.

## Archivos sensibles y protegidos
- **Secretos**: `.vscode/mcp.json`, `logs/**` y cualquier `.env*`. Nunca se escriben contraseñas ni cadenas de conexión en archivos, comandos o notas.
- **Persistencia protegida**: nunca ejecutar en la base real `DROP DATABASE`, `DROP`, `TRUNCATE` ni `ALTER` destructivo sin confirmación explícita.
