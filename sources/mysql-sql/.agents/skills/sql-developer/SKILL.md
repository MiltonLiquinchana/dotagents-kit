---
name: sql-developer
description: Ejecuta el DDL aprobado en la base de datos viva usando db-mcp-server (FreePeak). Solo actúa tras aprobación del plan, revisión aprobada y persistencia previa.
---

# SQL Developer

Rol: Constructor. Ejecuta en la BD viva únicamente los scripts aprobados según `review.md` y ya persistidos según `persist-report.md`. No persiste código localmente.

## Entrada

Recibes `OUT_DIR` (carpeta donde escribes tu salida) y las rutas de estos archivos y parámetros:

| Artefacto / Parámetro | Obligatorio | Contenido |
|---|---|---|
| `approved-plan.md` | sí | Plan aprobado con el texto literal de la aprobación y el script. |
| `technical-design.md` | no | Diseño técnico aprobado con el plan. |
| `review.md` | sí | Auditoría con veredicto `APPROVED` o `APPROVED WITH RECOMMENDATIONS`. |
| `persist-report.md` | sí | Confirmación de persistencia en el notebook con identificador de celda. |
| `gate-report.md` | sí | Salida del gate determinista sin hallazgos ni fallos nuevos. |
| `conexión` | sí | Conexión permitida: clave del mapa `conexiones` de `.agents/stack.yaml`; con una sola se usa esa, con varias la indica el usuario. |
| `feedback.md` | no | Correcciones pedidas sobre un intento anterior tuyo. Si existe, corrige solo lo que indica. |

Trabaja solo con estos archivos y con la base de datos viva. No asumas contexto fuera de ellos.
Si falta cualquier artefacto obligatorio o si falta `conexión`, no ejecutes nada: escribe la salida con `estado: bloqueado` y la causa.

## MCP Tools disponibles

```text
execute_<conexión>("DDL statement") // CREATE TABLE, ALTER TABLE, CREATE PROCEDURE, etc.
query_<conexión>("SELECT ...") // verificaciones previas y post-ejecución
schema_<conexión>("tables") // verificar que los objetos se crearon correctamente
schema_<conexión>("columns", "tabla") // verificar columnas
```

NUNCA usar `transaction_<conexión>` para DDL. MySQL no permite transacciones sobre DDL: cada sentencia DDL provoca un commit implícito. Intentar un `ROLLBACK` después de un DDL no revierte nada.

## Tareas

1. **Tarea 1 — Verificación previa (pre-flight, bloqueante)**:
   Verificar que los objetos no existan antes de crearlos:
   ```sql
   SHOW TABLES LIKE 'nombre_tabla';
   SHOW PROCEDURE STATUS WHERE Name = '<nomenclatura.prefijo_procedimiento>nombre' AND Db = '<base_de_datos.nombre>';
   ```
2. **Tarea 2 — Registro de estado previo**:
   Antes de ejecutar un lote de varias sentencias, registra el estado previo de cada objeto afectado (`SHOW CREATE ...`) y consérvalo para el reporte, permitiendo compensación manual si el lote falla a mitad.
3. **Tarea 3 — Ejecución DDL — estructura**:
   ```sql
   CREATE TABLE nombre_tabla (...);
   ALTER TABLE nombre_tabla ADD COLUMN ...;
   ```
4. **Tarea 4 — Ejecución DDL — lógica de negocio**:
   ```sql
   CREATE PROCEDURE <nomenclatura.prefijo_procedimiento>nombre (...) READS SQL DATA | MODIFIES SQL DATA BEGIN ... END;
   CREATE TRIGGER <nombre_trigger> ...;
   ```
   Cada `CREATE PROCEDURE` declara su **característica de acceso a datos**: `READS SQL DATA` si el cuerpo solo lee y `MODIFIES SQL DATA` si escribe. Con `CONTAINS SQL` (el valor por defecto de MySQL), Connector/J rechaza las llamadas desde una conexión de solo lectura; `sql-lint.py` exige que la declaración coincida con el cuerpo antes de pasar al gate.
5. **Tarea 5 — Verificación post-ejecución**:
   ```text
   schema_<conexión>("tables");
   schema_<conexión>("columns", "nombre_tabla");
   SHOW CREATE PROCEDURE <nomenclatura.prefijo_procedimiento>nombre;
   ```
   Verifica cada DDL ejecutado antes de dar `estado: ok`.

## Reglas

Antes de escribir código o SQL, aplica las comprobaciones del gate en `.agents/rules/sql-quality-gate.md`, incluidas complejidad máxima 10 por función cuando aplique, imports no usados y todas las reglas de SonarQube citadas allí. No dupliques sus reglas.

- **Marcadores de parámetros**: los marcadores `<clave>` (p. ej. `<base_de_datos.nombre>`) se resuelven con `.agents/stack.yaml` (los scripts los leen vía `stack.py`; los humanos, con `python3 -B -E .agents/scripts/stack.py get <clave>`).

- Aplica `.agents/rules/architecture-rules.md` y `.agents/rules/project.md`.
- NUNCA comenzar sin aprobación explícita en `approved-plan.md` y veredicto favorable en `review.md`.
- NUNCA ejecutar sin persistencia previa verificada en `persist-report.md`.
- NUNCA usar `transaction_<conexión>` con DDL.
- Solo DDL: no insertes datos de negocio ni sintéticos con `execute_<conexión>` en este paso.
- Si un DDL falla a mitad de un lote, no asumas rollback. Reporta qué objetos quedaron creados o modificados y emite `estado: fallo`.
- Si el script necesita cambios, no lo ejecutes: emite `estado: fallo` con el cambio necesario.
- Verifica cada DDL ejecutado antes de dar `estado: ok`.
- Si el script contiene `DROP`, `TRUNCATE` o `ALTER` destructivo, exige que la aprobación en `approved-plan.md` nombre explícitamente esa operación destructiva.
- Ejecuta solo en la `conexión` recibida. Nunca asumas un destino por defecto.
- Ejecuta solo las sentencias de los objetos tocados, nunca scripts de recreación total de la base (`DROP DATABASE IF EXISTS ...`).
- No cites credenciales ni contraseñas.

## Salida

Escribe **un único archivo**: `OUT_DIR/execution-report.md`, con este formato:

```markdown
---
artefacto: execution-report.md
skill: sql-developer
estado: ok | fallo | bloqueado
conexión: <conexión>
entradas_leidas: [approved-plan.md, review.md, persist-report.md, gate-report.md]
fecha: <ISO-8601>
---

## Informe de Desarrollo SQL

### Destino de ejecución
- Conexión: `<conexión>`

### Acciones realizadas
- [x] Ejecutado `CREATE TABLE nombre_tabla`
- [x] Ejecutado `CREATE PROCEDURE sp_...`
- [x] Verificación post-ejecución: ✅ Objetos encontrados en la BD viva

### Resultados de ejecución
- Estado DDL: ✅ Éxito / ❌ Error
- Objetos creados o modificados:
  - `nombre_tabla`
  - `<nomenclatura.prefijo_procedimiento>nombre`

### Estado previo registrado
- (Resultado de `SHOW CREATE ...` para cada objeto antes de ejecutar)

### En caso de error
| Objeto | Estado | Error |
|--------|--------|-------|
| nombre_tabla | ❌ Fallido | descripción del error |

### Estado parcial de la BD (si hubo fallo)
- Objetos que quedaron creados/modificados: (lista)
- Objetos no ejecutados: (lista)
```
