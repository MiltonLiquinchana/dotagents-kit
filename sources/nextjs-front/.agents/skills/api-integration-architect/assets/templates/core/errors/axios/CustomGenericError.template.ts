import { AxiosError } from "axios";
import SystemMessageConstructor from "../../SystemMessageConstructor";
import { CustomError } from "../CustomError";

/**
 * Clase genérica para errores no mapeados explícitamente, incluido estado 0 sin respuesta HTTP
 */
export class CustomGenericError extends CustomError {
  constructor(message: string, status: number, error: AxiosError, context: string) {
    super({
      message,
      errorCode: `ERROR_${status}`,
      systemMessage: SystemMessageConstructor(error),
      context,
    });
    this.name = "CustomGenericError";
  }
}
