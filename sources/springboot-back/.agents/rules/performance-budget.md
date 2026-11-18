---
trigger: model_decision
description: Métricas objetivo de rendimiento por endpoint (p95, throughput, pool de conexiones) y reglas backend.
---

# Performance Budget (Backend)

## Métricas objetivo por endpoint

- **Tiempo de respuesta p95**:
  - Consultas sin Stored Procedure: < 200ms
  - Consultas con Stored Procedure: < 500ms
- **Throughput mínimo**: 100 req/s por instancia de servicio
- **Pool de conexiones BD**: máximo 20 conexiones activas. Tiempo de espera para adquirir conexión: < 5ms

## Reglas de rendimiento

- Justifica toda query `nativeQuery = true` con una razón técnica concreta: complejidad de JOINs, funciones de BD no soportadas por JPQL, o uso de SP existente. No uses `nativeQuery` por defecto.
<!-- si backend.persistencia=jpa -->
- En la revisión de código se verifica: N+1, `FetchType.EAGER` sin justificación, queries sin límite de resultados, ausencia de `@Transactional(readOnly = true)` en lecturas.
<!-- fin -->
<!-- si backend.persistencia=jdbc -->
- En la revisión de código se verifica: N+1 y queries sin límite de resultados, y el uso correcto de transacciones de solo lectura con `CALL`: `@Transactional(readOnly = true)` exige que el procedimiento declare `READS SQL DATA` o `NO SQL`; con `CONTAINS SQL` (por defecto en MySQL) Connector/J rechaza la llamada con `Connection is read-only`.
<!-- fin -->
- Para queries complejas nuevas, se recomienda incluir el plan de ejecución (`EXPLAIN`) en el Plan de Implementación.
