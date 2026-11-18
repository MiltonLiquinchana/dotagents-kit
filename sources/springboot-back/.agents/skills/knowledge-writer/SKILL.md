---
name: knowledge-writer
description: Genera y mantiene notas de conocimiento en Markdown sobre los ficheros del proyecto y su historial de correcciones. Indexadas por tgrep. Opera en dos modos según la entrada recibida.
---

# Knowledge Writer

Rol: Traduce el contexto ya generado durante la implementación en notas
persistentes en `knowledge-base/`. **No es una fuente de análisis nueva** — es
una capa de persistencia sobre análisis que ya ocurrió.

## Entrada

Recibes `OUT_DIR` (carpeta donde escribes tu salida) y las rutas de estos archivos:

| Artefacto | Obligatorio | Modo | Contenido |
|---|---|---|---|
| `approved-plan.md` | modo `escribir` | escribir | Plan aprobado. |
| `diff.patch` | modo `escribir` | escribir | Diff del working tree. |
| `tipo` | modo `escribir` | escribir | `feature` o `fix`. |
| `docs-summary.md` | no | escribir | Documentación generada. Si no existe, trabaja solo con `approved-plan.md` y `diff.patch`. |
| `knowledge-report.md` | modo `verificar` | verificar | Reporte de notas creadas/actualizadas. |
| `feedback.md` | no | ambos | Correcciones pedidas sobre un intento anterior tuyo. Si existe, corrige solo lo que indica. |

**Modo**: si recibes `approved-plan.md` y `diff.patch` → modo `escribir`. Si recibes solo `knowledge-report.md` → modo `verificar`.

**Invocación a demanda (modo `escribir` simplificado)**: si recibes solo `request.md` con la ruta del fichero a documentar, documenta ese fichero único en modo `escribir`.
Si no recibiste Plan ni diff y tampoco hay contexto previo de ese fichero en la conversación, solo con `herramientas.codebase_memory: true` ejecuta `codebase-memory-mcp cli search_graph --project "<proyecto>" --name-pattern ".*<símbolo>.*"` o `codebase-memory-mcp cli get_file_outline --project "<proyecto>" --file-path "<fichero>"` (según `.agents/rules/codebase-memory.md`) como primera tarea. Lee el fichero directamente solo si el grafo no existe o no responde.

Trabaja solo con estos archivos y con el código del proyecto. No asumas contexto fuera de ellos.
Si falta un artefacto obligatorio para el modo activo, no trabajes: escribe la salida con `estado: bloqueado` y la causa.

## Selección de plantilla (1:1 solo para archivos con lógica)

Solo los ficheros de `src/main/java/` con lógica reciben o actualizan una nota en `knowledge-base/` con Plantilla de Análisis. Los DTOs, records, interfaces puras, constantes, enums y clases de error triviales no necesitan nota propia. Los ficheros de `src/test/java/` no reciben nota.

- **Con lógica o estado** (Controllers, `ServiceImpl`, Repositories con consultas, `@Configuration`, `@RestControllerAdvice`): **Plantilla de Análisis**.
<!-- si backend.persistencia=jpa -->
- **Sin lógica**: no crear nota propia para records, DTOs, `Request`/`Response`, interfaces puras, proyecciones JPA, `enum`, constantes, entidades sin lógica de negocio, clases de error triviales o `@SpringBootApplication`.
<!-- si backend.persistencia=jdbc -->
- **Sin lógica**: no crear nota propia para records, DTOs, `Request`/`Response`, interfaces puras, proyecciones, `enum`, constantes, entidades sin lógica de negocio, clases de error triviales o `@SpringBootApplication`.
<!-- fin -->

## Tareas

### Modo `escribir`

1. **Tarea 1 — Resolver ruta de la nota**: según la convención de `.agents/rules/knowledge-base.md`. Resuelve también `entidad_principal` — el nombre de la clase/símbolo principal del fichero.
2. **Tarea 2 — Usar el contexto ya generado**: el Plan aprobado + diff (más `docs-summary.md` si existe) **son** el contexto. No reanalices.
3. **Tarea 3 — Verificar si la nota existe**:
   - **No existe** → crear según el tipo de fichero (ver "Selección de plantilla"): Plantilla de Análisis o Plantilla Compacta. Establece `creado:` y `actualizado:` con la fecha actual (YYYY-MM-DD), y `estado_vinculacion: vinculada`.
   - **Existe y NO fue corrección** → actualizar `## Historial de cambios` con una fila nueva, y actualizar obligatoriamente el campo `actualizado:` del frontmatter con la fecha actual. Aplica SIEMPRE, incluso si el cambio es pequeño.
   - **Existe y SÍ fue corrección** →
     (a) añadir fila breve en Historial y actualizar `actualizado:` en el frontmatter,
     (b) añadir entrada nueva en `{ruta}-fixes.md` con la Plantilla de Corrección. Si el `-fixes.md` **no existe**, créalo primero con su cabecera de frontmatter (ver `references/templates.md`); si existe pero no tiene `fichero:` en su frontmatter, añádelo.
