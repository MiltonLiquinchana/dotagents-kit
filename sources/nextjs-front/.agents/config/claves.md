# Claves de `stack.yaml`

**Palabras que usan estas fichas**

- **`.agents`:** carpeta con las instrucciones y la configuración que usa el agente para trabajar en tu proyecto.
- **Plantilla:** archivo de ejemplo del que se parte para preparar instrucciones o proponer código adaptado al proyecto.
- **Generador:** programa `actualizar.py` que lee tus decisiones de `stack.yaml` y prepara `.agents` con las plantillas correspondientes.
- **Tarea o workflow:** instrucciones para un trabajo concreto, por ejemplo cambiar una versión o preparar documentación.
- **Plan aprobado:** propuesta de archivos y cambios que te enseña el agente y que solo aplica después de recibir tu sí.
- **Validador:** programa que comprueba que `stack.yaml` contiene las claves y los valores permitidos.
- **Comprobación previa (preflight):** revisión de una tarea que informa qué falta, qué difiere y qué impide continuar.
- **Registro `docs/decisiones-stack.md`:** si tu código no coincide con `stack.yaml`, la tarea te pregunta si quieres corregirlo en su plan (sí), conservar esa diferencia (no) o dejarla para revisión. Tu respuesta se guarda para ese valor y ese servicio: el no se recuerda en una línea sin volver a proponerlo; para revisión se recuerda con la opción de aplicarla.
- **Regenerar:** actualizar las instrucciones con `python3 -I -B .agents/actualizar.py --kit <KIT>`; sustituye `<KIT>` por la ruta del repositorio de plantillas. No cambia el código de tu aplicación.
- **Preparación del proyecto:** trabajo de `preparar-proyecto.sh`: crea archivos auxiliares que faltan y prepara exclusiones; lo ejecutas tú o lo autorizas expresamente.
- **Open Notebook:** aplicación que guarda las fuentes de documentación y permite consultar información de las versiones del proyecto con citas comprobables.
- **MCP:** conexión que permite al agente usar herramientas de un servidor externo, por ejemplo análisis de código o consultas de base de datos.
- **API:** rutas y operaciones que un programa ofrece a otro para intercambiar datos; por ejemplo, consultar pedidos.
- **Respaldo:** archivos que justifican lo explicado en una ficha; sus rutas son relativas al `.agents` generado.
- **URL:** dirección de un recurso o servidor, por ejemplo la API de documentación; no es una contraseña.
- **HTTP y HTTPS:** protocolos para comunicarse con una dirección web; HTTPS cifra esa comunicación.
- **Núcleo:** archivos base del front: cliente HTTP que llama a la API, manejo de errores y avisos a la persona usuaria.
- **CORS:** permiso que necesita el navegador para llamar a una API situada en otro origen, es decir, otra combinación de protocolo, servidor o puerto.
- **Token:** dato que acredita la sesión de una persona al llamar a la API; se configura y maneja sin mostrar su contenido.
- **Clerk:** servicio de identidad que permite iniciar sesión y comprobar quién hace una petición.
- **SonarQube:** servidor que analiza el código y comunica problemas de calidad.
- **Commit:** versión guardada de tus archivos en Git.
- **Rama:** línea de trabajo de Git, por ejemplo `development` o `feature/pedidos`.

Estas fichas explican tus decisiones de `stack.yaml`. Los ejemplos se adaptan a tu proyecto. Las alternativas siguen visibles y las claves sin uso se ocultan según tus opciones.

## version_esquema

**En resumen:** Identifica el formato de `stack.yaml`; déjalo como viene en el `stack.yaml` de ejemplo (`1`).

**Dónde se ve en tu proyecto:** Solo aparece en `stack.yaml`, por ejemplo `version_esquema: 1`. No es la versión de tu aplicación. El validador exige que exista la clave; cambiar el número no convierte un archivo de otro formato.

**Respaldo:** `scripts/stack.mjs`.

## proyecto.nombre

**En resumen:** Da una etiqueta reconocible a tu proyecto, por ejemplo `pedidos-web`.

**Dónde se ve en tu proyecto:** En `stack.yaml`, por ejemplo `nombre: pedidos-web`. Es una etiqueta para reconocer tu proyecto, no una orden para renombrar carpetas, paquetes o servicios.

**Para qué se usa:**
- El validador exige que exista la clave al revisar la configuración.
- Permite identificar el proyecto al leer su configuración; el nombre del código se decide en sus archivos.

**Qué pasa si está mal:** Si falta, el validador impide continuar. Una etiqueta equivocada puede confundirte al revisar la configuración, aunque no renombre tu aplicación.

**Cambiarla después:** Edita `stack.yaml`; no requiere regenerar ni ejecutar otra tarea por esta etiqueta.

**Si conservas el dato confirmado (por ejemplo, `pedidos-web`):** Por ejemplo, reconoces este proyecto como `pedidos-web` cuando revisas `stack.yaml`. Recomendado: un nombre que identifique el proyecto que ya tienes; confirma el detectado antes de usarlo.

**Respaldo:** `scripts/stack.mjs`.

## proyecto.stack

**En resumen:** Identifica el tipo de proyecto al que pertenece este `.agents`; conserva `nextjs`.

**Dónde se ve en tu proyecto:** En `stack.yaml`, por ejemplo `stack: nextjs`. El generador elige sus plantillas con este dato y el validador rechaza otro tipo de proyecto. Cambiarlo no transforma la tecnología del código existente.

**Respaldo:** `actualizar.py`; `scripts/stack.mjs`.

## frontend.llamadas_api

**En resumen:** Decide si la API recibe las peticiones del navegador o del servidor del front.

**Dónde se ve en tu proyecto:** En `utils/apiClient.ts`, por ejemplo `NEXT_PUBLIC_API_BASE_URL` configura la URL pública de la API para el navegador; `API_BASE_URL` se utiliza solo en el servidor.

**Para qué se usa:**
- Selecciona las plantillas del núcleo y, con Clerk, dónde se obtiene el token que identifica al usuario.
- Si difiere `frontend.llamadas_api` del código, la tarea te ofrece corregir el origen de las llamadas a la API en su plan, conservar la diferencia o dejarla para revisión.

**Qué pasa si está mal:** Si el código usa otra opción, las variables o el token pueden quedar donde no corresponden. Con llamadas del navegador, una API que no admite su origen mediante CORS bloqueará las peticiones.

**Cambiarla después:** Edita `stack.yaml` y regenera. Para adaptar el núcleo usa la tarea `implement-feature` (propone cambios del front y espera tu aprobación). Sin núcleo, la tarea `bootstrap-project` (prepara los archivos base con un plan aprobado) aplica esta elección.

**Si conservas lo detectado en tu código (por ejemplo, `servidor`):** Por ejemplo, la pantalla de pedidos llama a funciones del servidor, Server Actions en `app/<ruta>/actions.ts`. `API_BASE_URL` y el token no llegan al navegador; vuelven solo datos simples, serializables. Sin código previo, la plantilla usa `navegador`. Recomendado: conserva dónde se ejecutan las llamadas existentes para no trasladar variables ni tokens.

**Si eliges `navegador`:** Por ejemplo, la pantalla de pedidos llama a la API desde el navegador. `NEXT_PUBLIC_API_BASE_URL` es pública y el token de Clerk se obtiene en el cliente. Conviene si empiezas sin núcleo: la plantilla usa `navegador` con URL pública y CORS; el servidor mantiene URL y token fuera del navegador.

**Respaldo:** `rules/architecture-rules.md`; `scripts/registro_detectores.py`; `workflows/bootstrap-project.md`.

## frontend.framework

**En resumen:** Identifica Next.js como la tecnología del front para la que están preparadas estas plantillas.

**Dónde se ve en tu proyecto:** Conserva `framework: nextjs` en `stack.yaml`. En tu aplicación se reconoce por la dependencia `next` de `package.json`; cambiar esta etiqueta no convierte otro tipo de aplicación ni selecciona nuevas plantillas.

**Respaldo:** `scripts/stack.mjs`.

## frontend.version

**En resumen:** Fija la versión exacta de Next.js que debe utilizar tu front.

