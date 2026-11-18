// si-archivo integraciones.gestion_usuarios=organizaciones|aplicacion
"use client";
import {useState} from 'react';
import {useGestion} from '@/app/ui/perfiles/GestionProvider';
import {PerfilForm} from '@/app/ui/perfiles/PerfilForm';
import type {__PerfilResponse__} from '@/domains/responses/__PerfilResponse__';
import * as Notificador from '@/utils/Notificador';
export function PerfilesSection() {
  const api=useGestion();const [perfiles,setPerfiles]=useState<__PerfilResponse__[]>([]);
  const [busqueda,setBusqueda]=useState('');const [message,setMessage]=useState('');
  const [busy,setBusy]=useState(false);const [editing,setEditing]=useState<number|undefined>();const [show,setShow]=useState(false);
// si integraciones.gestion_usuarios=organizaciones
  const [organizacionId,setOrganizacionId]=useState(0);
// fin
  async function listar() {
    setBusy(true);try {setPerfiles(await api.listar({busqueda,
// si integraciones.gestion_usuarios=organizaciones
      organizacionId,
// fin
    }));} catch(error:unknown) {Notificador.error(error instanceof Error?error.message:'No se pudo listar',setMessage);}finally {setBusy(false);}
  }
  async function reconciliar(id:number) {
    setBusy(true);try {if(await api.reconciliar(id)){Notificador.exito('Perfil reconciliado',setMessage);await listar();}}
    catch(error:unknown){Notificador.error(error instanceof Error?error.message:'No se pudo reconciliar',setMessage);}finally{setBusy(false);}
  }
  return <section><h1>Perfiles</h1>{message && <p role="status">{message}</p>}
    <label>Filtro<input value={busqueda} onChange={e=>setBusqueda(e.target.value)}/></label>
{/* si integraciones.gestion_usuarios=organizaciones */}
    <label>ID de organización<input type="number" min={1} value={organizacionId||''} onChange={e=>setOrganizacionId(Number(e.target.value))}/></label>
{/* fin */}
    <button disabled={busy} onClick={()=>void listar()}>Buscar</button>
    <button onClick={()=>{setEditing(undefined);setShow(true);}}>Crear perfil</button>
    <table><thead><tr><th>Nombre</th><th>Correo</th><th>Estado</th><th>Acciones</th></tr></thead><tbody>
      {perfiles.map(x=><tr key={x.perfilId}><td>{x.nombres} {x.apellidos}</td><td>{x.correo}</td><td>{x.estadoPerfil}</td><td>
        <button onClick={()=>{setEditing(x.perfilId);setShow(true);}}>Editar</button>
        <button disabled={busy} onClick={()=>void reconciliar(x.perfilId)}>Reconciliar</button>
      </td></tr>)}
    </tbody></table>
    {show && <div role="dialog" aria-label="Perfil"><PerfilForm key={editing??'nuevo'} perfilId={editing} onSaved={()=>{setShow(false);void listar();}}/><button onClick={()=>setShow(false)}>Cerrar</button></div>}
  </section>;
}
