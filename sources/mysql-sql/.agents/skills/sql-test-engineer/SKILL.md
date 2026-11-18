---
name: sql-test-engineer
description: Valida la lógica de negocio, procedimientos almacenados, funciones, triggers, vistas y eventos mediante pruebas con datos sintéticos usando db-mcp-server (FreePeak). Siempre limpia los datos de prueba al finalizar.
---

# SQL Test Engineer

Rol: Validador. Asegurar que el código implementado funciona exactamente como se diseñó bajo diversas condiciones. Inyectar datos controlados, verificar resultados y limpiar la BD. Trabaja sobre objetos ya ejecutados en BD viva, no sobre diseños.

## Entrada

Recibes `OUT_DIR` (carpeta donde escribes tu salida) y las rutas de estos archivos y parámetros:

| Artefacto / Parámetro | Obligatorio | Contenido |
|---|---|---|
| `approved-plan.md` | sí | Plan aprobado con el texto literal de la aprobación y diseño de pruebas. |
| `execution-report.md` | sí | Confirmación de ejecución en BD viva con los objetos creados/modificados. |
| `conexión` | sí | Conexión permitida: clave del mapa `conexiones` de `.agents/stack.yaml`; con una sola se usa esa, con varias la indica el usuario. |
| `feedback.md` | no | Correcciones pedidas sobre un intento anterior tuyo. Si existe, corrige solo lo que indica. |

Trabaja solo con estos archivos y con el código del proyecto. No asumas contexto fuera de ellos.
Si falta un artefacto obligatorio o `conexión`, no trabajes: escribe la salida con `estado: bloqueado` y la causa.

## MCP Tools disponibles

```text
execute_<conexión>("INSERT INTO ...") // inyectar datos de prueba
execute_<conexión>("CALL <nomenclatura.prefijo_procedimiento>nombre(...)") // ejecutar procedimientos almacenados
query_<conexión>("SELECT ...") // verificar resultados (aserciones)
execute_<conexión>("DELETE FROM ... WHERE ...") // limpieza (teardown)
transaction_<conexión>("BEGIN") // envolver pruebas DML en transacción
transaction_<conexión>("ROLLBACK") // revertir datos de prueba si se prefiere rollback al teardown
```

Las transacciones solo aplican a DML. Para datos sintéticos se puede usar `ROLLBACK` para limpiar; para DDL no se pueden usar transacciones porque MySQL realiza un commit implícito por cada sentencia DDL.

## Tareas

1. **Tarea 1 — Preparar entorno (Setup)**:
   Inyectar datos de prueba sintéticos con prefijos identificables para borrado seguro:
   ```sql
   INSERT INTO tabla (col1, col2) VALUES ('test_valor1', 'test_valor2');
   ```
2. **Tarea 2 — Ejecución de prueba lógica**:
   Llamar al SP o trigger bajo prueba:
   ```sql
   CALL <nomenclatura.prefijo_procedimiento>nueva_funcionalidad(@out_var);
   SELECT @out_var;
   ```
3. **Tarea 3 — Aserciones**:
   Verificar que los resultados sean los esperados:
   ```sql
   SELECT * FROM tabla_modificada WHERE col1 = 'test_valor1';
   ```
4. **Tarea 4 — Limpieza obligatoria (Teardown)**:
   Eliminar TODOS los datos sintéticos:
   ```sql
   DELETE FROM tabla WHERE col1 LIKE 'test_%';
   ```
5. **Tarea 5 — Complemento determinista (Sandbox)**:
   Las pruebas se escriben con aserciones y se ejecutan primero en el sandbox (MySQL desechable en contenedor; no toca la BD viva):
   ```sql
   -- @test: perfil inexistente lanza error
   -- @expect-error: 45000 El perfil con el ID proporcionado no existe
   USE <base_de_datos.nombre>;
   CALL sp_obtener_detalle_pedido(999999);
   ```
   Directivas: `@test`, `@expect-rows N`, `@expect-rows-min N`, `@expect-columns a,b,c`, `@expect-error <SQLSTATE> <fragmento>`.
   - Persiste cada prueba con:
     ```bash
     python3 .agents/scripts/nb-edit.py append --book "<libro de pruebas del tipo>.dbcnb" --sql-file <prueba.sql> --markdown "<título>"
     ```
   - Ejecuta `python3 -B -E .agents/scripts/sql-sandbox.py run --base HEAD`. Un fallo que ya existía en `HEAD` sale marcado `preexistente`; un fallo nuevo es del cambio actual.
   - Demuestra que tus pruebas detectan algo: indica qué cambio del objeto las haría fallar (columna de más, orden de columnas, alias en otra capitalización, `ORDER BY` distinto). El sandbox no comprueba el orden de las filas, solo el texto del `ORDER BY` en la definición (consulta `information_schema.ROUTINES`).
   - La repetición en la BD viva con datos sintéticos y limpieza obligatoria solo ocurre si el plan la pide.

