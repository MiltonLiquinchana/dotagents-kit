/**
 * Página Orquestadora - Padre Libre de Estado
 * 
 * Orquesta la maquetación principal sin estados locales.
 * Solo sostiene un useRef para conectar el Trigger con la Section.
 * 
 * REGLA CLAVE:
 * - CERO useState en esta página
 * - Solo useRef para la comunicación imperativa
 * - No pasa datos entre componentes hermanos vía props
 */
"use client";

import { useRef } from "react";
import HeaderTrigger from "@/app/ui/[module]/header-trigger";
import AutonomousSection, { AutonomousSectionRef } from "@/app/ui/[module]/autonomous-section";

export default function [Page]() {
    const sectionRef = useRef<AutonomousSectionRef>(null);

    return (
        <div className="flex flex-col gap-6 w-full max-w-7xl mx-auto px-4 md:px-6">
            {/* Header: solo dispara el evento, no pasa datos */}
            <HeaderTrigger onApplyFilter={() => sectionRef.current?.handleApplyFilter()} />

            {/* Section: contenedor autónomo que lee Redux y maneja sus estados */}
            <AutonomousSection ref={sectionRef} entityId="1" />
        </div>
    );
}
