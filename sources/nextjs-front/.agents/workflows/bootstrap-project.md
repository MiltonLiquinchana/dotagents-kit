---
description: Inicializa la infraestructura base (utils, red, manejo de errores y providers) en un proyecto nuevo o en blanco a partir de los templates canónicos de .agents.
---

# Bootstrap Project — Inicializador de Arquitectura Base

Este workflow inicializa los cimientos arquitectónicos en un proyecto nuevo de Next.js / TypeScript. Al ejecutarse, siembra las utilidades core, la jerarquía de errores, el cliente API y la infraestructura de estado para que el proyecto quede 100% listo para implementar features bajo Clean Architecture.

---


## Control documental estricto antes de trabajar en código

Al entrar, antes de diseñar, generar o adaptar código, ejecuta estos controles en orden y detente al primer fallo. No uses --diagnostico ni omitas el control porque la infraestructura completa aún no esté preparada. Esta entrada comprueba solo documentación; conserva los demás controles del workflow y el preflight completo al cierre.

```bash
python3 -I -B .agents/scripts/documentacion.py comprobar-conexion || exit 1
python3 -I -B .agents/scripts/comprobar-documentacion.py || { echo "BLOCKED: Completa la documentación del catálogo mediante .agents/workflows/preparar-documentacion.md antes de repetir bootstrap-project.md." >&2; exit 1; }
python3 -I -B .agents/scripts/documentacion.py comprobar-existencia || exit 1
```

## Precondiciones

1. Repositorio Next.js creado con `package.json` y `tsconfig.json`.
2. Dependencias mínimas instaladas o planificadas:
   - `axios`
<!-- si frontend.llamadas_api=servidor -->
   - `server-only`
<!-- fin -->
<!-- si frontend.notificaciones=react-toastify -->
   - `react-toastify`
<!-- fin -->
   - `@reduxjs/toolkit` y `react-redux` (si se utilizará estado global)
   - `framer-motion` y `lucide-react` (para UI y motion)

---

## Pasos de Ejecución

### Paso 0: Carpeta de ejecución

1. Crear carpeta de ejecución: `RUN_DIR=".agent-runs/$(date +%Y%m%d-%H%M)-<slug-bootstrap>"` en la raíz del proyecto, nunca en `/tmp`.
2. Escribir `RUN_DIR/manifest.md` con una fila por paso, igual que `implement-feature.md`.
   La carpeta vive fuera de `.agents/`: los sandboxes de algunas herramientas montan `.agents/` en solo lectura, y los artefactos del bootstrap tendrían que pedir permiso por cada escritura.

### Paso 1: Siembra de Utilidades Core (`utils/`)

**Ejecución**: subagente con rol `api-integration-architect` (ver `.agents/workflows/references/ejecutar-fase.md`).

El agente copia y adapta los templates desde:
`.agents/skills/api-integration-architect/assets/templates/core/` hacia la carpeta `utils/` del proyecto:

1. **`utils/Logger.ts`** ➔ desde `Logger.template.ts`.
2. **`utils/SystemMessageConstructor.ts`** ➔ desde `SystemMessageConstructor.template.ts`.
3. **`utils/HandleAxiosError.ts`** ➔ desde `HandleAxiosError.template.ts`.
4. **`utils/apiClient.ts`** ➔ desde `apiClient.template.ts`, sin URL de respaldo.
5. **`utils/constants/ControllerContexts.ts`** ➔ desde `ControllerContexts.template.ts`.
6. **`utils/Notificador.ts`** ➔ desde `Notificador.template.ts`; la UI lo usa como punto único de avisos.
<!-- si frontend.notificaciones=react-toastify -->
   Copia también `utils/constants/ToastConfiguration.ts` desde `ToastConfiguration.template.ts`.
<!-- fin -->
<!-- si frontend.notificaciones=ninguna -->
   Cada componente entrega a `Notificador` la función que guarda y muestra el aviso en su estado.
