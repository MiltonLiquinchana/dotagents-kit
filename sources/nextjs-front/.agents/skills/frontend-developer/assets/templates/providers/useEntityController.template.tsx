// si-archivo frontend.llamadas_api=navegador
/**
 * Custom hook para acceder al <nomenclatura.controlador_implementacion> desde el contexto.
 * 
 * CONVENCIONES:
 * - Solo puede usarse dentro de un <[Entity]Provider>
 * - Lanza error explícito si se usa fuera del provider
 * - Retorna directamente la interfaz del controller (no el context completo)
 */
import { [Entity]Context } from "@/app/[ruta]/[Entity]Provider";
import { <nomenclatura.controlador_interfaz> } from "@/controllers/<nomenclatura.controlador_interfaz>";
import { useContext } from "react";

export function use<nomenclatura.controlador_implementacion>(): <nomenclatura.controlador_interfaz> {
    const context = useContext([Entity]Context);

    if (!context) {
        throw new Error('use<nomenclatura.controlador_implementacion> debe usarse dentro de [Entity]Provider');
    }

    return context.controller;
}
