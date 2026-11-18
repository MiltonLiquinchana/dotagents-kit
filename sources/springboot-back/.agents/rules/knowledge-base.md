---
trigger: model_decision
description: Base de conocimiento local (knowledge-base/), estructura de notas por microservicio, trazabilidad y convención de rutas.
---

# Base de Conocimiento (knowledge-base/, indexada por tgrep)

- **Ubicación**: `<raíz del repo>/knowledge-base/` — dentro del proyecto, versionada en Git junto al código. **Excluida de graphify** vía `.graphifyignore`; indexada y consultada por `tgrep` (ver `.agents/rules/tgrep.md`). Es Markdown plano y no depende de una aplicación externa para vivir dentro del repositorio.
- **Estructura**: `knowledge-base/<ruta relativa del fichero dentro del repo, sin extensión>.md` — espeja 1:1 la estructura de `<servicio>/src/main/java/...`. En un monorepo de microservicios no hace falta una capa de proyecto adicional: la carpeta del servicio ya queda reflejada porque forma parte de la ruta real del fichero. Ejemplo: `<servicio>/src/main/java/<paquete>/projection/DetallePedidoProjection.java` → `knowledge-base/<servicio>/src/main/java/<paquete>/projection/DetallePedidoProjection.md` (y `…-fixes.md` para sus correcciones). La ruta completa es obligatoria: hay clases homónimas en varios servicios (mismo nombre de clase en paquetes distintos) y proyecciones repetidas.
- **Una nota por fichero (1:1)**: todo fichero creado o tocado bajo `src/main/java/` tiene nota; los de `src/test/java/` no. El tipo de plantilla (Análisis o Compacta) lo decide la presencia de lógica, no el tamaño (ver criterios de documentación).
- **Campos de frontmatter mantenidos por el flujo**: `actualizado:` se refresca en toda edición de la nota; `estado_vinculacion:` (`vinculada` | `pendiente`) es el resultado de la verificación de vinculación.
- **Notas de corrección**: `knowledge-base/<misma ruta>-fixes.md` — log append-only. Cada corrección es una entrada nueva; nunca se sobreescribe.
- **Trazabilidad código↔nota**: cada nota declara `fichero:` (ruta real del código) en su frontmatter — esta es la fuente de verdad para la búsqueda `tgrep -F "fichero: <ruta>" knowledge-base/ -l`. La sección `## Fichero fuente` en el cuerpo es un recordatorio visual redundante, opcional para notas nuevas; ninguna herramienta depende de ella.
- **Mitigación de notas huérfanas — campo `entidad_principal`**: cada nota declara en su frontmatter el nombre exacto de la clase/símbolo principal tal como aparece en el código (ej. `InvitacionService`).
- **Actualización y mantenimiento**: las notas se generan o actualizan al finalizar cambios de código o a demanda para documentar ficheros específicos.
- **Decisión de arquitectura**: este proyecto excluye `knowledge-base/` del corpus de graphify. La verificación de vinculación (¿la nota referencia un fichero real?) se hace por convención de ruta (ver verificación de vinculación), no consultando el grafo.


## Notas proporcionadas por archivo

La nota 1:1 según Plantilla de Análisis es obligatoria solo para archivos con lógica. DTOs, interfaces puras, constantes y clases de error triviales no requieren nota propia. En modo `verificar`, no exijas una nota para esos archivos sin lógica; conserva la convención de rutas existente para que la búsqueda de `-fixes.md` siga funcionando.

Ejemplos de clientes y pedidos: ejemplo con la convención recomendada; las convenciones efectivas se leen de `.agents/stack.yaml`.