4. **Tarea 4 — Edición incremental**: nunca regeneres secciones no tocadas.

### Modo `verificar`

5. **Tarea 5 — Verificación de vinculación y autocorrección (por convención de ruta, no por el grafo)**:
   - Compara el reporte con los archivos del diff: exige notas solo para los que tienen lógica; omite DTOs, interfaces puras, constantes, enums, clases de error triviales y otros archivos sin lógica.
   - Confirma que el frontmatter de cada nota en `knowledge-report.md` declara `fichero:` con la ruta real del archivo de código (relativa a la raíz del repo, empezando por el servicio), y que ese archivo existe en disco.
   - Si existe, fija `estado_vinculacion: vinculada` en el frontmatter (si el campo falta en una nota preexistente, añádelo).
   - Si no existe (ruta movida, typo, archivo borrado), marca `estado_vinculacion: pendiente` y repórtalo para resolución.
   - La sección `## Fichero fuente` es opcional, solo un recordatorio visual — no bloquees por su ausencia.
   - **Codebase Memory no participa en esta verificación**: su grafo excluye `knowledge-base/` por diseño.
   - Si falla la escritura de alguna nota, emite `estado: fallo` con la causa.

## Plantillas

Ver `references/templates.md`. Cárgalo solo cuando vayas a crear o actualizar una nota o una entrada de corrección.

La convención de ruta para los archivos de knowledge-base refleja la ruta relativa del código fuente: por ejemplo, `<servicio>/src/main/java/ruta/EntidadController.java` → `knowledge-base/<servicio>/src/main/java/ruta/EntidadController.md`.

## Reglas

- Aplica `.agents/rules/architecture-rules.md`, `.agents/rules/project.md`, `.agents/rules/knowledge-base.md` y `.agents/rules/codebase-memory.md`.
- Esta skill no mantiene mapas ni índices globales.
- No sobreescribe notas existentes por completo — edición incremental por sección.
- No genera notas para ficheros de configuración sensibles (`application*.yml`/`application*.yaml`, secretos) salvo petición explícita del usuario.
- Si la escritura de la nota falla, emite `estado: fallo` con la causa.

## Salida

Escribe **un único archivo** en `OUT_DIR`:

- Modo `escribir` → `OUT_DIR/knowledge-report.md`
- Modo `verificar` → `OUT_DIR/link-check.md`

Formato:

```markdown
---
artefacto: knowledge-report.md | link-check.md
skill: knowledge-writer
estado: ok | fallo | bloqueado
entradas_leidas: [approved-plan.md, diff.patch]   # las que leíste completas
fecha: <ISO-8601>
---

## Notas creadas/actualizadas
| Nota | Acción | estado_vinculacion |
|------|--------|--------------------|
| knowledge-base/servicio/.../EntidadController.md | creada | vinculada |

## Archivos tocados
- knowledge-base/servicio/.../EntidadController.md
```


## Regla para archivos sin lógica

La nota 1:1 de Plantilla de Análisis se crea solo para archivos con lógica. DTOs, interfaces puras, constantes y clases de error triviales no necesitan nota propia. En modo `verificar`, no marques su ausencia como fallo. Mantén la convención de rutas actual para permitir búsquedas de `-fixes.md` por ruta.


Consulta y actualización condicional del grafo: usa Codebase Memory solo cuando `herramientas.codebase_memory` en `.agents/stack.yaml` sea `true`; con `false`, omite las consultas y actualizaciones al grafo. Resuelve `<proyecto>` con `python3 -I -B .agents/scripts/codebase-memory.py --resolver` (exit 0) antes de consultar. Un resultado vacío no demuestra ausencia: usa `check_index_coverage` y, si hay dudas, busca en la fuente. La actualización del grafo se hace con `python3 -I -B .agents/scripts/codebase-memory.py --indexar`; respeta la prohibición de reindexar desde aquí cuando figure en esta skill. `knowledge-base/` está excluida por `.cbmignore`.
