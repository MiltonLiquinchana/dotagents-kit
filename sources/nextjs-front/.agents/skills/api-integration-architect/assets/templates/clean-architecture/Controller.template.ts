// si frontend.llamadas_api=navegador
/**
 * Controlador [Entity]
 * Orquesta la comunicación entre la UI y la capa de servicios.
 * 
 * ESTRUCTURA CANÓNICA:
 * 1. Inyecciones privadas: logger y service
 * 2. Constructor: registra onError en ExceptionHandler con CONTROLLER_CONTEXTS
 * 3. Métodos: logger.info al inicio → delegación al service → logger.debug → retorno
 */
import { <nomenclatura.response> } from "@/domains/responses/<nomenclatura.response>";
import { <nomenclatura.controlador_interfaz> } from "./<nomenclatura.controlador_interfaz>";
import { Logger } from "@/utils/Logger";
import { <nomenclatura.servicio_interfaz> } from "@/services/<nomenclatura.servicio_interfaz>";
import { <nomenclatura.servicio_implementacion> } from "@/services/<nomenclatura.servicio_implementacion>";
import { ExceptionHandler } from "@/utils/ExceptionHandler";
import { CONTROLLER_CONTEXTS } from "@/utils/constants/ControllerContexts";

export class <nomenclatura.controlador_implementacion> implements <nomenclatura.controlador_interfaz> {

    // Logger para registrar actividad del controlador
    private readonly logger = new Logger();

    // Servicio inyectado para lógica de negocio
    private readonly service: <nomenclatura.servicio_interfaz> = new <nomenclatura.servicio_implementacion>();

    /**
     * Constructor del controlador
     * @param onError - Función que se ejecuta al detectar un error
     */
    constructor(onError: (errorMessage: string) => void) {
        // Configura la función de actualización de estado en el manejador de excepciones
        ExceptionHandler.defineOnErrorDetect(
            CONTROLLER_CONTEXTS.[ENTITY]_CONTROLLER,
            onError
        );

        // Log de inicialización
        this.logger.info({
            message: "se creo la instancia para el controlador <nomenclatura.controlador_implementacion>",
        });
    }

    async search[Entity]List(param: string): Promise<<nomenclatura.response>[]> {
        //Logger de información para saber que función se esta ejecutando
        this.logger.info({
            message: `${CONTROLLER_CONTEXTS.[ENTITY]_CONTROLLER} search[Entity]List`,
        });
        // Delega la lógica de negocio al servicio
        const response: <nomenclatura.response>[] =
            await this.service.search[Entity]List(param);

        this.logger.debug({
            message: "search[Entity]List response",
            data: response,
        });
        return response;
    }
}
// si frontend.llamadas_api=servidor
import "server-only";
import { <nomenclatura.response> } from "@/domains/responses/<nomenclatura.response>";
import { <nomenclatura.controlador_interfaz> } from "./<nomenclatura.controlador_interfaz>";
import type { Resultado } from "@/domains/types/Resultado";
import { Logger } from "@/utils/Logger";
import { CustomError } from "@/utils/errors/CustomError";
import { <nomenclatura.servicio_interfaz> } from "@/services/<nomenclatura.servicio_interfaz>";
import { <nomenclatura.servicio_implementacion> } from "@/services/<nomenclatura.servicio_implementacion>";

/** WHY: Cada petición crea su controlador sin callbacks ni estado compartido. */
export class <nomenclatura.controlador_implementacion> implements <nomenclatura.controlador_interfaz> {
    private readonly logger = new Logger();
    private readonly service: <nomenclatura.servicio_interfaz> = new <nomenclatura.servicio_implementacion>();

    /** Devuelve objetos planos que pueden cruzar la frontera de Server Actions. */
    async search[Entity]List(param: string): Promise<Resultado<<nomenclatura.response>[]>> {
        this.logger.info({ message: "<nomenclatura.controlador_implementacion> search[Entity]List" });
        try {
            const response = await this.service.search[Entity]List(param);
            this.logger.debug({ message: "search[Entity]List response", data: response });
            return { ok: true, data: response.map((item) => ({ ...item })) };
        } catch (error: unknown) {
            if (!(error instanceof CustomError)) throw error;
            return { ok: false, codigo: error.apiCode ?? error.errorCode, mensaje: error.message };
        }
    }
}
// fin
