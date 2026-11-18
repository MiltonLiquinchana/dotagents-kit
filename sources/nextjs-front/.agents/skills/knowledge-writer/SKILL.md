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

Trabaja solo con estos archivos y con el código del proyecto. No asumas contexto fuera de ellos.
Si falta un artefacto obligatorio para el modo activo, no trabajes: escribe la salida con `estado: bloqueado` y la causa.

## Selección de plantilla (1:1 para archivos con lógica)

Solo los ficheros creados o tocados que contienen lógica o estado reciben o actualizan una nota en `knowledge-base/` con **Plantilla de Análisis**. Los archivos sin lógica (DTOs, interfaces puras, constantes, tipos, clases de error triviales y modelos de datos simples) no necesitan nota propia.

## Tareas

### Modo `escribir`

1. **Tarea 1 — Resolver ruta de la nota**: según `.agents/rules/knowledge-base.md`. Resuelve `entidad_principal` — nombre de la clase/símbolo principal.
2. **Tarea 2 — Usar el contexto ya generado**: el Plan + diff (más `docs-summary.md` si existe) **son** el contexto. No reanalices.
3. **Tarea 3 — Verificar si la nota existe**:
   - **No existe** → crear según el tipo de fichero: Plantilla de Análisis si tiene lógica, o Plantilla Compacta si es sin lógica. Establecer `creado:` y `actualizado:` con la fecha actual (YYYY-MM-DD), y `estado_vinculacion: vinculada`.
   - **Existe y NO fue corrección** → actualizar `## Historial de cambios` con una fila nueva, y actualizar obligatoriamente el campo `actualizado:` del frontmatter con la fecha actual. Aplica SIEMPRE, incluso si el cambio es pequeño.
   - **Existe y SÍ fue corrección** →
     (a) añadir fila breve en Historial y actualizar `actualizado:` en el frontmatter,
     (b) añadir entrada nueva en `{ruta}-fixes.md` con Plantilla de Corrección. Si el `-fixes.md` **no existe**, créalo primero con su cabecera de frontmatter (ver `references/templates.md`); si existe pero no tiene `fichero:` en su frontmatter, añádelo.
4. **Tarea 4 — Edición incremental**: nunca regeneres secciones no tocadas.

### Modo `verificar`

5. **Tarea 5 — Verificación de vinculación y autocorrección (por convención de ruta, no por el grafo)**:
   - Compara el reporte con los archivos del diff: exige notas solo para los que tienen lógica o estado; omite DTOs, interfaces puras, constantes, tipos y clases de error triviales.
   - Confirma que el frontmatter de cada nota en `knowledge-report.md` declara `fichero:` con la ruta real del archivo de código, que ese archivo existe en disco, y que el frontmatter declara `estado_vinculacion: vinculada` (si falta el campo en una nota preexistente, agregarlo).
   - **Autocorrección**: Si el archivo no existe en la ruta declarada en `fichero:` (ruta movida, renombramiento o typo):
     - Busca en el proyecto el archivo por el nombre exacto de su `entidad_principal`.
     - Si hay **exactamente una coincidencia**, autocorrige automáticamente el campo `fichero:` con la nueva ruta relativa y establece `estado_vinculacion: vinculada`.
     - Si hay **cero o múltiples coincidencias**, marca `estado_vinculacion: pendiente` y reporta la causa en la salida para resolución.
   - La sección `## Fichero fuente` es opcional, solo un recordatorio visual (ver `.agents/rules/knowledge-base.md`) — no bloquees por su ausencia.
   - **graphify no participa en esta verificación**: su grafo es solo de código y no contiene nodos de `knowledge-base/`.
   - Si falla la escritura de alguna nota, emite `estado: fallo` con la causa.

## Plantillas

Ver `references/templates.md`. Cárgalo solo para crear o actualizar notas.

La convención de ruta para los archivos de knowledge-base: el fichero de la nota refleja la ruta relativa del código fuente dentro del proyecto, con la extensión del código reemplazada por `.md`. Por ejemplo, `controllers/EntidadController.ts` → `knowledge-base/controllers/EntidadController.md`. Los archivos de corrección añaden `-fixes`: `knowledge-base/controllers/EntidadController-fixes.md`.

## Reglas

- Aplica `.agents/rules/architecture-rules.md`, `.agents/rules/project.md`, `.agents/rules/knowledge-base.md` y `.agents/rules/graphify.md`.
- Esta skill no mantiene mapas ni índices globales.

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
| knowledge-base/controllers/EntidadController.md | creada | vinculada |

## Archivos tocados
- knowledge-base/controllers/EntidadController.md
```


## Regla para archivos sin lógica

La nota 1:1 de Plantilla de Análisis se crea solo para archivos con lógica. DTOs, interfaces puras, constantes y clases de error triviales no necesitan nota propia. En modo `verificar`, no marques su ausencia como fallo. Mantén la convención de rutas actual para permitir búsquedas de `-fixes.md` por ruta.


Consulta y actualización condicional del grafo: usa graphify solo cuando `herramientas.graphify` en `.agents/stack.yaml` sea `true`; con `false`, omite las consultas y actualizaciones al grafo.
