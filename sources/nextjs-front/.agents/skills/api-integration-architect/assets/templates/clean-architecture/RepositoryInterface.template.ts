/**
 * Interface del repositorio [Entity]
 * Define el contrato de acceso a datos.
 * 
 * CONVENCIONES:
 * - Métodos reciben primitivos o Requests
 * - Retornan Models (datos crudos de la API)
 */
import { <nomenclatura.modelo> } from "@/domains/models/<nomenclatura.modelo>";

export interface <nomenclatura.repositorio_interfaz> {
    search[Entity](param: string): Promise<<nomenclatura.modelo>[]>;
    // Agrega aquí los métodos públicos del repositorio
}
