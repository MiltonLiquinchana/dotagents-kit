---
description: Build the code-only graphify graph with the CLI
---

Si `herramientas.graphify` de `.agents/stack.yaml` es `false`, no ejecutes este workflow.

# Workflow: graphify

Este workflow no genera ni adapta código y no consulta documentación por versión en Open Notebook; no depende de su cobertura documental. Conserva sus controles propios.

Ejecuta todos los comandos desde la raíz del proyecto. Este workflow construye el grafo del proyecto y no admite un argumento de ruta.

1. Comprueba la preparación:

   ```bash
   bash .agents/scripts/preparar-proyecto.sh --comprobar
   ```

   Si falla, propone `bash .agents/scripts/preparar-proyecto.sh` y ejecútalo solo con permiso del usuario. Repite la comprobación y continúa solo si pasa.

2. Construye el grafo de código sin modelo:

   Si `command -v graphify` falla, propón `uv tool install graphifyy` y ejecútalo solo con permiso del usuario; luego repite.

   ```bash
   GRAPHIFY_BACKEND=none graphify .
   ```

   Si el comando falla, detente e informa. Si graphify pide un modelo, una clave o un paquete, detente e informa; no instales nada más ni cambies de backend.

3. Comprueba el JSON generado e informa del número de nodos y aristas:

   ```bash
   python3 -I -c 'import json; g=json.load(open("graphify-out/graph.json")); print("Nodos:", len(g["nodes"]), "Aristas:", len(g["links"]))'
   ```

   Si falta el archivo, el JSON no es válido o faltan los campos esperados, el comando falla: detente e informa; no des el grafo por comprobado.

`graphify-out/GRAPH_REPORT.md` puede no generarse con este modo. Es opcional y las reglas lo usan solo si existe.
