/**
 * Interface del controlador [Entity]
 * Define el contrato público que la clase Controller debe implementar.
 * 
 * CONVENCIONES:
 * - Cada método devuelve la respuesta o el resultado serializable definido en su firma.
 * - Los parámetros de entrada son primitivos o Models
 * - NO expone lógica interna ni detalles de implementación
 */
import { <nomenclatura.response> } from "@/domains/responses/<nomenclatura.response>";

// si frontend.llamadas_api=servidor
import type { Resultado } from "@/domains/types/Resultado";
// fin

export interface <nomenclatura.controlador_interfaz> {
// si frontend.llamadas_api=navegador
    search[Entity]List(param: string): Promise<<nomenclatura.response>[]>;
// si frontend.llamadas_api=servidor
    search[Entity]List(param: string): Promise<Resultado<<nomenclatura.response>[]>>;
// fin
    // Agrega aquí los métodos públicos del controlador
}