**Dónde se ve en tu proyecto:** En `package.json`, por ejemplo `"next": "15.0.1"`; si esa es tu versión, declaras `15.0.1`. No es la versión de React ni de Node. `package-lock.json` puede indicar qué versión quedó instalada.

**Para qué se usa:**
- La comprobación previa exige una declaración literal de `next` igual a esta clave y contrasta su versión instalada cuando puede leerla de `package-lock.json`.
- La tarea de cambio prepara fuentes sobre las capacidades y compatibilidad de la versión de destino en Open Notebook, y comprueba sus citas.

**Qué pasa si está mal:** Un rango como `^15.0.1` o una versión distinta detiene la comprobación previa. Con `pnpm-lock.yaml` o `yarn.lock`, la comprobación automática no obtiene de ellos la versión instalada de Next.js: compara la declaración de `package.json`.

**Cambiarla después:** Edita `stack.yaml`, sin regenerar, y usa la tarea `change-version` (propone alinear Next.js, dependencias y documentación con un plan aprobado). Si ya declaraste el destino, lo toma como propuesta.

**Si declaras la versión detectada:** Por ejemplo, copias la versión literal de `next` que ya usa pedidos. Recomendado: conserva la versión de tu código si no buscas actualizar; evita un cambio de dependencias innecesario.

**Si declaras otra versión de destino:** Por ejemplo, pedidos pasa a una versión nueva mediante cambios en `package.json` y sus dependencias. Conviene si quieres actualizar sus capacidades y aprobar también la documentación y las pruebas de esa versión.

**Respaldo:** `scripts/comprobar-versiones.mjs`; `scripts/inventario-versiones.mjs`; `workflows/change-version.md`.

## frontend.gestor_paquetes

**En resumen:** Elige la herramienta con la que instalas y mantienes las dependencias del front.

**Dónde se ve en tu proyecto:** En el proyecto de ejemplo `pedidos-web`, `package-lock.json` corresponde a `npm`; `pnpm-lock.yaml`, a `pnpm`; y `yarn.lock`, a `yarn`. Fijan las versiones.

**Para qué se usa:**
- La comprobación previa compara esos archivos con el gestor declarado y elige cómo ejecutar ESLint, el programa de revisión de código, ya instalado.
- Sin uno de esos archivos informa que no se puede comprobar el gestor; si difiere `frontend.gestor_paquetes` del código, la tarea te ofrece corregir el gestor de paquetes en su plan, conservar la diferencia o dejarla para revisión.

**Qué pasa si está mal:** Otro valor distinto de `npm`, `pnpm` o `yarn` se detiene con `STACK_INVALIDO`: gestor no admitido. Declarar `pnpm` con `package-lock.json`, o tener dos lockfiles aunque uno coincida, produce diferencia. `HERRAMIENTA` significa ejecutable ausente; `DEPENDENCIAS`, ESLint no instalado.

**Cambiarla después:** Edita `stack.yaml`, sin regenerar, y pide la tarea `implement-feature` (propone cambios del front y espera tu aprobación). Cambiar de gestor es una migración, no un cambio de versión: por eso no corresponde a `change-version`. La misma tarea aprobada migra las dependencias y quita el archivo sobrante; instalar requiere tu permiso.

**Si conservas lo detectado en tu código (por ejemplo, `pnpm`):** Por ejemplo, usas `pnpm install`, mantienes `pnpm-lock.yaml` y revisas con `pnpm exec eslint`. Recomendado: conserva el gestor cuyo archivo de versiones ya existe para no migrar las dependencias sin necesidad.

**Si eliges `npm`:** Por ejemplo, usas `npm install`, mantienes `package-lock.json` y ejecutas `npx --no-install eslint` para revisar pedidos. Conviene si empiezas sin lockfile: la plantilla usa `npm` y genera `package-lock.json`.

**Si eliges `yarn`:** Por ejemplo, usas `yarn` para instalar, mantienes `yarn.lock` y revisas con `yarn eslint`. Yarn PnP resuelve dependencias mediante `.pnp.cjs`, sin la carpeta habitual `node_modules`. Conviene si has aprobado migrar a Yarn y mantener solo `yarn.lock`, con resolución PnP si la usas.

**Respaldo:** `scripts/preflight_stack.py`; `scripts/registro_detectores.py`; `workflows/references/decisiones-stack.md`.

## frontend.eslint_config

**En resumen:** Indica el archivo de reglas que utiliza ESLint para revisar tu código.

**Dónde se ve en tu proyecto:** En `eslint.agent.config.mjs`, la ruta propuesta por la plantilla, o en otra ruta relativa a la raíz que acuerdes; por ejemplo, el comando de revisión usa `eslint -c eslint.agent.config.mjs`.

**Para qué se usa:**
- La preparación del proyecto copia allí la configuración de la plantilla si falta; no sobrescribe una existente.
- La comprobación previa y la revisión usan ese archivo. Una prueba de control es un pequeño archivo con un error deliberado: se comprueba que ESLint detecte `eval`, que ejecuta texto como código.

**Qué pasa si está mal:** Si falta el archivo, la comprobación previa se detiene con `PREPARACION`: falta completar la preparación del proyecto; propone `bash .agents/scripts/preparar-proyecto.sh`. Si ESLint no detecta el error deliberado de la prueba de control, tampoco da la revisión por válida.

**Cambiarla después:** Edita `stack.yaml`, sin regenerar. Si falta el archivo, la preparación del proyecto puede crearlo con tu autorización. Para cambiar reglas de uno existente pide la tarea `implement-feature` (propone cambios del front y espera tu aprobación).

**Si conservas la ruta detectada (`eslint.revision.config.mjs`):** Por ejemplo, las revisiones de pedidos leen tu configuración en esa ruta. Recomendado: conserva esta ruta si es la detectada y contiene las reglas necesarias.

**Si eliges `eslint.agent.config.mjs`:** Por ejemplo, las revisiones de pedidos leen las reglas de ese archivo. Conviene si no tienes configuración previa: es la ruta de la plantilla.

**Respaldo:** `scripts/preparar-proyecto.sh`; `scripts/preflight_stack.py`; `scripts/lint-touched.sh`.

## frontend.notificaciones

**En resumen:** Decide cómo aparecen mensajes como «Pedido guardado» en tu interfaz.

**Dónde se ve en tu proyecto:** En `utils/Notificador.ts`, por ejemplo `toast.success("Pedido guardado")` con `react-toastify`. Esa opción usa `<ToastContainer>` en el layout, normalmente `app/layout.tsx`, y la dependencia en `package.json`.

**Para qué se usa:**
- Selecciona la plantilla del adaptador, el archivo que entrega el mensaje a la forma de mostrarlo elegida.
- Si difiere `frontend.notificaciones` del código, la tarea te ofrece corregir notificaciones en su plan, conservar la diferencia o dejarla para revisión.

**Qué pasa si está mal:** Sin instalar `react-toastify` o sin integrar `<ToastContainer>`, sus mensajes pueden fallar. Con `ninguna`, quitar la dependencia no conecta por sí solo tu propio aviso.

**Cambiarla después:** Edita `stack.yaml` y regenera. Usa la tarea `implement-feature` (propone cambios del front y espera tu aprobación) para adaptar `utils/Notificador.ts` y su integración con la pantalla. Sin núcleo, la tarea `bootstrap-project` (prepara los archivos base con un plan aprobado) lo incorpora. Las instalaciones requieren tu permiso.

**Si conservas lo detectado en tu código (por ejemplo, `react-toastify`):** Por ejemplo, «Pedido guardado» aparece como un aviso flotante de Toastify y el layout incorpora `<ToastContainer>`. Sin código previo, la plantilla usa `react-toastify`. Recomendado: conserva la librería de avisos instalada para mantener el adaptador y evitar cambiar la interfaz.

**Si eliges `ninguna`:** Por ejemplo, «Pedido guardado» aparece en el área de alertas de tu pantalla: conectas su función de mostrar mensajes en `utils/Notificador.ts`. Conviene si preparas un núcleo nuevo: la plantilla usa `react-toastify`; `ninguna` exige completar el adaptador propio.