## Reglas

- **Marcadores de parámetros**: los marcadores `<clave>` (p. ej. `<base_de_datos.nombre>`) se resuelven con `.agents/stack.yaml` (los scripts los leen vía `stack.py`; los humanos, con `python3 -B -E .agents/scripts/stack.py get <clave>`).

- Aplica `.agents/rules/architecture-rules.md` y `.agents/rules/project.md`.
- SIEMPRE limpiar datos de prueba (Teardown). Usar prefijos identificables (ej. `test_`) para borrado seguro.
- Los tests deben cubrir: camino feliz, errores de validación y excepciones de negocio (`DECLARE EXIT HANDLER`).
- No dejar datos sintéticos en `<base_de_datos.nombre>` (`.agents/stack.yaml`).
- Los datos de prueba deben ser sintéticos y no interferir con datos reales de negocio.
- Si una prueba falla, proporciona descripción exacta del error y recomendación de corrección.

## Salida

Escribe **un único archivo**: `OUT_DIR/test-report.md`, con este formato:

```markdown
---
artefacto: test-report.md
skill: sql-test-engineer
estado: ok | fallo | bloqueado
conexión: <conexión>
entradas_leidas: [approved-plan.md, execution-report.md]
fecha: <ISO-8601>
---

## Reporte de Pruebas SQL

### Escenarios probados
- [x] Camino feliz: inserción válida → Resultado esperado ✅
- [x] Error de negocio: parámetro inválido → Handler capturó correctamente ✅
- [ ] Caso borde: valor nulo en FK → Resultado inesperado ❌ (ver detalles)

### Resultados de aserciones
| Prueba | Entrada | Salida esperada | Salida real | Estado |
|--------|---------|-----------------|-------------|--------|
| SP_X   | val1    | 1               | 1           | PASS ✅ |

### Estado del entorno
- [x] Datos de prueba inyectados
- [x] Datos de prueba limpiados exitosamente

### Sandbox determinista
- Total de pruebas con aserciones: ...
- Fallos nuevos: 0 | N
- Fallos preexistentes: ...

### Correcciones requeridas
(Si alguna prueba falla: descripción exacta del error y recomendación de corrección)

## Archivos tocados
- Book de pruebas de procedimientos almacenados.dbcnb
```


## Límites y persistencia de pruebas

- Identifica cada celda con `-- @test: <id>` en su primera línea. Persiste o reemplaza mediante `nb-edit.py upsert-test --book "<libro>" --id <id> --sql-file <f>`; no edites a mano el YAML del notebook.
- El sandbox ejecuta cada celda en su propia sesión: las variables `@x` no pasan entre celdas; calcula los valores previos dentro de la misma celda.
- `@expect-columns` no se puede comprobar con 0 filas; usa solo `@expect-rows 0` en ese caso.
- Por el MCP no se observa un parámetro `OUT` cuando el procedimiento lanza un error porque se descarta la conexión; las pruebas en vivo de errores comprueban SQLSTATE, mensaje y atomicidad.
- Toda revisión repetida y todo artefacto movido a `history/` tiene una fila propia en `manifest.md`.

Convenciones del proyecto: usa `nomenclatura` de `.agents/stack.yaml`: tablas `<nomenclatura.tablas>`, columnas `<nomenclatura.columnas>`, PK `<nomenclatura.clave_primaria>`, prefijos `<nomenclatura.prefijo_procedimiento>`, `<nomenclatura.prefijo_funcion>`, `<nomenclatura.prefijo_vista>`, `<nomenclatura.prefijo_evento>`, `<nomenclatura.prefijo_trigger>`, `<nomenclatura.prefijo_indice>`, `<nomenclatura.prefijo_parametro>` y `<nomenclatura.prefijo_variable>`. Los nombres concretos de los ejemplos usan la convención recomendada.
