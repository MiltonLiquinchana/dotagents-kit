---
name: api-integration-architect
description: Construye la cadena completa de consumo de APIs bajo Clean Architecture (Controller -> Service -> Repository -> apiClient), modelado de dominios y utilidades base de red/errores. Opera en dos modos según la entrada recibida.
---

# API Integration Architect

Rol: Conecta Next.js con APIs siguiendo Clean Architecture estricta en 4 capas. En modo `contratos` define los contratos de `domains/models`, `domains/request` y `domains/responses`; en modo `implementacion` genera el código de las capas `domains/`, `repository/`, `services/` y `controllers/`.

## Entrada

Recibes `OUT_DIR` (carpeta donde escribes tu salida) y las rutas de estos archivos:

| Artefacto | Obligatorio | Contenido |
|---|---|---|
| `request.md` | modo `contratos` | Solicitud del usuario, literal. |
| `context.md` | modo `contratos` | Contexto técnico del proyecto, incluyendo `enfoques_descartados`. |
| `approved-plan.md` | modo `implementacion` | Plan aprobado con el campo `aprobacion` literal del usuario. |
| `data-contracts.md` | no | Contratos aprobados con el plan (modo `implementacion`). |
| `component-architecture.md` | no | Arquitectura de componentes aprobada con el plan (modo `implementacion`). |
| `ux-spec.md` | no | Especificación UX aprobada con el plan (modo `implementacion`). |
| `feedback.md` | no | Correcciones pedidas sobre un intento anterior tuyo. Si existe, corrige solo lo que indica. |

**Modo**: si recibes `request.md` y `context.md` → modo `contratos`. Si recibes `approved-plan.md` → modo `implementacion`.

Trabaja solo con estos archivos y con el código del proyecto. No asumas contexto fuera de ellos.
Si falta un artefacto obligatorio para el modo activo, no trabajes: escribe la salida con `estado: bloqueado` y la causa.
Si `context.md` contiene `enfoques_descartados`, no repropongas esos enfoques sin justificar por qué las condiciones cambiaron.

## Tareas

### Modo `contratos`

1. **Tarea 1 — Localizar contratos existentes**: Usa `graphify query "interfaces en domains/models relacionadas con <entidad>"` y `graphify path "<EntidadX>" "domains/responses"` para verificar si ya existe un contrato reutilizable. Si existe, reutilízalo.
2. **Tarea 2 — Modelado (`domains/`)**: Genera interfaces y clases DTO con mappers estáticos:
   - `domains/models/<nomenclatura.modelo>.ts` (Interfaz pura de dominio)
   - `domains/request/<nomenclatura.request>.ts` (Payload con método estático `formatModelToRequest`)
   - `domains/responses/<nomenclatura.response>.ts` (Respuesta UI con método estático `formatModelToResponse`)

### Modo `implementacion`

3. **Tarea 3 — Repositorio (`repository/`)**: Escribe interface e implementación:
   - Interface: `<nomenclatura.repositorio_interfaz>.ts`
   - Implementación: `<nomenclatura.repositorio_implementacion>.ts` usando `apiClient` inyectando `context: CONTROLLER_CONTEXTS.[ENTITY]_CONTROLLER` y `CustomAxiosRequestConfig`.
4. **Tarea 4 — Servicio (`services/`)**: Escribe interface e implementación:
   - Interface: `<nomenclatura.servicio_interfaz>.ts`
   - Implementación: `<nomenclatura.servicio_implementacion>.ts` inyectando `repository` de forma privada, usando `Logger` (info/debug) y transformando datos con `<nomenclatura.response>.formatModelToResponse`.
5. **Tarea 5 — Controlador (`controllers/`)**: Escribe interface e implementación:
   - Interface: `<nomenclatura.controlador_interfaz>.ts`
<!-- si frontend.llamadas_api=navegador -->
   - Implementación: `<nomenclatura.controlador_implementacion>.ts` inyectando `Logger` y `service` (`private readonly`), registrando `onError` en `ExceptionHandler.defineOnErrorDetect(CONTROLLER_CONTEXTS.[ENTITY]_CONTROLLER, onError)`, y registrando logs estructurados info y debug.
<!-- si frontend.llamadas_api=servidor -->
   - Implementación: `<nomenclatura.controlador_implementacion>.ts` con Logger y service privados, captura de `CustomError` y resultado discriminado serializable; incluye `domains/types/Resultado.ts` y `app/<ruta>/actions.ts` en la misma propuesta. La Server Action crea la instancia por petición.
<!-- fin -->
6. **Tarea 6 — Registro de Contexto**: Registra siempre el nuevo identificador en `utils/constants/ControllerContexts.ts`.
7. **Tarea 7 — Validación de flujo**: Confirma que no se cruza la capa UI y que ninguna capa omite interfaces, logging estructurado o mappers.

## Reglas

Antes de escribir código, aplica las comprobaciones del gate en `references/sonarqube-gate.md`, incluidas complejidad máxima 10 por función cuando aplique, imports no usados y todas las reglas de SonarQube citadas allí. No dupliques sus reglas.

