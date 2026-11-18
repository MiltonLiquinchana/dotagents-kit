/**
 * Clase personalizada para manejo de errores extendida de la clase Error nativa
 * Proporciona información adicional como código de error, mensaje del sistema y contexto
 */
export class CustomError extends Error {
  public errorCode: string;
  // Código de negocio opcional del cuerpo de la API; no reemplaza errorCode.
  public apiCode?: string;
  public systemMessage: string;
  public context: string;

  /**
   * Constructor de la clase CustomError
   * @param message - Mensaje de error amigable para el usuario
   * @param errorCode - Código único del error (ej: "ERROR_404")
   * @param systemMessage - Mensaje técnico del sistema
   * @param context - Contexto donde ocurrió el error
   */
  constructor({
    message,
    errorCode,
    systemMessage,
    context,
  }: {
    message: string;
    errorCode: string;
    systemMessage: string;
    context: string;
  }) {
    super(message);
    this.name = "CustomError";
    this.errorCode = errorCode;
    this.systemMessage = systemMessage;
    this.context = context;
    Error.captureStackTrace?.(this, CustomError);
  }
}
