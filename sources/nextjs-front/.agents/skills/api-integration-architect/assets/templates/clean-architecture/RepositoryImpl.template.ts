/**
 * Implementación del repositorio [Entity]
 * Centraliza las llamadas HTTP a la API.
 * 
 * ESTRUCTURA CANÓNICA:
 * 1. Define CustomAxiosRequestConfig extendiendo AxiosRequestConfig con context
 * 2. logger.info al inicio
 * 3. Llamada a apiClient pasando context: CONTROLLER_CONTEXTS.[ENTITY]_CONTROLLER
 * 4. logger.debug con respuesta o fallback
 * 5. Mapeo a Model y retorno
 */
import { <nomenclatura.modelo> } from "@/domains/models/<nomenclatura.modelo>";
import { <nomenclatura.repositorio_interfaz> } from "./<nomenclatura.repositorio_interfaz>";
import { AxiosRequestConfig } from "axios";
import { Logger } from "@/utils/Logger";
import apiClient from "@/utils/apiClient";
import { CONTROLLER_CONTEXTS } from "@/utils/constants/ControllerContexts";

// Extiende la configuración de Axios para incluir contexto personalizado
interface CustomAxiosRequestConfig extends AxiosRequestConfig {
    context?: string;
}

export class <nomenclatura.repositorio_implementacion> implements <nomenclatura.repositorio_interfaz> {

    // Logger para registrar actividad del repositorio
    logger = new Logger();

    async search[Entity](param: string): Promise<<nomenclatura.modelo>[]> {
        //Logger de información para saber que función se esta ejecutando
        this.logger.info({
            message: "<nomenclatura.repositorio_implementacion> search[Entity]",
        });

        // Petición HTTP con contexto personalizado para identificación en logs
        const response = await apiClient.get(
            "/api/[entity]/search", // Endpoint específico
            {
                params: {
                    param: param
                },
                context: CONTROLLER_CONTEXTS.[ENTITY]_CONTROLLER,
                headers: {
                    "Content-Type": "application/json",
                },
            } as CustomAxiosRequestConfig
        );

        // WHY: Una respuesta undefined devuelve el vacío seguro de la operación:
        // listas [], búsquedas individuales null. Nunca se lee response.data sin comprobar.
        if (!response) {
            this.logger.debug({
                message:
                    "<nomenclatura.repositorio_implementacion> No se pudo encontrar resultados",
            });
        }
        this.logger.debug({
            message: "Se encontró resultados exitosamente (200 OK).",
            data: response,
        });
        return (response?.data as <nomenclatura.modelo>[]) ?? [];
    }
}
