-- si-archivo integraciones.gestion_usuarios=organizaciones|aplicacion
USE __BASE_DATOS__;
DROP PROCEDURE IF EXISTS <nomenclatura.prefijo_procedimiento>buscar_perfil_vinculacion;
CREATE PROCEDURE <nomenclatura.prefijo_procedimiento>buscar_perfil_vinculacion(IN <nomenclatura.prefijo_parametro>PerfilId INT, IN <nomenclatura.prefijo_parametro>Correo VARCHAR(250))
READS SQL DATA
BEGIN
 DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN RESIGNAL; END;
 SELECT p.__PerfilId__ AS perfilId, p.__Correo__ AS correo, p.__ClerkUserId__ AS clerkUserId, p.__EstadoPerfilId__ AS estadoPerfilId
-- si integraciones.gestion_usuarios=organizaciones
 ,p.__OrganizacionId__ AS organizacionId, o.__ClerkOrganizationId__ AS clerkOrganizationId
-- fin
 FROM __Perfiles__ p
-- si integraciones.gestion_usuarios=organizaciones
 JOIN __Organizaciones__ o ON o.__OrganizacionExternaId__=p.__OrganizacionId__
-- fin
 WHERE p.__PerfilId__=<nomenclatura.prefijo_parametro>PerfilId OR p.__Correo__=LOWER(TRIM(<nomenclatura.prefijo_parametro>Correo))
 ORDER BY (p.__PerfilId__=<nomenclatura.prefijo_parametro>PerfilId) DESC LIMIT 1;
END;
