/**
 * Componente StoreProvider
 * 
 * Implementa el patrón Provider de Redux optimizado para Next.js App Router.
 * 
 * ARQUITECTURA Y SSR:
 * - Aislamiento de Instancia: Utiliza `useRef` para garantizar que el store se 
 *   cree una sola vez por sesión en el cliente, evitando fugas de estado entre requests.
 * - Soporte Client-Side: Marcado con "use client" para permitir el uso de Context API.
 * - Hidratación Segura: Previene inconsistencias durante la rehidratación de React.
 */
'use client'

import { useRef } from 'react'
import { Provider } from 'react-redux'
import { makeStore, AppStore } from '../lib/store'

/**
 * Proveedor de Redux Store para la aplicación
 * 
 * @param children - Componentes hijos que tendrán acceso al store Redux
 * @returns JSX.Element con el Provider configurado
 */
export default function StoreProvider({
    children,
}: Readonly<{
    children: React.ReactNode
}>) {
    // Referencia persistente al store Redux
    const storeRef = useRef<AppStore>(undefined)

    // Solo crea la tienda si aún no ha sido creada
    storeRef.current ??= makeStore();

    // Proporciona la tienda a través del contexto Redux
    return <Provider store={storeRef.current}>{children}</Provider>
}
