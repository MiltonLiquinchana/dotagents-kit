---
name: sql-context-analyzer
description: Analiza el contexto técnico profundo de la base de datos MySQL en tiempo real usando db-mcp-server (FreePeak), tgrep sobre knowledge-base/ y, como complemento, Codebase Memory.
---

# SQL Context Analyzer

Rol: Mapea la realidad actual de la base de datos antes de tomar decisiones técnicas. Trabaja con datos reales desde MCP, tgrep sobre knowledge-base/ y, como complemento, Codebase Memory (que no cubre notebooks .dbcnb) — nunca con suposiciones.

## Entrada

Recibes `OUT_DIR` (carpeta donde escribes tu salida) y las rutas de estos archivos:

| Artefacto | Obligatorio | Contenido |
|---|---|---|
| `request.md` | sí | Solicitud del usuario, literal. |
| `feedback.md` | no | Correcciones pedidas sobre un intento anterior tuyo. Si existe, corrige solo lo que indica. |

Trabaja solo con estos archivos y con el código del proyecto. No asumas contexto fuera de ellos.
Si falta un artefacto obligatorio, no trabajes: escribe la salida con `estado: bloqueado` y la causa.
Si `tgrep` no está disponible, termina con `estado: bloqueado` y la causa.

## Fuentes de verdad (en orden de prioridad)

1. **MCP (`db-mcp-server`)** — Fuente primaria. Siempre refleja el estado real y actual de la BD viva. Solo herramientas de lectura (`schema_`, `query_`, `performance_`). NUNCA usar `execute_<conexión>` ni `transaction_<conexión>`.
2. **tgrep sobre `knowledge-base/`** — historial de decisiones y fixes por objeto.
3. **Codebase Memory** — Fuente secundaria. Complementa relaciones del SQL fuera de notebooks; los objetos se consultan con `db-index.py` y el MCP de lectura existente. Codebase Memory no cubre `.dbcnb`.

## MCP Tools disponibles (solo lectura)

Los tools se generan dinámicamente por conexión, siempre con una conexión del mapa `conexiones` de `.agents/stack.yaml`:
- `schema_<conexión>` — obtener tablas, columnas, índices y FKs
- `query_<conexión>` — ejecutar SELECT de solo lectura
- `performance_<conexión>` — analizar rendimiento de consultas (solo lectura)

## Tareas

1. **Tarea 1 — Búsqueda previa en knowledge-base (tgrep)**: Extrae 2-4 términos clave de la feature y búscalos con `tgrep "<término>" knowledge-base/ -C 3`.
2. **Tarea 2 — Detectar motor y versión**:
   ```sql
   SELECT VERSION();
   ```
   Anotar la versión exacta de MySQL/MariaDB (condiciona soporte de sintaxis).
3. **Tarea 3 — Mapear esquema real con MCP**:
   ```text
   schema_<conexión>("tables")
   schema_<conexión>("columns", "nombre_tabla")   // para tablas relevantes a la feature
   schema_<conexión>("constraints", "nombre_tabla")
   ```
4. **Tarea 4 — Verificar procedimientos almacenados existentes**:
   ```sql
   SHOW PROCEDURE STATUS WHERE Db = '<base_de_datos.nombre>';
   SHOW FUNCTION STATUS WHERE Db = '<base_de_datos.nombre>';
   SHOW FULL TABLES WHERE Table_type = 'VIEW';
   SHOW EVENTS FROM <base_de_datos.nombre>;
   ```
5. **Tarea 5 — Analizar tablas relevantes para la feature solicitada**:
   ```sql
   SHOW CREATE TABLE nombre_tabla;
   ```
6. **Tarea 6 — Consultar el grafo para relaciones entre objetos del repositorio**:
   Consulta los objetos de notebooks con `db-index.py` y el MCP de lectura existente. Solo si `herramientas.codebase_memory` es `true` y `python3 -I -B .agents/scripts/codebase-memory.py --comprobar` da OK, complementa las relaciones del SQL fuera de `.dbcnb`:
   ```bash
   codebase-memory-mcp cli search_graph --project "<proyecto>" --name-pattern ".*<símbolo>.*"
   codebase-memory-mcp cli trace_path --project "<proyecto>" --function-name "<símbolo>" --direction inbound
   codebase-memory-mcp cli get_architecture --project "<proyecto>"
   ```
   Si la búsqueda por nombre no basta, complementa con `codebase-memory-mcp cli search_graph --project "<proyecto>" --semantic-query '["texto"]'`. Un resultado vacío no demuestra ausencia; revisa cobertura y fuente. Con índice ausente, omite el complemento sin error.
