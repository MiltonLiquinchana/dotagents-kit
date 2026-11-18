// si-archivo frontend.llamadas_api=navegador
/**
 * [Entity] Controller Provider Component
 * 
 * Implementa el patrón Provider para compartir la instancia del
 * <nomenclatura.controlador_implementacion> entre múltiples componentes hijos.
 * 
 * OPTIMIZACIONES:
 * - ✅ Satisface el warning de SonarQube sobre context value stability
 * - ✅ Lazy initialization eficiente con useRef
 * - ✅ Sin re-renders innecesarios de componentes consumidores
 * - ✅ Type safety completo sin non-null assertions
 * 
 * ALTERNATIVA: Usar lazy useState como en UserManagementProvider:
 *   const [contextValue] = useState<[Entity]ContextType>(() => {
 *       const onError = (msg: string) => Notificador.error(msg);
 *       return { controller: new <nomenclatura.controlador_implementacion>(onError) };
 *   });
 */
'use client'

import { createContext, useRef } from 'react'
// si frontend.notificaciones=ninguna
import { useState } from 'react'
// fin
import * as Notificador from '@/utils/Notificador'
import { <nomenclatura.controlador_interfaz> } from '@/controllers/<nomenclatura.controlador_interfaz>'
import { <nomenclatura.controlador_implementacion> } from '@/controllers/<nomenclatura.controlador_implementacion>'

// ==================== TIPOS Y INTERFACES ====================

export interface [Entity]ContextType {
    controller: <nomenclatura.controlador_interfaz>;
}

interface [Entity]ProviderProps {
    children: React.ReactNode;
}

// ==================== CONTEXTO ====================

export const [Entity]Context = createContext<[Entity]ContextType | null>(null);

// ==================== PROVIDER COMPONENT ====================

export default function [Entity]Provider({
    children,
}: Readonly<[Entity]ProviderProps>) {
    
    // useRef con el objeto completo del contexto garantiza estabilidad de referencia
    const contextValueRef = useRef<[Entity]ContextType | null>(null);

// si frontend.notificaciones=ninguna
    // Sin librería de avisos: el mensaje se muestra en la propia pantalla. El Provider
    // guarda el último mensaje en su estado y pinta un área de alerta sobre los hijos.
    const [mensajeAlerta, setMensajeAlerta] = useState<string | null>(null);
// fin
    // Lazy initialization - solo se ejecuta una vez
    if (!contextValueRef.current) {
// si frontend.notificaciones=react-toastify
        const mostrarMensajeError = (mensajeError: string) => 
            Notificador.error(mensajeError);
        
        const controller = new <nomenclatura.controlador_implementacion>(mostrarMensajeError);
// fin
// si frontend.notificaciones=ninguna
        // El aviso en pantalla lo emite el componente consumidor con su propio estado:
        // `mostrar` es la función que guarda el mensaje (área de alerta abajo).
        const mostrarMensajeError = (mensajeError: string) =>
            Notificador.error(mensajeError, (m) => setMensajeAlerta(m));

        const controller = new <nomenclatura.controlador_implementacion>(mostrarMensajeError);
// fin
        contextValueRef.current = { controller };
    }

    return (
        <[Entity]Context.Provider value={contextValueRef.current}>
{/* si frontend.notificaciones=ninguna */}
            {mensajeAlerta && <div role="alert">{mensajeAlerta}</div>}
{/* fin */}
            {children}
        </[Entity]Context.Provider>
    );
}