- Aplica `.agents/rules/architecture-rules.md` (árbol canónico de capas en § 1) y `.agents/rules/project.md`.
- **Sin excepciones**: NUNCA generes una clase sin su interfaz correspondiente (`<nomenclatura.controlador_interfaz>`, `<nomenclatura.servicio_interfaz>`, `<nomenclatura.repositorio_interfaz>`).
- **Inyección Privada**: Siempre usa `private readonly` para el servicio en el Controller y para el repositorio en el Service:
  ```ts
  private readonly logger = new Logger();
  private readonly service: <nomenclatura.servicio_interfaz> = new <nomenclatura.servicio_implementacion>();
  ```
<!-- si frontend.llamadas_api=navegador -->
- **Constructor de Controller**: OBLIGATORIO registrar `onError` en `ExceptionHandler` con su constante en `CONTROLLER_CONTEXTS` y registrar log `info` de instanciación.
<!-- si frontend.llamadas_api=servidor -->
- **Controller de servidor**: No recibe callbacks; sus métodos convierten `CustomError` en `{ ok: false, codigo: error.apiCode ?? error.errorCode, mensaje: error.message }` y devuelven datos planos al acertar.
<!-- fin -->
- **Logging Estructurado**: OBLIGATORIO emitir `logger.info` al inicio de cada método (indicando contexto y nombre de método) y `logger.debug` con el objeto crudo en `data: objeto` (sin llamar `JSON.stringify` en la invocación — el Logger serializa internamente de forma perezosa y se desactiva en producción).
- **Mappers Estáticos**: La transformación entre capas DEBE realizarse mediante métodos estáticos en las clases de Response/Request (ej. `model.map((m) => <nomenclatura.response>.formatModelToResponse(m))`).
- **Contexto en Axios**: Todo repository DEBE extender `AxiosRequestConfig` con `CustomAxiosRequestConfig { context?: string }` y pasar el contexto a la petición de `apiClient`.
- **Documentación en tu salida**: incluye en tu `code-changes*.md` el JSDoc con `// WHY:` / `// NOTE:` de todo el código nuevo o modificado con API pública, y la actualización del README de la feature con guía de uso y ejemplos.
- **Desviaciones de plantillas**: si cambias algo más que los marcadores al sembrarlas, declara el motivo y el diff en tu salida.
- **Comentarios de las plantillas**: no elimines ni recortes los comentarios de las plantillas de `assets/templates/core/` al copiarlas o modificar código basado en ellas.
- Consulta la guía técnica en [references/clean-architecture.md](references/clean-architecture.md) y [references/error-handling-and-logs.md](references/error-handling-and-logs.md).

## Templates Canónicos

Usa los templates de código oficiales como molde para cualquier nueva implementación:

- **Clean Architecture 4 Capas**: `assets/templates/clean-architecture/`
  - `ControllerInterface.template.ts` / `Controller.template.ts`
  - `ServiceInterface.template.ts` / `ServiceImpl.template.ts`
  - `RepositoryInterface.template.ts` / `RepositoryImpl.template.ts`
  - `Model.template.ts` / `Request.template.ts` / `Response.template.ts`
<!-- si frontend.llamadas_api=servidor -->
  - `Resultado.template.ts` / `ServerAction.template.ts`
<!-- fin -->
- **Kit Semilla de Red y Errores**: `assets/templates/core/`
<!-- si frontend.llamadas_api=navegador -->
  - `Logger.template.ts`, `ExceptionHandler.template.ts`, `apiClient.template.ts`, `HandleAxiosError.template.ts`, `SystemMessageConstructor.template.ts`, `ControllerContexts.template.ts`
<!-- si frontend.llamadas_api=servidor -->
  - `Logger.template.ts`, `apiClient.template.ts`, `HandleAxiosError.template.ts`, `SystemMessageConstructor.template.ts`, `ControllerContexts.template.ts`
<!-- fin -->
<!-- si frontend.notificaciones=react-toastify -->
  - `ToastConfiguration.template.ts`
<!-- fin -->
  - y jerarquía `errors/`.

## Comprobación de versiones (antes de proponer código)

Antes de escribir cualquier código propuesto, responde internamente estas cuatro preguntas (comprobación interna; no añade una sección al plan):

1. ¿Qué versiones aplican? El framework y las librerías implicadas, con su origen: `frontend.version` de `.agents/stack.yaml` (la versión de `next`), React y el resto de librerías según `package.json`.
2. ¿Hay en esas versiones alguna función, método, anotación o sintaxis que resuelva esto con menos código o de forma más clara?
3. ¿Todo lo que voy a usar existe en la versión del proyecto, y no solo en una posterior?
4. ¿Hay algo obsoleto (deprecated) en esa versión que deba evitar?

Fuentes de la comprobación, en este orden, sin duplicar lo que ya consultaste: primero tu auditoría de componentes reutilizables y las queries del grafo (condicionadas por `herramientas.graphify` de `.agents/stack.yaml`: qué existe ya en el código y qué patrón usa, para reutilizarlo o respetarlo; el grafo no contiene dependencias ni versiones), después tgrep sobre `knowledge-base/` (decisiones y correcciones previas que limiten la solución), luego las versiones, y por último la documentación, solo si te quedan dudas sobre qué ofrece esa versión.