7. **Tarea 7 — Detectar discrepancias**: Comparar lo encontrado en la BD real (MCP) con lo encontrado en notas de tgrep y notebooks leídos directamente. Reportar diferencias sin corregirlas.
8. **Tarea 8 — Historial de correcciones (vinculante)**:
   ```bash
   tgrep --files knowledge-base/ | grep -E "/<objeto>-fixes\.md$"
   ```
   Si el historial reporta enfoques fallidos, inclúyelos en `enfoques_descartados` de la salida.
9. **Tarea 9 — Notas de conocimiento existentes**:
   ```bash
   tgrep "^entidad_principal: <objeto>\s*$" knowledge-base/ -l
   ```
   Si existe, léela e incorpórala como contexto.
10. **Tarea 10 — Complemento determinista**:
    `Codebase Memory` no cubre los notebooks `.dbcnb`. Como complemento determinista (sin MCP y sin conectarse a la BD) usa el índice de objetos:
    ```bash
    python3 -B -E .agents/scripts/db-index.py                       # resumen por tipo
    python3 -B -E .agents/scripts/db-index.py --list PROCEDURE      # nombres de un tipo
    python3 -B -E .agents/scripts/db-index.py --object <nombre>     # parámetros, tablas que usa, alias
    python3 -B -E .agents/scripts/db-index.py --table <Tabla>       # dependencias hacia ella
    python3 -B -E .agents/scripts/db-index.py --contracts           # contrato de cada procedimiento
    ```
    En el reporte, incluye los consumidores del contrato del backend cuando el objeto sea un procedimiento (`.agents/rules/architecture-rules.md` § 8).

## Reglas

- **Marcadores de parámetros**: los marcadores `<clave>` (p. ej. `<base_de_datos.nombre>`) se resuelven con `.agents/stack.yaml` (los scripts los leen vía `stack.py`; los humanos, con `python3 -B -E .agents/scripts/stack.py get <clave>`).

- Aplica `.agents/rules/architecture-rules.md`, `.agents/rules/project.md`, `.agents/rules/codebase-memory.md`, `.agents/rules/tgrep.md` y `.agents/rules/knowledge-base.md`.
- Solo lectura: NUNCA ejecutar DDL ni DML (`execute_<conexión>` ni `transaction_<conexión>`).
- No asumir esquemas sin verificar con los tools MCP.
- La conexión se elige con el mapa `conexiones` de `.agents/stack.yaml`: una entrada → esa; dos o más → pregunta; ninguna (`{}`) → sin ejecución en la base real. Nunca uses una conexión que no esté en el mapa, aunque el servidor MCP la exponga.
- `knowledge-base/` nunca se consulta vía Codebase Memory; siempre vía `tgrep`.
- No reindexes (`python3 -I -B .agents/scripts/codebase-memory.py --indexar`) desde aquí.

## Salida

Escribe **un único archivo**: `OUT_DIR/context.md`, con este formato:

```markdown
---
artefacto: context.md
skill: sql-context-analyzer
estado: ok | fallo | bloqueado
entradas_leidas: [request.md]
fecha: <ISO-8601>
enfoques_descartados: []
---

## Reporte de Contexto SQL

### Motor y versión
- Motor: MySQL (versión detectada: ej. 8.0.36)
- BD: (`base_de_datos.nombre` de `.agents/stack.yaml`)
- DB ID en config.json: (ej. mysql1)

### Tablas relevantes para la feature
| Tabla | Columnas clave | FKs | Índices existentes |
|-------|---------------|-----|-------------------|
| ...   | ...           | ... | ...               |

### Procedimientos almacenados relacionados
- (nombres encontrados o "Ninguno")

### Hallazgos del grafo (si aplica)
- Notebooks existentes que prueban objetos relacionados: ...
- Scripts del repositorio vinculados: ...

### Discrepancias detectadas (BD real vs. repositorio)
- [ ] (objeto en repositorio pero no en la BD, o viceversa)
- (o "Ninguna detectada")

### Correcciones previas relevantes
- (Lista de fixes o "N/A")

### Notas de conocimiento previas
- (Resumen o "N/A")

### Recomendación de diseño
- (Indicar si se puede extender lógica existente o si se debe crear estructura nueva)
```


Si `herramientas.codebase_memory` de `.agents/stack.yaml` es `false`, no consultes Codebase Memory: usa MCP de lectura, `db-index.py` y `tgrep` como fuentes de contexto.

Consulta y actualización condicional del grafo: usa Codebase Memory solo cuando `herramientas.codebase_memory` en `.agents/stack.yaml` sea `true`; con `false`, omite las consultas y actualizaciones al grafo. Resuelve `<proyecto>` con `python3 -I -B .agents/scripts/codebase-memory.py --resolver` (exit 0) antes de consultar. Un resultado vacío no demuestra ausencia: usa `check_index_coverage` y, si hay dudas, busca en la fuente.
