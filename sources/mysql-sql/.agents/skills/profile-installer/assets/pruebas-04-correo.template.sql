-- si-archivo integraciones.gestion_usuarios=organizaciones|aplicacion
-- @test: normalización del correo
-- @expect-rows: 1
SELECT __PerfilId__ AS perfilId FROM __Perfiles__ WHERE __Correo__='cliente@example.test';
