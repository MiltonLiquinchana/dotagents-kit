// si-archivo integraciones.autenticacion=clerk
import { SignUp } from '@clerk/nextjs';
// si integraciones.gestion_usuarios=organizaciones|aplicacion
/** La instancia debe usar registro restringido: esta página solo acepta invitaciones.
 * El formulario de pre-registro crea una solicitud local y no pasa por Clerk. */
// fin
export default function Page() { return <SignUp />; }
