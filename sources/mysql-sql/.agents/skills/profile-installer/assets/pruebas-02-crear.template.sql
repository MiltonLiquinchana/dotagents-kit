-- si-archivo integraciones.gestion_usuarios=organizaciones|aplicacion
-- @test: creación devuelve un ID real
-- @expect-rows: 1
-- @expect-columns: perfilId
CALL <nomenclatura.prefijo_procedimiento>guardar_nuevo_perfil(JSON_OBJECT('nombres','Cliente','apellidos','Ejemplo','correo','otro@example.test','estadoPerfilId',1
-- si integraciones.gestion_usuarios=organizaciones
,'organizacionId',1
-- fin
));
