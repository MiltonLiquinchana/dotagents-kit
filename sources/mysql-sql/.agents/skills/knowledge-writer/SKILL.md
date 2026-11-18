---
name: knowledge-writer
description: Genera y mantiene notas de conocimiento en Markdown sobre objetos SQL y su historial de correcciones. Indexadas por tgrep. Opera en dos modos según la entrada recibida.
---

# Knowledge Writer (SQL)

Rol: Traduce el contexto ya generado durante la implementación en notas persistentes en `knowledge-base/`. **No es una fuente de análisis nueva** — es una capa de persistencia sobre análisis que ya ocurrió.

## Entrada

Recibes `OUT_DIR` (carpeta donde escribes tu salida) y las rutas de estos archivos:

| Artefacto | Obligatorio | Modo | Contenido |
|---|---|---|---|
| `approved-plan.md` | modo `escribir` | escribir | Plan aprobado. |
| `diff.patch` | modo `escribir` | escribir | Diff del working tree. |
| `tipo` | modo `escribir` | escribir | `feature` o `fix`. |
| `docs-summary.md` | no | escribir | Documentación técnica generada. Si no existe, trabaja solo con `approved-plan.md` y `diff.patch`. |
| `knowledge-report.md` | modo `verificar` | verificar | Reporte de notas creadas/actualizadas. |
| `feedback.md` | no | ambos | Correcciones pedidas sobre un intento anterior tuyo. Si existe, corrige solo lo que indica. |

**Modo**: si recibes `approved-plan.md` y `diff.patch` → modo `escribir`. Si recibes solo `knowledge-report.md` → modo `verificar`.

**Invocación a demanda (modo `escribir` simplificado)**: si recibes solo `request.md` con la ruta del objeto a documentar, documenta ese objeto único en modo `escribir`.
Si se invoca de forma independiente sin contexto previo disponible, consulta el MCP con `SHOW CREATE ...` y lee la celda del notebook que define el objeto. Los notebooks no forman parte del grafo.

Trabaja solo con estos archivos y con el código del proyecto. No asumas contexto fuera de ellos.
Si falta un artefacto obligatorio para el modo activo, no trabajes: escribe la salida con `estado: bloqueado` y la causa.

## Tareas

### Modo `escribir`

1. **Tarea 1 — Resolver ruta de la nota**: según la convención de `.agents/rules/knowledge-base.md` (`knowledge-base/<tipo>/<objeto>.md`). Resuelve `tipo`, `entidad_principal` y `fichero:` (verifica con `find` la ruta real del notebook que contiene el objeto).
2. **Tarea 2 — Usar el contexto ya generado**: el Plan aprobado + diff (más `docs-summary.md` si existe) **son** el contexto. No reanalices.
3. **Tarea 3 — Verificar si la nota existe**:
   - **No existe** → crear con la Plantilla de Análisis SQL (ver `references/templates.md`). Establece `creado:` y `actualizado:` con la fecha actual (YYYY-MM-DD), y `estado_vinculacion: vinculada`.
   - **Existe y NO fue corrección** → actualizar únicamente la sección `## Historial de cambios` con una fila nueva que describa el cambio, la petición relacionada y la fecha, y actualizar obligatoriamente `actualizado:` en el frontmatter.
   - **Existe y SÍ fue corrección** →
     (a) añadir fila breve en `## Historial de cambios` de la nota principal y actualizar `actualizado:` en el frontmatter,
     (b) añadir entrada nueva en `{ruta}-fixes.md` con la Plantilla de Corrección SQL.
4. **Tarea 4 — Edición incremental**: nunca regeneres secciones no tocadas.

### Modo `verificar`

5. **Tarea 5 — Verificación de vinculación y autocorrección (por convención de ruta, no por el grafo)**:
   - Exige una nota solo para objetos con lógica SQL; no exijas nota para artefactos sin lógica (DTOs, interfaces puras, constantes o clases de error triviales).
   - Confirma que el frontmatter de cada nota en `knowledge-report.md` declara `fichero:` con la ruta real del notebook que contiene el objeto, y que ese notebook existe en disco.
   - Confirma que `grep -F "<entidad_principal>" <notebook>` lo encuentra.
   - Si no existe el notebook o el objeto en él, marca `estado_vinculacion: pendiente` y repórtalo para resolución.
   - **graphify no participa en esta verificación**: su grafo excluye `knowledge-base/` y no cubre notebooks.
   - Si falla la escritura de alguna nota, emite `estado: fallo` con la causa.

## Plantillas

Ver `references/templates.md`. Cárgalo solo cuando vayas a crear o actualizar una nota o una entrada de corrección.

## Reglas

- Aplica `.agents/rules/architecture-rules.md`, `.agents/rules/project.md`, `.agents/rules/knowledge-base.md` y `.agents/rules/graphify.md`.
- No sobreescribe notas existentes por completo — edición incremental por sección.
- No genera notas para objetos de configuración sensible salvo petición explícita del usuario.
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
| knowledge-base/procedimientos/sp_calcular_total_pedido.md | creada | vinculada |

## Archivos tocados
- knowledge-base/procedimientos/sp_calcular_total_pedido.md
```


## Regla para archivos sin lógica

La nota 1:1 de Plantilla de Análisis se crea solo para archivos con lógica. DTOs, interfaces puras, constantes y clases de error triviales no necesitan nota propia. En modo `verificar`, no marques su ausencia como fallo. Mantén la convención de rutas actual para permitir búsquedas de `-fixes.md` por ruta.


Consulta y actualización condicional del grafo: usa graphify solo cuando `herramientas.graphify` en `.agents/stack.yaml` sea `true`; con `false`, omite las consultas y actualizaciones al grafo.

Ejemplos de clientes y pedidos: ejemplo con la convención recomendada; las convenciones efectivas se leen de `.agents/stack.yaml`.
