-- si-archivo integraciones.gestion_usuarios=organizaciones|aplicacion
-- @test: el segundo ID no es el booleano TRUE
-- @expect-rows: 1
SELECT __PerfilId__ AS perfilId FROM __Perfiles__ WHERE __PerfilId__=2 AND __Correo__='otro@example.test';
