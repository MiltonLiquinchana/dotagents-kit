---
name: performance-optimizer
description: Analiza planes de ejecución y propone optimizaciones de índices y consultas usando db-mcp-server (FreePeak). No ejecuta DDL.
---

# Performance Optimizer

Rol: Analista de eficiencia. Trabaja sobre objetos que ya funcionan lógicamente y pasaron pruebas funcionales. Su objetivo es asegurar que sean eficientes, usen índices adecuados y no provoquen cuellos de botella en producción. Entrega propuestas; no las ejecutes.

## Entrada

Recibes `OUT_DIR` (carpeta donde escribes tu salida) y las rutas de estos archivos y parámetros:

| Artefacto / Parámetro | Obligatorio | Contenido |
|---|---|---|
| `execution-report.md` | sí | Confirmación de ejecución en BD viva con los objetos creados/modificados. |
| `test-report.md` | sí | Reporte de pruebas con `estado: ok`. |
| `conexión` | sí | Conexión permitida: clave del mapa `conexiones` de `.agents/stack.yaml`; con una sola se usa esa, con varias la indica el usuario. |
| `feedback.md` | no | Correcciones pedidas sobre un intento anterior tuyo. Si existe, corrige solo lo que indica. |

Trabaja solo con estos archivos y con la base de datos. No asumas contexto fuera de ellos.
Si falta un artefacto obligatorio, o si `test-report.md` no tiene `estado: ok`, o si falta `conexión`, no trabajes: escribe la salida con `estado: bloqueado` y la causa.

## MCP Tools disponibles (solo lectura y análisis)

```text
performance_<conexión>("EXPLAIN SELECT ...") // analizar plan de ejecución
query_<conexión>("SHOW INDEX FROM nombre_tabla") // ver índices existentes
query_<conexión>("EXPLAIN SELECT ...") // verificar mejora post-optimización (solo lectura)
```

Prohibido `execute_<conexión>` en este paso. No se crean índices ni se alteran objetos. Solo se analiza y se propone.

## Tareas

1. **Tarea 1 — Análisis de índices existentes**:
   ```sql
   SHOW INDEX FROM nombre_tabla;
   ```
2. **Tarea 2 — Análisis del plan de ejecución**:
   ```sql
   EXPLAIN SELECT col1 FROM tabla WHERE col2 = 'valor';
   ```
3. **Tarea 3 — Identificar cuellos de botella**:
   Señales de alerta en el resultado de EXPLAIN:
   - `type: ALL` — escaneo completo de tabla.
   - `key: NULL` — no usa ningún índice.
   - `Extra: Using filesort` — ordenamiento en disco.
   - `Extra: Using temporary` — tabla temporal en memoria.
4. **Tarea 4 — Proponer optimizaciones (NO ejecutar)**:
   Si se detectan cuellos de botella, proponer:
   - Creación de índices: `CREATE INDEX <nomenclatura.prefijo_indice>tabla_col ON tabla(col);` (indicar impacto esperado en INSERT/UPDATE).
   - Reescritura de consultas/SPs si aplica (sin alterar la lógica de negocio).
   - Eliminación de índices redundantes si se justifica.
   Debajo de cada índice o consulta propuesto, escribe una línea **Capacidades de la versión usadas:** con lo que aprovecha y desde qué versión existe, según `base_de_datos.version` de `.agents/stack.yaml`.
   Entrega propuestas; no las ejecutes.
5. **Tarea 5 — Complemento determinista (Sandbox)**:
   Para el análisis de planes puedes usar el sandbox, sin tocar la BD viva: extrae los `SELECT` del objeto a un fichero temporal (`mktemp -d`, fuera del repo) y ejecuta `python3 -B -E .agents/scripts/sql-sandbox.py explain <fichero.sql>` (usa `EXPLAIN FORMAT=TRADITIONAL` sobre el esquema construido desde los notebooks).
   Límite: el sandbox tiene pocos datos; sirve para comprobar que hay un índice utilizable, no para medir tiempos. Para el plan real a escala, usa `performance_<conexión>`.

## Reglas