**Respaldo:** `config/opciones.yaml`; `scripts/registro_detectores.py`; `skills/api-integration-architect/assets/templates/core/Notificador.template.ts`.

## sonarqube.url

**En resumen:** Indica la dirección de SonarQube donde la comprobación previa verifica si el análisis está disponible.

**Dónde se ve en tu proyecto:** En `stack.yaml`, por ejemplo `url: https://calidad.example.invalid`. Es la dirección de tu servidor de análisis, no la de la aplicación ni una credencial.

**Para qué se usa:**
- La comprobación previa consulta si ese servidor está listo para analizar.
- La variable de entorno `SONARQUBE_URL`, si existe, tiene prioridad para esta comprobación; la conexión MCP del análisis se configura por separado.

**Qué pasa si está mal:** Una dirección incorrecta o un servidor que no esté listo puede impedir continuar según la tarea. La dirección no debe llevar usuario, contraseña ni token.

**Cambiarla después:** Edita `stack.yaml`, sin regenerar. Si defines `SONARQUBE_URL`, cambiar solo esta clave no cambia la dirección consultada.

**Si conservas el dato confirmado (por ejemplo, `https://calidad.example.invalid`):** Por ejemplo, la comprobación previa consulta esa instalación antes de revisar pedidos. Recomendado: usa la dirección confirmada por quien mantiene tu SonarQube, porque una dirección de ejemplo no demuestra dónde está tu servidor.

**Respaldo:** `scripts/preflight_stack.py`; `scripts/stack.mjs`.

## sonarqube.project_key

**En resumen:** Identifica el proyecto del front que se analiza en SonarQube.

**Dónde se ve en tu proyecto:** En `stack.yaml`, por ejemplo `project_key: pedidos-web`; corresponde a `sonar.projectKey=pedidos-web` en `sonar-project.properties`. Es el identificador, no necesariamente el título visible.

**Para qué se usa:**
- El análisis busca esa clave entre los proyectos del servidor para aplicar el contexto del front.
- Su prueba de control analiza un archivo pequeño con un defecto conocido: comprueba que la herramienta lo detecta y exige un proyecto existente con esa clave.

**Qué pasa si está mal:** Si no existe el proyecto, el análisis de archivos puede omitir su identificador e informar que falta una evaluación del proyecto completo. La prueba de control no puede validarse con una clave desconocida.

**Cambiarla después:** Edita `stack.yaml`, sin regenerar. Pide la tarea `implement-feature` (propone cambios del front y espera tu aprobación) para alinear `sonar-project.properties`; crear un proyecto en el servidor requiere tu aprobación aparte.

**Si conservas el dato confirmado (por ejemplo, `pedidos-web`):** Por ejemplo, el análisis de pedidos utiliza el proyecto registrado con esa clave. Recomendado: usa tu identificador confirmado en el servidor, porque compartir un título visible no garantiza que sea el mismo proyecto.

**Respaldo:** `scripts/sonar-diff-gate.mjs`; `workflows/bootstrap-project.md`; `workflows/implement-feature.md`.

## mcp.sonarqube

**En resumen:** Nombra la entrada del servidor que `sonar-mcp.mjs` y el gate buscan para conectar con SonarQube.

**Dónde se ve en tu proyecto:** En `stack.yaml`, por ejemplo `sonarqube: analisis`. MCP permite que el agente use herramientas externas; `analisis` es el nombre público con el que registraste ese servidor, no una URL ni un token.

**Para qué se usa:**
- Con las tres variables `SONARQUBE_MCP_JAR`, `SONARQUBE_URL` y `SONARQUBE_TOKEN`, el análisis usa esa conexión antes que la registrada en la herramienta.
- Si no están las tres, `SONARQUBE_MCP_CONFIG` permite buscar primero en un archivo indicado por ti; ahí se selecciona la entrada con el nombre de esta clave. Después se busca en la configuración habitual de la herramienta.
- Puedes desactivar ese MCP en tu herramienta mientras su entrada siga legible para el resolvedor, o usar las tres variables anteriores. Conviene desactivarlo para no compartir almacenamiento entre dos servidores a la vez. Borrar o comentar la entrada, usar `.jsonc` con comentarios o una configuración que el resolvedor no lea puede impedir encontrarla. No compartas ni leas sus valores privados.

**Qué pasa si está mal:** Si ninguna de esas vías proporciona una conexión válida, el análisis se detiene. Con un archivo indicado por `SONARQUBE_MCP_CONFIG`, un nombre incorrecto no encuentra su entrada.

**Cambiarla después:** Edita `stack.yaml` con el nombre que tú confirmes; se lee al analizar, sin regenerar. Configura la conexión fuera del proyecto sin compartir sus archivos privados.

**Si conservas el dato confirmado (por ejemplo, `analisis`):** Por ejemplo, el análisis de pedidos busca el servidor que registraste como `analisis`. Recomendado: exactamente tu nombre registrado; no copies el de otra instalación aunque use también SonarQube.

**Respaldo:** `scripts/sonar-mcp.mjs`; `scripts/sonar-diff-gate.mjs`; `skills/code-reviewer/references/sonarqube-gate.md`; `scripts/stack.mjs`.

## integraciones.gestion_usuarios

**En resumen:** Decide si preparas gestión de perfiles y si cada persona pertenece a una organización.

**Dónde se ve en tu proyecto:** En `app/perfiles/page.tsx` y el formulario de perfiles; por ejemplo, un administrador ve el selector de organización solo con ese modelo.

**Para qué se usa:**
- Selecciona las plantillas y la tarea del modelo elegido.
- Si difiere `integraciones.gestion_usuarios` del código, la tarea te ofrece corregir gestion usuarios en su plan, conservar la diferencia o dejarla para revisión.
- El registro de Clerk admite solo invitados; el pre-registro crea un perfil local pendiente. Marcarlo `INACTIVO` no revoca sus sesiones.

**Qué pasa si está mal:** Un modelo distinto del contrato hace que el formulario pida datos que la API no admite. Gestión activa exige `integraciones.autenticacion: clerk` y los nombres de variables necesarios.

**Cambiarla después:** Edita `stack.yaml` y regenera. Usa la tarea `add-user-management` (prepara perfiles con un plan aprobado). Lleva el contrato en orden base (proyecto SQL) → back → front. Elegir `ninguna` no borra código ni datos. Retirarlo exige la tarea `implement-feature` (propone cambios del front y espera tu aprobación).

**Si conservas lo detectado en tu código (por ejemplo, `organizaciones`):** Por ejemplo, el administrador selecciona la organización del perfil y la invitación se dirige a esa organización de Clerk. Clerk debe restringir el registro a invitados; sin roles, cualquier usuario con sesión puede administrar. Sin código previo, la plantilla usa `ninguna`. Recomendado: conserva el modelo del contrato instalado para que SQL, API y pantallas sigan intercambiando los mismos datos.

**Si eliges `ninguna`:** Por ejemplo, pedidos no incorpora pantallas para administrar perfiles. Conviene si no hay módulo previo: `ninguna` es la plantilla; elige `organizaciones` para perfiles asociados o `aplicacion` para una lista común.

**Si eliges `aplicacion`:** Por ejemplo, el administrador invita a pedidos sin seleccionar organización. Clerk debe restringir el registro a invitados; sin roles, cualquier usuario con sesión puede administrar. Conviene si no hay módulo previo: `ninguna` es la plantilla; elige `organizaciones` para perfiles asociados o `aplicacion` para una lista común.

**Respaldo:** `config/opciones.yaml`; `workflows/add-user-management.md`; `scripts/registro_detectores.py`.

## integraciones.autenticacion

**En resumen:** Decide si el proyecto comprueba la identidad de sus usuarios con Clerk.

**Dónde se ve en tu proyecto:** En `app/layout.tsx`, por ejemplo `<ClerkProvider>`, y en el código que obtiene el token para llamar a la API.

**Para qué se usa:**
- Selecciona las plantillas de autenticación y la obtención o validación del token según este stack.
- Si difiere `integraciones.autenticacion` del código, la tarea te ofrece corregir autenticacion en su plan, conservar la diferencia o dejarla para revisión.

