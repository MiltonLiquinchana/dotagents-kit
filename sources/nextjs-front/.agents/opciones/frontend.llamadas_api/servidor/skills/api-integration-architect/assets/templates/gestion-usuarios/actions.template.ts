// si-archivo integraciones.gestion_usuarios=organizaciones|aplicacion
"use server";
import { __Controlador__ } from '@/controllers/__Controlador__';
import type { __PerfilRequest__,__PreRegistroRequest__,__FiltroPerfilRequest__ } from '@/domains/request/__PerfilRequest__';
export async function listar(data:__FiltroPerfilRequest__) {return new __Controlador__().listar(data);}
export async function detalle(id:number) {return new __Controlador__().detalle(id);}
export async function crear(data:__PerfilRequest__) {return new __Controlador__().crear(data);}
export async function actualizar(id:number,data:__PerfilRequest__) {return new __Controlador__().actualizar(id,data);}
export async function preRegistro(data:__PreRegistroRequest__) {return new __Controlador__().preRegistro(data);}
export async function reconciliar(id:number) {return new __Controlador__().reconciliar(id);}
export async function estados() {return new __Controlador__().estados();}
// si integraciones.gestion_usuarios=organizaciones
export async function organizaciones() {return new __Controlador__().organizaciones();}
// fin
