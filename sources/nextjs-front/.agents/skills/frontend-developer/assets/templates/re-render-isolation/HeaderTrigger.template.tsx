/**
 * Componente HeaderTrigger - Disparador Ciego (Patrón B)
 * 
 * Componente que dispara acciones en componentes hermanos sin conocer
 * ni manipular los datos de filtrado.
 * 
 * REGLA CLAVE:
 * - Recibe SOLO un callback () => void
 * - NO pasa fechas, filtros ni datos como argumento
 * - NO lee Redux para enviar datos al consumidor
 * - Solo actúa como "gatillo" del evento
 */
"use client"

interface HeaderTriggerProps {
    /** 
     * Callback que se dispara al hacer clic en Aplicar Filtro.
     * Firma limpia () => void: la recolección y validación
     * de las fechas se gestionan internamente en los componentes consumidores.
     */
    onApplyFilter?: () => void;
}

export default function HeaderTrigger({ onApplyFilter }: Readonly<HeaderTriggerProps>) {
    const handleAplicarFiltro = () => {
        onApplyFilter?.();
    };

    return (
        <div>
            {/* Controles de filtro (DateRangePicker, etc.) */}
            {/* El DateRangePicker actualiza Redux internamente */}
            <button onClick={handleAplicarFiltro}>Aplicar Filtro</button>
        </div>
    );
}