**Qué pasa si está mal:** Con Clerk faltan datos si no has declarado su configuración. Sin Clerk no puedes activar gestión de usuarios en este stack. La autenticación no añade permisos por roles.

**Cambiarla después:** Edita `stack.yaml` y regenera. Al activar Clerk añade las claves que pida el generador y usa la tarea `add-authentication` (propone la integración con un plan aprobado). Al retirarlo, quita las claves sin uso y pide la tarea `implement-feature` (te enseña un plan de cambios del front y espera tu sí).

**Si conservas lo detectado en tu código (por ejemplo, `clerk`):** Por ejemplo, una persona inicia sesión con Clerk antes de usar pedidos. Sin código previo, la plantilla usa `clerk`. Recomendado: conserva el proveedor instalado para no cambiar el inicio de sesión ni el contrato de identidad.

**Si eliges `ninguna`:** Por ejemplo, pedidos permite el acceso sin integrar Clerk. Conviene si has acordado ese proveedor para el código nuevo; la plantilla usa `clerk`, mientras `ninguna` omite esa integración.

**Respaldo:** `config/opciones.yaml`; `config/requisitos.yaml`; `workflows/add-authentication.md`; `scripts/registro_detectores.py`; `scripts/stack.mjs`.

<!-- si integraciones.autenticacion=clerk -->
## integraciones.variables_autenticacion

**En resumen:** Enumera nombres de variables de entorno de autenticación, nunca sus valores.

**Dónde se ve en tu proyecto:** En `stack.yaml`, por ejemplo `[CLERK_SECRET_KEY]`. Es el nombre que necesita la integración de pedidos: el valor se configura fuera de este archivo.

**Para qué se usa:**
- El generador informa los nombres y si están definidos en su terminal, sin mostrar el contenido.
- La tarea que prepara la integración usa los nombres declarados; una lista no crea ni configura las credenciales.
- Los nombres deben comenzar por letra mayúscula, seguir con mayúsculas, cifras o guiones bajos y tener como máximo `64` caracteres; se rechazan textos que parezcan credenciales.

**Qué pasa si está mal:** Un token escrito en lugar de su nombre es un error. El validador rechaza nombres no permitidos; una lista incompleta puede dejar la integración sin las variables que necesita. Solo se usa con `integraciones.autenticacion: clerk`.

**Cambiarla después:** Edita `stack.yaml`; no requiere regenerar por esta lista. Para adaptar la integración usa la tarea `add-authentication` (propone autenticación con un plan aprobado) o la tarea `implement-feature` (te enseña un plan de cambios del front y espera tu sí). Si su condición no se cumple, quítala; al activar la opción vuelve a añadirla cuando el generador la pida.

**Si conservas el dato confirmado (por ejemplo, `[CLERK_SECRET_KEY]`):** Por ejemplo, declaras únicamente ese nombre si es el que necesita tu integración de pedidos. Recomendado: los nombres que consume tu proyecto, sin copiar valores ni una lista ajena.

**Respaldo:** `actualizar.py`; `scripts/stack.mjs`; `workflows/`.

<!-- fin -->
## herramientas.codebase_memory

**En resumen:** Decide si el agente usa Codebase Memory para relacionar archivos y símbolos del código mediante su CLI.

**Dónde se ve en tu proyecto:** Se declara en `stack.yaml`. El índice vive en la caché local de CBM, no en el repositorio; cada máquina lo crea una vez. `.cbmignore` acompaña a `.agents/` y excluye `knowledge-base/` y `.agents/`.

**Para qué se usa:**
- El preflight comprueba la CLI `codebase-memory-mcp` y el índice real del proyecto; si el índice existe, lo reindexa en la entrada para incorporar los cambios. En el cierre solo comprueba su estado.
- Las consultas del código y sus actualizaciones se condicionan a esta clave. Las decisiones documentadas en `knowledge-base/` se consultan con `tgrep`.

**Qué pasa si está mal:** Si falta la CLI, informa `HERRAMIENTA`; si falta el proyecto o el índice no está listo, informa `GRAFO`. Un índice vacío, degradado al indexar o que no se pudo actualizar produce `GRAFO_AVISO`. El tratamiento depende del workflow según el catálogo de códigos. La falta de preparación de `.cbmignore` se informa como `PREPARACION`. Desactivar la clave omite el grafo y conserva los demás controles.

**Cambiarla después:** Edita `stack.yaml`; esta clave no requiere regenerar. Al activarla, usa la tarea `codebase-memory` para indexar el proyecto antes de `preparar-documentacion`. La clave antigua `herramientas.graphify` sigue aceptándose como alias cuando falta la nueva; si existen ambas, gana `herramientas.codebase_memory`. Renombra la antigua para retirar el aviso de validación.

**Si conservas lo detectado en tu código (por ejemplo, `false`):** Trabajas en pedidos sin preparar el índice. Mantén la decisión y las herramientas del proyecto; activar el grafo añade su preparación y sus controles.

**Si eliges `true`:** Consultas las relaciones del código de pedidos en el índice local. La plantilla de este stack lo activa al empezar. Las dependencias y versiones se leen del inventario del proyecto y de `package-lock.json` (sin lock, la declaración literal). A diferencia del código Java, los notebooks SQL `.dbcnb` no quedan cubiertos por CBM; en el stack SQL se usa `db-index.py` y CBM es complementario.

**Respaldo:** `.agents/scripts/codebase-memory.py`; `.agents/scripts/preflight.py`; `.agents/rules/codebase-memory.md`; `.agents/workflows/codebase-memory.md`; `.agents/scripts/stack.mjs`.

## git.rama_base

**En resumen:** Hoy la comprobación previa solo lee esta decisión: no la pasa al análisis; para comparar con otra rama debes indicar `--base`.

**Dónde se ve en tu proyecto:** En `stack.yaml`, por ejemplo `rama_base: development`, si creaste `feature/pedidos` desde esa rama. El análisis sin `--base` compara con el último commit de la rama actual.

**Para qué se usa:**
- Guarda la base de comparación que quieres usar y la comprobación previa puede leerla; no cambia automáticamente la selección de archivos.
- El programa que selecciona cambios admite `--base development` para comparar efectivamente con esa referencia.

**Qué pasa si está mal:** Cambiar solo esta clave no cambia la comparación. Si el comando recibe una rama inexistente, no puede seleccionar los cambios contra esa referencia.

**Cambiarla después:** Edita `stack.yaml`, sin regenerar. Para revisar otra base, el comando de análisis debe recibir también `--base`; la clave no se propaga por sí sola.

**Si eliges `null`:** Por ejemplo, el análisis sin `--base` revisa los cambios de pedidos que aún no están en un commit. Recomendado: encaja si dejas que el agente haga los cambios y tú haces el commit al final.

**Si eliges `development`:** Por ejemplo, declaras esa base para `feature/pedidos` y pasas `--base development` al análisis. Conviene si haces commits durante la tarea y necesitas comparar también esos cambios con una rama conocida.

**Respaldo:** `scripts/preflight.py`; `scripts/touched-files.sh`.

## api_error.campo_mensaje

**En resumen:** Nombra el campo que lleva el texto del error que verá la persona usuaria.

**Dónde se ve en tu proyecto:** En `utils/HandleAxiosError.ts`, por ejemplo `const API_MESSAGE_FIELD: string = "message";`, cuando tu API devuelve `{"message":"Pedido no encontrado"}`.

**Para qué se usa:**
- El front lee ese campo cuando recibe un error HTTP; si no contiene texto válido, muestra su mensaje genérico.
- Si difiere `api_error.campo_mensaje` del código, la tarea te ofrece corregir el campo del mensaje en su plan, conservar la diferencia o dejarla para revisión.

**Qué pasa si está mal:** Si falta o está vacío, el validador se detiene. Si el back envía `message` y el front busca `detalle`, la interfaz puede mostrar un mensaje genérico en lugar de «Pedido no encontrado».

**Cambiarla después:** Edita `stack.yaml`; no requiere regenerar. Para llevar el contrato al código existente, usa la tarea `implement-feature` (te enseña un plan de cambios del front y espera tu sí). Si aún no hay manejador de errores, acuerda el contrato desde ahora; no se instala solo por declarar esta clave.

