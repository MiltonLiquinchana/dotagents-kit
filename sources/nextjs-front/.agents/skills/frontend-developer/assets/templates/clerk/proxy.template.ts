// si-archivo integraciones.autenticacion=clerk
import { clerkMiddleware, createRouteMatcher } from '@clerk/nextjs/server';
const isPublicRoute = createRouteMatcher([
  '/sign-in(.*)', '/sign-up(.*)',
// si integraciones.gestion_usuarios=organizaciones|aplicacion
  '/pre-register(.*)',
// fin
]);
export default clerkMiddleware(async (auth, request) => {
  if (!isPublicRoute(request)) await auth.protect();
});
export const config = {
  matcher: ['/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|png|gif|svg|ico|woff2?)).*)', '/(api|trpc)(.*)'],
};
