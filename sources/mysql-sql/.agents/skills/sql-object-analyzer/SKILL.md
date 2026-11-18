---
name: sql-object-analyzer
description: Analiza objetos SQL existentes o recién creados y inserta o actualiza mediante nb-edit.py upsert-doc una celda markdown de documentación justo debajo de la celda de código en el notebook .dbcnb correspondiente. Soporta modo creacion y modo analisis.
---

# SQL Object Analyzer

Rol: Analista y documentador de objetos SQL. Genera celdas markdown de documentación por objeto en notebooks `.dbcnb`, explicando qué hace, relaciones, parámetros, retorno y lógica desglosada. No modifica la lógica del SQL.

## Entrada

Recibes `OUT_DIR` (carpeta donde escribes tu salida) y las rutas de estos archivos:

| Artefacto | Obligatorio | Modo | Contenido |
|---|---|---|---|
| `persist-report.md` | modo `creacion` | creacion | Celda y notebook del objeto creado o modificado. |
| `docs-summary.md` | no | ambos | Resumen de documentación técnica generada, si existe. |
| `request.md` | modo `analisis` | analisis | Solicitud con el nombre del objeto o notebook a documentar. |
| `feedback.md` | no | ambos | Correcciones pedidas sobre un intento anterior tuyo. Si existe, corrige solo lo que indica. |

**Modo**: si recibes `persist-report.md` → modo `creacion`. Si recibes `request.md` → modo `analisis`.

Trabaja solo con estos archivos y con el código del proyecto. No asumas contexto fuera de ellos.
Si falta un artefacto obligatorio para el modo activo, no trabajes: escribe la salida con `estado: bloqueado` y la causa.

## MCP Tools disponibles (solo lectura)

```text
query_<conexión>("SHOW CREATE PROCEDURE <nomenclatura.prefijo_procedimiento>nombre")
query_<conexión>("SHOW CREATE FUNCTION <nomenclatura.prefijo_funcion>nombre")
query_<conexión>("SHOW CREATE TRIGGER <nombre_trigger>")
query_<conexión>("SHOW CREATE VIEW <nomenclatura.prefijo_vista>nombre")
query_<conexión>("SHOW CREATE EVENT <nomenclatura.prefijo_evento>nombre")
schema_<conexión>("columns", "tabla_relacionada")
query_<conexión>("SELECT ...") // solo verificación de referencias, sin modificar datos
```

NUNCA usar `execute_<conexión>` ni `transaction_<conexión>` en esta skill.

## Tareas

1. **Tarea 1 — Localizar objeto y notebook**:
   - En modo `creacion`, extrae el notebook y el identificador de celda desde `persist-report.md`.
   - En modo `analisis`, identifica el notebook según la naturaleza del objeto:
     - Procedimientos → `Procedimientos Almacenados.dbcnb`
     - Funciones → `Funciones.dbcnb`
     - Vistas → `Vistas.dbcnb`
     - Triggers → `Triggers.dbcnb`
     - Eventos → `Eventos.dbcnb`
     - DDL → `Script de creacion de la base de datos.dbcnb`
2. **Tarea 2 — Obtener código y relaciones**:
   - En modo `creacion`, usa `persist-report.md` y, si existe, `docs-summary.md` como base sin re-analizar desde cero.
   - En modo `analisis`, lee el código de la celda identificada, consulta el DDL con `SHOW CREATE ...` si está disponible vía MCP, y busca relaciones en `knowledge-base/` con `tgrep "<objeto>" knowledge-base/ -C 3`.
3. **Tarea 3 — Estructurar documentación**:
   Identificar:
   - Propósito general.
   - Tablas referenciadas y tipo de acceso (`SELECT`, `INSERT`, `UPDATE`, `DELETE`).
   - Parámetros (`IN`, `OUT`, `INOUT`) con tipo.
   - Retorno: columnas del `SELECT` o valores de salida.
   - Lógica desglosada en pasos internos.
   - Relaciones con otros SPs, triggers o vistas.
