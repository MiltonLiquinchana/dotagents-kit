// si frontend.llamadas_api=servidor
import "server-only";
// fin
import axios, { type AxiosRequestConfig } from "axios";
import { handleAxiosError } from "./HandleAxiosError";
// si integraciones.autenticacion=clerk
import { getClerkToken } from "./ClerkToken";
// fin

/** Configuración por petición: el contexto viaja con cada llamada, sin estado global. */
export interface CustomAxiosRequestConfig extends AxiosRequestConfig {
  context?: string;
}

/** WHY: La configuración se exige al pedir datos, nunca al importar durante el build. */
export class ApiConfigurationError extends Error {}

/**
 * Cliente HTTP configurado con Axios.
 * Incluye interceptores para manejo automático de errores.
 * La URL se toma del entorno sin respaldo; el módulo se puede importar sin ella.
 * Si el proyecto usa autenticación, agrega el interceptor correspondiente
 * sin registrar tokens ni compartir credenciales entre peticiones.
 */
const apiClient = axios.create();

// si integraciones.autenticacion=ninguna
apiClient.interceptors.request.use((config) => {
// si integraciones.autenticacion=clerk
apiClient.interceptors.request.use(async (config) => {
// fin
// si frontend.llamadas_api=navegador
  const baseURL = process.env.NEXT_PUBLIC_API_BASE_URL;
  const variable = "NEXT_PUBLIC_API_BASE_URL";
// si frontend.llamadas_api=servidor
  const baseURL = process.env.API_BASE_URL;
  const variable = "API_BASE_URL";
// fin
  if (!baseURL?.trim()) {
    throw new ApiConfigurationError(`falta ${variable}; copia .env.example a .env.local`);
  }
  config.baseURL = baseURL;
// si integraciones.autenticacion=clerk
  const token = await getClerkToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
// fin
  return config;
});

// Interceptor de respuesta: manejo automático de errores, sin imprimir AxiosError.
apiClient.interceptors.response.use(
  (response) => response,
  (error: unknown) => {
// si frontend.llamadas_api=navegador
    // El diagnóstico de configuración debe llegar al invocador también en el navegador.
// si frontend.llamadas_api=servidor
    // El diagnóstico de configuración se propaga al invocador del servidor.
// fin
    if (error instanceof ApiConfigurationError) return Promise.reject(error);
    const config = axios.isAxiosError(error)
      ? (error.config as CustomAxiosRequestConfig | undefined)
      : undefined;
    const context = config?.context ?? "default context";
    handleAxiosError({ error, context });
// si frontend.llamadas_api=navegador
    // El callback notificó y la petición se resuelve con undefined.
// si frontend.llamadas_api=servidor
    // El CustomError rechazó la petición; solo una cancelación llega aquí.
// fin
    return undefined;
  }
);

export default apiClient;