<!-- fin -->
7. **`utils/constants/ErrorMessages.ts`** ➔ desde `ErrorMessages.template.ts`.
8. **`utils/errors/CustomError.ts`** ➔ desde `errors/CustomError.template.ts`.
9. **`utils/errors/axios/*`** ➔ desde `errors/axios/*.template.ts`: `CustomConflictError`, `CustomGenericError`, `CustomInternalServerError`, `CustomNotFoundError` y `CustomTimeoutError`.
<!-- si frontend.llamadas_api=navegador -->
10. **`utils/ExceptionHandler.ts`** ➔ desde `ExceptionHandler.template.ts`: conserva el callback del controlador y el vacío seguro del repositorio. Crea `.env.example` con `NEXT_PUBLIC_API_BASE_URL=http://api.example.test`; el README explica copiarlo a `.env.local` y configurar la URL antes del build (Next incrusta `NEXT_PUBLIC_API_BASE_URL` en el cliente).
<!-- si frontend.llamadas_api=servidor -->
10. Conserva `import "server-only"` al principio de `utils/apiClient.ts` y `utils/HandleAxiosError.ts`. Al implementar una ruta, usa `clean-architecture/ServerAction.template.ts` como `app/<ruta>/actions.ts` y `Resultado.template.ts` como `domains/types/Resultado.ts`; la acción crea el controlador por petición. No copies el mapa de callbacks. Declara `server-only` entre las dependencias necesarias. Crea `.env.example` con `API_BASE_URL=http://api.example.test`; el README explica copiarlo a `.env.local` y configurar la URL del servidor.
<!-- fin -->

Después de sembrar, lee `api_error.campo_mensaje` y `api_error.campo_codigo` con `node .agents/scripts/stack.mjs get <clave>`. Sustituye los marcadores `<api_error.campo_mensaje>` y `<api_error.campo_codigo>` como expresiones TypeScript: serializa cada texto con `JSON.stringify` y usa el literal `null` cuando el lector devuelva una línea vacía para el código. No añadas comillas manualmente ni un campo alternativo. Con código `null`, el extractor no lee ningún código del cuerpo.

Comprueba con `rg -n '<api_error\.[^>]+>' utils/ controllers/ repository/` las carpetas existentes (omite solo las que todavía no existan). Exit 0 significa marcadores pendientes → `estado: fallo`; exit 1 significa ninguno → OK; exit ≥2 → detener e informar con la salida literal.

Comprueba con `git check-ignore --no-index .env.example` que el archivo de ejemplo no está ignorado; si lo está, añade la excepción `!.env.example` después de la regla que lo ignora y repite la comprobación. No leas valores de `.env.local`.

Si falta la variable, la primera petición falla con «falta <VARIABLE>; copia .env.example a .env.local»; importar el núcleo durante `next build` no exige esa variable. El README describe este comportamiento.

Cualquier cambio respecto a las plantillas, salvo sustituir marcadores, se declara en la salida del bootstrap como desviación con motivo y diff. No elimines ni recortes comentarios de las plantillas. Esta obligación también rige al sembrarlas durante una feature.

### Paso 2: Infraestructura de Estado Global (`app/` y `lib/`)

**Ejecución**: subagente con rol `frontend-developer` (ver `.agents/workflows/references/ejecutar-fase.md`).

Si el proyecto utilizará Redux para estado global (por ejemplo, filtros de fecha compartidos o asistentes multi-paso), el agente siembra desde:
`.agents/skills/frontend-developer/assets/templates/providers/`:

1. **`lib/store.ts`** ➔ desde `store.template.ts`
2. **`app/StoreProvider.tsx`** ➔ desde `StoreProvider.template.tsx`
<!-- si frontend.notificaciones=ninguna -->
3. Envolver el `children` en `app/layout.tsx` dentro de `<StoreProvider>`.
<!-- fin -->
<!-- si frontend.notificaciones=react-toastify -->
3. Envolver el `children` en `app/layout.tsx` dentro de `<StoreProvider>` y añadir `<ToastContainer />`.
<!-- fin -->

<!-- si integraciones.autenticacion=clerk -->
### Base de autenticación

La fase de integración copia `ClerkToken.template.ts` a `utils/ClerkToken.ts`. La fase de UI siembra los assets de `frontend-developer/assets/templates/clerk/`: `proxy.template.ts` a `proxy.ts`, SignIn/SignUp a `app/(login)/sign-in/[[...sign-in]]/page.tsx` y `app/(login)/sign-up/[[...sign-up]]/page.tsx`, e integra ClerkLayout en el layout existente sin eliminar otros providers. Si está generado ClerkTokenSetup, lo copia a `app/ui/auth/ClerkTokenSetup.tsx` y lo monta dentro de ClerkProvider. No usa un getter global de tokens del servidor.

