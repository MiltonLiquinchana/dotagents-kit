-- CanarySql.sql - Fixture de canario del Paso 0 (NO MODIFICAR, NO EJECUTAR EN NINGUNA BASE).
-- Contiene a propósito cuatro defectos que sql-lint.py debe detectar siempre:
--   select-star, dynamic-sql, destructive (DROP TABLE) y exit-handler (procedimiento sin EXIT HANDLER).
-- Si el canario falla, es un problema del linter o de su entorno, no del código de la feature.
USE canario_no_ejecutar;

DROP PROCEDURE IF EXISTS sp_canario_defectuoso;
CREATE PROCEDURE sp_canario_defectuoso(
    IN p_Nombre VARCHAR(50)
)
BEGIN
    SELECT * FROM Pedidos ORDER BY ClienteId;

    SET @consulta = CONCAT('SELECT ClienteId FROM Pedidos WHERE Nombres = ''', p_Nombre, '''');
    PREPARE sentencia FROM @consulta;
    EXECUTE sentencia;
    DEALLOCATE PREPARE sentencia;

    DROP TABLE TablaDeEjemplo;
    INSERT INTO Roles (Rol) VALUES ('canario');
END;