4. **Tarea 4 — Insertar o actualizar celda markdown** (modos `creacion` y `analisis`):
   - Guarda el Markdown del objeto en `OUT_DIR/<objeto>-doc.md`; si recibes `docs-summary.md`, úsalo como entrada junto con el código real.
   - Ejecuta `python3 -B -E .agents/scripts/nb-edit.py upsert-doc --book "<libro>" --object <nombre> --markdown-file "OUT_DIR/<objeto>-doc.md"`.
   - Esta es la única vía de persistencia de la celda de documentación del notebook: no edites el `.dbcnb` a mano ni cambies la celda SQL original.
5. **Tarea 5 — Verificar escritura**:
   - Confirma que el comando insertó o actualizó la celda markdown debajo del objeto sin errores. Anota el comando exacto, su código de salida y su salida literal en el reporte; con error, devuelve `estado: fallo`.

## Plantilla de celda markdown generada

```markdown
## <nombre_objeto>

### Qué hace
...

### Relaciones con tablas
| Tabla | Tipo de acceso |
|-------|----------------|
| ...   | SELECT / INSERT / UPDATE / DELETE |

### Parámetros
| Parámetro | Tipo | Modo | Descripción |
|-----------|------|------|-------------|
| ...       | ...  | IN   | ...         |

### Retorno
| Columna / Valor | Tipo | Descripción |
|-----------------|------|-------------|
| ...             | ...  | ...         |

### Lógica desglosada
1. ...
2. ...

### Relaciones con otros objetos
- Llama a: ...
- Es llamado por: ...
- Triggers relacionados: ...
- Vistas relacionadas: ...
```

## Reglas

- Aplica `.agents/rules/architecture-rules.md` y `.agents/rules/project.md`.
- Solo lectura. No ejecutar DDL ni DML.
- No modificar la lógica del SQL original.
- Basarse solo en código real y evidencia verificable.
- Si hay discrepancia entre notebook y BD viva, reportarla sin corregir.
- No reindexes (`python3 -I -B .agents/scripts/codebase-memory.py --indexar`) desde aquí.

## Salida

Además del Markdown auxiliar que consume el comando, escribe el reporte: `OUT_DIR/object-doc-report.md`, con este formato:

```markdown
---
artefacto: object-doc-report.md
skill: sql-object-analyzer
estado: ok | fallo | bloqueado
entradas_leidas: [persist-report.md]   # las que leíste completas
fecha: <ISO-8601>
---

## Reporte de Análisis de Objeto SQL

### Objeto analizado
- Nombre: `<nomenclatura.prefijo_procedimiento>nombre`
- Tipo: Procedimiento almacenado / Función / Trigger / Vista / Evento
- Notebook: `Procedimientos Almacenados.dbcnb`
- Modo: creacion | analisis

### Celda insertada o actualizada
- Comando ejecutado: `<comando exacto de nb-edit.py upsert-doc>`
- Código de salida: `<código real>`
- Salida literal:

    <salida copiada de la terminal>

- Verificación: celda markdown debajo del objeto; celda SQL intacta.

### Discrepancias detectadas
- (Ninguna / lista de diferencias entre notebook y BD viva)

## Archivos tocados
- Procedimientos Almacenados.dbcnb
```


Si `herramientas.codebase_memory` de `.agents/stack.yaml` es `false`, no consultes Codebase Memory: usa MCP de lectura, `db-index.py` y `tgrep` como fuentes de contexto.

Consulta y actualización condicional del grafo: usa Codebase Memory solo cuando `herramientas.codebase_memory` en `.agents/stack.yaml` sea `true`; con `false`, omite las consultas y actualizaciones al grafo. Resuelve `<proyecto>` con `python3 -I -B .agents/scripts/codebase-memory.py --resolver` (exit 0) antes de consultar. Un resultado vacío no demuestra ausencia: usa `check_index_coverage` y, si hay dudas, busca en la fuente. Los objetos se consultan con `db-index.py` y el MCP de lectura existente; CBM solo complementa SQL fuera de `.dbcnb`.
