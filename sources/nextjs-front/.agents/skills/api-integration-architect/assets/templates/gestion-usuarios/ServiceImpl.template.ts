// si-archivo integraciones.gestion_usuarios=organizaciones|aplicacion
import { __RepositorioImpl__ } from '@/repository/__RepositorioImpl__';
import type { __Repositorio__ } from '@/repository/__Repositorio__';
import { __PerfilModel__ } from '@/domains/models/__PerfilModel__';
import { __EstadoPerfilModel__ } from '@/domains/models/__EstadoPerfilModel__';
import type { __PerfilRequest__,__PreRegistroRequest__,__FiltroPerfilRequest__ } from '@/domains/request/__PerfilRequest__';
import type { __Servicio__ } from './__Servicio__';
export class __ServicioImpl__ implements __Servicio__ {
  constructor(private readonly repository:__Repositorio__ = new __RepositorioImpl__()) {}
  async listar(data:__FiltroPerfilRequest__) { return (await this.repository.listar(data)).map(x=>__PerfilModel__.formatModelToResponse(new __PerfilModel__(x))); }
  async detalle(id:number) { const x=await this.repository.detalle(id);return x ? __PerfilModel__.formatModelToResponse(new __PerfilModel__(x)) : null; }
  crear(data:__PerfilRequest__) { return this.repository.crear({...data,correo:data.correo.trim().toLowerCase()}); }
  actualizar(id:number,data:__PerfilRequest__) { return this.repository.actualizar(id,{...data,correo:data.correo.trim().toLowerCase()}); }
  preRegistro(data:__PreRegistroRequest__) { return this.repository.preRegistro({...data,correo:data.correo.trim().toLowerCase()}); }
  reconciliar(id:number) { return this.repository.reconciliar(id); }
  async estados() { return (await this.repository.estados()).map(x=>__EstadoPerfilModel__.formatModelToResponse(new __EstadoPerfilModel__(x))); }
// si integraciones.gestion_usuarios=organizaciones
  organizaciones() { return this.repository.organizaciones(); }
// fin
}
