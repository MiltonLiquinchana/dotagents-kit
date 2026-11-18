-- si-archivo integraciones.gestion_usuarios=organizaciones|aplicacion
USE __BASE_DATOS__;
DROP PROCEDURE IF EXISTS <nomenclatura.prefijo_procedimiento>listar_estado_perfiles;
CREATE PROCEDURE <nomenclatura.prefijo_procedimiento>listar_estado_perfiles()
READS SQL DATA
BEGIN
 DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN RESIGNAL; END;
 SELECT __EstadoPerfilId__ AS estadoPerfilId, __EstadoPerfil__ AS estadoPerfil
 FROM __EstadoPerfiles__ ORDER BY __EstadoPerfilId__;
END;
