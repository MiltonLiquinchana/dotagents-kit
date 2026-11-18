// si-archivo frontend.llamadas_api=servidor
"use server";

import { <nomenclatura.controlador_implementacion> } from "@/controllers/<nomenclatura.controlador_implementacion>";

/** WHY: La UI invoca esta acción; la instancia no se comparte entre usuarios. */
export async function search[Entity]List(param: string) {
    return new <nomenclatura.controlador_implementacion>().search[Entity]List(param);
}
