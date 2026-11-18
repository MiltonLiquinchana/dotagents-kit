---
trigger: model_decision
description: Base de conocimiento local (knowledge-base/), estructura de notas, notas de corrección y trazabilidad con tgrep.
---

# Base de Conocimiento (knowledge-base/, indexada por tgrep)

- **Ubicación**: `<raíz del repo>/knowledge-base/` — dentro del proyecto, versionada en Git junto al código. **Excluida de graphify** vía `.graphifyignore`; indexada y consultada por `tgrep` (ver `.agents/rules/tgrep.md`). Es Markdown plano y no depende de ninguna aplicación externa. El frontmatter YAML y la sintaxis `[[ruta]]` de las plantillas se mantienen porque no le cuestan nada a `tgrep` (busca texto plano, no interpreta sintaxis).
- **Estructura**: `knowledge-base/<ruta relativa del fichero sin extensión>.md` — espeja 1:1 la estructura de `app/`, `controllers/`, `services/`, `repository/`, `domains/`, `utils/`, `lib/`, `hooks/` y `__tests__/`.
- **Notas de corrección**: `knowledge-base/<misma ruta>-fixes.md` — log append-only. Cada corrección es una entrada nueva; nunca se sobreescribe.
- **Trazabilidad código↔nota**: cada nota declara `fichero:` (ruta real del código) en su frontmatter — esta es la fuente de verdad para la búsqueda `tgrep -F "fichero: <ruta>" knowledge-base/ -l`. La sección `## Fichero fuente` en el cuerpo es un recordatorio visual redundante, opcional para notas nuevas; ninguna herramienta depende de ella.
- **Mitigación de notas huérfanas — campo `entidad_principal`**: cada nota declara en su frontmatter el nombre exacto de la clase/símbolo principal.
- **Actualización y mantenimiento**: las notas se generan o actualizan al finalizar cambios de código o a demanda para documentar ficheros específicos.


## Notas proporcionadas por archivo

La nota 1:1 según Plantilla de Análisis es obligatoria solo para archivos con lógica. DTOs, interfaces puras, constantes y clases de error triviales no requieren nota propia. En modo `verificar`, no exijas una nota para esos archivos sin lógica; conserva la convención de rutas existente para que la búsqueda de `-fixes.md` siga funcionando.
