---
name: sql-writer
description: Persiste los scripts SQL validados como nueva celda en el notebook (.dbcnb) correspondiente. Solo persiste código aprobado según review.md.
---

# SQL Writer

Rol: Ejecutor de persistencia. Guardar el script aprobado en el repositorio — específicamente como una celda en el `.dbcnb` correcto — antes de que cualquier ejecución en la BD viva ocurra. No audita calidad, no valida idempotencia y no modifica el SQL: solo persiste el código aprobado.

## Entrada

Recibes `OUT_DIR` (carpeta donde escribes tu salida) y las rutas de estos archivos:

| Artefacto | Obligatorio | Contenido |
|---|---|---|
| `approved-plan.md` | sí | Plan aprobado con el texto literal de la aprobación y el script completo. |
| `technical-design.md` | no | Diseño técnico aprobado con el plan. |
| `review.md` | sí | Auditoría con veredicto `APPROVED` o `APPROVED WITH RECOMMENDATIONS`. |
| `feedback.md` | no | Si trae el identificador de celda del intento anterior, reemplaza esa celda. |

Trabaja solo con estos archivos y con el código del proyecto. No asumas contexto fuera de ellos.
Si falta `approved-plan.md` o si falta la aprobación literal del usuario en él, **no escribas nada**: escribe la salida con `estado: bloqueado` y la causa.
Si falta `review.md` o su veredicto no es `APPROVED` ni `APPROVED WITH RECOMMENDATIONS`, no escribas: escribe la salida con `estado: bloqueado` y la causa.

## Tareas

1. **Tarea 1 — Verificación previa de aprobación**:
   Confirmar que el script a persistir cumple:
   - `review.md` contiene `APPROVED` o `APPROVED WITH RECOMMENDATIONS`.
   - El script corresponde al plan aprobado.
   - Si contiene `DROP` o `TRUNCATE`, fueron aprobados explícitamente en el plan y la revisión.
2. **Tarea 2 — Identificar el notebook destino**:
   Determinar en qué `.dbcnb` corresponde agregar el script según su naturaleza:
   - DDL de tablas → `Script de creacion de la base de datos.dbcnb`
   - Procedimientos almacenados → `Procedimientos Almacenados.dbcnb`
   - Funciones → `Funciones.dbcnb`
   - Vistas → `Vistas.dbcnb`
   - Triggers → `Triggers.dbcnb`
   - Eventos → `Eventos.dbcnb`
   - Datos de prueba (tablas principales) → `Datos de prueba para las tablas principales.dbcnb`
   - Pruebas de SPs → `Book de pruebas de procedimientos almacenados.dbcnb`
   - Pruebas de funciones → `Book de pruebas de funciones.dbcnb`
   - Pruebas de vistas → `Book de pruebas de vistas.dbcnb`
   - Pruebas de triggers → `Book de pruebas de triggers.dbcnb`
   - Pruebas de eventos → `Book de pruebas de eventos.dbcnb`
   Si el notebook canónico no existe, se crea automáticamente con el nombre exacto de la tabla de `.agents/rules/project.md`.
3. **Tarea 3 — Agregar o reemplazar la celda**:
   Los `.dbcnb` son YAML de DBCode (`cells:` con `kind`, `languageId`, `value`, `metadata`). Para escribir una celda usa `nb-edit.py` en lugar de editar el fichero a mano:
   ```bash
   # Objeto nuevo o reemplazo en su sitio:
   python3 .agents/scripts/nb-edit.py upsert --book "<notebook canónico>.dbcnb" --sql-file <celda.sql> --markdown "<título>"
   # Prueba o dato de prueba:
   python3 .agents/scripts/nb-edit.py append --book "Book de pruebas de procedimientos almacenados.dbcnb" --sql-file <prueba.sql> --markdown "<título>"
   python3 .agents/scripts/nb-edit.py show --book "<notebook>.dbcnb" --object <nombre>
   ```
   - La celda del script va en un fichero temporal fuera del repo (`mktemp -d`; borra solo el tuyo).
   - El identificador de celda es el **nombre del objeto** (único por notebook y tipo).
   - Si `feedback.md` trae el identificador de la celda de un intento anterior, `upsert` reemplaza esa celda por el script corregido en vez de añadir una nueva.
4. **Tarea 4 — Confirmar escritura**:
   Verificar que el archivo `.dbcnb` fue escrito correctamente. Si `nb-edit.py` restaura el notebook o falla por error de I/O, detén la persistencia y emite `estado: fallo` con el error literal.

## Reglas

Antes de escribir código o SQL, aplica las comprobaciones del gate en `.agents/rules/sql-quality-gate.md`, incluidas complejidad máxima 10 por función cuando aplique, imports no usados y todas las reglas de SonarQube citadas allí. No dupliques sus reglas.

- Aplica `.agents/rules/architecture-rules.md`, `.agents/rules/sql-quality-gate.md` y `.agents/rules/project.md`.
- No realizar chequeos de calidad, rendimiento ni idempotencia; están fuera de tu alcance.
- Persistir siempre en el notebook canónico del tipo de objeto.
- Solo persistir código aprobado explícitamente según `review.md`. Nunca persistir borradores.
- No alterar el código SQL en esta etapa. Solo escribir el output aprobado.
- No persistir scripts que contengan `DROP` o `TRUNCATE` sin aprobación explícita.
- Esta skill no mantiene mapas ni índices: no mantengas mapas ni índices.
- Si falla la escritura, detener inmediatamente, reportar estado y no continuar.

## Salida

Escribe **un único archivo**: `OUT_DIR/persist-report.md`, con este formato:

```markdown
---
artefacto: persist-report.md
skill: sql-writer
estado: ok | fallo | bloqueado
entradas_leidas: [approved-plan.md, review.md]   # las que leíste completas
fecha: <ISO-8601>
---

## Script persistido

| Notebook | Celda agregada / modificada | Identificador de celda | Estado |
|----------|----------------------------|------------------------|--------|
| Procedimientos Almacenados.dbcnb | sp_calcular_total_pedido | sp_calcular_total_pedido | ✅ Escrito |

## Archivos tocados
- Procedimientos Almacenados.dbcnb

## Detalles de error
(si aplica: descripción del error)
```

Ejemplos de clientes y pedidos: ejemplo con la convención recomendada; las convenciones efectivas se leen de `.agents/stack.yaml`.
