// si-archivo frontend.llamadas_api=navegador
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { createServer, type Server } from "node:http";
import axios, { AxiosError, CanceledError } from "axios";
import apiClient from "@/utils/apiClient";
import { handleAxiosError } from "@/utils/HandleAxiosError";
import { CustomError } from "@/utils/errors/CustomError";
import { ExceptionHandler } from "@/utils/ExceptionHandler";

const MESSAGE_FIELD: string = <api_error.campo_mensaje>;
const CODE_FIELD: string | null = <api_error.campo_codigo>;
const VARIABLE = "NEXT_PUBLIC_API_BASE_URL";
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

beforeEach(() => { process.env[VARIABLE] = baseURL; vi.spyOn(ExceptionHandler, "handle").mockImplementation(() => undefined); });
afterEach(() => { vi.restoreAllMocks(); });
afterAll(async () => {
  if (previousURL === undefined) delete process.env[VARIABLE];
  else process.env[VARIABLE] = previousURL;
  if (server.listening) await new Promise<void>((resolve, reject) => server.close((error) => error ? reject(error) : resolve()));
});

function lastError(): CustomError {
  const error = vi.mocked(ExceptionHandler.handle).mock.calls.at(-1)?.[0].error;
  if (!(error instanceof CustomError)) throw new Error("no llegó CustomError");
  return error;
}
async function requestError(path: string): Promise<CustomError> {
  expect(await apiClient.get(path)).toBeUndefined();
  return lastError();
}
function classifiedError(error: unknown): CustomError {
  expect(() => handleAxiosError({ error, context: "test" })).not.toThrow();
  return lastError();
}

describe("núcleo de errores navegador", () => {
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
    expect(ExceptionHandler.handle).not.toHaveBeenCalled();
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
  it("si el callback falla solo se registra el mensaje", () => {
    vi.mocked(ExceptionHandler.handle).mockImplementation(() => { throw new Error("callback falló"); });
    const log = vi.spyOn(console, "error").mockImplementation(() => undefined);
    expect(() => handleAxiosError({ error: new AxiosError("red", "ERR_NETWORK"), context: "test" })).not.toThrow();
    expect(log).toHaveBeenCalledOnce();
    expect(log.mock.calls[0]).toHaveLength(1);
    expect(typeof log.mock.calls[0][0]).toBe("string");
    expect(log.mock.calls[0][0]).toContain("callback falló");
  });
});