**Si conservas lo detectado en tu código (por ejemplo, `detalle`):** Por ejemplo, `{"detalle":"Pedido no encontrado"}` usa `detalle`. Recomendado: conserva el campo que ya comparte tu contrato; cambiarlo exige adaptar la respuesta y su lectura.

**Si eliges `message`:** Por ejemplo, el texto de `{"message":"Pedido no encontrado"}` se lee en `message`. Conviene si aún no hay contrato de errores: la plantilla propone `message`.

**Respaldo:** `scripts/stack.mjs`; `scripts/registro_detectores.py`; `skills/api-integration-architect/assets/templates/core/HandleAxiosError.template.ts`.

## api_error.campo_codigo

**En resumen:** Nombra el campo opcional que identifica un error de negocio, además de su mensaje.

**Dónde se ve en tu proyecto:** En `utils/HandleAxiosError.ts`, por ejemplo `API_CODE_FIELD = "code"`; con `null` no intenta leer ese campo.

**Para qué se usa:**
- El back decide el código; el front puede usarlo para reaccionar de forma distinta sin comparar el texto del mensaje.
- Si difiere `api_error.campo_codigo` del código, la tarea te ofrece corregir el campo del código en su plan, conservar la diferencia o dejarla para revisión.

**Qué pasa si está mal:** Si el campo no coincide con el que envía el back, el front pierde ese código. El validador admite `null` o texto no vacío.

**Cambiarla después:** Edita `stack.yaml`, sin regenerar. Para adaptarlo en el código existente usa la tarea `implement-feature` (propone cambios del front y espera tu aprobación). Acuerda el mismo contrato con el back.

**Ejemplo del cuerpo de error:** Si los campos acordados son `message` y `code`, una respuesta puede ser `{"status":404,"message":"El cliente no existe","code":"CLIENTE_NO_ENCONTRADO"}`. Con `campo_codigo: null` sería `{"status":404,"message":"El cliente no existe"}`. `status` es el estado HTTP; el código permite distinguir el caso sin comparar el texto. Los nombres de mensaje y código salen de tu contrato.

**Si conservas lo detectado en tu código (por ejemplo, `code`):** Por ejemplo, el front recibe `"code":"PEDIDO_NO_ENCONTRADO"` y puede distinguir ese caso. Recomendado: conserva el contrato detectado, incluido `null` si no publica ese campo, para no romper a quien recibe los errores.

**Si eliges `null`:** Por ejemplo, el error del pedido solo se trata por su mensaje y estado HTTP. Conviene si la API no publica código de negocio; `null` es el inicio de la plantilla.

**Respaldo:** `scripts/stack.mjs`; `scripts/registro_detectores.py`; `skills/api-integration-architect/assets/templates/core/HandleAxiosError.template.ts`.

## nomenclatura.controlador_interfaz

**En resumen:** Da el patrón de nombre para la interfaz del controlador.

**Dónde se ve en tu proyecto:** Con el patrón `{Entidad}ControllerInterface`, por ejemplo, aparece `controllers/PedidoControllerInterface.ts` y la declaración `export interface PedidoControllerInterface`. La interfaz enumera las operaciones que la pantalla puede pedir al controlador; describe lo que ofrece sin implementar el trabajo.

**Para qué se usa:**
- El generador escribe este patrón en las instrucciones de arquitectura; el agente lo aplica al proponer código nuevo.
- Si difiere `nomenclatura.controlador_interfaz` del código, la tarea te ofrece corregir el patrón de interfaz del controlador en su plan, conservar la diferencia o dejarla para revisión.
- La comparación admite los patrones de interfaz e implementación de esa misma carpeta; excluye `index.ts` y los archivos `.d.ts`.
- La plantilla llama a la interfaz del controlador `{Entidad}ControllerInterface`, pero a la del servicio `{Entidad}Service` y a su implementación `{Entidad}ServiceImpl`; son convenciones distintas de la misma plantilla.
- La propuesta de perfiles sustituye este patrón en archivos, declaraciones e imports antes de entregarla; no renombra automáticamente lo que ya existe.

**Qué pasa si está mal:** Si falta `{Entidad}`, el validador se detiene. Si cambias el patrón sin regenerar, la comprobación previa exige regenerar antes de continuar.

**Cambiarla después:** Edita `stack.yaml` y regenera. Para renombrar código existente, pide la tarea `implement-feature` (te enseña un plan de cambios del front y espera tu sí); el plan aprobado debe contemplar archivos e imports. Regenerar solo actualiza instrucciones.

**Si conservas lo detectado en tu código (por ejemplo, `{Entidad}ControllerInterface`):** Por ejemplo, pedidos usa `PedidoControllerInterface.ts`. Sin código previo, la plantilla usa `{Entidad}ControllerInterface`. Recomendado: mantén el patrón detectado de tus archivos para evitar renombrar código existente.

**Si eliges `{Entidad}ContratoControlador`:** Por ejemplo, pedidos usa `PedidoContratoControlador.ts`. Conviene si quieres cambiar a esta convención, con los nombres concretos del ejemplo y sus referencias en el plan aprobado.

**Respaldo:** `scripts/stack.mjs`; `scripts/preflight.py`; `scripts/registro_detectores.py`; `rules/architecture-rules.md`; `skills/api-integration-architect/SKILL.md`.

## nomenclatura.controlador_implementacion

**En resumen:** Da el patrón de nombre para la clase del controlador.

**Dónde se ve en tu proyecto:** Con el patrón `{Entidad}Controller`, por ejemplo, aparece `controllers/PedidoController.ts` y la declaración `export class PedidoController`. El controlador recibe las acciones de la pantalla, coordina la llamada al servicio y entrega su resultado.

**Para qué se usa:**
- El generador escribe este patrón en las instrucciones de arquitectura; el agente lo aplica al proponer código nuevo.
- Si difiere `nomenclatura.controlador_implementacion` del código, la tarea te ofrece corregir el patrón de implementación del controlador en su plan, conservar la diferencia o dejarla para revisión.
- La comparación admite los patrones de interfaz e implementación de esa misma carpeta; excluye `index.ts` y los archivos `.d.ts`.
- La propuesta de perfiles sustituye este patrón en archivos, declaraciones e imports antes de entregarla; no renombra automáticamente lo que ya existe.

**Qué pasa si está mal:** Si falta `{Entidad}`, el validador se detiene. Si cambias el patrón sin regenerar, la comprobación previa exige regenerar antes de continuar.

**Cambiarla después:** Edita `stack.yaml` y regenera. Para renombrar código existente, pide la tarea `implement-feature` (te enseña un plan de cambios del front y espera tu sí); el plan aprobado debe contemplar archivos e imports. Regenerar solo actualiza instrucciones.

**Si conservas lo detectado en tu código (por ejemplo, `{Entidad}Controller`):** Por ejemplo, pedidos usa `PedidoController.ts`. Sin código previo, la plantilla usa `{Entidad}Controller`. Recomendado: mantén el patrón detectado de tus archivos para evitar renombrar código existente.

**Si eliges `{Entidad}Controlador`:** Por ejemplo, pedidos usa `PedidoControlador.ts`. Conviene si quieres cambiar a esta convención, con los nombres concretos del ejemplo y sus referencias en el plan aprobado.

**Respaldo:** `scripts/stack.mjs`; `scripts/preflight.py`; `scripts/registro_detectores.py`; `rules/architecture-rules.md`; `skills/api-integration-architect/SKILL.md`.

## nomenclatura.servicio_interfaz

**En resumen:** Da el patrón de nombre para la interfaz del servicio.

**Dónde se ve en tu proyecto:** Con el patrón `{Entidad}Service`, por ejemplo, aparece `services/PedidoService.ts` y la declaración `export interface PedidoService`. La interfaz declara las operaciones de negocio que necesita el controlador, separadas de la clase que las realiza.

