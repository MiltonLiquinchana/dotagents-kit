-- si-archivo integraciones.gestion_usuarios=organizaciones
USE __BASE_DATOS__;
DROP PROCEDURE IF EXISTS <nomenclatura.prefijo_procedimiento>listar_organizaciones;
CREATE PROCEDURE <nomenclatura.prefijo_procedimiento>listar_organizaciones()
READS SQL DATA
BEGIN
 DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN RESIGNAL; END;
 SELECT __OrganizacionExternaId__ AS organizacionId, __Nombre__ AS nombre FROM __Organizaciones__ ORDER BY __Nombre__;
END;
