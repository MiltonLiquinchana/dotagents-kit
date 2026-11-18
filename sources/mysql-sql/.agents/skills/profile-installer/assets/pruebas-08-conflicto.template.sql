-- si-archivo integraciones.gestion_usuarios=organizaciones|aplicacion
-- @test: no sustituye una vinculación ajena
-- @expect-error: 45000 Vinculación incompatible
CALL <nomenclatura.prefijo_procedimiento>vincular_perfil_clerk(1,'user_otro');
