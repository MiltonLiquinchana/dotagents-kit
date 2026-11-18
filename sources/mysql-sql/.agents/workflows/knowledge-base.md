---
description: Genera o actualiza la nota de conocimiento en knowledge-base/ para un objeto SQL específico a demanda.
---

# Workflow: knowledge-base

Este workflow no genera ni adapta código y no consulta documentación por versión en Open Notebook; no depende de su cobertura documental. Conserva sus controles propios.

Este workflow se ejecuta a demanda para crear o actualizar la nota de conocimiento de un objeto SQL específico en `knowledge-base/`.

## Paso 0 — Inicialización

1. Si no se especificó el objeto en la solicitud, preguntar al usuario qué objeto documentar.
2. Crear carpeta de ejecución:
   ```bash
   RUN_DIR=".agent-runs/$(date +%Y%m%d-%H%M)-kb-$(basename <nombre-objeto>)"
   mkdir -p "$RUN_DIR/history"
   ```
   La carpeta vive en la raíz del proyecto, fuera de `.agents/`: los sandboxes de algunas herramientas montan `.agents/` en solo lectura, y los artefactos de la documentación tendrían que pedir permiso por cada escritura.
3. Escribir `RUN_DIR/request.md` con el nombre del objeto a documentar.
4. Inicializar `RUN_DIR/manifest.md`.

## Paso 1 — Documentar objeto

- **Skill**: `knowledge-writer` (modo `escribir` simplificado)
- **Ejecución**: subagente (ver `.agents/workflows/references/ejecutar-fase.md`)
- **Entrada**: `RUN_DIR/request.md`
- **Salida esperada**: `RUN_DIR/knowledge-report.md`
- **Condición**: siempre
- **Según el resultado**:
  - `estado: ok` → Paso 2.
  - `estado: fallo` | `bloqueado` → detener e informar al usuario.

## Paso 2 — Verificar vinculación

- **Skill**: `knowledge-writer` (modo `verificar`)
- **Ejecución**: subagente (ver `.agents/workflows/references/ejecutar-fase.md`)
- **Entrada**: `RUN_DIR/knowledge-report.md`
- **Salida esperada**: `RUN_DIR/link-check.md`
- **Condición**: siempre
- **Según el resultado**:
  - `estado: ok` → informar al usuario del objeto documentado con éxito.
  - `estado: fallo` | `bloqueado` → informar al usuario del estado pendiente para su resolución manual.
