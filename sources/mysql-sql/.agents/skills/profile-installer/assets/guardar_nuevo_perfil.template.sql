-- si-archivo integraciones.gestion_usuarios=organizaciones|aplicacion
USE __BASE_DATOS__;
DROP PROCEDURE IF EXISTS <nomenclatura.prefijo_procedimiento>guardar_nuevo_perfil;
CREATE PROCEDURE <nomenclatura.prefijo_procedimiento>guardar_nuevo_perfil(IN <nomenclatura.prefijo_parametro>DatosPerfil JSON)
MODIFIES SQL DATA
BEGIN
 DECLARE <nomenclatura.prefijo_variable>EstadoPendiente INT DEFAULT 1;
 DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;
 START TRANSACTION;
 IF <nomenclatura.prefijo_parametro>DatosPerfil IS NULL OR JSON_TYPE(<nomenclatura.prefijo_parametro>DatosPerfil) <> 'OBJECT' THEN
  SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Datos inválidos';
 END IF;
 IF COALESCE(TRIM(JSON_UNQUOTE(JSON_EXTRACT(<nomenclatura.prefijo_parametro>DatosPerfil, '$.nombres'))), '') IN ('', 'null')
 OR COALESCE(TRIM(JSON_UNQUOTE(JSON_EXTRACT(<nomenclatura.prefijo_parametro>DatosPerfil, '$.apellidos'))), '') IN ('', 'null')
 OR COALESCE(TRIM(JSON_UNQUOTE(JSON_EXTRACT(<nomenclatura.prefijo_parametro>DatosPerfil, '$.correo'))), '') IN ('', 'null') THEN
  SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Campos obligatorios';
 END IF;
 INSERT INTO __Perfiles__ (__Nombres__, __Apellidos__, __Correo__, __EstadoPerfilId__
-- si integraciones.gestion_usuarios=organizaciones
 ,__OrganizacionId__
-- fin
 ) VALUES (
 TRIM(JSON_UNQUOTE(JSON_EXTRACT(<nomenclatura.prefijo_parametro>DatosPerfil, '$.nombres'))),
 TRIM(JSON_UNQUOTE(JSON_EXTRACT(<nomenclatura.prefijo_parametro>DatosPerfil, '$.apellidos'))),
 LOWER(TRIM(JSON_UNQUOTE(JSON_EXTRACT(<nomenclatura.prefijo_parametro>DatosPerfil, '$.correo')))),
 COALESCE(JSON_EXTRACT(<nomenclatura.prefijo_parametro>DatosPerfil, '$.estadoPerfilId'), <nomenclatura.prefijo_variable>EstadoPendiente)
-- si integraciones.gestion_usuarios=organizaciones
 ,JSON_EXTRACT(<nomenclatura.prefijo_parametro>DatosPerfil, '$.organizacionId')
-- fin
 );
 -- WHY: el consumidor necesita el ID real, no TRUE como en el original.
 SELECT LAST_INSERT_ID() AS perfilId;
 COMMIT;
END;
