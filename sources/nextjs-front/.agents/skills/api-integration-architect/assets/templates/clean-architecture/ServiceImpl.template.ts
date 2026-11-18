/**
 * Implementación del servicio [Entity]
 * Orquesta la lógica de negocio y transforma datos entre capas.
 * 
 * ESTRUCTURA CANÓNICA:
 * 1. logger.info al inicio del método
 * 2. logger.debug con parámetros de entrada
 * 3. Llamada al repository obteniendo Model
 * 4. logger.debug con respuesta del repositorio
 * 5. Transformación con método estático: Model → Response
 */
import { <nomenclatura.repositorio_interfaz> } from "@/repository/<nomenclatura.repositorio_interfaz>";
import { <nomenclatura.repositorio_implementacion> } from "@/repository/<nomenclatura.repositorio_implementacion>";
import { Logger } from "@/utils/Logger";
import { <nomenclatura.servicio_interfaz> } from "./<nomenclatura.servicio_interfaz>";
import { <nomenclatura.response> } from "@/domains/responses/<nomenclatura.response>";
import { <nomenclatura.modelo> } from "@/domains/models/<nomenclatura.modelo>";

export class <nomenclatura.servicio_implementacion> implements <nomenclatura.servicio_interfaz> {
    // Logger para registrar actividad del servicio
    logger = new Logger();
    // Inyección de dependencia - repositorio para acceso a datos
    private readonly repository: <nomenclatura.repositorio_interfaz> = new <nomenclatura.repositorio_implementacion>();

    async search[Entity]List(param: string): Promise<<nomenclatura.response>[]> {
        //Logger de información para saber que función se esta ejecutando
        this.logger.info({ message: "<nomenclatura.servicio_implementacion> search[Entity]List" });

        //Logger para debug del parámetro de entrada
        this.logger.debug({
            message: "search[Entity]List query path",
            data: param,
        });
        // Obtiene datos en bruto del repositorio
        const model: <nomenclatura.modelo>[] =
            await this.repository.search[Entity](param);

        this.logger.debug({
            message: "search[Entity]List data response",
            data: model,
        });

        // Retorna la lista transformada usando el mapper estático del Response
        return model.map((m) => <nomenclatura.response>.formatModelToResponse(m));
    }
}
