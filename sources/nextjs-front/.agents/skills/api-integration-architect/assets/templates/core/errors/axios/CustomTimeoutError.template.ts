import { AxiosError } from "axios";
import systemMessageConstructor from "../../SystemMessageConstructor";
import { CustomError } from "../CustomError";

/**
 * Clase específica para errores 408 (Request Timeout)
 */
export class CustomTimeoutError extends CustomError {
  constructor(message: string, error: AxiosError, context: string) {
    super({
      message,
      errorCode: "ERROR_408",
      systemMessage: systemMessageConstructor(error),
      context,
    });
    this.name = "TimeoutError";
  }
}