**Para qué se usa:**
- El generador escribe este patrón en las instrucciones de arquitectura; el agente lo aplica al proponer código nuevo.
- Si difiere `nomenclatura.servicio_interfaz` del código, la tarea te ofrece corregir el patrón de interfaz del servicio en su plan, conservar la diferencia o dejarla para revisión.
- La comparación admite los patrones de interfaz e implementación de esa misma carpeta; excluye `index.ts` y los archivos `.d.ts`.
- La propuesta de perfiles sustituye este patrón en archivos, declaraciones e imports antes de entregarla; no renombra automáticamente lo que ya existe.

**Qué pasa si está mal:** Si falta `{Entidad}`, el validador se detiene. Si cambias el patrón sin regenerar, la comprobación previa exige regenerar antes de continuar.

**Cambiarla después:** Edita `stack.yaml` y regenera. Para renombrar código existente, pide la tarea `implement-feature` (te enseña un plan de cambios del front y espera tu sí); el plan aprobado debe contemplar archivos e imports. Regenerar solo actualiza instrucciones.

**Si conservas lo detectado en tu código (por ejemplo, `{Entidad}Service`):** Por ejemplo, pedidos usa `PedidoService.ts`. Sin código previo, la plantilla usa `{Entidad}Service`. Recomendado: mantén el patrón detectado de tus archivos para evitar renombrar código existente.

**Si eliges `{Entidad}ContratoServicio`:** Por ejemplo, pedidos usa `PedidoContratoServicio.ts`. Conviene si quieres cambiar a esta convención, con los nombres concretos del ejemplo y sus referencias en el plan aprobado.

**Respaldo:** `scripts/stack.mjs`; `scripts/preflight.py`; `scripts/registro_detectores.py`; `rules/architecture-rules.md`; `skills/api-integration-architect/SKILL.md`.

## nomenclatura.servicio_implementacion

**En resumen:** Da el patrón de nombre para la clase del servicio.

**Dónde se ve en tu proyecto:** Con el patrón `{Entidad}ServiceImpl`, por ejemplo, aparece `services/PedidoServiceImpl.ts` y la declaración `export class PedidoServiceImpl`. La clase del servicio aplica la lógica de negocio y transforma los datos que obtiene del repositorio.

**Para qué se usa:**
- El generador escribe este patrón en las instrucciones de arquitectura; el agente lo aplica al proponer código nuevo.
- Si difiere `nomenclatura.servicio_implementacion` del código, la tarea te ofrece corregir el patrón de implementación del servicio en su plan, conservar la diferencia o dejarla para revisión.
- La comparación admite los patrones de interfaz e implementación de esa misma carpeta; excluye `index.ts` y los archivos `.d.ts`.
- La propuesta de perfiles sustituye este patrón en archivos, declaraciones e imports antes de entregarla; no renombra automáticamente lo que ya existe.

**Qué pasa si está mal:** Si falta `{Entidad}`, el validador se detiene. Si cambias el patrón sin regenerar, la comprobación previa exige regenerar antes de continuar.

**Cambiarla después:** Edita `stack.yaml` y regenera. Para renombrar código existente, pide la tarea `implement-feature` (te enseña un plan de cambios del front y espera tu sí); el plan aprobado debe contemplar archivos e imports. Regenerar solo actualiza instrucciones.

**Si conservas lo detectado en tu código (por ejemplo, `{Entidad}ServiceImpl`):** Por ejemplo, pedidos usa `PedidoServiceImpl.ts`. Sin código previo, la plantilla usa `{Entidad}ServiceImpl`. Recomendado: mantén el patrón detectado de tus archivos para evitar renombrar código existente.

**Si eliges `{Entidad}Servicio`:** Por ejemplo, pedidos usa `PedidoServicio.ts`. Conviene si quieres cambiar a esta convención, con los nombres concretos del ejemplo y sus referencias en el plan aprobado.

**Respaldo:** `scripts/stack.mjs`; `scripts/preflight.py`; `scripts/registro_detectores.py`; `rules/architecture-rules.md`; `skills/api-integration-architect/SKILL.md`.

## nomenclatura.repositorio_interfaz

**En resumen:** Da el patrón de nombre para la interfaz del repositorio API.

**Dónde se ve en tu proyecto:** Con el patrón `{Entidad}ApiRepository`, por ejemplo, aparece `repository/PedidoApiRepository.ts` y la declaración `export interface PedidoApiRepository`. La interfaz declara qué operaciones de acceso a la API puede usar el servicio, separadas de su implementación.

**Para qué se usa:**
- El generador escribe este patrón en las instrucciones de arquitectura; el agente lo aplica al proponer código nuevo.
- Si difiere `nomenclatura.repositorio_interfaz` del código, la tarea te ofrece corregir el patrón de interfaz del repositorio en su plan, conservar la diferencia o dejarla para revisión.
- La comparación admite los patrones de interfaz e implementación de esa misma carpeta; excluye `index.ts` y los archivos `.d.ts`.
- La propuesta de perfiles sustituye este patrón en archivos, declaraciones e imports antes de entregarla; no renombra automáticamente lo que ya existe.

**Qué pasa si está mal:** Si falta `{Entidad}`, el validador se detiene. Si cambias el patrón sin regenerar, la comprobación previa exige regenerar antes de continuar.

**Cambiarla después:** Edita `stack.yaml` y regenera. Para renombrar código existente, pide la tarea `implement-feature` (te enseña un plan de cambios del front y espera tu sí); el plan aprobado debe contemplar archivos e imports. Regenerar solo actualiza instrucciones.

**Si conservas lo detectado en tu código (por ejemplo, `{Entidad}ApiRepository`):** Por ejemplo, pedidos usa `PedidoApiRepository.ts`. Sin código previo, la plantilla usa `{Entidad}ApiRepository`. Recomendado: mantén el patrón detectado de tus archivos para evitar renombrar código existente.

**Si eliges `{Entidad}ContratoRepositorio`:** Por ejemplo, pedidos usa `PedidoContratoRepositorio.ts`. Conviene si quieres cambiar a esta convención, con los nombres concretos del ejemplo y sus referencias en el plan aprobado.

**Respaldo:** `scripts/stack.mjs`; `scripts/preflight.py`; `scripts/registro_detectores.py`; `rules/architecture-rules.md`; `skills/api-integration-architect/SKILL.md`.

## nomenclatura.repositorio_implementacion

**En resumen:** Da el patrón de nombre para la clase del repositorio API.

**Dónde se ve en tu proyecto:** Con el patrón `{Entidad}ApiRepositoryImpl`, por ejemplo, aparece `repository/PedidoApiRepositoryImpl.ts` y la declaración `export class PedidoApiRepositoryImpl`. La clase del repositorio concentra las peticiones HTTP a la API que necesita el servicio.

**Para qué se usa:**
- El generador escribe este patrón en las instrucciones de arquitectura; el agente lo aplica al proponer código nuevo.
- Si difiere `nomenclatura.repositorio_implementacion` del código, la tarea te ofrece corregir el patrón de implementación del repositorio en su plan, conservar la diferencia o dejarla para revisión.
- La comparación admite los patrones de interfaz e implementación de esa misma carpeta; excluye `index.ts` y los archivos `.d.ts`.
- La propuesta de perfiles sustituye este patrón en archivos, declaraciones e imports antes de entregarla; no renombra automáticamente lo que ya existe.

**Qué pasa si está mal:** Si falta `{Entidad}`, el validador se detiene. Si cambias el patrón sin regenerar, la comprobación previa exige regenerar antes de continuar.

**Cambiarla después:** Edita `stack.yaml` y regenera. Para renombrar código existente, pide la tarea `implement-feature` (te enseña un plan de cambios del front y espera tu sí); el plan aprobado debe contemplar archivos e imports. Regenerar solo actualiza instrucciones.

**Si conservas lo detectado en tu código (por ejemplo, `{Entidad}ApiRepositoryImpl`):** Por ejemplo, pedidos usa `PedidoApiRepositoryImpl.ts`. Sin código previo, la plantilla usa `{Entidad}ApiRepositoryImpl`. Recomendado: mantén el patrón detectado de tus archivos para evitar renombrar código existente.

**Si eliges `{Entidad}RepositorioApi`:** Por ejemplo, pedidos usa `PedidoRepositorioApi.ts`. Conviene si quieres cambiar a esta convención, con los nombres concretos del ejemplo y sus referencias en el plan aprobado.

