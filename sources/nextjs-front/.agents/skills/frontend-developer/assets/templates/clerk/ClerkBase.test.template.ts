// si-archivo integraciones.autenticacion=clerk
import {it,expect,vi} from 'vitest';
import {getClerkToken} from '@/utils/ClerkToken';
import {auth,createRouteMatcher} from '@clerk/nextjs/server';
vi.mock('@clerk/nextjs/server',()=>({
 auth:vi.fn(async()=>({getToken:async()=> 'token_de_prueba'})),
 createRouteMatcher:vi.fn(()=>()=>false),clerkMiddleware:vi.fn(handler=>handler),
}));
// si frontend.llamadas_api=navegador
import {setupClerkTokenInjection} from '@/utils/ClerkToken';
it('registra y retira el getter sin conservar otro token',async()=>{
 const getter=vi.fn(async()=> 'token_de_prueba');const dispose=setupClerkTokenInjection(getter);
 expect(await getClerkToken()).toBe('token_de_prueba');expect(getter).toHaveBeenCalledOnce();
 dispose();expect(await getClerkToken()).toBeNull();expect(auth).not.toHaveBeenCalled();
});
// si frontend.llamadas_api=servidor
it('obtiene auth en cada petición, sin singleton de sesión',async()=>{
 await getClerkToken();await getClerkToken();expect(auth).toHaveBeenCalledTimes(2);
});
// fin
it('declara solo las rutas públicas de la variante',async()=>{
 vi.resetModules();
 await import('@/proxy');
 expect(createRouteMatcher).toHaveBeenCalledWith(expect.arrayContaining(['/sign-in(.*)','/sign-up(.*)']));
// si integraciones.gestion_usuarios=organizaciones|aplicacion
 expect(createRouteMatcher).toHaveBeenCalledWith(expect.arrayContaining(['/pre-register(.*)']));
// si integraciones.gestion_usuarios=ninguna
 expect(createRouteMatcher).not.toHaveBeenCalledWith(expect.arrayContaining(['/pre-register(.*)']));
// fin
});