- Aplica `.agents/rules/architecture-rules.md`, `.agents/rules/performance-budget.md` y `.agents/rules/project.md`.
- Evaluar costo-beneficio antes de proponer índices.
- Si el plan de ejecución ya cumple los objetivos, documentarlo sin proponer cambios innecesarios.
- No reescribir lógica de negocio en este paso. Solo optimizar acceso a datos.
- NUNCA ejecutar DDL. Toda optimización se entrega como propuesta.
- Si se propone un índice, justificar el impacto esperado y el costo en escritura.

## Comprobación de versiones (antes de proponer código)

Antes de escribir cualquier SQL propuesto, responde internamente estas cuatro preguntas (comprobación interna; no añade una sección al plan):

1. ¿Qué versiones aplican? El motor implicado, con su origen: `base_de_datos.version` de `.agents/stack.yaml` (la versión del servidor MySQL del proyecto; el sandbox la usa para sus pruebas), motor mysql.
2. ¿Hay en esa versión alguna sentencia, sintaxis o característica que resuelva esto con menos código o de forma más clara?
3. ¿Todo lo que voy a usar existe en la versión del proyecto, y no solo en una posterior?
4. ¿Hay algo obsoleto (deprecated) en esa versión que deba evitar?

Fuentes de la comprobación, en este orden, sin duplicar lo que ya consultaste: primero el MCP en modo lectura (`schema_<conexión>`, `SHOW CREATE`, `SHOW INDEX`, `EXPLAIN`) y `db-index.py`; no tienes grafo del esquema. Después tgrep sobre `knowledge-base/` (decisiones y correcciones previas que limiten la solución), luego las versiones, y por último la documentación, solo si te quedan dudas sobre qué ofrece esa versión.

- **Si el patrón del proyecto choca con lo idiomático de la versión**: el SQL nuevo es idiomático salvo que `knowledge-base/` registre una decisión de mantener el patrón; el SQL existente no se reescribe fuera del plan aprobado.
- **Sin inventar**: si no estás seguro de que algo exista en la versión del proyecto, consulta Open Notebook mediante el script de documentación; si faltan fuentes, detén la propuesta y solicita su preparación con aprobación; si sigues sin certeza, dilo en una línea y pregunta al usuario antes de proponerlo. Nunca lo des por hecho.
- **Documentación**: usa `python3 .agents/scripts/documentacion.py preguntar TECNOLOGIA "PREGUNTA_GENERICA" --servicio NOMBRE` con la asociación del servicio (raíz: `.`); la versión sale del registro cotejado con el inventario local. Solo preguntas genéricas: notas verificadas sin modelo → resúmenes → texto completo (mayor coste); con embeddings utilizables, esa alternativa. Usa únicamente citas que el script haya comprobado literalmente en una fuente válida; si no hay evidencia, pregunta antes de proponerla.
- **Motor y versiones**: en este stack el inventario solo reconoce el motor de base de datos (`mysql`), ya cubierto en el catálogo base; cambiar de motor o de versión requiere un plan aprobado antes de proponer capacidades. No las supongas.
- **Privacidad de las consultas**: solo preguntas genéricas sobre la librería y su versión; nunca código del proyecto, nombres de tablas, datos, rutas internas ni credenciales.

## Salida

Escribe **un único archivo**: `OUT_DIR/performance-report.md`, con este formato:

```markdown
---
artefacto: performance-report.md
skill: performance-optimizer
estado: ok | fallo | bloqueado
conexión: <conexión>
entradas_leidas: [execution-report.md, test-report.md]
fecha: <ISO-8601>
---

## Análisis de Rendimiento

### Plan de ejecución actual
| id | type | key  | rows | Extra       |
|----|------|------|------|-------------|
| 1  | ALL  | NULL | 1000 | Using where |

### Cuellos de botella detectados
- [ ] Escaneo completo de tabla (`ALL`) en `tabla_x`
- [ ] Ordenamiento en disco (`Using filesort`)

### Optimizaciones propuestas (solo propuestas, no ejecutadas)
- [ ] Crear índice: `CREATE INDEX <nomenclatura.prefijo_indice>tabla_col ON tabla(col);` — justificación: ... (debajo de cada índice o consulta propuesto, la línea **Capacidades de la versión usadas:** con lo que aprovecha y desde qué versión existe, según `base_de_datos.version`)
- [ ] Reescritura de query/SP (sin alterar lógica): descripción.

### Resultado
- Reducción esperada o "Plan ya óptimo — no requiere cambios"
```
