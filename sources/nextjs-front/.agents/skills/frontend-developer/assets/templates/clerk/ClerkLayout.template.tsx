// si-archivo integraciones.autenticacion=clerk
import { ClerkProvider } from '@clerk/nextjs';
// si frontend.llamadas_api=navegador
import ClerkTokenSetup from '@/app/ui/auth/ClerkTokenSetup';
// fin
/** Integrar en el layout existente conservando sus providers, estilos y metadata. */
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <ClerkProvider><html lang="es"><body>
{/* si frontend.llamadas_api=navegador */}
    <ClerkTokenSetup />
{/* fin */}
    {children}
  </body></html></ClerkProvider>;
}