**Respaldo:** `scripts/stack.mjs`; `scripts/preflight.py`; `scripts/registro_detectores.py`; `rules/architecture-rules.md`; `skills/api-integration-architect/SKILL.md`.

## nomenclatura.modelo

**En resumen:** Da el patrón de nombre para los modelos de datos.

**Dónde se ve en tu proyecto:** Con el patrón `{Entidad}Model`, por ejemplo, aparece `domains/models/PedidoModel.ts` y la declaración `export interface PedidoModel`. Un modelo describe los datos con los que trabaja la interfaz; por ejemplo, las propiedades de un pedido.

**Para qué se usa:**
- El generador escribe este patrón en las instrucciones de arquitectura; el agente lo aplica al proponer código nuevo.
- Si difiere `nomenclatura.modelo` del código, la tarea te ofrece corregir modelo en su plan, conservar la diferencia o dejarla para revisión.
- La comprobación previa revisa los nombres y omite `index.ts` y `.d.ts`; las declaraciones e imports se adaptan dentro de la tarea que apruebas.
- La propuesta de perfiles sustituye este patrón en archivos, declaraciones e imports antes de entregarla; no renombra automáticamente lo que ya existe.

**Qué pasa si está mal:** Si falta `{Entidad}`, el validador se detiene. Si cambias el patrón sin regenerar, la comprobación previa exige regenerar antes de continuar.

**Cambiarla después:** Edita `stack.yaml` y regenera. Para renombrar código existente, pide la tarea `implement-feature` (te enseña un plan de cambios del front y espera tu sí); el plan aprobado debe contemplar archivos e imports. Regenerar solo actualiza instrucciones.

**Si conservas lo detectado en tu código (por ejemplo, `{Entidad}Model`):** Por ejemplo, pedidos usa `PedidoModel.ts`. Sin código previo, la plantilla usa `{Entidad}Model`. Recomendado: mantén el patrón detectado de tus archivos para evitar renombrar código existente.

**Si eliges `{Entidad}Datos`:** Por ejemplo, pedidos usa `PedidoDatos.ts`. Conviene si quieres cambiar a esta convención, con los nombres concretos del ejemplo y sus referencias en el plan aprobado.

**Respaldo:** `scripts/stack.mjs`; `scripts/preflight.py`; `scripts/registro_detectores.py`; `rules/architecture-rules.md`; `skills/api-integration-architect/SKILL.md`.

## nomenclatura.request

**En resumen:** Da el patrón de nombre para los datos enviados a la API.

**Dónde se ve en tu proyecto:** Con el patrón `{Entidad}Request`, por ejemplo, aparece `domains/request/PedidoRequest.ts` y la declaración `export class PedidoRequest`. Este tipo agrupa los datos de entrada de una operación; por ejemplo, los campos que envías para crear un pedido.

**Para qué se usa:**
- El generador escribe este patrón en las instrucciones de arquitectura; el agente lo aplica al proponer código nuevo.
- Si difiere `nomenclatura.request` del código, la tarea te ofrece corregir request en su plan, conservar la diferencia o dejarla para revisión.
- La comprobación previa revisa los nombres y omite `index.ts` y `.d.ts`; las declaraciones e imports se adaptan dentro de la tarea que apruebas.
- La propuesta de perfiles sustituye este patrón en archivos, declaraciones e imports antes de entregarla; no renombra automáticamente lo que ya existe.

**Qué pasa si está mal:** Si falta `{Entidad}`, el validador se detiene. Si cambias el patrón sin regenerar, la comprobación previa exige regenerar antes de continuar.

**Cambiarla después:** Edita `stack.yaml` y regenera. Para renombrar código existente, pide la tarea `implement-feature` (te enseña un plan de cambios del front y espera tu sí); el plan aprobado debe contemplar archivos e imports. Regenerar solo actualiza instrucciones.

**Si conservas lo detectado en tu código (por ejemplo, `{Entidad}Request`):** Por ejemplo, pedidos usa `PedidoRequest.ts`. Sin código previo, la plantilla usa `{Entidad}Request`. Recomendado: mantén el patrón detectado de tus archivos para evitar renombrar código existente.

**Si eliges `{Entidad}Entrada`:** Por ejemplo, pedidos usa `PedidoEntrada.ts`. Conviene si quieres cambiar a esta convención, con los nombres concretos del ejemplo y sus referencias en el plan aprobado.

**Respaldo:** `scripts/stack.mjs`; `scripts/preflight.py`; `scripts/registro_detectores.py`; `rules/architecture-rules.md`; `skills/api-integration-architect/SKILL.md`.

## nomenclatura.response

**En resumen:** Da el patrón de nombre para los datos que responde la API.

**Dónde se ve en tu proyecto:** Con el patrón `{Entidad}Response`, por ejemplo, aparece `domains/responses/PedidoResponse.ts` y la declaración `export class PedidoResponse`. Este tipo agrupa los datos de respuesta de una operación; por ejemplo, el pedido creado que devuelve la API.

**Para qué se usa:**
- El generador escribe este patrón en las instrucciones de arquitectura; el agente lo aplica al proponer código nuevo.
- Si difiere `nomenclatura.response` del código, la tarea te ofrece corregir response en su plan, conservar la diferencia o dejarla para revisión.
- La comprobación previa revisa los nombres y omite `index.ts` y `.d.ts`; las declaraciones e imports se adaptan dentro de la tarea que apruebas.
- La propuesta de perfiles sustituye este patrón en archivos, declaraciones e imports antes de entregarla; no renombra automáticamente lo que ya existe.

**Qué pasa si está mal:** Si falta `{Entidad}`, el validador se detiene. Si cambias el patrón sin regenerar, la comprobación previa exige regenerar antes de continuar.

**Cambiarla después:** Edita `stack.yaml` y regenera. Para renombrar código existente, pide la tarea `implement-feature` (te enseña un plan de cambios del front y espera tu sí); el plan aprobado debe contemplar archivos e imports. Regenerar solo actualiza instrucciones.

**Si conservas lo detectado en tu código (por ejemplo, `{Entidad}Response`):** Por ejemplo, pedidos usa `PedidoResponse.ts`. Sin código previo, la plantilla usa `{Entidad}Response`. Recomendado: mantén el patrón detectado de tus archivos para evitar renombrar código existente.

**Si eliges `{Entidad}Salida`:** Por ejemplo, pedidos usa `PedidoSalida.ts`. Conviene si quieres cambiar a esta convención, con los nombres concretos del ejemplo y sus referencias en el plan aprobado.

**Respaldo:** `scripts/stack.mjs`; `scripts/preflight.py`; `scripts/registro_detectores.py`; `rules/architecture-rules.md`; `skills/api-integration-architect/SKILL.md`.

## nomenclatura.archivo_seccion_ui

**En resumen:** Da el patrón de nombre para el archivo de una sección de la interfaz.

**Dónde se ve en tu proyecto:** Con el patrón `{nombre}-section.tsx`, por ejemplo, aparece `app/ui/pedidos-section.tsx`. Una sección agrupa una parte visual de la pantalla; por ejemplo, la lista o el formulario de pedidos. Por ejemplo, perfiles se propone en `app/ui/perfiles/perfiles-section.tsx`.

**Para qué se usa:**
- El generador escribe este patrón en las instrucciones de arquitectura; el agente lo aplica al proponer código nuevo.
- Si difiere `nomenclatura.archivo_seccion_ui` del código, la tarea te ofrece corregir el nombre del archivo de pantalla en su plan, conservar la diferencia o dejarla para revisión.
- La comprobación previa revisa los nombres y omite `index.ts` y `.d.ts`; las declaraciones e imports se adaptan dentro de la tarea que apruebas.
- La propuesta de perfiles sustituye este patrón en archivos, declaraciones e imports antes de entregarla; no renombra automáticamente lo que ya existe.

**Qué pasa si está mal:** Si falta `{nombre}`, el validador se detiene. Si cambias el patrón sin regenerar, la comprobación previa exige regenerar antes de continuar.

