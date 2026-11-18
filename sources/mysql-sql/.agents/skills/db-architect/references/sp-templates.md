# Referencia: plantillas de SPs

Carga este archivo solo cuando el diseño en curso incluya al menos un
procedimiento almacenado nuevo. Si la feature es solo tablas, columnas,
índices o migraciones, no lo cargues.

**Marcadores**: `<base_de_datos.nombre>` y cualquier `<clave>` se resuelven con
`.agents/stack.yaml` (los scripts los leen vía `stack.py`; los humanos, con
`python3 -B -E .agents/scripts/stack.py get <clave>`).

Estas plantillas reflejan las reglas de `.agents/rules/architecture-rules.md` § 6:
los SPs de solo lectura NO abren transacción ni usan `p_resultado`; los
errores se propagan con `SIGNAL`/`RESIGNAL`. Abrir o revertir
transacciones desde un SP de lectura afecta la transacción del llamador.

Cada `CREATE PROCEDURE` declara su característica de acceso a datos:
`READS SQL DATA` para los de solo lectura y `MODIFIES SQL DATA` para los
que escriben (ambas van entre la lista de parámetros y el `BEGIN`). Con
`CONTAINS SQL`, el valor por defecto de MySQL, Connector/J rechaza las
llamadas desde una conexión de solo lectura; `sql-lint.py` exige que la
declaración coincida con el cuerpo.

## Plantilla para SPs que modifican datos (INSERT/UPDATE/DELETE/DDL)

```sql
USE <base_de_datos.nombre>;

DROP PROCEDURE IF EXISTS <nomenclatura.prefijo_procedimiento>nombre_accion;

CREATE PROCEDURE <nomenclatura.prefijo_procedimiento>nombre_accion(
    IN <nomenclatura.prefijo_parametro>parametro TIPO,
    OUT p_resultado INT
)
MODIFIES SQL DATA
BEGIN
    -- Variables principales
    DECLARE <nomenclatura.prefijo_variable>variable TIPO DEFAULT valor;
    
    -- Manejador de errores centralizado
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        SET p_resultado = -1;
        RESIGNAL;
    END;
    
    -- ========================================
    -- VALIDACIONES BÁSICAS DE ENTRADA
    -- ========================================
    IF <nomenclatura.prefijo_parametro>parametro IS NULL THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'El parámetro no puede ser nulo';
    END IF;
    
    -- ========================================
    -- PROCESAMIENTO PRINCIPAL
    -- ========================================
    START TRANSACTION;
    
    -- Lógica del negocio (INSERT / UPDATE / DELETE)

    -- Confirmar toda la operación
    COMMIT;
    SET p_resultado = 1;
END;
```

## Plantilla para SPs de solo lectura (únicamente SELECT)

```sql
USE <base_de_datos.nombre>;

DROP PROCEDURE IF EXISTS <nomenclatura.prefijo_procedimiento>nombre_accion;

CREATE PROCEDURE <nomenclatura.prefijo_procedimiento>nombre_accion(
    IN <nomenclatura.prefijo_parametro>parametro TIPO
)
READS SQL DATA
BEGIN
    DECLARE <nomenclatura.prefijo_variable>variable TIPO DEFAULT valor;

    -- Manejador de errores: solo lectura, sin ROLLBACK ni transacción
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        RESIGNAL;
    END;

    -- Validar parámetro de entrada
    IF <nomenclatura.prefijo_parametro>parametro IS NULL THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'El parámetro no puede ser nulo';
    END IF;

    -- Verificar existencia
    SELECT COUNT(*) INTO <nomenclatura.prefijo_variable>variable
    FROM tabla
    WHERE columna = <nomenclatura.prefijo_parametro>parametro;

    IF <nomenclatura.prefijo_variable>variable = 0 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'El registro no existe';
    END IF;

    -- Retornar el resultado
    SELECT
        columna1 AS alias1,
        columna2 AS alias2
    FROM tabla
    WHERE columna = <nomenclatura.prefijo_parametro>parametro;

END;
```