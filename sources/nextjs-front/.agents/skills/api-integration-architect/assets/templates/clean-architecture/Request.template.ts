/**
 * Request DTO para [Entity]
 * Interfaz que define el payload enviado a la API.
 * 
 * CONVENCIONES:
 * - Solo contiene propiedades tipadas para el payload
 * - Método estático `formatModelToRequest` para transformar Model → Request
 */
import { <nomenclatura.modelo> } from "../models/<nomenclatura.modelo>";

export class <nomenclatura.request> {
    constructor(
        public id: string,
        // Agrega aquí las propiedades del request
    ) {}

    /**
     * Transforma un Model de dominio a un Request para la API
     */
    static formatModelToRequest(model: <nomenclatura.modelo>): <nomenclatura.request> {
        return new <nomenclatura.request>(
            model.id.toString(),
            // Mapea aquí las propiedades
        );
    }
}
