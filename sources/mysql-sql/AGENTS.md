# Instrucciones para agentes

## Antes de empezar
Lee siempre `.agents/stack.yaml` (parámetros del proyecto) y `.agents/rules/project.md` (descripción del
proyecto). Los marcadores `<clave>` que aparezcan en skills, reglas o workflows se resuelven con `stack.yaml`.

## Cómo trabajar
- Las skills están en `.agents/skills/<nombre>/SKILL.md`; esa ruta identifica el contenido de la skill cuando un workflow asigna una fase.
- Para implementar cualquier nueva funcionalidad o cambio estructural en la BD, sigue estrictamente el workflow [.agents/workflows/build-database-feature.md](.agents/workflows/build-database-feature.md).
- Todo cambio de código o de artefactos del proyecto (incluido adaptar pipeline, manifiestos o código tras cambiar `stack.yaml`) sigue un workflow. Si el usuario no lo nombra, el agente elige el que corresponde y lo dice antes de empezar; nunca aplica una skill suelta: `implement-microservice-feature` en el back, `implement-feature` en el front o `build-database-feature` en el SQL según el cambio, y los de versión, documentación e incorporación cuando proceda.
- Para generar o actualizar notas de conocimiento de objetos SQL sin implementar cambios, sigue [.agents/workflows/knowledge-base.md](.agents/workflows/knowledge-base.md).

## Reglas globales
- **Criterio senior**: Actúa con el rigor técnico de un arquitecto de datos o DBA senior. No pidas permiso para decisiones técnicas cubiertas por las reglas.
- **Seguridad First**: Considerar siempre el riesgo de inyección SQL, bloqueos de tabla (locks) y pérdida de datos.
- **Confirmación explícita**: Solicita confirmación solo en decisiones irreversibles: `DROP`, `TRUNCATE`, `ALTER` destructivo, o cambios que afecten el contrato de datos con otros servicios.
- **Secretos protegidos**: Ninguna tarea lee ni cita credenciales ni pasa archivos sensibles como contexto. Está prohibido leer archivos de configuración para extraer un token, aunque no se imprima; solo los scripts de `.agents` pueden usarlo internamente. Si una credencial falla, detente e informa. Nunca pruebes otras credenciales, usuarios o servidores ni adivines contraseñas. Las rutas concretas de este proyecto están en `.agents/rules/project.md`.
- **MCP de base de datos (`<mcp.base_de_datos>`)**: En tareas de análisis, diseño y auditoría, usa MCP exclusivamente en modo lectura (solo las conexiones declaradas en `conexiones` de `.agents/stack.yaml`, con herramientas `schema_<conexión>`, `query_<conexión>`, `performance_<conexión>`). Operaciones de modificación (`execute_<conexión>`, `transaction_<conexión>`) requieren validación previa en sandbox y persistencia en notebook.
- **Temporales**: Crea tus ficheros temporales con `mktemp -d` fuera del repositorio y borra **solo el directorio que tú creaste** (guarda la ruta que devolvió `mktemp`). Nunca borres con comodines (`/tmp/tmp.*`): puedes eliminar el trabajo de otra fase.

## Herramientas de consulta
- **MCP de base de datos (`<mcp.base_de_datos>`)**: Fuente primaria de verdad sobre el esquema real de la base de datos viva (las conexiones permitidas y su destino están en `conexiones` de `.agents/stack.yaml`; herramientas `<acción>_<conexión>`). Detalle en `.agents/rules/project.md`.
- **Codebase Memory**: Si `herramientas.codebase_memory` de `.agents/stack.yaml` es `true`, consulta el grafo (`search_graph`, `trace_path`, `get_code_snippet` y `get_file_outline`, con el proyecto resuelto por `python3 -I -B .agents/scripts/codebase-memory.py --resolver`) para dependencias de código; los notebooks no están en el grafo. Detalle en `.agents/rules/codebase-memory.md`.
- **tgrep**: Consulta notas de contexto e historial vinculante de correcciones previas en `knowledge-base/`. Detalle en `.agents/rules/tgrep.md`.

