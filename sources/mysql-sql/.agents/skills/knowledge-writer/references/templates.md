# Referencia: Plantillas de Knowledge Writer para SQL

Carga este archivo solo cuando vayas a crear o actualizar una nota principal o una entrada de corrección.

## Plantilla de Análisis SQL — `{Objeto}.md`

```markdown
---
tipo: analisis_sql
fichero: <ruta relativa del notebook .dbcnb que contiene el objeto>
entidad_principal: <nombre_objeto>
tipo_objeto: <sp|tabla|funcion|vista|trigger|evento>
proyecto: <nombre_proyecto>
tags: [<etiquetas>]
creado: <YYYY-MM-DD>
actualizado: <YYYY-MM-DD>
---

# {Objeto}

## Propósito
(Qué hace, en 2-3 líneas)

## Por qué se creó
(Petición original / feature que lo originó)

## Responsabilidades
- ...

## Dependencias y relaciones (vía MCP / tgrep)
- Llama a: ...
- Es llamado por: ...
- Tablas afectadas: ...
- Triggers relacionados: ...

## Decisiones de diseño
- Decisión: ... — Razón: ...

## Historial de cambios
| Fecha | Cambio | Petición relacionada |
|-------|--------|----------------------|
| YYYY-MM-DD | Creación inicial | ... |

## Correcciones
Ver [[{Objeto}-fixes]] (si existen)
```

## Plantilla de Corrección SQL — entrada en {Objeto}-fixes.md

````markdown
## {YYYY-MM-DD} — {título breve del error}

**Petición**: (qué se pidió resolver)

**Error / síntoma**: (qué fallaba — mensaje o comportamiento observado)

**Causa raíz**: (por qué ocurría)

**Código antes**:
```sql
...
```

**Código después**:
```sql
...
```

**Por qué esta solución**: (razón de elegir este enfoque sobre alternativas)

**Por qué funciona ahora y antes no**: (explicación técnica del contraste)
````
