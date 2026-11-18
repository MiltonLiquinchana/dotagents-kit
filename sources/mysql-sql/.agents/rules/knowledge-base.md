---
trigger: model_decision
description: Base de conocimiento local (knowledge-base/), estructura de notas por objeto SQL y trazabilidad con tgrep.
---

# Base de Conocimiento (knowledge-base/, indexada por tgrep)

- **Ubicación**: `<raíz del repo>/knowledge-base/`, versionada en Git. Excluida de Codebase Memory vía `.cbmignore`; indexada y consultada por `tgrep` (ver `.agents/rules/tgrep.md`). Markdown plano; no depende de ninguna aplicación externa.
- **Estructura**: una nota por objeto SQL, no una por notebook (un `.dbcnb` contiene muchos objetos).
  - Nota: `knowledge-base/<tipo>/<objeto>.md`, con `<tipo>` ∈ `tabla | sp | funcion | vista | trigger | evento`.
  - Ejemplo: `knowledge-base/sp/sp_crear_pedido.md`.
- **Notas de corrección**: `knowledge-base/<tipo>/<objeto>-fixes.md`, log append-only. Cada corrección es una entrada nueva; nunca se sobreescribe.
- **Trazabilidad código↔nota**: cada nota declara en el frontmatter `fichero:` (ruta relativa del notebook `.dbcnb` que contiene el objeto) y `entidad_principal:` (nombre exacto del objeto). La verificación comprueba por convención de ruta que el notebook existe y que el nombre del objeto aparece dentro de él. Codebase Memory no participa.
- **Mitigación de notas huérfanas**: `entidad_principal` con el nombre exacto del objeto.
- **Actualización y mantenimiento**: las notas se generan o actualizan al finalizar cambios en objetos SQL o a demanda para documentar objetos específicos.
- **Control de versiones**: `knowledge-base/` está versionada y las notas se commitean junto con los notebooks. El índice en ejecución de `tgrep` (`knowledge-base/.tgrep/`) no se versiona y permanece ignorado por Git.


## Notas proporcionadas por archivo

La nota 1:1 según Plantilla de Análisis es obligatoria solo para archivos con lógica. DTOs, interfaces puras, constantes y clases de error triviales no requieren nota propia. En modo `verificar`, no exijas una nota para esos archivos sin lógica; conserva la convención de rutas existente para que la búsqueda de `-fixes.md` siga funcionando.

Ejemplos de clientes y pedidos: ejemplo con la convención recomendada; las convenciones efectivas se leen de `.agents/stack.yaml`.