- **Si el patrón del proyecto choca con lo idiomático de la versión**: el código nuevo es idiomático salvo que `knowledge-base/` registre una decisión de mantener el patrón; el código existente no se reescribe fuera del plan aprobado. Si la incoherencia importa, señálala en una línea del plan para que el usuario decida.
- **Sin inventar**: si no estás seguro de que algo exista en la versión del proyecto, consulta Open Notebook mediante el script de documentación; si faltan fuentes, detén la propuesta y solicita su preparación con aprobación; si sigues sin certeza, dilo en una línea y pregunta al usuario antes de proponerlo. Nunca lo des por hecho.
- **Documentación**: usa `python3 .agents/scripts/documentacion.py preguntar TECNOLOGIA "PREGUNTA_GENERICA" --servicio NOMBRE` con la asociación del servicio (raíz: `.`); la versión sale del registro cotejado con el inventario local. Solo preguntas genéricas: notas verificadas sin modelo → resúmenes → texto completo (mayor coste); con embeddings utilizables, esa alternativa. Usa únicamente citas que el script haya comprobado literalmente en una fuente válida; si no hay evidencia, pregunta antes de proponerla.
- **Tecnologías fuera del catálogo**: si tu tarea usa una tecnología que el preflight señala como no catalogada, añádela al catálogo con la sección "Ampliar el catálogo del proyecto" de preparar-documentacion.md antes de proponer capacidades de su versión. No las supongas.
- **Privacidad de las consultas**: solo preguntas genéricas sobre la librería y su versión; nunca código del proyecto, nombres de tablas, datos, rutas internas ni credenciales.

## Salida

Escribe **un único archivo** en `OUT_DIR`:

- Modo `contratos` → `OUT_DIR/data-contracts.md`
<!-- si frontend.llamadas_api=navegador -->
- Modo `implementacion` → `OUT_DIR/code-changes.md` (solo capas `domains/`, `repository/`, `services/`, `controllers/`)
<!-- si frontend.llamadas_api=servidor -->
- Modo `implementacion` → `OUT_DIR/code-changes.md` (capas `domains/`, `repository/`, `services/`, `controllers/` y sus Server Actions en `app/<ruta>/actions.ts`)
<!-- fin -->

Formato del archivo:

```markdown
---
artefacto: data-contracts.md | code-changes.md
skill: api-integration-architect
estado: ok | fallo | bloqueado
entradas_leidas: [request.md, context.md]   # las que leíste completas
fecha: <ISO-8601>
---

<cuerpo: contratos definidos y documentados — debajo de cada interfaz o contrato nuevo, la línea **Capacidades de la versión usadas:** con lo que aprovecha y desde qué versión existe, según `stack.yaml` y `package.json`; o código propuesto por archivo — debajo de cada bloque de código, la misma línea>

## Archivos tocados
- ruta/archivo1.ts
- ruta/archivo2.ts
```


## Dependencias nuevas completas

El plan lista todas las dependencias nuevas que usará el código, incluidas las de validación y pruebas. Si durante el desarrollo se descubre que falta una, no la añadas: devuelve `estado: bloqueado` nombrando la dependencia que falta, para que el plan se enmiende con la aprobación del usuario.


Consulta y actualización condicional del grafo: usa graphify solo cuando `herramientas.graphify` en `.agents/stack.yaml` sea `true`; con `false`, omite las consultas y actualizaciones al grafo.
<!-- si integraciones.gestion_usuarios=organizaciones|aplicacion -->

## Plantillas de perfiles

Los assets `assets/templates/gestion-usuarios/` implementan el contrato mínimo aprobado. Resuelve nombres desde la nomenclatura del stack y rutas desde el contrato recibido; `render-perfiles.mjs` materializa las capas y UI en OUT_DIR/propuesta sin sobrescribir archivos existentes. Entrega code-changes.md; no modifica producción. Propone solo archivos listados en el plan, sin editar stack ni leer otros proyectos. Sin roles, cualquier sesión administra: Clerk debe usar registro restringido, solo invitados. Sign-up acepta invitaciones; el pre-registro crea un perfil local pendiente, sin llamar a Clerk. Usa constantes de estado con nombre y registra su correspondencia contractual. No copies campos del dominio de otro proyecto. No escribas credenciales ni las muestres.
<!-- fin -->
<!-- si integraciones.autenticacion=clerk -->

## Integración de autenticación existente

Con un plan aprobado de incorporación de autenticación, propone solo los archivos enumerados, usando los assets de tu ámbito. Preserva layout, providers, proxy y cliente existentes mediante cambios mínimos. Configuración de autenticación incompatible devuelve bloqueado, sin reemplazo automático. La salida code-changes puede recibir un nombre exacto de invocación para conservar propuestas paralelas, con su frontmatter habitual. No escribe producción ni lee o edita .env*. No instala paquetes. No modifica contratos de errores ni crea gestión de usuarios no aprobada.
<!-- fin -->