**Cambiarla después:** Edita `stack.yaml` y regenera. Para renombrar código existente, pide la tarea `implement-feature` (te enseña un plan de cambios del front y espera tu sí); el plan aprobado debe contemplar archivos e imports. Regenerar solo actualiza instrucciones.

**Si conservas lo detectado en tu código (por ejemplo, `{nombre}-section.tsx`):** Por ejemplo, pedidos usa `pedidos-section.tsx`. Sin código previo, la plantilla usa `{nombre}-section.tsx`. Recomendado: mantén el patrón detectado de tus archivos para evitar renombrar código existente.

**Si eliges `{nombre}-vista.tsx`:** Por ejemplo, pedidos usa `pedidos-vista.tsx`. Conviene si quieres cambiar a esta convención, con los nombres concretos del ejemplo y sus referencias en el plan aprobado.

**Respaldo:** `scripts/stack.mjs`; `scripts/preflight.py`; `scripts/registro_detectores.py`; `rules/architecture-rules.md`; `skills/api-integration-architect/SKILL.md`.

## documentacion.url_api

**En resumen:** Indica dónde está la API de Open Notebook, que aporta la documentación que consultan las tareas.

**Dónde se ve en tu proyecto:** En `stack.yaml`, por ejemplo `url_api: http://127.0.0.1:6060`, si publicaste allí tu instalación. Es la dirección de la API, no la URL de una fuente documental ni una ruta del código.

**Para qué se usa:**
- Mantiene `.agents/documentacion.json` y `.agents/documentacion.md`, con fuentes vinculadas por servicio; comprueba conexión e IDs de documentos sin consultar modelos.
- La tarea `preparar-documentacion` propone fuentes; comprueba su oficialidad por servidor y ruta según `dominios_oficiales`. Apruebas la descarga mediante `propuesta.aprobacion_sha256`; las citas se verifican con el resumen criptográfico del texto extraído.
- Sin documentación activa válida o versión resoluble de una tecnología catalogada, se detiene. Una no catalogada avisa: puedes añadirla mediante «Ampliar el catálogo del proyecto» de esa tarea.

**Qué pasa si está mal:** Una dirección inválida o inaccesible detiene la comprobación. Admite HTTP(S) sin usuario, contraseña, consulta ni fragmento; HTTP fuera del equipo local genera aviso. Si el servicio está arrancado, comprueba también el aislamiento de tu herramienta.

**Cambiarla después:** Edita `stack.yaml`; se lee en cada uso, sin regenerar. Si cambias de instalación, revisa la documentación asociada: cambiar la dirección no transporta tus documentos al otro servidor.

**Si conservas el dato confirmado (por ejemplo, `http://127.0.0.1:6060`):** Por ejemplo, las consultas de documentación de pedidos usan la API que tú publicaste en ese puerto. Recomendado: tu dirección confirmada de Open Notebook; no elijas una dirección solo por aparecer en la plantilla.

**Respaldo:** `scripts/documentacion.py`; `scripts/comprobar-documentacion.py`; `workflows/preparar-documentacion.md`.

## documentacion.variable_password

**En resumen:** Nombra la variable que contiene la contraseña de Open Notebook, sin guardarla en el proyecto.

**Dónde se ve en tu proyecto:** En `stack.yaml`, por ejemplo `variable_password: DOCS_PASSWORD`. Solo se escribe el nombre; tú configuras su contenido fuera de ese archivo.

**Para qué se usa:**
- El cliente de documentación usa esa variable para autenticarse ante Open Notebook.
- Si declaras un nombre y la variable no existe o está vacía, informa de su ausencia antes de consultar; no prueba otras credenciales.

**Qué pasa si está mal:** Una variable ausente, vacía o incorrecta impide autenticarte. Su nombre admite letras, cifras y guion bajo, sin comenzar con cifra; no copies la contraseña en lugar del nombre.

**Cambiarla después:** Edita `stack.yaml`, sin regenerar. Al activar contraseña en el servidor, configura tú la variable y declara su nombre antes de repetir la consulta.

**Si eliges `null`:** Por ejemplo, tu instalación local de documentación de pedidos permite entrar sin contraseña. Al comprobar la conexión, el programa de documentación te avisa si acepta ese acceso. Recomendado: es la opción de la plantilla para una API sin contraseña; no sirve si tu instalación exige autenticación.

**Si eliges `DOCS_PASSWORD`:** Por ejemplo, la API de documentación de pedidos utiliza el contenido de esa variable para comprobar tu acceso. Conviene si tu instalación exige contraseña y has configurado esa variable; comprueba solo si está definida, sin mostrar su valor.

**Respaldo:** `scripts/documentacion.py`.

## documentacion.modelo_chat

**En resumen:** Elige el modelo que responde las preguntas de documentación.

**Dónde se ve en tu proyecto:** Con `modelo_chat: null` se usa el modelo de chat predeterminado de tu Open Notebook. Después puedes editar `stack.yaml`, sin regenerar, con un ID que hayas configurado, por ejemplo `modelo-documental`. Un ID inexistente detiene la consulta. No es una clave del proveedor y no cambia la configuración global del servidor.

**Respaldo:** `scripts/documentacion.py`.

## documentacion.modelo_contexto_grande

**En resumen:** Permite elegir un modelo para una fuente completa que exceda el contexto del chat normal.

**Dónde se ve en tu proyecto:** Con `modelo_contexto_grande: null` no eliges una alternativa especial; si la fuente no cabe, la consulta lo informa. Solo se usa como alternativa por tamaño con un ID explícito; no prueba otros proveedores. Después puedes editar `stack.yaml`, sin regenerar, con un ID que hayas configurado, por ejemplo `modelo-documental`. Un ID inexistente detiene esa alternativa. No es una clave del proveedor y no cambia la configuración global del servidor.

**Respaldo:** `scripts/documentacion.py`.

## documentacion.modelo_transformacion

**En resumen:** Elige el modelo que resume capacidades de una fuente documental.

**Dónde se ve en tu proyecto:** Con `modelo_transformacion: null` se usa el predeterminado de transformaciones de Open Notebook. Después puedes editar `stack.yaml`, sin regenerar, con un ID que hayas configurado, por ejemplo `modelo-documental`. Un ID inexistente detiene la consulta. No es una clave del proveedor y no cambia la configuración global del servidor.

**Respaldo:** `scripts/documentacion.py`.

## documentacion.timeout_chat

**En resumen:** Fija cuántos segundos se espera una respuesta de Open Notebook que necesite un modelo.

**Dónde se ve en tu proyecto:** En `stack.yaml`, por ejemplo `timeout_chat: 120` permite esperar hasta dos minutos; un modelo ejecutado en tu equipo puede necesitar más tiempo.

**Para qué se usa:**
- Limita preguntas, resúmenes y comprobaciones de búsqueda por significado: se busca texto relacionado, aunque no use las mismas palabras.
- Ask es una consulta que hace varias llamadas internas al modelo y dispone del triple. La comprobación previa de conexión usa cinco segundos por lectura y no cambia con esta clave.
- Las demás peticiones esperan `30` segundos; los trabajos asíncronos, `180`. Tras cargar un documento se comprueba su índice de búsqueda cada `5` segundos hasta `600`, sin volver a indexarlo.

**Qué pasa si está mal:** El validador exige un entero entre `1` y `3600`. `MODELO_TIMEOUT` significa respuesta no recibida a tiempo; `MODELO_FALLO`, error del servidor al responder, con su código HTTP y sin mostrar el cuerpo. No se reintenta ni se cambia de modelo por esos fallos.

**Cambiarla después:** Edita `stack.yaml`, sin regenerar. Esperar más no arregla una API inaccesible ni un proveedor caído; el procesamiento de documentos recién cargados tiene su propio plazo.

**Si eliges `120`:** Por ejemplo, esperas dos minutos por una respuesta sobre pedidos y hasta seis por Ask. Recomendado: es la espera de la plantilla para empezar con un límite razonable.

**Si eliges `240`:** Por ejemplo, das cuatro minutos a un modelo lento y hasta doce a Ask. Conviene si has observado respuestas que necesitan esa espera adicional, no un fallo de conexión.

**Respaldo:** `scripts/documentacion.py`; `scripts/stack.mjs`.
