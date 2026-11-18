// si-archivo integraciones.gestion_usuarios=organizaciones|aplicacion
"use client";
import {useEffect,useState,type FormEvent} from 'react';
import {useGestion} from '@/app/ui/perfiles/GestionProvider';
import {ESTADO_PERFIL} from '@/domains/types/GestionTipos';
import type {__PerfilRequest__,__PreRegistroRequest__} from '@/domains/request/__PerfilRequest__';
import type {__EstadoPerfilResponse__} from '@/domains/responses/__EstadoPerfilResponse__';
import * as Notificador from '@/utils/Notificador';
// si integraciones.gestion_usuarios=organizaciones
import {useUser} from '@clerk/nextjs';
// fin
export function PerfilForm({publico=false,perfilId,onSaved}:Readonly<{publico?:boolean;perfilId?:number;onSaved?:()=>void}>) {
  const api=useGestion();const [message,setMessage]=useState('');const [busy,setBusy]=useState(false);
  const [estados,setEstados]=useState<__EstadoPerfilResponse__[]>([]);
  const [form,setForm]=useState<__PerfilRequest__>({nombres:'',apellidos:'',correo:'',estadoPerfilId:ESTADO_PERFIL.PENDIENTE,
// si integraciones.gestion_usuarios=organizaciones
    organizacionId:0,
// fin
  });
// si integraciones.gestion_usuarios=organizaciones
  const {user}=useUser();const [organizaciones,setOrganizaciones]=useState<{organizacionId:number;nombre:string}[]>([]);
  useEffect(()=>{void api.organizaciones().then(setOrganizaciones).catch(()=>setMessage('No se pudieron cargar las organizaciones'));},[api]);
// fin
  useEffect(()=>{
    let active=true;
    if (!publico) void api.estados().then(x=>{if(active)setEstados(x);}).catch(()=>setMessage('No se pudieron cargar los estados'));
    if (perfilId) void api.detalle(perfilId).then(x=>{
      if(active && x)setForm({nombres:x.nombres,apellidos:x.apellidos,correo:x.correo,estadoPerfilId:x.estadoPerfilId,
// si integraciones.gestion_usuarios=organizaciones
        organizacionId:x.organizacionId,
// fin
      });
    }).catch(()=>setMessage('No se pudo cargar el perfil'));
    return ()=>{active=false;};
  },[api,perfilId,publico]);
  async function submit(event:FormEvent) {
    event.preventDefault();setBusy(true);setMessage('');
    try {
      let ok:boolean;
      if (publico) {
        // WHY: el DTO público nunca envía el estado editable del formulario administrativo.
        const request:__PreRegistroRequest__={nombres:form.nombres,apellidos:form.apellidos,correo:form.correo,
// si integraciones.gestion_usuarios=organizaciones
          organizacionId:form.organizacionId,
// fin
        };ok=await api.preRegistro(request);
      } else {
        const request={...form,
// si integraciones.gestion_usuarios=organizaciones
          inviterUserId:user?.id,
// fin
        };ok=perfilId ? await api.actualizar(perfilId,request) : (await api.crear(request))>0;
      }
      if (ok) {Notificador.exito(publico?'Solicitud pendiente registrada':'Perfil guardado',setMessage);onSaved?.();}
      else Notificador.error('No se pudo guardar el perfil',setMessage);
    } catch(error:unknown) {Notificador.error(error instanceof Error?error.message:'No se pudo guardar',setMessage);}
    finally {setBusy(false);}
  }
  return <form onSubmit={submit}>
    <h2>{publico?'Solicitar acceso':perfilId?'Editar perfil':'Crear perfil'}</h2>
    {publico && <p>La solicitud queda pendiente en esta aplicación; no te registra en Clerk.</p>}
    {message && <p role="status">{message}</p>}
    <label>Nombres<input required maxLength={250} value={form.nombres} onChange={e=>setForm({...form,nombres:e.target.value})}/></label>
    <label>Apellidos<input required maxLength={250} value={form.apellidos} onChange={e=>setForm({...form,apellidos:e.target.value})}/></label>
    <label>Correo<input type="email" required maxLength={250} value={form.correo} onChange={e=>setForm({...form,correo:e.target.value})}/></label>
{/* si integraciones.gestion_usuarios=organizaciones */}
    <label>Organización<select required value={form.organizacionId||''} onChange={e=>setForm({...form,organizacionId:Number(e.target.value)})}>
      <option value="">Selecciona una organización</option>{organizaciones.map(x=><option key={x.organizacionId} value={x.organizacionId}>{x.nombre}</option>)}
    </select></label>
{/* fin */}
    {!publico && <label>Estado<select value={form.estadoPerfilId} onChange={e=>setForm({...form,estadoPerfilId:Number(e.target.value)})}>
      {estados.map(x=><option key={x.estadoPerfilId} value={x.estadoPerfilId}>{x.estadoPerfil}</option>)}
    </select></label>}
    {!publico && <p>Seleccionar INVITADO_A_CLERK envía una invitación al crear o cambiar a ese estado.</p>}
    <button disabled={busy} type="submit">{busy?'Guardando…':'Guardar'}</button>
  </form>;
}
