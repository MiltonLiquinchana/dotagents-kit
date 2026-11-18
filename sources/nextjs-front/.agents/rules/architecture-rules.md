---
trigger: model_decision
description: Reglas de arquitectura, TypeScript, patrones de componentes y estado para Next.js.
---

# Reglas de Arquitectura (Next.js / TypeScript)

Reglas obligatorias para mantener consistencia y calidad en el proyecto frontend.

**OBLIGATORIO — Versiones del proyecto**: escribe código compatible e idiomático con las versiones del proyecto: `frontend.version` de `.agents/stack.yaml` es la versión de `next`; React y el resto se leen del inventario: `package-lock.json` si existe; sin lock, declaraciones literales y aviso de rangos. Next del manifiesto y del lock debe coincidir con el stack. Sin APIs de otras versiones. Si una versión ofrece una forma más simple, segura o clara de resolver algo (con menos código), úsala en lugar del patrón antiguo. Ejemplos: en un Server Component, carga los datos con `async`/`await` en lugar de `useEffect` con estado manual; usa `satisfies` cuando sustituya anotaciones redundantes; usa las APIs vigentes de React/Next en lugar de las que esa versión deprecó. La regla se aplica a todo el código que se escriba, conforme al plan o al completar la implementación. Si al escribir surge una duda sobre si algo existe en la versión del proyecto, consulta Open Notebook mediante el script de documentación; si faltan fuentes, detén la propuesta y solicita su preparación con aprobación; si sigue la duda, pregunta al usuario antes de usarla, y solo con preguntas genéricas sobre la librería y su versión (nunca código, datos ni rutas del proyecto).
El preflight comprueba la conexión con Open Notebook por GET y coteja el registro local: las tecnologías del catálogo requieren documentación activa y válida de su versión; una versión catalogada no resoluble bloquea. Las tecnologías fuera del catálogo avisan; si la tarea las usa, se requiere añadirlas al catálogo con la sección "Ampliar el catálogo del proyecto" de preparar-documentacion.md, sin suponer capacidades de su versión. Una retirada propone archivar solo sin usuarios. El usuario decide entre otra documentación/fuente o cambiar versiones mediante un plan aprobado.

## 1. Clean Architecture

- **Flujo estricto**: UI → Controller → Service → Repository → API.
- UI nunca llama a Repository ni a `apiClient` directamente.
<!-- si frontend.llamadas_api=navegador -->
- Controller recibe `onError` en su constructor y lo registra en `ExceptionHandler.defineOnErrorDetect`.
<!-- si frontend.llamadas_api=servidor -->
- La UI llama a una Server Action; esta crea un Controller por petición. El Controller captura `CustomError` y devuelve `{ ok: false, codigo: error.apiCode ?? error.errorCode, mensaje: error.message }`; la UI muestra el mensaje con `Notificador`.
<!-- fin -->
- Service orquesta la lógica de negocio y transforma datos con mappers estáticos (`formatModelToResponse`).
- Repository centraliza las llamadas a API usando `apiClient` con `CustomAxiosRequestConfig` inyectando `context: CONTROLLER_CONTEXTS...`.
- **Dualidad obligatoria**: Todo Controller, Service y Repository DEBE tener su interfaz pública separada de la clase de implementación. Prohibido omitir interfaces.
- **Inyección Privada**: Siempre `private readonly logger = new Logger()` y `private readonly service/repository = new ...Impl()`.
- **Estructura de carpetas**: TODO el código visual (componentes, layouts, vistas) y hooks DEBE estar dentro de `app/ui/` o `app/`.
- **Árbol canónico**: estas carpetas parten de la raíz del proyecto, sin carpeta por entidad; `repository` va en singular:

```text
controllers/   <nomenclatura.controlador_implementacion>.ts, <nomenclatura.controlador_interfaz>.ts
services/      <nomenclatura.servicio_interfaz>.ts, <nomenclatura.servicio_implementacion>.ts
repository/    <nomenclatura.repositorio_interfaz>.ts, <nomenclatura.repositorio_implementacion>.ts
domains/       models/, request/, responses/, types/
app/ui/        componentes visuales, en <nomenclatura.archivo_seccion_ui>
```

<!-- si frontend.llamadas_api=servidor -->
- Las Server Actions viven en `app/<ruta>/actions.ts` y solo exportan funciones asíncronas.
<!-- fin -->
- Si el plan tiene varias secciones de pantalla, crea un archivo `<nomenclatura.archivo_seccion_ui>` por sección.
- **Referencia canónica**: interfaces y templates en Clean Architecture.

