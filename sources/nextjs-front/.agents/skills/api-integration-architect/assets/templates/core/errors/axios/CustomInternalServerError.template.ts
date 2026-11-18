import { CustomError } from "../CustomError";
import systemMessageConstructor from "../../SystemMessageConstructor";
import { AxiosError } from "axios";

/**
 * Clase específica para errores 500 (Internal Server Error)
 */
export class CustomInternalServerError extends CustomError {
  constructor(message: string, error: AxiosError, context: string) {
    super({
      message,
      errorCode: "ERROR_500",
      systemMessage: systemMessageConstructor(error),
      context,
    });
    this.name = "CustomInternalServerError";
  }
}
