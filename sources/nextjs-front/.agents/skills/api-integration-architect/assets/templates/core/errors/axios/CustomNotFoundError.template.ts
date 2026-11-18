import { AxiosError } from "axios";
import SystemMessageConstructor from "../../SystemMessageConstructor";
import { CustomError } from "../CustomError";

/**
 * Clase específica para errores 404 (Not Found)
 */
export class CustomNotFoundError extends CustomError {
  constructor(message: string, error: AxiosError, context: string) {
    super({
      message,
      errorCode: "ERROR_404",
      systemMessage: SystemMessageConstructor(error),
      context,
    });
    this.name = "CustomNotFoundError";
  }
}
