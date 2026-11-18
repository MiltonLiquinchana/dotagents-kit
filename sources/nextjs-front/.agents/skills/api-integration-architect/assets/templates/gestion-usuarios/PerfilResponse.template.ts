// si-archivo integraciones.gestion_usuarios=organizaciones|aplicacion
export interface __PerfilResponse__ {
  perfilId: number; nombres: string; apellidos: string; correo: string;
  estadoPerfilId: number; estadoPerfil: string; clerkUserId: string | null;
  fechaCreacion?: string; fechaModificacion?: string;
// si integraciones.gestion_usuarios=organizaciones
  organizacionId: number; organizacion?: string;
// fin
}
