-- si-archivo integraciones.gestion_usuarios=organizaciones|aplicacion
USE __BASE_DATOS__;
DROP PROCEDURE IF EXISTS <nomenclatura.prefijo_procedimiento>listar_perfiles_filtrados;
CREATE PROCEDURE <nomenclatura.prefijo_procedimiento>listar_perfiles_filtrados(
-- si integraciones.gestion_usuarios=organizaciones
 IN <nomenclatura.prefijo_parametro>OrganizacionId INT,
-- fin
 IN <nomenclatura.prefijo_parametro>Busqueda VARCHAR(100))
READS SQL DATA
BEGIN
 DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN RESIGNAL; END;
 SELECT p.__PerfilId__ AS perfilId, p.__Nombres__ AS nombres, p.__Apellidos__ AS apellidos,
 p.__Correo__ AS correo, p.__ClerkUserId__ AS clerkUserId,
 p.__EstadoPerfilId__ AS estadoPerfilId, e.__EstadoPerfil__ AS estadoPerfil
-- si integraciones.gestion_usuarios=organizaciones
 ,p.__OrganizacionId__ AS organizacionId, o.__Nombre__ AS organizacion
-- fin
 FROM __Perfiles__ p JOIN __EstadoPerfiles__ e ON e.__EstadoPerfilId__=p.__EstadoPerfilId__
-- si integraciones.gestion_usuarios=organizaciones
 JOIN __Organizaciones__ o ON o.__OrganizacionExternaId__=p.__OrganizacionId__
-- fin
 WHERE (<nomenclatura.prefijo_parametro>Busqueda IS NULL OR CONCAT(p.__Nombres__, ' ', p.__Apellidos__, ' ', p.__Correo__) LIKE CONCAT('%', <nomenclatura.prefijo_parametro>Busqueda, '%'))
-- si integraciones.gestion_usuarios=organizaciones
 AND p.__OrganizacionId__=<nomenclatura.prefijo_parametro>OrganizacionId
-- fin
 ORDER BY p.__FechaCreacion__ DESC, p.__PerfilId__ DESC;
END;
