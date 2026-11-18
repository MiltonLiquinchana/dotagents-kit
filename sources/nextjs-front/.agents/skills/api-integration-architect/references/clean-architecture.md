# Clean Architecture — Guía de Capas (Next.js / TypeScript)

Referencia técnica para la cadena completa de consumo de APIs bajo Clean Architecture.

## Flujo de Datos

```
UI (Page/Component)
<!-- si frontend.llamadas_api=navegador -->
  └─▶ Controller  (orquesta, recibe onError, registra en ExceptionHandler)
<!-- si frontend.llamadas_api=servidor -->
  └─▶ Controller  (orquesta y devuelve un resultado serializable)
<!-- fin -->
        └─▶ Service  (lógica de negocio, mapea Model ↔ Response)
              └─▶ Repository  (llamadas HTTP con apiClient + context)
                    └─▶ API  (servidor externo)
```

## Reglas Canónicas por Capa

### Controller

<!-- si frontend.llamadas_api=servidor -->
El Controller convierte `CustomError` al resultado serializable; cada Server Action crea una instancia sin callback y la pantalla muestra el mensaje con `Notificador`. Consulta el contrato de servidor en `error-handling-and-logs.md`.
<!-- fin -->

1. **Archivo Interface** (`<nomenclatura.controlador_interfaz>.ts`): Contrato público con métodos tipados.
2. **Archivo Clase** (`<nomenclatura.controlador_implementacion>.ts`): Implementa la interface.

**Estructura interna obligatoria:**

```
private readonly logger = new Logger();
private readonly service: <nomenclatura.servicio_interfaz> = new <nomenclatura.servicio_implementacion>();
```

**Constructor:**
<!-- si frontend.llamadas_api=navegador -->
- Registra `onError` en `ExceptionHandler.defineOnErrorDetect(CONTROLLER_CONTEXTS.[ENTITY]_CONTROLLER, onError)`.
<!-- si frontend.llamadas_api=servidor -->
- Sin registro de callbacks: captura el error tipado y devuelve su resultado serializable.
<!-- fin -->
- Log de inicialización: `this.logger.info({ message: "se creo la instancia para el controlador <nomenclatura.controlador_implementacion>" })`.

**Cada método:**
1. `this.logger.info({ message: \`\${CONTROLLER_CONTEXTS.[ENTITY]_CONTROLLER} [methodName]\` })`
2. Delegación al service: `const res = await this.service.[methodName](...)`
3. `this.logger.debug({ message: "[methodName] response", data: res })`
4. `return res`

### Service

**Estructura interna obligatoria:**

```
logger = new Logger();
private readonly repository: <nomenclatura.repositorio_interfaz> = new <nomenclatura.repositorio_implementacion>();
```

**Cada método:**
1. `this.logger.info({ message: "<nomenclatura.servicio_implementacion> [methodName]" })`
2. `this.logger.debug({ message: "[methodName] query path", data: param })`
3. Llamada al repository obteniendo `Model`
4. `this.logger.debug({ message: "[methodName] data response", data: model })`
5. Retorno con transformación estática: `model.map((m) => <nomenclatura.response>.formatModelToResponse(m))`

### Repository

**Estructura interna obligatoria:**

```
interface CustomAxiosRequestConfig extends AxiosRequestConfig {
    context?: string;
}

logger = new Logger();
```

**Cada método:**
1. `this.logger.info({ message: "<nomenclatura.repositorio_implementacion> [methodName]" })`
2. Llamada a `apiClient` pasando `context: CONTROLLER_CONTEXTS.[ENTITY]_CONTROLLER`
3. Validación de respuesta y log de fallback
4. `this.logger.debug({ message: "Se encontró resultados exitosamente (200 OK).", data: response })`
5. `return (response?.data as <nomenclatura.modelo>[]) ?? []`

### Dominios (`domains/`)

| Tipo | Ubicación | Responsabilidad |
|------|-----------|-----------------|
| `Model` | `domains/models/` | Interfaz pura (estructura cruda de la API) |
| `Request` | `domains/request/` | Payload hacia la API + `formatModelToRequest()` estático |
| `Response` | `domains/responses/` | Estructura para la UI + `formatModelToResponse()` estático |

## Templates Canónicos

Los templates completos de cada capa están disponibles en:
`assets/templates/clean-architecture/`

