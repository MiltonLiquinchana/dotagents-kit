# Referencia: Plantillas de notas Knowledge Writer

Carga este archivo solo cuando vayas a crear o actualizar una nota principal
o una entrada de corrección.

## Plantilla de Análisis — `{Fichero}.md`

```markdown
---
tipo: analisis
fichero: <ruta real del fichero en el repo>
entidad_principal: <clase o símbolo principal, ej. InvitacionService>
proyecto: <nombre del proyecto según package.json>
tags: [<capa>, <servicio>]
creado: <YYYY-MM-DD>
actualizado: <YYYY-MM-DD>
---
# {Fichero}

## Fichero fuente
[[<ruta relativa sin extensión, igual al campo `fichero:` del frontmatter>]]

## Propósito
(Qué hace, en 2-3 líneas)

## Por qué se creó
(Petición original / feature que lo originó)

## Responsabilidades
- ...

## Dependencias y relaciones
(Vía Graphify — enlaza con [[OtroFichero]] cuando exista nota relacionada)

## Decisiones de diseño
- Decisión: ... — Razón: ...

## Historial de cambios
| Fecha | Cambio | Petición relacionada |
|-------|--------|----------------------|
| YYYY-MM-DD | Creación inicial | ... |

## Correcciones
Ver [[{Fichero}-fixes]] (si existen)
```

## Plantilla Compacta — `{Fichero}.md` (ficheros sin lógica: modelos, DTOs, interfaces, constantes)

```markdown
---
tipo: compacto
fichero: <ruta real del fichero en el repo>
entidad_principal: <interfaz, tipo o constante principal, ej. DetallePedidoModel>
proyecto: <nombre del proyecto según package.json>
tags: [<capa>, <entidad>]
estado_vinculacion: <vinculada | pendiente>
creado: <YYYY-MM-DD>
actualizado: <YYYY-MM-DD>
---
# {Fichero}

## Fichero fuente
[[<ruta relativa sin extensión, igual al campo `fichero:` del frontmatter>]]

## Propósito
(Qué representa o define, en 1 línea)

## Contrato / Campos clave
- `campo`: tipo — descripción breve

## Historial de cambios
| Fecha | Cambio | Petición relacionada |
|-------|--------|----------------------|
| YYYY-MM-DD | Creación inicial | ... |

## Correcciones
Ver [[{Fichero}-fixes]] (si existen)
```

## Cabecera de `{Fichero}-fixes.md` (solo al crear el fichero)

El fichero de correcciones es un log *append-only*. Al **crearlo**, empieza con este
frontmatter; las entradas se añaden después, sin tocar la cabecera. La búsqueda
`tgrep -F "fichero: <ruta>" knowledge-base/ -g "*-fixes.md"` depende de que `fichero:`
exista aquí, así que es obligatorio (la vía principal sigue siendo la ruta completa,
la vía principal sigue siendo verificar la ruta completa del archivo en el proyecto).

```markdown
---
tipo: correccion
fichero: <ruta real del fichero en el repo, igual que en su nota principal>
entidad_principal: <clase o símbolo principal, igual que en su nota principal>
proyecto: <nombre del proyecto según package.json>
tags: [fixes, <capa>]
creado: <YYYY-MM-DD>
---

# Registro de Correcciones — `<ruta real del fichero>`
```

## Plantilla de Corrección — entrada en {Fichero}-fixes.md
```markdown
## {YYYY-MM-DD} — {título breve del error}

**Petición**: (qué se pidió resolver)

**Error / síntoma**: (qué fallaba — mensaje o comportamiento observado)

**Causa raíz**: (por qué ocurría)

**Código antes**:
​```ts
...
​```

**Código después**:
​```ts
...
​```

**Por qué esta solución**: (razón de elegir este enfoque sobre alternativas)

**Por qué funciona ahora y antes no**: (explicación técnica del contraste)
```
Ejemplos de clientes y pedidos: ejemplo con la convención recomendada; las convenciones efectivas se leen de `.agents/stack.yaml`.
