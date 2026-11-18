// si-archivo integraciones.gestion_usuarios=organizaciones|aplicacion
import {describe,it,expect,vi,beforeEach} from 'vitest';
import {__RepositorioImpl__} from '@/repository/__RepositorioImpl__';
import {__ServicioImpl__} from '@/services/__ServicioImpl__';
import {__Controlador__} from '@/controllers/__Controlador__';
import type {__PerfilResponse__} from '@/domains/responses/__PerfilResponse__';
import {ESTADO_PERFIL} from '@/domains/types/GestionTipos';
import apiClient from '@/utils/apiClient';
vi.mock('@/utils/apiClient',()=>({default:{post:vi.fn(),get:vi.fn(),put:vi.fn()}}));
const data:__PerfilResponse__={perfilId:42,nombres:'Cliente',apellidos:'Ejemplo',correo:'cliente@example.test',estadoPerfilId:ESTADO_PERFIL.PENDIENTE,estadoPerfil:'PENDIENTE',clerkUserId:null,
// si integraciones.gestion_usuarios=organizaciones
 organizacionId:1,
// fin
};
const request={nombres:data.nombres,apellidos:data.apellidos,correo:' CLIENTE@example.test ',estadoPerfilId:ESTADO_PERFIL.INVITADO_A_CLERK,
// si integraciones.gestion_usuarios=organizaciones
 organizacionId:1,
// fin
};
describe('gestión de perfiles por capas',()=>{
 beforeEach(()=>vi.resetAllMocks());
 it('mapea lista y filtra por el contrato',async()=>{
   vi.mocked(apiClient.post).mockResolvedValue({data:[data]});
   const service=new __ServicioImpl__();
   const result=await service.listar({busqueda:'Cliente',
// si integraciones.gestion_usuarios=organizaciones
     organizacionId:1,
// fin
   });expect(result).toEqual([data]);expect(result[0]).not.toBe(data);
 });
 it('normaliza correo y conserva el ID real creado',async()=>{
   vi.mocked(apiClient.post).mockResolvedValue({data:{perfilId:42}});
   expect(await new __ServicioImpl__().crear(request)).toBe(42);
   expect(vi.mocked(apiClient.post).mock.calls[0][1]).toMatchObject({correo:'cliente@example.test'});
 });
 it('vacíos seguros del repositorio sin inventar éxito',async()=>{
   vi.mocked(apiClient.post).mockResolvedValue(undefined);
   const repo=new __RepositorioImpl__();expect(await repo.crear(request)).toBe(0);expect(await repo.reconciliar(42)).toBe(false);
 });
 it('controlador delega reconciliación',async()=>{
   vi.mocked(apiClient.post).mockResolvedValue({status:204});
// si frontend.llamadas_api=navegador
   const controller=new __Controlador__(()=>{});
   expect(await controller.reconciliar(42)).toBe(true);
// si frontend.llamadas_api=servidor
   const controller=new __Controlador__();
   expect(await controller.reconciliar(42)).toEqual({ok:true,data:true});
// fin
 });
});