Usa `@clerk/nextjs` con la versión compatible declarada en el proyecto (referencia del original: ^7.2.2); no instala paquetes sin permiso. Declara solo los nombres de `integraciones.variables_autenticacion` en el ejemplo de entorno, sin valores. Las rutas de acceso y registro son públicas. La variante de gestión determina si aparece pre-registro en el proxy; bootstrap no crea una pantalla de gestión sin su instalación aprobada.
<!-- fin -->
### Paso 3: Verificación de Tipos

Ejecuta en consola:
```bash
npx tsc --noEmit
```
Verifica que todos los archivos recién creados compilen sin errores de TypeScript y que los alias de path (`@/*`) en `tsconfig.json` apunten correctamente a la raíz del proyecto.

### Paso 4: Inicialización del Grafo de Conocimiento (Graphify)

Si `herramientas.graphify` de `.agents/stack.yaml` es `true`, una vez sembrada la base ejecuta:
```bash
GRAPHIFY_BACKEND=none graphify .
```
Esto genera `graphify-out/graph.json` con los primeros nodos del proyecto indexados para que las próximas features puedan consultar el grafo desde el primer momento.

Si es `false`, omite este paso y regístralo en el informe del workflow.

### Paso 5: Registro del Proyecto en SonarQube (Setup inicial)

Si el entorno cuenta con una instancia de SonarQube configurada:
1. Resuelve el `projectKey` como el valor `sonarqube.project_key` de `.agents/stack.yaml`.
2. Verifica si el proyecto existe en el servidor (`node .agents/scripts/sonar-mcp.mjs search_my_sonarqube_projects --json '{"q":"<projectKey>"}'`). Si no existe, pide permiso al usuario para crear un proyecto privado y, con su permiso, ejecuta:
   ```bash
   node .agents/scripts/sonar-diff-gate.mjs --registrar-proyecto <projectKey>
   ```
3. Asegura que `sonar-project.properties` contenga:
   ```properties
   sonar.projectKey=<projectKey>
   ```


---

### Paso 6: Preflight completo antes de declarar la entrega lista

Ejecuta `bash .agents/scripts/preflight.sh --workflow bootstrap-project --fase cierre` sin omisiones y registra su salida. No declares lista la entrega si falla. Si falta preparación, informa del diagnóstico; si el árbol sucio lo bloquea, espera a que el usuario resuelva su estado git, sin commits automáticos ni ocultar cambios. El control documental inicial no sustituye este cierre completo.

## Resultado Final

El proyecto cuenta con:
- Infraestructura de red desacoplada con interceptor de errores y contexto.
<!-- si frontend.llamadas_api=navegador -->
- Despacho centralizado de excepciones con `ExceptionHandler`.
<!-- si frontend.llamadas_api=servidor -->
- Errores del servidor convertidos por el controlador en resultados serializables para la UI.
<!-- fin -->
- Logging estructurado uniforme con timestamps y niveles.
- Soporte para StoreProvider SSR-safe.
- Listo para recibir features mediante el workflow `implement-feature.md`.



### Dependencias de las plantillas core

<!-- si frontend.notificaciones=react-toastify -->
Las plantillas de `.agents/skills/api-integration-architect/assets/templates/core/` requieren `axios` y `react-toastify`. Antes de instalarlos, informa de ambos paquetes y solicita permiso explícito; si se rechaza, no los instales y detén la inicialización dependiente de ellos.
<!-- fin -->
<!-- si frontend.notificaciones=ninguna -->
Las plantillas de `.agents/skills/api-integration-architect/assets/templates/core/` requieren `axios`. Antes de instalarlo, informa del paquete y solicita permiso explícito; si se rechaza, no lo instales y detén la inicialización dependiente de él.
<!-- fin -->

Antes de aprobar cualquier plan, sigue `.agents/workflows/references/decisiones-stack.md`; consulta clases, remedios y códigos que resuelve este workflow en `.agents/config/codigos.yaml`.

En la entrada especial, antes del plan, ejecuta `python3 -I -B .agents/scripts/registro-stack.py comprobar` sin preflight completo; conserva la entrada documental estricta existente y no exijas commit de la importación para diseñar.
