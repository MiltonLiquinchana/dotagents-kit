import { AxiosError } from "axios";
import SystemMessageConstructor from "../../SystemMessageConstructor";
import { CustomError } from "../CustomError";

/**
 * Clase específica para errores 409 (Conflict)
 */
export class CustomConflictError extends CustomError {
  constructor(message: string, error: AxiosError, context: string) {
    super({
      message,
      errorCode: "ERROR_409",
      systemMessage: SystemMessageConstructor(error),
      context,
    });
    this.name = "CustomConflictError";
  }
}
