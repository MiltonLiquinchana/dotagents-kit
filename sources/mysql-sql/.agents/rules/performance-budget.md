---
trigger: model_decision
description: Presupuesto y métricas de rendimiento SQL, escaneo de filas, uso de índices y planes de ejecución EXPLAIN.
---

# Performance Budget (Base de Datos)

## Métricas objetivo por consulta/SP

- **Escaneo de filas**:
  - < 1000 filas para consultas frecuentes.
  - Para tablas > 1000 filas, `type` en `EXPLAIN` debe ser `ref` o mejor; `ALL` es inaceptable.
- **Uso de índices**:
  - Toda FK debe tener índice asociado.
  - Toda columna usada en `WHERE`, `JOIN` u `ORDER BY` debe estar indexada, salvo justificación documentada.
- **Tiempo de ejecución**:
  - < 100ms para SPs transaccionales.
  - < 500ms para SPs de reportes.
- **Impacto en escritura**: en tablas con alta tasa de `INSERT`/`UPDATE`, cada índice adicional debe justificarse contra el costo de mantenimiento.

## Reglas de rendimiento

- Todo SP nuevo o modificado debe tener su plan de ejecución (`EXPLAIN`) documentado durante la fase de optimización.
- Si el plan de ejecución ya cumple los objetivos, se debe documentar y aprobar sin proponer cambios innecesarios.
- Si se detectan cuellos de botella (`type: ALL`, `key: NULL`, `Using filesort`, `Using temporary`), se debe proponer una optimización concreta sujeta a revisión técnica.
- En la revisión previa se verifica:
  - Sargability: no usar funciones que impidan el uso de índices en columnas del `WHERE`.
  - Tipos de datos de parámetros compatibles con columnas, para evitar conversiones implícitas.
  - Índices en FKs.
- En la verificación posterior se comprueba:
  - Que la mejora propuesta reduce el escaneo de filas o el tipo de acceso según `EXPLAIN`.
  - Que no se introdujeron regresiones de rendimiento.
- Prohibido `SELECT *` en producción. Toda consulta debe listar columnas explícitas.
