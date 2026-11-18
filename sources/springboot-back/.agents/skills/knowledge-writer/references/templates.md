# Referencia: Plantillas de notas Knowledge Writer

Carga este archivo solo cuando vayas a crear o actualizar una nota principal
o una entrada de corrección.

## Plantilla de Análisis — `{Fichero}.md`

```markdown
---
tipo: analisis
fichero: <ruta real del fichero en el repo>
entidad_principal: <clase o símbolo principal, ej. InvitacionService>
proyecto: <nombre del servicio (carpeta del fichero)>
tags: [<capa>, <servicio>]
estado_vinculacion: <vinculada | pendiente>
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
(Vía tgrep sobre knowledge-base/ — enlaza con [[OtroFichero]] cuando exista nota relacionada)

## Decisiones de diseño
- Decisión: ... — Razón: ...

## Historial de cambios
| Fecha | Cambio | Petición relacionada |
|-------|--------|----------------------|
| YYYY-MM-DD | Creación inicial | ... |

## Correcciones
Ver [[{Fichero}-fixes]] (si existen)
```

## Plantilla Compacta — `{Fichero}.md` (ficheros sin lógica)

<!-- si backend.persistencia=jpa -->
Para: `record`, DTOs, `Request`/`Response`, interfaces puras (p. ej. `*Service`
sin implementación), proyecciones JPA, `enum`, constantes, clases `@Entity` sin
lógica de negocio y la clase `@SpringBootApplication`. Si el fichero tiene lógica
o estado (Controller, ServiceImpl, Repository con consultas, `@Configuration`,
`@RestControllerAdvice`), usa la Plantilla de Análisis.
<!-- si backend.persistencia=jdbc -->
Para: `record`, DTOs, `Request`/`Response`, interfaces puras (p. ej. `*Service`
sin implementación), proyecciones, `enum`, constantes, la clase `@SpringBootApplication`. Si el fichero tiene lógica
o estado (Controller, ServiceImpl, Repository con consultas, `@Configuration`,
`@RestControllerAdvice`), usa la Plantilla de Análisis.
<!-- fin -->

```markdown
---
tipo: compacto
fichero: <ruta real del fichero en el repo, ej. <servicio>/src/main/java/<paquete>/projection/DetallePedidoProjection.java>
entidad_principal: <record, interfaz, enum o clase principal, ej. DetallePedidoProjection>
proyecto: <nombre del servicio (carpeta del fichero)>
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
- `campo` / `getCampo()`: tipo — descripción breve (en proyecciones, indica el alias del SELECT que respalda al getter)

## Historial de cambios
| Fecha | Cambio | Petición relacionada |
|-------|--------|----------------------|
| YYYY-MM-DD | Creación inicial | ... |

## Correcciones
Ver [[{Fichero}-fixes]] (si existen)
```

## Plantilla de Corrección — entrada en {Fichero}-fixes.md
```markdown
## {YYYY-MM-DD} — {título breve del error}

**Petición**: (qué se pidió resolver)

**Error / síntoma**: (qué fallaba — mensaje o comportamiento observado)

**Causa raíz**: (por qué ocurría)

**Código antes**:
​```java
...
​```

**Código después**:
​```java
...
​```

**Por qué esta solución**: (razón de elegir este enfoque sobre alternativas)

**Por qué funciona ahora y antes no**: (explicación técnica del contraste)
```
Ejemplos de clientes y pedidos: ejemplo con la convención recomendada; las convenciones efectivas se leen de `.agents/stack.yaml`.
