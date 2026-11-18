/**
 * Response DTO para [Entity]
 * Clase que define la estructura de respuesta consumida por la UI.
 * 
 * CONVENCIONES:
 * - Método estático `formatModelToResponse` obligatorio
 * - Transforma tipos de la API (number, Date) a tipos de la UI (string)
 * - Constructor público con todas las propiedades
 */
import { <nomenclatura.modelo> } from "../models/<nomenclatura.modelo>";

export class <nomenclatura.response> {
    constructor(
        public id: string,
        // Agrega aquí las propiedades de respuesta para la UI
    ) {}

    /**
     * Transforma un Model de dominio a un Response para la UI
     */
    static formatModelToResponse(model: <nomenclatura.modelo>): <nomenclatura.response> {
        return new <nomenclatura.response>(
            model.id.toString(),
            // Mapea aquí las propiedades transformando tipos según necesidad
        );
    }
}
