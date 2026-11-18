// si-archivo integraciones.gestion_usuarios=organizaciones|aplicacion
export interface __PreRegistroRequest__ {
  nombres: string; apellidos: string; correo: string;
// si integraciones.gestion_usuarios=organizaciones
  organizacionId: number;
// fin
}
export interface __PerfilRequest__ extends __PreRegistroRequest__ {
  estadoPerfilId: number;
// si integraciones.gestion_usuarios=organizaciones
  inviterUserId?: string;
// fin
}
export interface __FiltroPerfilRequest__ {
  busqueda: string;
// si integraciones.gestion_usuarios=organizaciones
  organizacionId: number;
// fin
}
