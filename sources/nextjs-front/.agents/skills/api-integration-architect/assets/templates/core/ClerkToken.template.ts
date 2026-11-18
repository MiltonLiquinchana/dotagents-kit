// si-archivo integraciones.autenticacion=clerk
// si frontend.llamadas_api=navegador
let tokenGetter: (() => Promise<string | null>) | null = null;
/** WHY: el hook vive en React; el cliente HTTP solo recibe su función. */
export function setupClerkTokenInjection(getToken: () => Promise<string | null>): () => void {
  tokenGetter = getToken;
  return () => { if (tokenGetter === getToken) tokenGetter = null; };
}
export async function getClerkToken(): Promise<string | null> {
  return tokenGetter ? tokenGetter() : null;
}
// si frontend.llamadas_api=servidor
import "server-only";
import { auth } from "@clerk/nextjs/server";
/** WHY: auth y token por petición; nunca se guardan credenciales en un singleton. */
export async function getClerkToken(): Promise<string | null> {
  return (await auth()).getToken();
}
// fin
