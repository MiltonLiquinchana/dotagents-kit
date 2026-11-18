-- si-archivo integraciones.gestion_usuarios=organizaciones|aplicacion
-- Correspondencia contractual: PENDIENTE=1, INVITADO_A_CLERK=2, ACTIVO=3, INACTIVO=4.
INSERT INTO __EstadoPerfiles__ (__EstadoPerfilId__, __EstadoPerfil__, __Descripcion__) VALUES
 (1, 'PENDIENTE', 'Pre-registro local; no llama a Clerk'),
 (2, 'INVITADO_A_CLERK', 'Invitación enviada a Clerk'),
 (3, 'ACTIVO', 'Perfil vinculado a Clerk'),
 (4, 'INACTIVO', 'Estado local; no revoca sesiones de Clerk');
