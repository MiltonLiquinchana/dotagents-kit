/**
 * Define los niveles de log soportados por el sistema
 * - INFO: Información general del flujo de la aplicación (solo mensaje/contexto, sin payloads pesados)
 * - DEBUG: Información detallada útil para depuración (desactivado en producción)
 * - ERROR: Errores y excepciones que ocurren durante la ejecución
 */
type LogLevel = "INFO" | "DEBUG" | "ERROR";

/**
 * Clase utilitaria para gestionar logs de manera consistente en toda la aplicación.
 * Proporciona métodos para diferentes niveles de log con formato estandarizado.
 *
 * OPTIMIZACIÓN DE RENDIMIENTO (TBT / PII):
 * - Los métodos reciben el objeto crudo en `data` (no llamar JSON.stringify en la invocación).
 * - En `NODE_ENV === "production"`, `debug` se suprime automáticamente sin costo de serialización.
 * - La serialización se realiza internamente de forma perezosa (lazy).
 */
export class Logger {
  
  /**
   * Método privado que da formato a los mensajes de log
   * Añade timestamp y nivel para una mejor organización y seguimiento
   *
   * @param level - Nivel de log (INFO, DEBUG, ERROR)
   * @param message - Mensaje a registrar
   * @returns Cadena formateada con timestamp y nivel
   */
  private formatMessage(level: LogLevel, message: string): string {
    const timestamp = new Date().toISOString();
    return `[${timestamp}] [${level}] ${message}`;
  }

  /**
   * Registra mensajes informativos sobre el funcionamiento normal de la aplicación.
   * Solo registra contexto/evento, sin payloads ni datos sensibles.
   *
   * @param log - Objeto con el mensaje a registrar
   */
  info(log: { message: string }): void {
    console.info(this.formatMessage("INFO", log.message));
  }

  /**
   * Registra mensajes de depuración con datos adicionales opcionales.
   * Suprimido automáticamente en producción para proteger el TBT y evitar fugas de memoria.
   *
   * @param log - Objeto con el mensaje y datos crudos (sin serializar previamente)
   */
  debug(log: { message: string; data?: unknown }): void {
    if (process.env.NODE_ENV === "production") {
      return;
    }
    console.debug(this.formatMessage("DEBUG", log.message));
    if (log.data !== undefined) {
      console.debug(log.data);
    }
  }

  /**
   * Registra mensajes de error con detalles de la excepción.
   *
   * @param log - Objeto con el mensaje de error y la excepción opcional
   */
  error(log: { message: string; error?: unknown }): void {
    console.error(this.formatMessage("ERROR", log.message));
    if (log.error) {
      console.error(log.error);
    }
  }
}