## 2. TypeScript y Modelos

- Usa `interface` para objetos públicos. Prohíbe `any`.
- Modelos en `domains/models`, requests en `domains/request`, responses en `domains/responses`.
- DTOs deben implementar métodos estáticos de mapeo (`formatModelToRequest`, `formatModelToResponse`).
- Los contratos de `domains/` se definen durante el diseño de integración y se consumen en las capas de UI, sin redefinirlos.
- **Clean Code**: Aplica SOLID, DRY, YAGNI. Complejidad ciclomática ≤ 10.
- **TypeScript estricto**: Usa tipos explícitos. Prohíbe `any`. Prefiere `interface` sobre `type` para objetos públicos.

## 3. Next.js y Renderizado

- Server Components por defecto en `app/`. Usa `"use client"` solo en componentes que requieran estado, efectos, event handlers o interactividad del navegador.
- `next/image` para todas las imágenes. `dynamic imports` para componentes pesados.

## 4. Estado

| Estrategia | Cuándo usar |
|------------|-------------|
| `useState` / `useRef` local | Estado de un solo componente o formulario simple |
<!-- si frontend.llamadas_api=navegador -->
| Controller Pattern (`useRef` + `useEffect`) | Lógica de negocio en un solo componente |
| Controller Provider (`EntityProvider` + hook) | Misma instancia de controller compartida entre 2 o más componentes |
<!-- si frontend.llamadas_api=servidor -->
| Server Actions + estado local/Context de UI | Invocar el controlador de servidor y mostrar resultados serializables |
<!-- fin -->
| Zustand / Context | Estado de UI compartido entre componentes no emparentados |
| Redux (`StoreProvider` + `makeStore`) | Flujos globales de múltiples etapas con acciones y reducers (ej. filtros de fecha, wizard) |

<!-- si frontend.llamadas_api=navegador -->
- **Regla de Controller Providers**: Si 2 o más componentes requieren el mismo Controller, se debe crear un Provider con `useRef` para el objeto del contexto (garantizando estabilidad de referencia para SonarQube) y un hook tipado `use<nomenclatura.controlador_implementacion>()`.
<!-- si frontend.llamadas_api=servidor -->
- Comparte estado de UI mediante Context o hooks; el Controller permanece en el servidor y nunca se instancia en un Provider cliente.
<!-- fin -->
- **Referencia canónica**: patrón de Controller Providers para React.

## 5. Estilos

- Tailwind CSS con design tokens del proyecto. SCSS para estilos globales.
- Archivos `.scss` solo en `app/ui/sass/`. Parciales `_Nombre.scss` se importan en `Global.scss`.
- `app/ui/css/Global.css` es autogenerado. **PROHIBIDO** editar `.css` directamente.
- Motion y animaciones con `framer-motion`. Requerido: staggered reveals, transiciones, `backdrop-blur`.

## 6. Accesibilidad

- Cumplir WCAG 2.1 (AA). Contraste mínimo 4.5:1.
- Roles ARIA, focus management, etiquetas semánticas en formularios.

## 7. Calidad y Pruebas

- Cobertura > 80%. Complejidad ciclomática ≤ 10. Prohíbe duplicar lógica.
- Se verifica el cumplimiento de calidad antes del commit.
- **Testing Obligatorio**: Todo cambio de lógica en `services/` o `controllers/` requiere tests unitarios cuando el proyecto cuente con un test runner configurado (script `"test"` en `package.json`). Si el proyecto no define script de pruebas, se omite documentándolo en el plan.

## 8. Patrones de Aislamiento de Re-renders

Esta sección complementa § 4 — aplica las estrategias de estado ya definidas, añadiendo criterios de aislamiento para evitar re-renders cruzados. Al diseñar componentes que consultan la API o gestionan estado de carga, evaluar:

### Patrón A — Contenedor Autónomo de Estado

**Aplicar cuando:**
- El estado de una sección visual (carga, datos) re-renderizaría componentes hermanos o el padre que no deberían verse afectados.
- La sección tiene un ciclo de vida de datos independiente al de sus hermanos.

**No aplicar cuando:**
- El componente ya gestiona todos sus estados sin afectar a hermanos.
- Solo existe una sección de datos en la página.
- El estado es compartido → usar Redux/Zustand.

