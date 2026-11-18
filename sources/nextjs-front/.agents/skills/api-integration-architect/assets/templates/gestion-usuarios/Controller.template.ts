// si-archivo integraciones.gestion_usuarios=organizaciones|aplicacion
// si frontend.llamadas_api=servidor
import 'server-only';
import { CustomError } from '@/utils/errors/CustomError';
import type { GestionResultado } from '@/domains/types/GestionTipos';
// si frontend.llamadas_api=navegador
import { ExceptionHandler } from '@/utils/ExceptionHandler';
import { GESTION_CONTEXT } from '@/domains/types/GestionTipos';
// fin
import { __ServicioImpl__ } from '@/services/__ServicioImpl__';
import type { __Servicio__ } from '@/services/__Servicio__';
import type { __ControladorInterfaz__ } from './__ControladorInterfaz__';
import type { __PerfilRequest__,__PreRegistroRequest__,__FiltroPerfilRequest__ } from '@/domains/request/__PerfilRequest__';
export class __Controlador__ implements __ControladorInterfaz__ {
// si frontend.llamadas_api=navegador
  constructor(onError:(message:string)=>void,private readonly service:__Servicio__=new __ServicioImpl__()) {
    ExceptionHandler.defineOnErrorDetect(GESTION_CONTEXT,onError);
  }
  private run<T>(action:()=>Promise<T>): Promise<T> { return action(); }
// si frontend.llamadas_api=servidor
  constructor(private readonly service:__Servicio__=new __ServicioImpl__()) {}
  private async run<T>(action:()=>Promise<T>): Promise<GestionResultado<T>> {
    try { return {ok:true,data:await action()}; }
    catch (error:unknown) {
      if (!(error instanceof CustomError)) throw error;
      return {ok:false,codigo:error.apiCode ?? error.errorCode,mensaje:error.message};
    }
  }
// fin
  listar(data:__FiltroPerfilRequest__) { return this.run(()=>this.service.listar(data)); }
  detalle(id:number) { return this.run(()=>this.service.detalle(id)); }
  crear(data:__PerfilRequest__) { return this.run(()=>this.service.crear(data)); }
  actualizar(id:number,data:__PerfilRequest__) { return this.run(()=>this.service.actualizar(id,data)); }
  preRegistro(data:__PreRegistroRequest__) { return this.run(()=>this.service.preRegistro(data)); }
  reconciliar(id:number) { return this.run(()=>this.service.reconciliar(id)); }
  estados() { return this.run(()=>this.service.estados()); }
// si integraciones.gestion_usuarios=organizaciones
  organizaciones() { return this.run(()=>this.service.organizaciones()); }
// fin
}