## Mapa de reglas
| Archivo | Qué contiene |
|---|---|
| `.agents/stack.yaml` | Parámetros del proyecto: motor, versión, esquema, carpeta y mapa de notebooks, conexiones MCP que usan scripts, skills y workflows |
| `.agents/rules/project.md` | Descripción de este proyecto: dónde vive cada cosa, conexión MCP (mismo servidor para libro y pruebas), nomenclatura y secretos |
| `.agents/rules/architecture-rules.md` | Reglas de arquitectura SQL (MySQL, tipos de datos, FKs, índices, SPs y contratos) |
| `.agents/rules/sql-quality-gate.md` | Gate determinista de calidad, linter diferencial (sql-lint.py), sandbox y aserciones |
| `.agents/rules/performance-budget.md` | Métricas y reglas de rendimiento de consultas y SPs (EXPLAIN, sargability) |
| `.agents/rules/codebase-memory.md` | Guía de uso y reglas del grafo de conocimiento de código |
| `.agents/rules/knowledge-base.md` | Estructura, trazabilidad y mantenimiento de notas en `knowledge-base/` |
| `.agents/rules/tgrep.md` | Búsqueda y consulta de historial de decisiones y correcciones con tgrep |

## Documentación por versión

Open Notebook es obligatorio. El preflight comprueba su conexión y la existencia de los IDs asociados por GET, y coteja el inventario con `.agents/documentacion.json`. Prepara fuentes con aprobación en `.agents/workflows/preparar-documentacion.md`. `documentacion.json`, su Markdown y el catálogo del proyecto los escribe solo `documentacion.py`; nunca los edites a mano ni con código propio. Las órdenes con `--confirmar` o `--sha256-aprobado` solo se ejecutan dentro de `preparar-documentacion` (o `change-version`, si lo resuelve), tras la aprobación explícita del usuario de esa fuente y ese hash. Fuera de esos workflows, un «lanza preparar-documentacion» del preflight se propone al usuario, no se ejecuta. El catálogo del proyecto (`.agents/catalogo-proyecto.json`) lo amplía el script con la sección "Ampliar el catálogo del proyecto" de `preparar-documentacion.md`; el generador no lo sobrescribe. Consulta `python3 -I -B .agents/scripts/documentacion.py preguntar TECNOLOGIA "PREGUNTA_GENERICA" --servicio NOMBRE` (raíz: `.`). Solo preguntas públicas genéricas, sin código, tablas, datos, rutas ni credenciales. Solo las citas verificadas pueden entrar en un plan; sin evidencia pregunta al usuario. No cambies sus modelos ni su protección de Open Notebook.

Si faltan fuentes del catálogo, se pueden añadir patrones a una tecnología existente o aportar una URL pública concreta o un archivo público externo al repositorio, según la sección «Fuentes aportadas por el usuario» de preparar-documentacion.md, preparando primero el notebook de la tecnología y versión. Requiere revisión de contenido, versión, privacidad y aprobación de propuesta.aprobacion_sha256, el hash de bytes de la fuente. El script decide oficialidad mediante dominios_oficiales del catálogo (host y ruta); una tecnología nueva puede proponer esas reglas al ampliar el catálogo. Registra origen, oficialidad y hashes; «no oficial» significa procedencia del fabricante/proyecto no acreditada y requiere aviso y aprobación, sin rechazo automático. No se cargan archivos internos, credenciales ni datos del proyecto. El cotejo sigue siendo local y los registros antiguos se leen sin reescribirlos.

## Bloqueos y alcance del preflight

Ante un bloqueo del preflight, conserva y muestra la salida literal y su remedio. Lee la salida entera; si es larga, guárdala en un archivo dentro de `mktemp -d` y léela completa. No la recortes con `head`, `tail` ni filtros. Antes de `RESUMEN`, las líneas `REPASO bloqueo i/N` (o, si no las hay, la línea `RESULTADO` anterior) listan todos los bloqueos con su remedio. Consulta `.agents/config/codigos.yaml` para el workflow y la fase de la invocación. El agente solo aplica un remedio si ese código pertenece al alcance de su workflow y el remedio está incluido en el plan aprobado. En otro caso se detiene; no modifica scripts de `.agents` ni código del proyecto para conseguir que pase el preflight. Un aviso o una parte del plan no autoriza escrituras: presenta su alcance y espera la aprobación del plan. Nunca edites `.agents/stack.yaml` ni regeneres tus instrucciones durante el workflow: lo hace el usuario. La única excepción previa al plan es PREPARACION: cualquier workflow puede proponer `bash .agents/scripts/preparar-proyecto.sh`; solo lo ejecuta con permiso del usuario. El commit `chore: preparar el proyecto para .agents` lo hace el usuario, o el agente únicamente con su permiso. Después repite el preflight con los mismos argumentos. Si quedan otros bloqueos, se aplica esta misma regla.