**Estructura canónica:**
- Componente en `app/ui/.../<nomenclatura.archivo_seccion_ui>`
- Props mínimas (ej. solo `pedidoId`)
- `useEffect` de carga inicial interno
- Estados `isLoading` y `data` locales
- Expone acciones externas mediante `ref` (`forwardRef` o React 19 `ref`) + `useImperativeHandle`.

---

### Patrón B — Suscripción Redux en el Consumidor (Trigger Ciego)

**Regla de Firma Vacía:** Toda función expuesta mediante `useImperativeHandle` para filtrado o recarga DEBE tener firma `() => void` (**CERO parámetros**). El componente que **ejecuta lógica** sobre un estado Redux debe ser quien haga `useSelector` internamente. El componente disparador (ej. Header) **NUNCA** debe leer el estado para reenviarlo como argumento.

**Aplicar cuando:**
- Un encabezado/botón dispara una actualización → el consumidor lee Redux directamente.
- Pasar el estado como prop haría que el disparador y la página padre también se re-rendericen al cambiar Redux.

**Página Orquestadora:**
- La página padre sostiene únicamente un `useRef<SectionRef>(null)` (CERO `useState`).
- Pasa `onApplyFilter={() => sectionRef.current?.handleApplyFilter()}` al disparador.
- Resultado: **Cero re-renders globales** al interactuar con filtros.

**Referencia canónica:** patrones de aislamiento de re-renders para React.

## 9. Consumidores antes de tocar una ruta o contrato exportado

Antes de ocultar, eliminar, renombrar o cambiar la firma de algo que otros ficheros importan o que el navegador solicita, identifica sus consumidores y decláralos en el Plan:

- **Qué cuenta**: una ruta de `app/` (página o `route.ts`), un handler de API, un componente o hook exportado, un método público de un Controller/Service/Repository, un tipo de `domains/` o una variable `NEXT_PUBLIC_*`.
- **Cómo se identifican**: `codebase-memory-mcp cli trace_path --project "<proyecto>" --function-name "<símbolo>" --direction inbound` (y `codebase-memory-mcp cli trace_path --project "<proyecto>" --function-name "<símbolo>" --direction inbound` si hay duda); para rutas, busca además los `href`, `router.push`, `redirect` y `fetch`/`apiClient` que apuntan a ella (el grafo no resuelve cadenas de URL).
- **Qué se declara**: la lista de consumidores y, por cada uno, si se actualiza en el mismo cambio o queda roto. Un consumidor sin actualizar es **Bloqueante** en la revisión de código.
- **Cuándo se exige en revisión**: solo cuando el diff oculta, elimina o renombra algo exportado, o cambia su firma de forma incompatible. Un cambio aditivo no lo dispara.
- **Límite**: el grafo indexa AST de código; no ve consumidores fuera del repositorio (otros proyectos, enlaces externos). Si hay sospecha de ellos, el Plan lo declara como riesgo.


## Núcleo compartido

El núcleo transversal (`Logger`, `apiClient`, errores y contextos) vive en `utils/`. Usa las plantillas de `.agents/skills/<skill-de-integracion>/assets/templates/core/`, sembradas por el bootstrap inicial. No crees un segundo núcleo en otra carpeta.

Ejemplos de clientes y pedidos: ejemplo con la convención recomendada; las convenciones efectivas se leen de `.agents/stack.yaml`.
<!-- si integraciones.gestion_usuarios=organizaciones|aplicacion -->
## Gestión de usuarios y registro restringido

La instancia de Clerk debe tener registro restringido, solo personas invitadas. Sin roles, cualquier usuario con sesión puede usar las operaciones de administración. La página de registro solo sirve para aceptar invitaciones; el pre-registro crea un perfil local PENDIENTE y no pasa por Clerk. No se implementa autorización por roles. PENDIENTE=1, INVITADO_A_CLERK=2, ACTIVO=3, INACTIVO=4 se expresan como constantes con nombre; el contrato registra la correspondencia final. INACTIVO es estado local y no revoca sesiones de Clerk. No hay contraseñas locales ni tabla de roles.
<!-- fin -->

Si surge una duda de API en diseño, desarrollo o revisión, consulta mediante `python3 .agents/scripts/documentacion.py preguntar TECNOLOGIA "PREGUNTA_GENERICA" --version VERSION`. La referencia debe corresponder a la serie del proyecto (major.minor; JDK: mayor) y las notas al parche exacto. Solo se usa una cita verificada literalmente. Sin evidencia, pregunta; no envíes código, tablas, datos, rutas ni credenciales. Las decisiones del proyecto siguen en knowledge-base/ con tgrep.
