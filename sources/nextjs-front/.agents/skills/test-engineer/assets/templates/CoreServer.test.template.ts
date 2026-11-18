// si-archivo frontend.llamadas_api=servidor
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { createServer, type Server } from "node:http";
import axios, { AxiosError, CanceledError } from "axios";
import apiClient from "@/utils/apiClient";
import { handleAxiosError } from "@/utils/HandleAxiosError";
import { CustomError } from "@/utils/errors/CustomError";
// WHY: El runner no ejecuta el empaquetador de Next; solo neutraliza su guardia de importación.
vi.mock("server-only", () => ({}));
import { EjemploController } from "@/controllers/EjemploController";


const MESSAGE_FIELD: string = <api_error.campo_mensaje>;
const CODE_FIELD: string | null = <api_error.campo_codigo>;
const VARIABLE = "API_BASE_URL";
let server: Server;
let baseURL: string;
let previousURL: string | undefined;

/** WHY: Un servidor local verifica el interceptor real sin depender de una API externa. */
beforeAll(async () => {
  previousURL = process.env[VARIABLE];
  server = createServer((request, response) => {
    const path = request.url ?? "/404";
    const status = Number(path.slice(1));
    response.statusCode = Number.isInteger(status) && status >= 400 ? status : 404;
    response.setHeader("Content-Type", "application/json");
    if (path === "/null") return response.end("null");
    const body: Record<string, string> = { [MESSAGE_FIELD]: "No existe" };
    if (CODE_FIELD !== null) body[CODE_FIELD] = "RECURSO_AUSENTE";
    response.end(JSON.stringify(body));
  });
  await new Promise<void>((resolve, reject) => { server.once("error", reject); server.listen(0, "127.0.0.1", resolve); });
  const address = server.address();
  if (address === null || typeof address === "string") throw new Error("sin puerto local");
  baseURL = `http://127.0.0.1:${address.port}`;
});

beforeEach(() => { process.env[VARIABLE] = baseURL;  });
afterEach(() => { vi.restoreAllMocks(); });
afterAll(async () => {
  if (previousURL === undefined) delete process.env[VARIABLE];
  else process.env[VARIABLE] = previousURL;
  if (server.listening) await new Promise<void>((resolve, reject) => server.close((error) => error ? reject(error) : resolve()));
});

async function requestError(path: string): Promise<CustomError> {
  try { await apiClient.get(path); } catch (error: unknown) {
    if (error instanceof CustomError) return error;
    throw error;
  }
  throw new Error("la petición no rechazó");
}
function classifiedError(error: unknown): CustomError {
  try { handleAxiosError({ error, context: "test" }); } catch (handled: unknown) {
    if (handled instanceof CustomError) return handled;
    throw handled;
  }
  throw new Error("el clasificador no rechazó");
}

describe("núcleo de errores servidor", () => {
  it("404 conserva el mensaje y el código de negocio opcional", async () => {
    const error = await requestError("/404");
    expect(error.message).toBe("No existe");
    expect(error.errorCode).toBe("ERROR_404");
    expect(error.apiCode).toBe(CODE_FIELD === null ? undefined : "RECURSO_AUSENTE");
  });
  it("cuerpo null usa el mensaje por defecto sin TypeError", async () => {
    expect((await requestError("/null")).message).toBe("Ha ocurrido un error");
  });
  it("sin respuesta crea ERROR_0 y un aviso de conexión", () => {
    const error = classifiedError(new AxiosError("sin conexión", "ERR_NETWORK"));
    expect(error.errorCode).toBe("ERROR_0");
    expect(error.message).toContain("No se pudo conectar");
  });
  it("cancelación se ignora", () => {
    expect(() => handleAxiosError({ error: new CanceledError("cancelada"), context: "test" })).not.toThrow();
    
  });
  it("500 clasifica el error sin exponer el mensaje interno", async () => {
    const error = await requestError("/500");
    expect(error.errorCode).toBe("ERROR_500");
    expect(error.message).toBe("Ocurrio un error inesperado");
  });
  it.each([408, 409, 400])("estado %i conserva la clasificación", async (status) => {
    expect((await requestError(`/${status}`)).errorCode).toBe(`ERROR_${status}`);
  });
  it.each(["<html>proxy</html>", {}, 42])("cuerpo inesperado %j no rompe la extracción", (data) => {
    const error = classifiedError(new AxiosError("respuesta", "ERR_BAD_RESPONSE", undefined, undefined, {
      data, status: 404, statusText: "", headers: {}, config: { headers: new axios.AxiosHeaders() },
    }));
    expect(error.message).toBe("Ha ocurrido un error");
  });
  it("timeout del cliente se clasifica", () => {
    expect(classifiedError(new AxiosError("timeout", "ECONNABORTED")).errorCode).toBe("ERROR_408");
  });
  it("falta la variable: importar funciona y la primera petición explica la configuración", async () => {
    delete process.env[VARIABLE];
    await expect(import("@/utils/apiClient")).resolves.toBeDefined();
    await expect(apiClient.get("/404")).rejects.toThrow(`falta ${VARIABLE}; copia .env.example a .env.local`);
  });
  it("conexión HTTP local rechazada se convierte en ERROR_0", async () => {
    const unused = createServer();
    await new Promise<void>((resolve) => unused.listen(0, "127.0.0.1", resolve));
    const address = unused.address();
    if (address === null || typeof address === "string") throw new Error("sin puerto");
    await new Promise<void>((resolve) => unused.close(() => resolve()));
    process.env[VARIABLE] = `http://127.0.0.1:${address.port}`;
    expect((await requestError("/404")).errorCode).toBe("ERROR_0");
  });
  it("el controlador devuelve el código de API y datos serializables", async () => {
    const result = await new EjemploController().searchEjemploList("test");
    expect(result).toEqual({ ok: false, codigo: CODE_FIELD === null ? "ERROR_404" : "RECURSO_AUSENTE", mensaje: "No existe" });
    expect(JSON.parse(JSON.stringify(result))).toEqual(result);
  });
});
