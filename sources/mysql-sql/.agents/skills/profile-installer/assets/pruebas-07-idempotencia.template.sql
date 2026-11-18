-- si-archivo integraciones.gestion_usuarios=organizaciones|aplicacion
-- @test: evento repetido no reactiva el perfil inactivo
-- @expect-rows: 1
UPDATE __Perfiles__ SET __EstadoPerfilId__=4 WHERE __PerfilId__=1;
CALL <nomenclatura.prefijo_procedimiento>vincular_perfil_clerk(1,'user_prueba');
SELECT __PerfilId__ AS perfilId FROM __Perfiles__ WHERE __PerfilId__=1 AND __EstadoPerfilId__=4;
