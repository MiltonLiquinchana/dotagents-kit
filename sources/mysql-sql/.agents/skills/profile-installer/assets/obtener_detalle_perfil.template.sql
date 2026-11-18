-- si-archivo integraciones.gestion_usuarios=organizaciones|aplicacion
USE __BASE_DATOS__;
DROP PROCEDURE IF EXISTS <nomenclatura.prefijo_procedimiento>obtener_detalle_perfil;
CREATE PROCEDURE <nomenclatura.prefijo_procedimiento>obtener_detalle_perfil(IN <nomenclatura.prefijo_parametro>PerfilId INT)
READS SQL DATA
BEGIN
 DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN RESIGNAL; END;
 SELECT p.__PerfilId__ AS perfilId, p.__Nombres__ AS nombres, p.__Apellidos__ AS apellidos,
 p.__Correo__ AS correo, p.__ClerkUserId__ AS clerkUserId, p.__EstadoPerfilId__ AS estadoPerfilId,
 e.__EstadoPerfil__ AS estadoPerfil, p.__FechaCreacion__ AS fechaCreacion, p.__FechaModificacion__ AS fechaModificacion
-- si integraciones.gestion_usuarios=organizaciones
 ,p.__OrganizacionId__ AS organizacionId, o.__Nombre__ AS organizacion
-- fin
 FROM __Perfiles__ p JOIN __EstadoPerfiles__ e ON e.__EstadoPerfilId__=p.__EstadoPerfilId__
-- si integraciones.gestion_usuarios=organizaciones
 JOIN __Organizaciones__ o ON o.__OrganizacionExternaId__=p.__OrganizacionId__
-- fin
 WHERE p.__PerfilId__=<nomenclatura.prefijo_parametro>PerfilId;
END;
