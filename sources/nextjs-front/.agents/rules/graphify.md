---
trigger: model_decision
description: Consult the graphify knowledge graph at graphify-out/ for codebase and architecture questions.
---

## graphify

- Si `herramientas.graphify` en `.agents/stack.yaml` es `false`, no ejecutes graphify ni consultes el grafo.
- Resuelve las consultas de código y arquitectura solo con la CLI: `graphify query "<pregunta>"`, `graphify path "<A>" "<B>"` y `graphify explain "<concepto>"`. No uses el servidor MCP de graphify.
- Si falta la CLI, el preflight ya bloquea con `HERRAMIENTA`; no hay una alternativa de consulta.
- Para revisiones amplias de arquitectura, consulta `graphify-out/GRAPH_REPORT.md` solo si existe.
- Después de modificar código, actualiza desde la raíz del proyecto con `GRAPHIFY_BACKEND=none graphify . --update`. Si cambió `.graphifyignore`, reconstruye con `GRAPHIFY_BACKEND=none graphify .`: la actualización incremental no elimina los nodos que las nuevas exclusiones dejan fuera.
- El grafo cubre solo código y se genera sin modelo de lenguaje con `GRAPHIFY_BACKEND=none`. Si graphify pide un modelo, una clave o un paquete, detente e informa; no instales nada ni cambies de backend.
- `.graphifyignore` es obligatorio y debe acompañar a `.agents/` como archivo del repositorio. Debe excluir `knowledge-base/` y `.agents/`; el preflight lo comprueba con `PREPARACION`, que bloquea. Su preparación requiere permiso del usuario. Las exclusiones y sus consecuencias para el proyecto se declaran en `.agents/rules/project.md`.
