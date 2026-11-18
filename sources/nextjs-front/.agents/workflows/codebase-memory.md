---
description: Index the project with the Codebase Memory CLI
---

Si `herramientas.codebase_memory` de `.agents/stack.yaml` es `false`, no ejecutes este workflow.

# Workflow: codebase-memory

Este workflow no genera ni adapta código y no consulta documentación por versión en Open Notebook; no depende de su cobertura documental. Conserva sus controles propios.

Ejecuta todos los comandos desde la raíz del proyecto. Este workflow indexa el repositorio desde su raíz.

1. Comprueba la preparación:

   ```bash
   bash .agents/scripts/preparar-proyecto.sh --comprobar
   ```

   Si falla, propone `bash .agents/scripts/preparar-proyecto.sh` y ejecútalo solo con permiso del usuario. Repite la comprobación y continúa solo si pasa.

2. Comprueba la CLI con `command -v codebase-memory-mcp`. Si falta, propone:

   ```bash
   curl -fsSL https://raw.githubusercontent.com/DeusData/codebase-memory-mcp/main/install.sh | bash -s -- --skip-config
   ```

   Espera a que el usuario lo ejecute o autorice su ejecución y repite la comprobación. Este comando instala solo el binario. Si CBM pide una clave, un modelo o un servicio, detente e informa; no instales nada más.

3. Indexa el proyecto:

   ```bash
   python3 -I -B .agents/scripts/codebase-memory.py --indexar
   ```

   Si falla, detente y muestra la salida literal. Si informa un índice degradado, conserva el aviso al informar el resultado.

4. Comprueba el índice real e informa del proyecto y sus nodos:

   ```bash
   python3 -I -B .agents/scripts/codebase-memory.py --comprobar
   ```

   Si falla, detente y muestra la salida. Con 0 nodos, revisa `.cbmignore`; resuelve el nombre con `python3 -I -B .agents/scripts/codebase-memory.py --resolver` para mostrar también el proyecto cuando la comprobación solo emita el aviso de índice sin nodos.
