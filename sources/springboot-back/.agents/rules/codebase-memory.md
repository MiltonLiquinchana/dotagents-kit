---
trigger: model_decision
description: Query the Codebase Memory graph with its CLI for code and architecture questions.
---

## Codebase Memory

- Si `herramientas.codebase_memory` de `.agents/stack.yaml` es `false`, no consultes ni indexes el grafo.
- Usa la CLI `codebase-memory-mcp cli <herramienta> --project <proyecto>` para las consultas. Resuelve `<proyecto>` con `python3 -I -B .agents/scripts/codebase-memory.py --resolver` y continúa solo si termina con exit 0. Consulta la sintaxis con `codebase-memory-mcp cli <herramienta> --help`.
- Localiza primero símbolos por nombre con `search_graph --name-pattern ".*<símbolo>.*"`. Si no basta, complementa con `search_code --pattern "<texto literal>"` para localizar un literal del código (un mensaje, una ruta, una anotación o un texto de la interfaz); con `--regex true` admite una expresión regular. Usa `trace_path` para llamadas y dependencias, y `--direction inbound` para consumidores. Lee el código relevante con `get_code_snippet` y `get_file_outline` sin abrir archivos completos cuando el grafo responda.
- Usa `get_architecture` y `--aspects '["routes","hotspots","dependencies","cycles","layers","boundaries","entry_points"]'` para rutas, puntos calientes, dependencias, ciclos y módulos; `detect_changes` para el impacto de los cambios del árbol y de la rama frente a la rama base (`--base-branch`; por defecto `origin/HEAD`). Si `git.rama_base` de `.agents/stack.yaml` no es `null`, pásalo en `--base-branch`. Usa `search_code` para texto. Reserva `query_graph` para relaciones que las otras herramientas no cubran.
- Un resultado vacío no demuestra ausencia. Consulta `check_index_coverage` con las rutas y ámbitos relevantes; es orientativo. Si hay dudas o cobertura incompleta, busca en la fuente antes de concluir.
- Si falta la CLI, el preflight bloquea con `HERRAMIENTA`; no hay consulta alternativa.
- Actualiza desde la raíz con `python3 -I -B .agents/scripts/codebase-memory.py --indexar`. No uses `--name` ni `--persistence`; no instales hooks ni cambies la configuración de CBM.
- Si CBM pide una clave, un modelo o un servicio, detente e informa; no instales nada.
- `.cbmignore` es obligatorio, acompaña a `.agents/` como archivo versionado y excluye `knowledge-base/` y `.agents/`. Lo comprueba `PREPARACION`, que bloquea; prepararlo requiere permiso del usuario. Las exclusiones del proyecto se declaran en `.agents/rules/project.md`.
- El índice no contiene dependencias ni versiones: léelas de `<servicio>/build.gradle`. Las rutas de Spring Data REST no aparecen como `Route`; búscalas por `@RepositoryRestResource`.
