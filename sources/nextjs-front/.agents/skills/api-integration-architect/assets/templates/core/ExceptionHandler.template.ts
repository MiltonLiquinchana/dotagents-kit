// si-archivo frontend.llamadas_api=navegador
import { CustomError } from "./errors/CustomError";

interface ExceptionHandlerProps {
  error: unknown;
  context: string;
}

type ErrorHandler = {
  onErrorDetect: (errorMessage: string) => void;
};

/**
 * Clase estática para manejo centralizado de excepciones
 * Procesa errores personalizados y actualiza el estado de la UI
 */
export class ExceptionHandler {
  private static handlers: Record<string, ErrorHandler> = {};

  /**
   * Define la función que se usará para actualizar el estado de la UI
   * @param controllerContext - Identificador del controlador
   * @param onErrorDetect - Función callback para ejecutar cuando se detecte un error
   */
  static defineOnErrorDetect(
    controllerContext: string,
    onErrorDetect: (errorMessage: string) => void
  ) {
    ExceptionHandler.handlers[controllerContext] = { onErrorDetect };
  }

  /**
   * Maneja las excepciones de forma centralizada
   * @param error - Error a procesar
   * @param context - Contexto del controlador
   */
  static handle({ error, context }: ExceptionHandlerProps) {
    if (error instanceof CustomError) {
      console.warn(`[${error.context}] ${error.name}:`, {
        code: error.errorCode,
        message: error.systemMessage,
      });

      if (ExceptionHandler.handlers[context]) {
        ExceptionHandler.handlers[context].onErrorDetect(error.message);
      }
    }
  }
}
