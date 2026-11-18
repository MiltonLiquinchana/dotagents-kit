-- si-archivo integraciones.gestion_usuarios=organizaciones|aplicacion
USE __BASE_DATOS__;
DROP PROCEDURE IF EXISTS <nomenclatura.prefijo_procedimiento>actualizar_perfil;
CREATE PROCEDURE <nomenclatura.prefijo_procedimiento>actualizar_perfil(IN <nomenclatura.prefijo_parametro>PerfilId INT, IN <nomenclatura.prefijo_parametro>DatosPerfil JSON)
MODIFIES SQL DATA
BEGIN
 DECLARE <nomenclatura.prefijo_variable>Nombres VARCHAR(250);
 DECLARE <nomenclatura.prefijo_variable>Apellidos VARCHAR(250);
 DECLARE <nomenclatura.prefijo_variable>Correo VARCHAR(250);
 DECLARE <nomenclatura.prefijo_variable>EstadoPerfilId INT;
-- si integraciones.gestion_usuarios=organizaciones
 DECLARE <nomenclatura.prefijo_variable>OrganizacionId INT;
-- fin
 DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;
 START TRANSACTION;
 IF NOT EXISTS(SELECT 1 FROM __Perfiles__ WHERE __PerfilId__=<nomenclatura.prefijo_parametro>PerfilId) THEN
  SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Perfil no encontrado';
 END IF;
 IF <nomenclatura.prefijo_parametro>DatosPerfil IS NULL OR JSON_TYPE(<nomenclatura.prefijo_parametro>DatosPerfil) <> 'OBJECT' THEN
  SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Datos inválidos';
 END IF;
 IF COALESCE(TRIM(JSON_UNQUOTE(JSON_EXTRACT(<nomenclatura.prefijo_parametro>DatosPerfil, '$.nombres'))), '') IN ('', 'null')
 OR COALESCE(TRIM(JSON_UNQUOTE(JSON_EXTRACT(<nomenclatura.prefijo_parametro>DatosPerfil, '$.apellidos'))), '') IN ('', 'null')
 OR COALESCE(TRIM(JSON_UNQUOTE(JSON_EXTRACT(<nomenclatura.prefijo_parametro>DatosPerfil, '$.correo'))), '') IN ('', 'null') THEN
  SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Campos obligatorios';
 END IF;
 SET <nomenclatura.prefijo_variable>Nombres=TRIM(JSON_UNQUOTE(JSON_EXTRACT(<nomenclatura.prefijo_parametro>DatosPerfil, '$.nombres')));
 SET <nomenclatura.prefijo_variable>Apellidos=TRIM(JSON_UNQUOTE(JSON_EXTRACT(<nomenclatura.prefijo_parametro>DatosPerfil, '$.apellidos')));
 SET <nomenclatura.prefijo_variable>Correo=LOWER(TRIM(JSON_UNQUOTE(JSON_EXTRACT(<nomenclatura.prefijo_parametro>DatosPerfil, '$.correo'))));
 SET <nomenclatura.prefijo_variable>EstadoPerfilId=JSON_EXTRACT(<nomenclatura.prefijo_parametro>DatosPerfil, '$.estadoPerfilId');
-- si integraciones.gestion_usuarios=organizaciones
 SET <nomenclatura.prefijo_variable>OrganizacionId=JSON_EXTRACT(<nomenclatura.prefijo_parametro>DatosPerfil, '$.organizacionId');
-- fin
 -- Los datos personales y el estado/relación se actualizan en la misma transacción.
 UPDATE __Perfiles__ SET __Nombres__=<nomenclatura.prefijo_variable>Nombres,
 __Apellidos__=<nomenclatura.prefijo_variable>Apellidos, __Correo__=<nomenclatura.prefijo_variable>Correo
 WHERE __PerfilId__=<nomenclatura.prefijo_parametro>PerfilId;
 UPDATE __Perfiles__ SET __EstadoPerfilId__=<nomenclatura.prefijo_variable>EstadoPerfilId
-- si integraciones.gestion_usuarios=organizaciones
 ,__OrganizacionId__=<nomenclatura.prefijo_variable>OrganizacionId
-- fin
 WHERE __PerfilId__=<nomenclatura.prefijo_parametro>PerfilId;
 COMMIT;
END;
