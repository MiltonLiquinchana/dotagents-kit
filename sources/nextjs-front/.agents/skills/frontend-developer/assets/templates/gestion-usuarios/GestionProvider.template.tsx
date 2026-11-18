// si-archivo integraciones.gestion_usuarios=organizaciones|aplicacion
"use client";
import {createContext,useContext,useState} from 'react';
import type {GestionApi} from '@/domains/types/GestionTipos';
import * as Notificador from '@/utils/Notificador';
// si frontend.llamadas_api=navegador
import {__Controlador__} from '@/controllers/__Controlador__';
// si frontend.llamadas_api=servidor
import * as actions from '@/app/perfiles/actions';
import type {GestionResultado} from '@/domains/types/GestionTipos';
async function unwrap<T>(result:Promise<GestionResultado<T>>):Promise<T> {
  const value=await result;if (!value.ok) throw new Error(value.mensaje);return value.data;
}
// fin
const Context=createContext<GestionApi|null>(null);
export function GestionProvider({children}:Readonly<{children:React.ReactNode}>) {
  const [message,setMessage]=useState('');
// si frontend.llamadas_api=navegador
  const [api]=useState<GestionApi>(()=>new __Controlador__(m=>Notificador.error(m,setMessage)));
// si frontend.llamadas_api=servidor
  const [api]=useState<GestionApi>(()=>({
    listar:data=>unwrap(actions.listar(data)),detalle:id=>unwrap(actions.detalle(id)),
    crear:data=>unwrap(actions.crear(data)),actualizar:(id,data)=>unwrap(actions.actualizar(id,data)),
    preRegistro:data=>unwrap(actions.preRegistro(data)),reconciliar:id=>unwrap(actions.reconciliar(id)),
    estados:()=>unwrap(actions.estados()),
// fin
// si frontend.llamadas_api=servidor
// La asignación del catálogo opcional se integra al instanciar sin importar código servidor en UI.
    ...__CATALOGO_ACTIONS__
  }));
// fin
  return <Context.Provider value={api}>{message && <p role="alert">{message}</p>}{children}</Context.Provider>;
}
export function useGestion():GestionApi {
  const api=useContext(Context);if (!api) throw new Error('Falta GestionProvider');return api;
}
