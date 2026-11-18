// si-archivo integraciones.gestion_usuarios=organizaciones|aplicacion
import type { __PerfilResponse__ } from '@/domains/responses/__PerfilResponse__';
import type { __EstadoPerfilResponse__ } from '@/domains/responses/__EstadoPerfilResponse__';
import type { __PerfilRequest__, __PreRegistroRequest__, __FiltroPerfilRequest__ } from '@/domains/request/__PerfilRequest__';
export const ESTADO_PERFIL = { PENDIENTE: 1, INVITADO_A_CLERK: 2, ACTIVO: 3, INACTIVO: 4 } as const;
export const GESTION_CONTEXT = 'GESTION_PERFILES';
export type GestionResultado<T> = {ok:true; data:T} | {ok:false; codigo:string; mensaje:string};
export interface GestionApi {
  listar(filtro: __FiltroPerfilRequest__): Promise<__PerfilResponse__[]>;
  detalle(id:number): Promise<__PerfilResponse__ | null>;
  crear(data:__PerfilRequest__): Promise<number>;
  actualizar(id:number,data:__PerfilRequest__): Promise<boolean>;
  preRegistro(data:__PreRegistroRequest__): Promise<boolean>;
  reconciliar(id:number): Promise<boolean>;
  estados(): Promise<__EstadoPerfilResponse__[]>;
// si integraciones.gestion_usuarios=organizaciones
  organizaciones(): Promise<{organizacionId:number; nombre:string}[]>;
// fin
}
