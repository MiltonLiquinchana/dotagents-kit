# Manejo de Errores y Logging — Referencia Técnica

El contrato externo se declara en `api_error.campo_mensaje` y `api_error.campo_codigo` de `.agents/stack.yaml`. El bootstrap sustituye sus marcadores como literales TypeScript; con código `null` no se lee código del cuerpo. No se intenta otro nombre de campo.

La extracción acepta cuerpos null, texto, HTML y objetos sin campos válidos sin lanzar TypeError. `CustomError.apiCode` conserva el código de negocio; `errorCode` conserva `ERROR_<status>`.

Clasificación: 404, 408 y 409 conservan el mensaje válido del backend (por defecto «Ha ocurrido un error»); 500 y el resto usan «Ocurrio un error inesperado», como el clasificador canónico. Timeout del cliente (`ECONNABORTED` o `ETIMEDOUT`) usa «La solicitud tardó demasiado. Intenta nuevamente.»; sin respuesta HTTP se crea `CustomGenericError` con estado 0 y un mensaje de conexión. Las cancelaciones (`axios.isCancel`) se ignoran.

<!-- si frontend.llamadas_api=navegador -->
## Contrato de navegador

`apiClient` → `handleAxiosError` → `CustomError` → `ExceptionHandler.handle` → callback `onError` del Controller → `Notificador` en la UI.

`handleAxiosError` nunca lanza: incluso si el callback falla, registra solo su mensaje. El interceptor resuelve con `undefined` a propósito. Cada Repository devuelve el vacío seguro de la operación (`[]` para listas o `null` para un objeto), sin leer `response.data` si no hay respuesta. Un vacío no sustituye la notificación: el callback ya avisó a la pantalla.

El Controller registra su callback con `ExceptionHandler.defineOnErrorDetect` y `CONTROLLER_CONTEXTS`; un Provider estable permite compartirlo entre consumidores del navegador.

La variable pública es `NEXT_PUBLIC_API_BASE_URL`: Next la incrusta al construir el cliente.
<!-- si frontend.llamadas_api=servidor -->
## Contrato de servidor

`apiClient` y `HandleAxiosError` comienzan con `import "server-only"`. El interceptor rechaza con `CustomError`; no hay registro estático de callbacks ni funciones de UI guardadas en el servidor.

El Controller captura solo `CustomError` y devuelve el discriminado plano `Resultado<T>`: `{ ok: true, data }` o `{ ok: false, codigo: error.apiCode ?? error.errorCode, mensaje: error.message }`. Convierte las instancias DTO a objetos planos antes de devolverlas; los errores inesperados se propagan.

`app/<ruta>/actions.ts` empieza con `"use server"` y crea un controlador por llamada. La pantalla invoca la acción, estrecha por `resultado.ok` y muestra `resultado.mensaje` con `Notificador.error(resultado.mensaje, mostrar)`. El segundo argumento guarda el aviso en el estado de la UI cuando no hay librería de avisos. Nunca se importan las capas del servidor desde componentes cliente.

La variable privada es `API_BASE_URL` y no se expone en el navegador.
<!-- fin -->

## Configuración y logging

Sin URL de respaldo: el módulo se importa sin configuración, pero la primera petición sin variable rechaza con un error que nombra la variable y pide copiar `.env.example` a `.env.local`. El fallo de configuración se propaga al invocador.

`SystemMessageConstructor` produce `METHOD URL returned STATUS`, sin cabeceras. No registres el `AxiosError` ni su config: contienen `Authorization`. Registra solo el mensaje; `Logger.info` marca las operaciones y `Logger.debug` se suprime en producción.

## Templates

Las utilidades canónicas están en `assets/templates/core/`; las capas en `assets/templates/clean-architecture/`.
