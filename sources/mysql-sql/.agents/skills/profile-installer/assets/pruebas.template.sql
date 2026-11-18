-- si-archivo integraciones.gestion_usuarios=organizaciones|aplicacion
-- @test: catálogo contractual de cuatro estados
-- @expect-rows: 4
-- @expect-columns: estadoPerfilId, estadoPerfil
CALL <nomenclatura.prefijo_procedimiento>listar_estado_perfiles();
