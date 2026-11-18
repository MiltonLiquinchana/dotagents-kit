/**
 * Interface del servicio [Entity]
 * Define el contrato público de la capa de negocio.
 * 
 * CONVENCIONES:
 * - Métodos reciben primitivos o Models
 * - Retornan Response (transformados desde Model)
 */
import { <nomenclatura.response> } from "@/domains/responses/<nomenclatura.response>";

export interface <nomenclatura.servicio_interfaz> {
    search[Entity]List(param: string): Promise<<nomenclatura.response>[]>;
    // Agrega aquí los métodos públicos del servicio
}
