-- si-archivo integraciones.gestion_usuarios=organizaciones|aplicacion
-- @test: correo único incluso con otra capitalización
-- @expect-error: 23000
CALL <nomenclatura.prefijo_procedimiento>guardar_nuevo_perfil(JSON_OBJECT('nombres','Cliente','apellidos','Ejemplo','correo','CLIENTE@example.test','estadoPerfilId',1
-- si integraciones.gestion_usuarios=organizaciones
,'organizacionId',1
-- fin
));
