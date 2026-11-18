// si-archivo integraciones.gestion_usuarios=organizaciones|aplicacion
import apiClient, { type CustomAxiosRequestConfig } from '@/utils/apiClient';
import type { __Repositorio__ } from './__Repositorio__';
import type { __PerfilResponse__ } from '@/domains/responses/__PerfilResponse__';
import type { __EstadoPerfilResponse__ } from '@/domains/responses/__EstadoPerfilResponse__';
import type { __PerfilRequest__,__PreRegistroRequest__,__FiltroPerfilRequest__ } from '@/domains/request/__PerfilRequest__';
import { GESTION_CONTEXT } from '@/domains/types/GestionTipos';
const prefix='__PREFIJO_API__';
const config: CustomAxiosRequestConfig = {context:GESTION_CONTEXT};
export class __RepositorioImpl__ implements __Repositorio__ {
  async listar(data:__FiltroPerfilRequest__) { return (await apiClient.post<__PerfilResponse__[]>(prefix+'/perfil/listarresumenperfiles',data,config))?.data ?? []; }
  async detalle(id:number) { return (await apiClient.get<__PerfilResponse__>(prefix+'/perfil/obtenerdetalleperfil/'+id,config))?.data ?? null; }
  async crear(data:__PerfilRequest__) { return (await apiClient.post<{perfilId:number}>(prefix+'/perfil/crearperfil',data,config))?.data.perfilId ?? 0; }
  async actualizar(id:number,data:__PerfilRequest__) { return (await apiClient.put(prefix+'/perfil/actualizarperfil/'+id,data,config))?.status === 204; }
  async preRegistro(data:__PreRegistroRequest__) { return (await apiClient.post(prefix+'/solicitar-acceso',data,config))?.status === 201; }
  async reconciliar(id:number) { return (await apiClient.post(prefix+'/perfil/'+id+'/vincular-clerk',undefined,config))?.status === 204; }
  async estados() { return (await apiClient.get<__EstadoPerfilResponse__[]>(prefix+'/estadosperfiles/listarestadosperfiles',config))?.data ?? []; }
// si integraciones.gestion_usuarios=organizaciones
  async organizaciones() { return (await apiClient.get<{organizacionId:number;nombre:string}[]>(prefix+'/organizaciones/listarorganizaciones',config))?.data ?? []; }
// fin
}
