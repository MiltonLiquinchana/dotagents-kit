-- si-archivo integraciones.gestion_usuarios=organizaciones|aplicacion
-- @test: vinculación activa el perfil
-- @expect-rows: 1
CALL <nomenclatura.prefijo_procedimiento>vincular_perfil_clerk(1,'user_prueba');
SELECT __PerfilId__ AS perfilId FROM __Perfiles__ WHERE __PerfilId__=1 AND __ClerkUserId__='user_prueba' AND __EstadoPerfilId__=3;
