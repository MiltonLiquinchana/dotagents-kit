---
trigger: model_decision
description: Consult knowledge-base/ via tgrep for engineering history, past decisions, and prior fixes.
---

## tgrep (notas de conocimiento, exclusivamente)

`knowledge-base/` es la memoria de largo plazo del proyecto: decisiones, propósito y correcciones previas de cada fichero, en Markdown, indexadas por `tgrep` (no por graphify — ver `.agents/rules/graphify.md`). `tgrep` da recall exacto e instantáneo, sin costo de tokens.

**Precondición (bloqueante)**: `tgrep` es parte de la infraestructura del flujo, no una ayuda opcional. `bash .agents/scripts/preflight.sh` la verifica y solo la arranca en la fase permitida sin bloqueos estrictos; si consultas fuera de ese flujo, confirma tú el estado:
```bash
tgrep status knowledge-base/
```
Con el servidor activo, la salida empieza por `Server status for …`. Si empieza por `Index status for …` y muestra `Server: not running`, no hay servidor: propone `preparar-proyecto.sh --arrancar-tgrep`, con el mismo permiso previo de PREPARACION antes del plan; solo tras obtenerlo se arranca en segundo plano, desacoplado de la subshell (indexa y queda vigilando cambios en vivo):
```bash
bash .agents/scripts/preparar-proyecto.sh --arrancar-tgrep
```
`knowledge-base/` debe existir (el repositorio versiona `knowledge-base/.gitkeep`). Un índice vacío converge de inmediato (`Files: 0`, `Indexing:   complete`).

Un servidor recién arrancado responde a `tgrep status` de inmediato, pero mientras `Indexing:` no marque `complete` las búsquedas se resuelven contra un índice vacío y devuelven cero resultados sin error — indistinguible de "no hay historial". Esto es crítico para la búsqueda de "Historial de correcciones vinculante" (ver análisis de contexto): un resultado vacío con el índice aún en construcción no autoriza reproponer un enfoque ya marcado como fallido. Si `tgrep serve` se acaba de arrancar en esta misma invocación, vuelve a chequear `tgrep status` y confirma `Indexing:   complete` antes de confiar en un resultado vacío.

**Sin fallback.** Si tras 3 reintentos de `tgrep status` (con 2 s de espera entre intentos y 1 s después de arrancar) `Indexing:` sigue sin marcar `complete`, o `tgrep` no está instalado, **detén la ejecución con `BLOCKED [TGREP]` (o `BLOCKED [HERRAMIENTA]` si falta la CLI)** ("Índice de tgrep no converge a complete tras 3 intentos" / "CLI tgrep no encontrada"). No caigas a `grep`/`rg`: un resultado vacío sobre un índice no fiable no autoriza reproponer un enfoque ya marcado como fallido, y un fallback silencioso ocultaría exactamente ese caso.

## Códigos de salida y estados que no son fallo

- `tgrep` termina con exit 0 si hay coincidencias, exit 1 si **no hay coincidencias** (un resultado válido, no un fallo) y exit ≥ 2 solo ante un error real.
- Si `tgrep` avisa `falling back to local index`, no es un error: si el último `tgrep status` reporta `Indexing: complete`, el índice local devuelve los mismos resultados que el servidor. Continúa con la búsqueda. La regla "sin fallback" significa no cambiar a `grep`/`rg`, no usar ese índice.
- Si, dentro del sandbox de tu herramienta, `tgrep status` dice `Server: not running` pero existe `knowledge-base/.tgrep/serve.json`, el servidor existe y el sandbox no lo ve: **no arranques otro servidor, no borres el índice ni el lock** y no diagnostiques con `ps`. Busca igual con el índice local; si necesitas el servidor, pide al usuario permisos de red y procesos para tu herramienta.
- Si `knowledge-base/` solo contiene `.gitkeep` o no tiene ninguna nota `.md`, no hay historial que buscar: la fase registra "sin historial (`knowledge-base` vacío)" y continúa sin tgrep (no lo necesita).

## Reglas

- **Búsqueda literal previa, antes de razonar sobre una feature o un bug**: extrae 2-4 términos clave (mensaje de error exacto, nombre de clase, componente) y búscalos primero aquí — gratis y determinístico, a diferencia de `graphify query`:
```bash
  tgrep "<término exacto>" knowledge-base/ -C 3
  tgrep "<término>" knowledge-base/ -g "*-fixes.md" -C 3
```
- **Encontrar la nota de un fichero de código específico**, por su campo `fichero:` en frontmatter:
```bash
  tgrep -F "fichero: <ruta relativa del código>" knowledge-base/ -l
```
- **Historial de correcciones vinculante**: antes de proponer un enfoque, comprueba **por ruta completa** si existe la nota de correcciones del fichero: `knowledge-base/<ruta relativa del código sin extensión>-fixes.md` con `test -f`. **No busques por nombre base**: en este monorepo hay clases homónimas en varios servicios (mismo nombre de clase en paquetes distintos) y proyecciones repetidas, y una búsqueda por nombre devuelve la nota de otro servicio. Si la nota existe, revisa si documentó un intento fallido sobre el mismo síntoma. Un enfoque ya marcado como fallido no puede reproponerse sin que el Plan documente por qué las condiciones cambiaron (ver análisis de contexto).
- **Nunca esperes que graphify sepa esto.** Las dos fuentes son independientes por diseño.
