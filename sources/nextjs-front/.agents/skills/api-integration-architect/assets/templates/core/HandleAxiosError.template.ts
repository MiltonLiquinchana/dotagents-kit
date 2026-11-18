// si frontend.llamadas_api=servidor
import "server-only";
// fin
import axios, { AxiosError } from "axios";
import { CustomError } from "./errors/CustomError";
import { CustomNotFoundError } from "./errors/axios/CustomNotFoundError";
import { CustomTimeoutError } from "./errors/axios/CustomTimeoutError";
import { CustomConflictError } from "./errors/axios/CustomConflictError";
import { CustomInternalServerError } from "./errors/axios/CustomInternalServerError";
import { CustomGenericError } from "./errors/axios/CustomGenericError";
// si frontend.llamadas_api=navegador
import { ExceptionHandler } from "./ExceptionHandler";
// fin
// si frontend.llamadas_api=navegador
import { Logger } from "./Logger";
// fin

// Interface para definir los parámetros de la función
interface HandleAxiosErrorProps {
  error: unknown; // Error desconocido que puede venir de Axios
  context: string; // Contexto (controller) donde ocurrió el error
}

// Mensajes para el usuario
const TIMEOUT_MESSAGE = "La solicitud tardó demasiado. Intenta nuevamente.";
const NO_RESPONSE_MESSAGE =
  "No se pudo conectar con el servidor. Verifica tu conexión e intenta nuevamente.";
const DEFAULT_BACKEND_MESSAGE = "Ha ocurrido un error";
const UNEXPECTED_MESSAGE = "Ocurrio un error inesperado";

// Status sintético para errores sin respuesta HTTP (red caída, CORS, servidor inaccesible) → errorCode "ERROR_0"
const NO_HTTP_STATUS = 0;

// Códigos de axios para timeout del cliente (ETIMEDOUT solo si transitional.clarifyTimeoutError)
const CLIENT_TIMEOUT_CODES: ReadonlySet<string> = new Set(["ECONNABORTED", "ETIMEDOUT"]);

// si frontend.llamadas_api=navegador
const logger = new Logger();
// fin

const API_MESSAGE_FIELD: string = <api_error.campo_mensaje>;
const API_CODE_FIELD: string | null = <api_error.campo_codigo>;

/**
 * Extrae el mensaje del backend sin asumir la forma del cuerpo
 * (puede ser null, string, HTML de un proxy, etc.).
 */
function extractBackendMessage(data: unknown): string {
  if (data !== null && typeof data === "object" && API_MESSAGE_FIELD in data) {
    const message = (data as Record<string, unknown>)[API_MESSAGE_FIELD];
    if (typeof message === "string" && message.trim() !== "") {
      return message;
    }
  }
  return DEFAULT_BACKEND_MESSAGE;
}

/** WHY: Un contrato sin campo de código no intenta leer un código del cuerpo. */
function extractBackendCode(data: unknown): string | undefined {
  if (API_CODE_FIELD === null || data === null || typeof data !== "object") {
    return undefined;
  }
  const code = (data as Record<string, unknown>)[API_CODE_FIELD];
  return typeof code === "string" && code.trim() !== "" ? code : undefined;
}

/**
 * Clasifica un AxiosError en su CustomError correspondiente.
 * No lanza: devuelve siempre una instancia de CustomError.
 */
function classifyCustomError(axiosError: AxiosError, context: string): CustomError {
  // Timeout del cliente (antes escapaba con throw fuera del try → rechazo sin manejar)
  if (axiosError.code && CLIENT_TIMEOUT_CODES.has(axiosError.code)) {
    return new CustomTimeoutError(TIMEOUT_MESSAGE, axiosError, context);
  }

  // Sin respuesta HTTP: ERR_NETWORK, CORS, servidor caído (antes: return silencioso)
  const response = axiosError.response;
  if (!response) {
    return new CustomGenericError(NO_RESPONSE_MESSAGE, NO_HTTP_STATUS, axiosError, context);
  }

  // Lectura defensiva del cuerpo (antes: destructuring fuera del try → TypeError con data === null)
  const userMessage = extractBackendMessage(response.data);

  switch (response.status) {
    case 404:
      return new CustomNotFoundError(userMessage, axiosError, context);
    case 408:
      return new CustomTimeoutError(userMessage, axiosError, context);
    case 409:
      return new CustomConflictError(userMessage, axiosError, context);
    case 500:
      return new CustomInternalServerError(UNEXPECTED_MESSAGE, axiosError, context);
    default:
      return new CustomGenericError(UNEXPECTED_MESSAGE, response.status, axiosError, context);
  }
}

/** WHY: Conserva el código de negocio sin sustituir ERROR_<status>. */
function buildCustomError(axiosError: AxiosError, context: string): CustomError {
  const customError = classifyCustomError(axiosError, context);
  customError.apiCode = extractBackendCode(axiosError.response?.data);
  return customError;
}

// si frontend.llamadas_api=navegador
/**
 * Función para manejar errores de Axios.
 * Convierte el error en un CustomError y lo despacha a ExceptionHandler (toast por contexto).
 * Nunca lanza: el interceptor de apiClient resuelve la petición con `undefined`
 * y cada Repository devuelve su vacío seguro (`[]` o `null`).
 * Las cancelaciones explícitas (axios.isCancel) se ignoran en silencio.
 * @param error - Error original
 * @param context - Contexto donde ocurrió
 */
export function handleAxiosError({ error, context }: HandleAxiosErrorProps): void {
  if (!axios.isAxiosError(error) || axios.isCancel(error)) {
    return;
  }

  try {
    ExceptionHandler.handle({ error: buildCustomError(error, context), context });
  } catch (handlingError) {
    // Garantiza que handleAxiosError no lance (p. ej. si el onError de la UI falla).
    // Solo se registra el mensaje: el AxiosError lleva config.headers.Authorization.
    logger.error({
      message: `handleAxiosError: fallo al despachar el error en ${context}: ${
        handlingError instanceof Error ? handlingError.message : "error desconocido"
      }`,
    });
  }
}
// si frontend.llamadas_api=servidor
/**
 * Convierte errores Axios en CustomError para el controlador de servidor.
 * WHY: No guarda callbacks ni estado de usuario entre peticiones.
 * Las cancelaciones se ignoran; los errores ajenos a Axios se propagan sin registrarlos.
 */
export function handleAxiosError({ error, context }: HandleAxiosErrorProps): void {
  if (axios.isCancel(error)) return;
  if (!axios.isAxiosError(error)) throw error;
  throw buildCustomError(error, context);
}
// fin
