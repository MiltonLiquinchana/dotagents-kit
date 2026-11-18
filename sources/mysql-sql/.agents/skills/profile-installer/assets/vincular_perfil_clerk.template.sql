-- si-archivo integraciones.gestion_usuarios=organizaciones|aplicacion
USE __BASE_DATOS__;
DROP PROCEDURE IF EXISTS <nomenclatura.prefijo_procedimiento>vincular_perfil_clerk;
CREATE PROCEDURE <nomenclatura.prefijo_procedimiento>vincular_perfil_clerk(IN <nomenclatura.prefijo_parametro>PerfilId INT, IN <nomenclatura.prefijo_parametro>ClerkUserId VARCHAR(250))
MODIFIES SQL DATA
BEGIN
 DECLARE <nomenclatura.prefijo_variable>EstadoActivo INT DEFAULT 3;
 DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;
 START TRANSACTION;
 IF COALESCE(TRIM(<nomenclatura.prefijo_parametro>ClerkUserId), '')='' THEN
  SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Usuario Clerk obligatorio';
 END IF;
 IF NOT EXISTS(SELECT 1 FROM __Perfiles__ WHERE __PerfilId__=<nomenclatura.prefijo_parametro>PerfilId) THEN
  SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Perfil no encontrado';
 END IF;
 IF EXISTS(SELECT 1 FROM __Perfiles__ WHERE __PerfilId__=<nomenclatura.prefijo_parametro>PerfilId AND __ClerkUserId__ IS NOT NULL AND __ClerkUserId__<> <nomenclatura.prefijo_parametro>ClerkUserId) THEN
  SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Vinculación incompatible';
 END IF;
 -- WHY: repetir un evento no reactiva un perfil inactivo ya vinculado.
 UPDATE __Perfiles__ SET __EstadoPerfilId__=IF(__ClerkUserId__ IS NULL,<nomenclatura.prefijo_variable>EstadoActivo,__EstadoPerfilId__), __ClerkUserId__=<nomenclatura.prefijo_parametro>ClerkUserId
 WHERE __PerfilId__=<nomenclatura.prefijo_parametro>PerfilId;
 COMMIT;
END;
