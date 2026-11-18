import { AxiosError } from "axios";

/**
 * Función utilitaria para construir mensajes del sistema a partir de errores de Axios
 * @param axiosError - Error de Axios del cual extraer información
 * @returns Mensaje del sistema formateado
 */
export default function SystemMessageConstructor(axiosError: AxiosError) {
  let systemMessage = "Recurso no encontrado.";

  if (axiosError) {
    const method = axiosError.config?.method?.toUpperCase() ?? "UNKNOWN_METHOD";
    const url = axiosError.config?.url ?? "UNKNOWN_URL";
    const status = axiosError.response?.status ?? "NO_STATUS";

    systemMessage = `${method} ${url} returned ${status}`;
  }

  return systemMessage;
}
