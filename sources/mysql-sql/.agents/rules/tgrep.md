---
trigger: model_decision
description: Consult knowledge-base/ via tgrep for engineering history, past decisions, and prior fixes.
---

## tgrep (notas de conocimiento, exclusivamente)

`knowledge-base/` es la memoria de largo plazo del proyecto: decisiones, propósito y correcciones previas de cada objeto SQL, en Markdown, indexadas por `tgrep` (no por graphify — ver `.agents/rules/graphify.md`). `tgrep` da recall exacto e instantáneo.

**Precondición bloqueante**: confirma que el servidor está activo antes de consultar:
```bash
tgrep status knowledge-base/
```
Si no responde, propón la preparación y pide permiso al usuario antes del plan; solo con ese permiso ejecútala (indexa y queda vigilando cambios en vivo):
```bash
bash .agents/scripts/preparar-proyecto.sh --arrancar-tgrep
```
**Si `tgrep` no está instalado o el servidor no arranca, la ejecución se detiene e informa al usuario.**

Un servidor recién arrancado responde a `tgrep status` de inmediato, pero mientras `Indexing:` no marque `complete` las búsquedas se resuelven contra un índice vacío y devuelven cero resultados sin error — indistinguible de "no hay historial". Esto es crítico para la búsqueda de "Historial de correcciones vinculante" (ver análisis de contexto): un resultado vacío con el índice aún en construcción no autoriza reproponer un enfoque ya marcado como fallido. Si `tgrep serve` se acaba de arrancar en esta misma sesión de trabajo, vuelve a chequear `tgrep status` y confirma `Indexing: complete` antes de confiar en un resultado vacío de esa búsqueda vinculante.

Si tras 3 reintentos de `tgrep status` (2 s entre intentos; 1 s tras arrancar) no aparece `Indexing:   complete`, detente con `BLOCKED [TGREP]`. No hay fallback a grep/rg.

## Reglas

- **Búsqueda literal previa** (2-4 términos: mensaje de error, nombre de objeto, tabla):
  ```bash
  tgrep "<término exacto>" knowledge-base/ -C 3
  tgrep "<término>" knowledge-base/ -g "*-fixes.md" -C 3
  ```
- **Nota de un objeto SQL** (ruta anclada, evita falsos positivos por prefijo):
  ```bash
  tgrep --files knowledge-base/ | grep -E "/<objeto>\.md$"
  ```
- **Confirmación por frontmatter**:
  ```bash
  tgrep "^entidad_principal: <objeto>\s*$" knowledge-base/ -l
  ```
- **Objetos documentados de un notebook**:
  ```bash
  tgrep -F "fichero: <ruta del notebook>" knowledge-base/ -l
  ```
- **Historial de correcciones vinculante** (anclado al nombre completo):
  ```bash
  tgrep --files knowledge-base/ | grep -E "/<objeto>-fixes\.md$"
  ```
- **Historial vinculante**: un enfoque marcado como fallido en `<objeto>-fixes.md` no puede reproponerse sin que el Plan documente por qué cambiaron las condiciones (ver análisis de contexto).
- **Nunca esperes que graphify sepa esto**: las dos fuentes son independientes por diseño. Además, los notebooks `.dbcnb` no están en el grafo.
