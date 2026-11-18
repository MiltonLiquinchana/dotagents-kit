# Manual de usuario

Usa este manual para preparar el `.agents` de tu proyecto, elegir una tarea y resolver sus avisos.
Las rutas de comandos parten de la raíz de **tu proyecto**, salvo que se indique otra cosa.
`<KIT>` es la ruta absoluta donde clonaste `dotagents-kit` (por ejemplo, `/home/ana/dotagents-kit`):
sustitúyela en cada comando y prompt.

- [0. Antes de empezar](#0-antes-de-empezar)
  - [Palabras que encontrarás](#palabras-que-encontrarás)
  - [Requisitos](#requisitos)
- [1. Preparar un proyecto](#1-preparar-un-proyecto)
  - [Primera preparación con la guía](#primera-preparación-con-la-guía)
  - [Qué haces después de generar](#qué-haces-después-de-generar)
  - [Regenerar un proyecto existente](#regenerar-un-proyecto-existente)
  - [Claves nuevas y sin uso](#claves-nuevas-y-sin-uso)
- [2. Trabajar con los workflows](#2-trabajar-con-los-workflows)
  - [Catálogo del back](#back)
  - [Catálogo del front](#front)
  - [Catálogo SQL](#sql)
  - [Adoptar y refactorizar un proyecto que ya tiene código](#adoptar-y-refactorizar-un-proyecto-que-ya-tiene-código)
- [3. Cuando el preflight se para](#3-cuando-el-preflight-se-para)
  - [Códigos frecuentes y remedios](#códigos-frecuentes-y-remedios)
  - [Si pide regenerar o avisa de plantillas nuevas](#si-pide-regenerar-o-avisa-de-plantillas-nuevas)
  - [Pedir más detalle](#pedir-más-detalle)
  - [Decidir qué diferencias conservar](#decidir-qué-diferencias-conservar)
  - [Conexión, permisos y SonarQube](#conexión-permisos-y-sonarqube)
- [4. Cambiar algo después](#4-cambiar-algo-después)
  - [Activar DevOps o cambiar sus valores](#activar-devops-o-cambiar-sus-valores)
  - [Activar autenticación o gestión de usuarios](#activar-autenticación-o-gestión-de-usuarios)
  - [Cambiar una versión o un gestor](#cambiar-una-versión-o-un-gestor)
- [5. Temas por stack](#5-temas-por-stack)
  - [Back: servicios y DevOps](#back-servicios-y-devops)
    - [DevOps y Jenkins](#devops-y-jenkins)
      - [Entornos y promoción](#entornos-y-promoción)
      - [Nombres y recursos](#nombres-y-recursos)
      - [SonarQube por servicio](#sonarqube-por-servicio)
      - [Archivos que aplicas tú](#archivos-que-aplicas-tú)
    - [Servicios y gateway](#servicios-y-gateway)
      - [Perfiles y variables](#perfiles-y-variables)
    - [Compilar en local](#compilar-en-local)
  - [Front: gestor de paquetes](#front-gestor-de-paquetes)
  - [SQL: versión y pruebas](#sql-versión-y-pruebas)
  - [Varios stacks](#varios-stacks)
    - [Gestión de usuarios con Clerk](#gestión-de-usuarios-con-clerk)
    - [Documentación con Open Notebook](#documentación-con-open-notebook)
    - [Cambiar versiones](#cambiar-versiones)
- [6. Referencia](#6-referencia)
  - [Dónde vive cada cosa](#dónde-vive-cada-cosa)
  - [actualizar.py en detalle](#actualizarpy-en-detalle)
    - [Primera generación manual sin guía](#primera-generación-manual-sin-guía)
  - [Variables y avisos de credenciales](#variables-y-avisos-de-credenciales)
  - [Nomenclatura, fichas y datos del proyecto](#nomenclatura-fichas-y-datos-del-proyecto)

## 0. Antes de empezar

### Palabras que encontrarás

| Palabra | Qué significa aquí |
|---|---|
| Stack | Tecnologías y decisiones de tu proyecto: Spring Boot, Next.js o MySQL. |
| Workflow o tarea | Instrucciones que sigue la IA para el trabajo que tú pides. |
| Skill | Instrucciones especializadas para una fase, como diseñar, escribir o revisar. |
| Plan aprobado | Cambios y archivos que revisas antes de autorizar su aplicación. |
| Preflight | Comprobación previa que indica qué falta, difiere o impide continuar. |
| Código del preflight | Nombre en MAYÚSCULAS del control que falló, como `OPEN_NOTEBOOK`. |
| Diagnóstico | Detalle del script, como `API_CAIDA`: la API no responde. |
| Open Notebook | Aplicación donde cargas y consultas documentación por versión. |
| Notebook | Colección de fuentes en Open Notebook; en SQL también es el archivo `.dbcnb` de consultas. |
| dotagents-kit | Repositorio que mantiene las fuentes para generar tu `.agents`. |
| Registro | Solo `docs/decisiones-stack.md`, que recuerda tus decisiones sobre diferencias. |
| Huella | Resumen calculado del contenido o configuración para detectar cambios. |
| Regenerar | Volver a preparar las instrucciones con `actualizar.py`. |
| `no_determinable` | Faltan datos para decidir; no significa que todo coincida. |
| Base del nombre | `rootProject.name` sin `-service` final, usada para identificar recursos. |
| Base de datos | Servidor o esquema donde están las tablas y otros objetos SQL. |
| Sandbox | Aislamiento de la herramienta o, en pruebas SQL, base de datos desechable. |
| MCP | Conexión para usar herramientas de un servidor externo. |
| API | Operaciones que un programa ofrece a otro. |
| Clerk | Servicio que permite iniciar sesión y verificar quién hace una petición. |
| Codebase Memory | Herramienta que construye un grafo de relaciones del código para consultarlo. |
| agent-browser | CLI que permite recorrer la app local en un navegador, comprobar errores y guardar una captura. |
| Gateway | Servicio de entrada que dirige peticiones hacia otros servicios. |
| Context-path | Prefijo de URL de un servicio, por ejemplo `/pedidos`. |
| Artefactos de DevOps | Archivos para construir o desplegar: Dockerfile, pipeline y manifiestos. |
| Lockfile | Archivo que fija las versiones de dependencias instaladas. |
| Initializr | Herramienta de Spring para obtener el ZIP inicial de un servicio. |
| Ficha | Explicación de una clave en `.agents/config/claves.md`. |
| Ruta completa o de corrección | Recorrido del workflow según necesite diseño nuevo o un ajuste puntual. |
| Plan maestro | Plan común de contratos y dependencias para un cambio en varios servicios. |
| Contrato | Acuerdo de nombres, datos y operaciones que deben respetar los proyectos conectados. |
| Gate | Control automático que bloquea problemas nuevos antes de continuar. |
| BOM | Lista que fija versiones compatibles de un conjunto de librerías. |
| Cierre estricto | Comprobación final sin omitir controles exigidos para dar la entrega por lista. |
| Núcleo del front | Archivos compartidos de red, errores y avisos al usuario. |
| Quality gate (SonarQube) | Condiciones que SonarQube evalúa sobre un análisis; en CI pueden bloquear el build. El gate local diferencial tiene otro alcance. |
| `.dbcnb` | Notebook SQL de DBCode; en estos workflows `nb-edit.py` también los crea y mantiene. |
| `tgrep` | Herramienta que indexa y permite consultar las notas de `knowledge-base/`. |
| `knowledge-base/` | Carpeta de notas del proyecto vinculadas a archivos u objetos SQL. |

Prepara un repositorio Git con al menos un commit, Open Notebook y una IA abierta en el proyecto. Los workflows habituales de
código requieren árbol limpio; incorporate-service, bootstrap-project, change-version y
preparar-documentacion permiten empezar con cambios pendientes; su cierre puede exigir árbol limpio.

### Requisitos

Instala lo necesario para tu stack antes de lanzar sus workflows. Las opciones se eligen en `stack.yaml`.

| Herramienta o recurso | Para qué | Obligatoria u opcional | Stacks |
|---|---|---|---|
| Git | Repositorio con commits y control del árbol | Obligatorio | Todos |
| Python 3 | Generador y scripts | Obligatorio | Todos |
| Bash y utilidades de shell | Preparación y entrada del preflight | Obligatorios | Todos |
| `jq` | Procesar datos JSON en los scripts | Obligatorio | Todos |
| [`tgrep`](https://github.com/microsoft/tgrep) | Indexar y consultar notas; instala según su README (p. ej. `brew install tgrep`) | Obligatorio | Todos |
| `knowledge-base/` | Guardar las notas indexadas; la crea `preparar-proyecto.sh` | Obligatoria | Todos |
| [Codebase Memory](https://github.com/DeusData/codebase-memory-mcp) | Índice local de código; CLI `codebase-memory-mcp`; instalar solo el binario con `curl -fsSL https://raw.githubusercontent.com/DeusData/codebase-memory-mcp/main/install.sh \| bash -s -- --skip-config` | Con `herramientas.codebase_memory: true` | Todos |
| [Open Notebook](https://github.com/lfnovo/open-notebook) y proveedor de modelos | Documentación con chat, transformación y embeddings; API en `documentacion.url_api` (plantilla: `http://localhost:5055`) | Obligatorios; configura los modelos predeterminados | Todos |
| IA con ejecución de comandos y escritura de archivos | Seguir las instrucciones y guardar cambios aprobados | Obligatoria; permite acceso local y las rutas indicadas abajo | Todos |
| Node.js | Ejecutar los scripts `.mjs` | Obligatorio | Back y front |
| `curl` | Comprobar SonarQube | Obligatorio | Back y front |
| SonarQube y [servidor MCP de SonarQube](https://github.com/SonarSource/sonarqube-mcp-server) | Análisis, comprobaciones con defectos conocidos y gate diferencial | Obligatorios; runtime de Java en la versión requerida por el README del servidor; configura el nombre de `mcp.sonarqube` o las variables de entorno de [Conexión, permisos y SonarQube](#conexión-permisos-y-sonarqube) | Back y front |
| JDK y wrapper Gradle ejecutable | Compilar y comprobar toolchains | Obligatorios; JDK de la versión `backend.java` que Gradle detecta (`./gradlew javaToolchains`) | Back |
| npm/`npx`, pnpm o Yarn y ESLint local | Dependencias y linter | El gestor de `frontend.gestor_paquetes`; con npm se comprueba `npx`; Yarn admite PnP | Front |
| [agent-browser](https://github.com/vercel-labs/agent-browser) | Verificación en el navegador; instala con `npm install -g agent-browser` y después `agent-browser install` | Con `herramientas.agent_browser: true` | Front |
| PyYAML en el Python del sistema (p. ej. `python3-yaml`); los scripts no cargan el site-packages del usuario | Leer y mantener notebooks `.dbcnb` | Obligatorio | SQL |
| Docker o Podman operativo e imagen MySQL local | Sandbox de pruebas | Obligatorios para el sandbox; imagen alineada con la versión del stack, sin descarga automática | SQL |
| [`db-mcp-server`](https://github.com/FreePeak/db-mcp-server) | Consultar o ejecutar sobre la base real autorizada | Necesario para pasos con base real; con `conexiones: {}` se detienen esos pasos | SQL |

Da a la herramienta acceso a `localhost` y a `<KIT>`, y permiso para escribir en `.agents`
(registro de documentación) y en `.git` (commits del flujo). Añade ambas carpetas a las rutas
escribibles; en codex, `-c 'sandbox_workspace_write.writable_roots=["<proyecto>/.agents","<proyecto>/.git"]'`.
Las carpetas deben existir antes de abrir la sesión; en un proyecto nuevo, crea `.agents` vacía.
En el back, Gradle necesita escribir su caché en `~/.gradle`: añade también `"<tu-home>/.gradle"`.
Si falla un acceso, consulta [Conexión, permisos y SonarQube](#conexión-permisos-y-sonarqube).

## 1. Preparar un proyecto

Elige según lo que ya tengas: usa la guía si aún no hay un `.agents` generado; si ya existe
`.agents/.generado.json`, ve a [Regenerar un proyecto existente](#regenerar-un-proyecto-existente).
Preparar las instrucciones y adaptar el código que ya existe son tareas distintas.

### Primera preparación con la guía

Abre la IA en el workspace de tu proyecto y pega este prompt tal cual:

   ```text
   Quiero preparar el .agents de este proyecto. Lee entera la guía
   <KIT>/guia-ia-preparar-proyecto.md y síguela paso a paso.
   La ruta de dotagents-kit es <KIT> y este proyecto es el
   workspace actual. Respeta sus límites: escribe solo .agents/stack.yaml y .agents/actualizar.py, no
   leas secretos ni configuración con credenciales y ejecuta actualizar.py solo como dice la guía, con
   mi confirmación. Pregúntame lo que no puedas detectar y espera mi confirmación antes de escribir.
   ```

Contesta una decisión por pregunta. La guía propone lo detectado con archivo y línea; solo si no hay
dato presenta el valor de plantilla. Tú eliges las versiones y opciones permitidas de las fichas.
En SQL, la guía te pregunta cómo se llama el notebook con datos de prueba y no lo abre: lo excluye por
nombre antes de leer SQL. Propone `conexiones: {}` sin acceso a una base de datos real.
Solo pide nombres de variables y servidores MCP, nunca valores ni la configuración de tus herramientas.
Open Notebook es obligatorio; los modelos opcionales en `null` usan sus predeterminados.

Revisa el `stack.yaml` propuesto. Con tu confirmación la IA escribe `.agents/stack.yaml` y
`.agents/actualizar.py`, simula la generación y muestra los avisos y el resumen de archivos.
Tras resolver los avisos pide un «sí» explícito para generar y enseña las variables, solo por nombre.
Después valida el stack; si hay un bloqueo, repite la corrección, simulación y consentimiento.

En la primera generación la guía usa `--si` tras tu confirmación. Si ya había un `.agents` generado,
se detiene: sigue [Regenerar un proyecto existente](#regenerar-un-proyecto-existente), sin forzar ese argumento.

### Qué haces después de generar

Si usas Claude Code, crea en la raíz del proyecto un `CLAUDE.md` con la línea `@AGENTS.md` para que cargue las instrucciones generadas.

Sigue este orden:

1. Ejecuta `bash .agents/scripts/preparar-proyecto.sh`: crea auxiliares que faltan y prepara exclusiones.
   Revisa y haz el commit `chore: preparar el proyecto para .agents` en tu repositorio.
2. Si elegiste versiones distintas del código, pide change-version o ajusta tú las claves de versión de `stack.yaml` para que coincidan con las del código;
   change-version carga también la documentación de las versiones nuevas.
3. Si `herramientas.codebase_memory` es `true`, pide `.agents/workflows/codebase-memory.md` para crear el grafo antes de
   `preparar-documentacion`: sin grafo, su cierre bloquea con `BLOCKED [GRAFO]`.
   Con Codebase Memory activo, `GRAFO` bloquea en entrada y cierre de los workflows de código (grupo E);
   en `change-version` (grupo V) avisa en ambas fases; en `preparar-documentacion` (grupo D) avisa
   en la entrada y bloquea al cerrar.
4. Pide `.agents/workflows/preparar-documentacion.md` para completar la documentación del proyecto.
   Hazlo antes que los demás workflows, salvo `codebase-memory`: si falta documentación, los otros se detienen y te proponen
   lanzarlo; no cargan fuentes por su cuenta. Solo `preparar-documentacion` (y change-version, para sus
   versiones) carga fuentes, y cada carga necesita que apruebes esa fuente y su hash.
5. Elige la tarea en [Trabajar con los workflows](#2-trabajar-con-los-workflows).

Por ejemplo, con back sin servicios, tú traes el primero desde Initializr; con front sin Next.js,
tú creas el proyecto con la versión elegida y preparas sus dependencias antes de bootstrap.
Si ya tienes código, puedes usar los [prompts opcionales de adopción y refactor](#adoptar-y-refactorizar-un-proyecto-que-ya-tiene-código).

### Regenerar un proyecto existente

Consulta «Cambiarla después» en la ficha: [la tabla de cambios](#4-cambiar-algo-después) distingue los casos.
Regenera por opciones/nomenclatura, mejoras de plantillas o cuando el workflow lo pida.

Desde la raíz de tu proyecto, revisa primero una simulación:

```bash
python3 -I -B .agents/actualizar.py --kit <KIT> --simular
```

Luego ejecuta la generación con confirmación interactiva:

```bash
python3 -I -B .agents/actualizar.py --kit <KIT>
```

Revisa qué archivos crea, modifica o borra. Si detecta uno editado a mano, te pregunta antes de
sobrescribirlo. No fuerces `--si`: también aceptaría esas sobrescrituras. Cuando termine, revisa los
cambios de Git y vuelve a lanzar el workflow que se había detenido.

Regenera tú, o pídeselo expresamente a la IA; recuerda que comprobará las variables en su entorno,
que puede ser distinto de tu terminal. La generación guiada inicial es la excepción.

### Claves nuevas y sin uso

Resuelve los avisos antes de seguir:

- **«falta en tu stack.yaml»**: añade la clave indicada con un valor de tu proyecto. Las obligatorias
  bloquean hasta completarlas; no basta con regenerar un stack incompleto.
- **«ya no se usa»**: puedes quitar esa clave cuando su opción no está activa. Si activas la opción
  después, el generador te indicará qué claves debes volver a añadir.

Un entorno con `imagen: ninguna` no tiene combinación válida: no despliega ni añade acciones útiles.
Elige construir o promover según lo que deba hacer, o elimina esa entrada.

## 2. Trabajar con los workflows

Pide a la IA una tarea concreta y cita su workflow si ya sabes cuál necesitas. Por ejemplo:
«Sigue `.agents/workflows/implement-feature.md` para añadir la pantalla de pedidos».
Cuando la IA propone una tarea para resolver un aviso, tú decides si la lanzas.

Las tareas de cambios presentan su plan antes de escribir; los ajustes de alcance necesitan aprobación.
Las rutas completa y de corrección son recorridos internos de las features; no las lanzas por separado.

Knowledge-base y Codebase Memory no cambian código, no traen plan propio ni requieren cobertura documental.
Codebase Memory indexa el repositorio desde su raíz y exige `herramientas.codebase_memory: true`; knowledge-base pregunta
qué fichero u objeto documentar. La IA puede proponerte estas tareas; tú eliges si las lanzas.

### Back

#### `incorporate-service.md`

Pídelo al pegar Initializr: «Incorpora la carpeta `pedidos-service`»; la guía también lo ofrece para
revisar existentes. Recibe la carpeta exacta y propone un plan de configuración y base del nombre:
versiones, dependencias, paquete/clase, puerto, contexto, perfiles, errores y artefactos DevOps.
Apruebas cada servicio y autorizas Gradle. No reorganiza negocio ni sobrescribe con un esqueleto nuevo.
Su cierre exige árbol limpio: tú haces commit de cada servicio antes de continuar con el siguiente.

#### `implement-microservice-feature.md`

Pídelo para feature, corrección o refactor: «Añade una consulta de pedidos»; la IA también lo propone
para adaptar diferencias del registro. La **ruta completa** crea archivos, capas, contratos o patrones;
la **de corrección** ajusta lo existente sin esa estructura nueva. Si hay duda, pregunta; apruebas el plan.

En varios servicios presenta primero un **plan maestro** aprobado de contratos y dependencias;
construye en ese orden y revisa los contratos cruzados. Un aviso no autoriza arreglos ajenos al plan.
Un rechazo arquitectónico pide confirmación para rediseñar; las rutas incluyen commits atómicos al cerrar.

#### `add-authentication.md`

Pídelo tras elegir Clerk y regenerar: «Añade autenticación al gateway existente»; la IA puede proponerlo
como remedio. Apruebas dependencia, JWT, issuer y rutas públicas; autorizas Gradle o descargas.
No crea gateway ni roles. Si ya hay seguridad, informa y termina sin modificarla: requiere plan específico.
No cambia el contrato de errores ni aplica recursos en el clúster.

#### `add-user-management.md`

Pídelo con gestión activa: «Instala perfiles con el contrato SQL <ruta>». Si no hay contrato, declara
supuestos. Apruebas servicio, API, rutas públicas y artefactos por entorno; autorizas Gradle.
No añade roles ni abre otros proyectos o aplica secrets. Lleva sus contratos según [Clerk](#gestión-de-usuarios-con-clerk).

#### `change-version.md`

Pídelo ante `VERSIONES` o para cambiar: «Alinea Java y Spring Boot con mi stack».
Apruebas versiones, documentación y archivos; confirmas rutas JDK y autorizas compilar.
El alcance y tus pasos finales están en [Cambiar versiones](#cambiar-versiones).

#### `preparar-documentacion.md`

Pídelo ante `DOCUMENTACION`: «Carga documentación de mis versiones»; la IA lo propone si faltan fuentes.
En back detecta versiones por servicio y resuelve las gestionadas por BOM antes de preparar notebooks.
Las aprobaciones y límites están en [Open Notebook](#documentación-con-open-notebook).

#### `knowledge-base.md`

Ejemplo: «Documenta el fichero <ruta> y verifica la vinculación de su nota».

#### `codebase-memory.md`

Ejemplo: «Indexa el repositorio desde su raíz y comprueba el índice».

### Front

#### `bootstrap-project.md`

Pídelo para Next.js nuevo o en blanco, ya creado: «Prepara el núcleo de este front».
Siembra red, errores y providers; instalar dependencias o registrar un proyecto SonarQube exige permiso.
No declara plan propio ni migra un front avanzado. Su cierre exige preflight completo y espera si el
árbol está sucio, sin commit automático. Si `herramientas.codebase_memory` es `false`, omite el paso de Codebase Memory y
lo deja anotado en su informe.

#### `implement-feature.md`

Pídelo para módulos, UI o refactor: «Reorganiza pedidos sin cambiar su comportamiento»; también sirve
para migrar de gestor. La **ruta completa** crea archivos/capas, contratos/firmas, componentes o cambios
visuales; la **de corrección** hace ajustes puntuales sin estructura nueva o cosméticos menores.
Pregunta si hay duda y pide aprobar el plan. Si falta núcleo, propone bootstrap y espera tu respuesta.
No repara infraestructura ajena; rediseñar exige confirmación. Incluye commit atómico tras comprobar;
Codebase Memory sí se condiciona a su opción en este workflow.
Con `herramientas.agent_browser: true`, añade una verificación en el navegador después de la prueba de humo por HTTP: recorre la feature como una persona, comprueba consola, excepciones y peticiones fallidas y guarda una captura. La app debe apuntar a una API de desarrollo, porque se crean datos de prueba con el prefijo `kit-agente`. Con Clerk, inicia sesión con el usuario de prueba `kit-agente+clerk_test@example.com` (código `424242`), que necesita una instancia de desarrollo con el Test mode y el código por correo; si la protección contra bots lo impide, la tarea se detiene y te dice qué cambiar. Por defecto el navegador no muestra ventana; para verlo en vivo, exporta `AGENT_BROWSER_HEADED=1` en la terminal desde la que lanzas la IA o pídele que lo abra con ventana.

##### Usuario de prueba de Clerk

1. Usa la instancia de desarrollo, con el Test mode activo (lo está por defecto) y el código por correo.
2. Si la instancia solo admite invitados, crea `kit-agente+clerk_test@example.com` en el panel de la instancia de desarrollo (Users → Create user).
3. Añádelo a la organización con el rol que necesiten las pantallas.
4. Si la app exige un perfil local activo para el usuario, créalo en la base de desarrollo.

- Las invitaciones a direcciones `+clerk_test` se prueban: Clerk no envía correos a direcciones de prueba.
- Aceptar una invitación necesita el enlace del correo, que no llega; queda para verificación manual.
- Quien comparta la instancia comparte también el usuario.

Si falta el usuario de prueba, la tarea se detiene y te remite a la ficha `herramientas.agent_browser` de `.agents/config/claves.md` de tu proyecto, apartado «Usuario de prueba de Clerk».

#### `add-authentication.md`

Pídelo tras elegir Clerk y regenerar: «Integra Clerk conservando mi layout». Apruebas proxy, rutas,
páginas, providers y cliente API; instalar exige permiso específico. Si hay autenticación incompatible,
se detiene sin sustituirla ni repetir bootstrap. No instala gestión ni cambia los errores API.

#### `add-user-management.md`

Pídelo con gestión activa: «Crea las pantallas de perfiles con el contrato API <ruta>».
Apruebas campos, rutas, menú y archivos; si falta contrato, declara el supuesto. Conserva el layout y,
si falta núcleo, usa bootstrap aprobado. Prueba sin Clerk real; no instala sin permiso, añade roles ni
cambia otros proyectos o el contrato de errores. [Clerk](#gestión-de-usuarios-con-clerk) explica el intercambio de contratos.

#### `change-version.md`

Pídelo ante `VERSIONES`: «Alinea Next con `frontend.version`». Apruebas versiones, manifiestos, lockfile,
compatibilidad y documentación; instalar/descargar exige permiso. No migra de gestor: usa implement-feature.
Lee el alcance común y tus pasos finales en [Cambiar versiones](#cambiar-versiones).

#### `preparar-documentacion.md`

Pídelo ante `DOCUMENTACION`: «Prepara fuentes de mis versiones»; la IA puede proponértelo.
Front detecta dependencias en manifiestos/lock y admite ampliar el catálogo del proyecto.
Consulta aprobaciones y límites en [Open Notebook](#documentación-con-open-notebook).

#### `knowledge-base.md`

Ejemplo: «Actualiza la nota de conocimiento de <ruta> y verifica su vinculación».

#### `codebase-memory.md`

Ejemplo: «Actualiza el grafo de este front».

### SQL

#### `build-database-feature.md`

Pídelo para crear o modificar objetos: «Optimiza este procedimiento sin cambiar su firma».
También es la tarea para refactorizar objetos existentes con el alcance aprobado.

Revisa las conexiones y la consulta inicial en [SQL: versión y pruebas](#sql-versión-y-pruebas).

La **ruta completa** cubre objetos nuevos, cambios estructurales de tablas o de parámetros/resultados.
La **ruta de corrección** cubre lógica interna, optimización sin cambio de esquema/firma y correcciones
de errores o nombres. Apruebas el plan; si cambia el diseño, vuelve a pedir aprobación.

El flujo puede ejecutar SQL aprobado en la base de datos real después de auditoría y gate/sandbox.
Un fallo DDL puede dejar cambios parciales: restaurar archivos Git no los revierte. La ruta incluye
commit atómico de notebooks/notas; no es adopción automática.

#### `add-user-management.md`

Pídelo con gestión activa: «Prepara los objetos SQL de perfiles». [SQL: versión y pruebas](#sql-versión-y-pruebas)
explica conexiones y dato inicial. Apruebas objetos, notebooks y pruebas; con organizaciones, si usar
una tabla nueva o tuya y sus columnas necesarias. Prueba en sandbox con imagen local y permiso.
No modifica back/front ni descarga imágenes; entrega su contrato según [Clerk](#gestión-de-usuarios-con-clerk), sin commit automático.

#### `change-version.md`

Pídelo para compatibilidad MySQL: «Revisa los objetos para `base_de_datos.version`».
Apruebas destino, documentación, citas, registro y pruebas; el sandbox requiere permiso e imagen local.
Lee las conexiones en [SQL: versión y pruebas](#sql-versión-y-pruebas) y tus pasos en [Cambiar versiones](#cambiar-versiones).

#### `preparar-documentacion.md`

Pídelo ante `DOCUMENTACION`: «Carga documentación de mi versión MySQL»; la IA puede proponértelo.
Lee la versión declarada y admite fuentes MySQL del usuario, sin ampliar motores detectados.
Consulta aprobaciones y límites en [Open Notebook](#documentación-con-open-notebook).

#### `knowledge-base.md`

Ejemplo: «Documenta el procedimiento <nombre> y verifica la vinculación de su nota».

#### `codebase-memory.md`

Ejemplo: «Genera o repara el grafo del proyecto SQL».

### Adoptar y refactorizar un proyecto que ya tiene código

Elige un prompt de tu stack y rellena su lista. Son **opcionales**: ninguno se lanza solo.
Adoptar significa revisar cómo encaja lo que ya tienes; refactorizar pide reorganizarlo manteniendo
el comportamiento. La IA te presenta cambios concretos antes de aplicarlos.

**Back.** Revisa configuración y base del nombre, sin reorganizar negocio. La adopción de servicios ya
commiteados tiene una limitación conocida: si el workflow no los reconoce, **se detiene** sin forzarlos.

Prompt: adoptar (back)
```text
Quiero alinear con el .agents de la raíz de este proyecto estos servicios que ya existen, uno por uno, con .agents/workflows/incorporate-service.md y un plan aprobado para cada servicio:
- <ruta exacta del servicio 1>
- <ruta exacta del servicio 2>
Si el workflow no reconoce el servicio, detente y dímelo; no lo fuerces. No reorganices el código de negocio. Al terminar cada servicio, espera a que yo haga commit antes del siguiente.
```

Prompt: refactorizar (back)
```text
Quiero refactorizar estos servicios con .agents/workflows/implement-microservice-feature.md; compáralos con .agents/rules/architecture-rules.md:
- <ruta exacta del servicio 1>
- <ruta exacta del servicio 2>
Propón un plan sin cambiar el comportamiento y espera mi aprobación; si afecta varios servicios, presenta primero el plan maestro.
```

**Front.** No hay una tarea de adopción general. Bootstrap está pensado para un front nuevo o en blanco,
no para sembrar encima de uno avanzado. Este prompt solo revisa y propone peticiones posteriores;
implement-feature hará su propio plan cuando elijas una de ellas.

Prompt: adoptar (front)
```text
Quiero revisar con el .agents de la raíz de este proyecto estos módulos que ya existen: compara su configuración y núcleo con stack.yaml y las reglas; no ejecutes bootstrap-project sobre el proyecto existente:
- <ruta del módulo 1>
- <ruta del módulo 2>
No hay workflow de adopción general: presenta diferencias y propón qué peticiones lanzar después con implement-feature, sin escribir cambios; espera mi decisión.
```

Prompt: refactorizar (front)
```text
Quiero refactorizar estos módulos con .agents/workflows/implement-feature.md; compáralos con .agents/rules/architecture-rules.md:
- <ruta del módulo 1>
- <ruta del módulo 2>
Propón un plan para adaptar carpetas y capas sin cambiar el comportamiento y espera mi aprobación antes de escribir.
```

**SQL.** No hay adopción dedicada: solo revisa y propone, sin persistir ni ejecutar SQL. El refactor
usa build-database-feature, que puede ejecutar en la base de datos real declarada tras aprobar y comprobar.

Prompt: adoptar (sql)
```text
Quiero revisar con el .agents de la raíz de este proyecto estos objetos que ya existen: compara sus notebooks permitidos con stack.yaml y .agents/rules/architecture-rules.md, excluyendo datos de prueba antes de abrirlos:
- <objeto y notebook 1>
- <objeto y notebook 2>
No hay workflow de adopción dedicado: presenta diferencias y un plan, sin persistir ni ejecutar SQL; espera mi decisión.
```

Prompt: refactorizar (sql)
```text
Quiero refactorizar estos objetos con .agents/workflows/build-database-feature.md; compáralos con .agents/rules/architecture-rules.md y excluye los datos de prueba antes de leer:
- <objeto y notebook 1>
- <objeto y notebook 2>
Propón un plan sin cambiar el comportamiento, las firmas ni el esquema y espera mi aprobación antes de aplicar cambios.
```

## 3. Cuando el preflight se para

Lee el **código**, el detalle y el remedio antes de pedir un arreglo. El preflight revisa repositorio,
configuración generada, herramientas, documentación y controles del stack según workflow y fase.
Los workflows habituales lo llaman al entrar; algunos también al cerrar.

No todos los workflows comprueban lo mismo: preparar-documentacion arranca aunque falte documentación,
porque su trabajo es cargarla. Para lanzar tú el preflight, usa `bash .agents/scripts/preflight.sh`.
Ejemplo ilustrativo de cuatro líneas con el formato real; no es una ejecución de tu proyecto:

```text
BLOCKED [REGENERAR] servicio=* cambió una opción sin regenerar
AVISO [STACK_CODIGO] servicio=pedidos-service hay una diferencia que decidir
PARTE DEL PLAN [PERFILES_TOCADO] servicio=pedidos-service falta el perfil local
OMITIDO [GRAFO] (depende de herramientas.codebase_memory=false) servicio=*
```

| Salida | Cómo la interpretas |
|---|---|
| `BLOCKED` | Hay un impedimento; aplica el remedio sin ampliar por tu cuenta el trabajo. |
| `AVISO` | Se informa de algo pendiente; no autoriza una reparación automática. |
| `PARTE DEL PLAN` | El cambio corresponde al alcance que tendrá que aprobarse. |
| `OMITIDO` | Ese control no se ejecutó; la salida indica la dependencia o razón. |
| `REPASO bloqueo i/N` | Justo antes de `RESUMEN`, repite cada `BLOCKED` con su remedio (N = `bloqueos=`). Si la salida es larga, basta con leer el final. |

Un preflight con avisos u omisiones **no demuestra** que pasen los controles omitidos.
El código de salida 0 permite continuar revisando esas condiciones; 1 detiene y 2 indica error de uso.
Con `PREPARACION`, la IA te propone ejecutar `preparar-proyecto.sh`; tú das permiso y se repite el preflight.

### Códigos frecuentes y remedios

Consulta `.agents/config/codigos.yaml` de tu proyecto para el catálogo completo y las clases de cada
workflow/fase. Estos son los casos frecuentes; algunos son avisos o parte del plan, no bloqueos:

| Código del preflight | Dónde | Qué haces |
|---|---|---|
| `REGENERAR` | Todos | Revisa qué opciones/nomenclatura cambiaron o qué metadatos faltan; regenera y relanza el workflow. |
| `PREPARACION` | Todos | Ejecuta o autoriza preparar-proyecto.sh, revisa, haz el commit necesario y repite. |
| `ARBOL_SUCIO` | Todos | Revisa y confirma tus cambios en Git; no los escondas ni descartes para pasar. |
| `STACK_INVALIDO` | Todos | Corrige tú la clave indicada en stack.yaml. |
| `OPEN_NOTEBOOK` | Todos | Lee el diagnóstico de conexión y comprueba acceso/aislamiento, sin mostrar credenciales. |
| `DOCUMENTACION` | Todos | Fuera de preparar-documentacion y change-version, la IA se detiene y te propone lanzar preparar-documentacion con las tecnologías y versiones indicadas. |
| `REGISTRO` | Todos | Distingue recordatorio de decisión y fila inválida; esta última se corrige en un plan, sin duplicarla. |
| `STACK_CODIGO` | Todos | Pide más detalle y decide sí, no o para revisión sobre la diferencia. |
| `PLANTILLAS_NUEVAS` | Todos | Hay mejoras en la carpeta de tu stack: puedes regenerar y relanzar la tarea. |
| `VERSIONES` | Back/front | Pide change-version para alinear código y stack, o ajusta tú las claves de versión de `stack.yaml` para que coincidan con las del código. |
| `PERFILES` / `PERFILES_TOCADO` | Back | Revisa los archivos que faltan según [Perfiles y variables](#perfiles-y-variables). |
| `DEVOPS_ESTADO` / `DEVOPS_VALORES` | Back | Decide si el plan de escritura prepara/alinea los artefactos; regenerar no los cambia. |
| `DEPENDENCIAS` | Front | Prepara dependencias con el gestor declarado y el permiso necesario. |
| `VERSION_REAL` | SQL | Decide el trabajo local/documental de change-version; servidor y stack siguen a tu cargo. |
| `NOTEBOOKS` / `CONTENEDORES` / `SANDBOX` | SQL | Revisa el diagnóstico: notebooks, herramienta de contenedores o imagen local/entorno de pruebas. |

Cada workflow solo incorpora reparaciones que le corresponden y están en su plan aprobado.
Por ejemplo, change-version resuelve versiones y su documentación; informa de perfiles y DevOps ajenos
como pendientes. No cambies scripts del `.agents` para hacer pasar un control.

Distingue **códigos del preflight** de **diagnósticos**. `OPEN_NOTEBOOK` es un código; `API_CAIDA`,
`AUTENTICACION`, `MODELO_CONFIG`, `MODELO_TIMEOUT` y `LIMITE_USO` pueden ser diagnósticos de
`documentacion.py`. `AUTENTICACION` también existe como código del stack: mira quién lo emite.
`HISTORIAL_INCOMPLETO` y `MIGRACION` son mensajes del pipeline, no códigos del preflight.

### Si pide regenerar o avisa de plantillas nuevas

Si aparece `REGENERAR`, sigue [Regenerar un proyecto existente](#regenerar-un-proyecto-existente).
`PLANTILLAS_NUEVAS` avisa de cambios en la carpeta de tu stack; en otra máquina el preflight no sabe
dónde está dotagents-kit y no avisa de plantillas nuevas: regenera con `--kit`.

### Pedir más detalle

Pide más detalle: la comprobación del registro (`registro-stack.py`) usa una muestra fija y muestra
**como mucho diez líneas de evidencia por clave**. El análisis completo amplía el recorrido y la evidencia,
sin convertir expresiones dinámicas o datos insuficientes en certezas.

Este es el comando, igual en los tres stacks; sustituye servicio y workflow:

```bash
python3 -I -B .agents/scripts/registro-stack.py comprobar --completo --servicios <servicio> --workflow <workflow>
```

En front y SQL el servicio es `.`. Ejemplo con versión real comprobada `8.4.3`:

```bash
python3 -I -B .agents/scripts/registro-stack.py comprobar --completo --servicios . --workflow build-database-feature --dato version_real=8.4.3
```

Solo añade el dato si conoces la versión normalizada; no lo inventes.
`--completo` es una opción de **registro-stack.py comprobar**, no del preflight.
Si aparece `no_determinable`, revisa qué no pudo comprobarse. No significa «coincide» ni una
adaptación que pueda aplicarse sin aclarar datos.

### Decidir qué diferencias conservar

Responde a la **tarea** cuando te ofrezca una diferencia. El preflight solo informa; no escribe el
registro ni decide por ti. La tarea guarda tu respuesta en `docs/decisiones-stack.md`, dentro de su
plan aprobado y fuera del `.agents` generado.

| Respuesta | Qué pasa |
|---|---|
| Sí | El cambio entra en el plan; al verificarlo queda como aplicado. |
| No | Se conserva la diferencia para ese valor y servicio; se recuerda en una línea sin volver a proponértela. |
| Para revisión | Se recuerda la clave y sus servicios, con opción de aplicarla en una tarea posterior. |

Por ejemplo, si conservas un nombre de clase en un servicio, ese «no» no acepta nombres nuevos ni
otro valor del patrón. Las decisiones valen por **clave, valor y alcance**; incorporar otro servicio
no amplía automáticamente la aceptación. Ejemplo de alcance de proyecto: decidir el gestor de todo el front, no de un módulo.

Para cambiar un «no», pide: «Quiero revisar los cambios registrados». La IA propone pasar esa decisión
a «para revisión» dentro del nuevo plan. No edites la tabla a mano.

Algunas comprobaciones de nomenclatura aceptan nombres concretos; los nuevos se siguen comparando.
La estrategia física JPA —cómo convierte nombres Java a tablas— se decide para la clave entera;
por ejemplo, conservarlos tal cual o convertirlos a snake_case. Aceptar nombres no oculta no evaluados.

«Aplicado» solo acredita lo que se verificó en ese trabajo. No certifica que tu servidor real esté
actualizado ni que hayan pasado comprobaciones omitidas. En SQL, una decisión aplicada sobre versión
real cubre el par real/stack registrado; cambiar cualquiera de los dos vuelve a comprobarlo.

En el back se comparan, con las limitaciones de su evidencia, persistencia/Lombok, group,
gateway/CORS, autenticación y gestión, issuer y nombres de variables de autenticación,
nomenclatura, contrato de errores y la ruta JDK gestionada. No es una auditoría completa del proyecto.
Consulta los perfiles pendientes en [Perfiles y variables](#perfiles-y-variables).

### Conexión, permisos y SonarQube

Si Open Notebook está arrancado y ves `OPEN_NOTEBOOK` con `API_CAIDA`, pide a la IA que repita fuera del
aislamiento el comando que falló —el preflight o `documentacion.py comprobar-conexion`—, o da a la
herramienta permiso de red local. Si dice «no existe actualizar.py», comprueba que la herramienta puede leer `<KIT>`.

Algunas herramientas dejan `.agents` y `.git` en solo lectura aunque el resto del proyecto se pueda escribir: por
ejemplo, codex en modo `workspace-write`. Ahí `documentacion.py` responde `REGISTRO_SOLO_LECTURA` antes de tocar
Open Notebook («No se puede escribir en .agents… No se ha cambiado nada»); la IA se detiene y te pide el permiso.

**SonarQube sin cargar su MCP (front y back).** La IA llama a SonarQube con `.agents/scripts/sonar-mcp.mjs`, que
arranca el servidor MCP por su cuenta y solo deja usar las herramientas que el `.agents` necesita
(`config/sonar-mcp.json`); las de escritura (cambiar el estado de un issue o de un hotspot) exigen tu aprobación
explícita. Así puedes **desactivar** el MCP de SonarQube en tu herramienta y ahorrar contexto en cada sesión:
- desactívalo sin borrar su entrada, porque el script (como el gate) lee de ahí cómo arrancar el servidor. Por
  ejemplo, en opencode `"enabled": false` dentro de su entrada de `~/.config/opencode/opencode.json`;
  en codex, `enabled = false` en su tabla de `~/.codex/config.toml`. En otras herramientas, usa su opción de
  desactivar si conserva la entrada;
- si borras la entrada, la comentas o la tienes en un `.jsonc` con comentarios, el script responde
  `SONAR_SERVIDOR` («no se encontró el servidor MCP…»). Alternativa: las variables `SONARQUBE_MCP_JAR`,
  `SONARQUBE_URL` y `SONARQUBE_TOKEN`, o un JSON propio con la entrada apuntado por `SONARQUBE_MCP_CONFIG`;
- no tengas a la vez el MCP activo y el script usando la misma carpeta de almacenamiento del servidor MCP
  de SonarQube (la indicada por `SONARQUBE_STORAGE_PATH`, si se configura). El error `90028` indica
  que esa carpeta está bloqueada por otro proceso; si ves ese error o `MVStoreException`, cierra la
  herramienta que usa el MCP;
- en herramientas con aislamiento (codex `workspace-write`), el script necesita red, como el gate;
- no añadas a la lista de órdenes permitidas `sonar-mcp.mjs … --confirmar`: ese `--confirmar` lo escribe la IA, y
  cada escritura tiene que pasar por tu aprobación.

El plazo de conexión con Open Notebook es fijo: **5 segundos**; `documentacion.timeout_chat` no lo cambia. Una conexión
rechazada o bloqueada puede fallar al instante aunque el mensaje hable del plazo; subirlo no abre la
conexión. Las demás [herramientas necesarias](#requisitos) dependen del stack y el preflight indica cuál falta.

## 4. Cambiar algo después

Busca «Cambiarla después» en la ficha de la clave; solo admite valores vacíos cuando así lo indica.
Las claves obligatorias se completan desde el principio.

Estas categorías ayudan a elegir la tarea; las fichas no tienen cuatro textos fijos:

| Caso | Ejemplo | Qué haces |
|---|---|---|
| Basta editar stack.yaml | `documentacion.timeout_chat` | Cambia la espera de chat; se lee al usarla, sin regenerar. Para conexión, consulta [Conexión, permisos y SonarQube](#conexión-permisos-y-sonarqube). |
| Editar y regenerar, después adaptar el código existente | `backend.lombok`; también `integraciones.autenticacion` | Regenera y pide implement-microservice-feature para clases/dependencias; para activar Clerk, add-authentication. Aprueba el plan. |
| Editar sin regenerar, después adaptar artefactos | `devops.slack_canal` | Cambia el canal y pide implement-microservice-feature para actualizar el pipeline con un plan aprobado. |
| No se cambia | `version_esquema`, `proyecto.stack`, `backend.build`, `frontend.framework`, `base_de_datos.motor` | Conserva los valores que identifican este formato y stack; no sirven para migrar a otra tecnología. |

Regenerar **no renombra código, migra lockfiles, actualiza una base de datos real ni prepara `devops/`**;
esos trabajos necesitan su tarea y aprobación.

### Activar DevOps o cambiar sus valores

Si empezaste sin infraestructura, cambia `devops.infraestructura` a `jenkins-kubernetes`, completa
las claves que pida el generador y regenera. Después pide implement-microservice-feature para los
artefactos, o acepta esa parte del plan cuando una tarea de escritura te la ofrezca.

El preflight avisa del estado DevOps. Con tu «sí», el plan enumera los artefactos de **todos los
servicios y el gateway**, con sus entornos; no solo los de la feature actual. Change-version muestra
estos avisos como pendientes y no instala DevOps por ese motivo.

Las diferencias de `devops.*` con los artefactos existentes se deciden en el registro y se corrigen con plan aprobado.

### Activar autenticación o gestión de usuarios

Para activar Clerk, cambia `integraciones.autenticacion`, añade las claves requeridas, regenera y pide
add-authentication en back/front. Para gestión, elige `integraciones.gestion_usuarios` y regenera;
[Clerk](#gestión-de-usuarios-con-clerk) indica los contratos y el orden de tareas. Elegir `ninguna` no borra código ni datos:
retirarlos requiere una tarea aprobada.

### Cambiar una versión o un gestor

Pide change-version en los tres stacks; [Cambiar versiones](#cambiar-versiones) explica el alcance y tus pasos.

Para migrar de npm a pnpm o Yarn, usa implement-feature en el front. No es un cambio de versión.
Tienes un prompt en [Front: gestor de paquetes](#front-gestor-de-paquetes).

## 5. Temas por stack

Elige el tema de tu stack. Aquí están los detalles de operación; los workflows se eligen en el
[catálogo](#2-trabajar-con-los-workflows) y las decisiones generales se toman en [Cambiar algo después](#4-cambiar-algo-después).

### Back: servicios y DevOps

#### DevOps y Jenkins

Configura tú el job, las máquinas, credenciales y registry; la IA prepara/valida artefactos aprobados,
sin ejecutar Jenkins, Docker ni kubectl. Haz coincidir Script Path con `devops.jenkinsfile`, por ejemplo
`devops/Jenkinsfile`: cambiar la clave no renombra el archivo ni modifica Jenkins. Puedes conservar
el pipeline existente y pedir sus cambios en el plan.

Las tres etiquetas eligen coordinación, compilación/análisis e imágenes; cada ejecutor permite un trabajo.
Si usas una etiqueta para todo, el nodo necesita **al menos tres ejecutores disponibles**.
Mantén un único `devops.java_home_nodo`, existente donde se compila; no crees una herramienta JDK en Jenkins.

Para el contenedor, la IA propone la carpeta que crea el tar de `devops.jdk_url` bajo `/opt/` y tú confirmas.
Si el tar de `jdk_url` crea `jdk-27.0.1.0.3/` bajo `/opt/`, confirma esa carpeta para JAVA_HOME.
Ejemplo de forma; sustituye la URL de ejemplo por tu descarga oficial confirmada:

```yaml
devops:
  jdk_url: https://descargas.example.invalid/openjdk-27.0.1.0.3_linux-x64_bin.tar.gz
  java_home_contenedor: /opt/jdk-27.0.1.0.3
```

Confirma que esa es la carpeta del tar de tu URL oficial; si no se sabe, la IA pregunta sin descargarlo.
Los artefactos usan después el stack; la ruta del nodo es independiente. Ejemplo de etiquetas:

```yaml
devops:
  nodos:
    general: jenkins-general
    compilacion: jenkins-compilacion
    docker: jenkins-imagenes
```

##### Entornos y promoción

Declara tus entornos bajo `devops.entornos`. El nombre de la entrada es su carpeta, no necesariamente
la rama: una entrada `development` prepara `devops/development/`. La tabla se revisa antes del plan.

| Dato de cada entorno | Para qué sirve |
|---|---|
| `rama` | Rama exacta o prefijo como `feature/*`; dos entornos no pueden solaparse. |
| `sufijo` | Distingue perfiles, recursos y nombres de variables; no se repite entre entornos. |
| `credencial_kubeconfig` | Solo el ID de la credencial de Jenkins; nunca su contenido. |
| `imagen` | Construir una imagen o promover una existente; solo puede haber un constructor. |
| `desplegar` | Decide si hay despliegue; promover exige true. Un constructor puede no desplegar. |
| `replicas`, `cpu_*`, `memoria_*` | Recursos de los entornos que despliegan. |
| `nodo_puerto_base`, `gateway_nodo_puerto` | Puertos externos; para gateway hay un valor específico. |
| `cors_origenes`, `clerk_issuer_uri` | Orígenes del front e issuer públicos del entorno cuando correspondan. |

Por ejemplo, development construye y despliega; main promueve. Completa los recursos de la tabla
para cada destino que despliegue. Este fragmento muestra los valores literales de `imagen` y los IDs:
`kubeconfig-dev` y `kubeconfig-main` son IDs de ejemplo; sustitúyelos por los de tus credenciales de Jenkins.

```yaml
devops:
  entornos:
    development:
      rama: development
      sufijo: dev
      credencial_kubeconfig: kubeconfig-dev
      imagen: construir
      desplegar: true
    main:
      rama: main
      sufijo: prod
      credencial_kubeconfig: kubeconfig-main
      imagen: promover
      desplegar: true
```

Una rama sin entrada sigue compilando y pasando SonarQube. Sin despliegue, un constructor conserva
pipeline y Dockerfile, pero no recibe manifiestos ni cuentas; JDK, registry y Slack son comunes.

El constructor sube imágenes `X.Y.Z-<commit>`; promoción se detiene sin imagen válida con el último cambio.
Solo el constructor, ante cambios solo de manifiestos sin imagen nueva, puede usar un tag histórico
si aún no hay tags con commit para ese servicio, con aviso `MIGRACION`. Antes del primer despliegue
de main necesitas una imagen nueva con commit de **cada servicio**.

Quita shallow clone: un historial incompleto produce `HISTORIAL_INCOMPLETO`; promueve con merge,
sin squash/rebase. Configura los IDs `dockerhub_integration_credentials`,
`sonarqube-webhook-integration-secret` y los kubeconfig por entorno, de tipo archivo;
varios entornos del mismo clúster pueden compartirlos. Configura la instalación de SonarQube en
Jenkins con el nombre `SonarQubeServer`, usado por `withSonarQubeEnv` en el Jenkinsfile.

Si ya hay pipeline, añadir un servicio actualiza su lista aprobada. Migrar su lógica o mapa de
entornos requiere que el plan enumere ese cambio y su diff; no se sustituye a ciegas.

##### Nombres y recursos

Consulta los nombres calculados antes de aprobar una generación o migración:

```bash
python3 -I -B .agents/scripts/servicios.py nombres
```

La **base del nombre** sale de `rootProject.name` sin el `-service` final, también en el gateway. La carpeta,
el nombre del proyecto y el context-path pueden ser diferentes; este último solo define URL y rutas, no recursos Kubernetes.

Por ejemplo, nombre `pedidos-service`, base del nombre `pedidos`, sufijo `dev` y context-path `/ventas`:

| Qué | Resultado |
|---|---|
| Service Kubernetes | `pedidos-dev-service` |
| Deployment | `pedidos-dev-deployment` |
| Secret de base de datos | `pedidos-dev-service-db-secret` |
| Archivo de ese secret | `secrets-pedidos-dev.yaml` |
| `spring.application.name` | `pedidos-service-dev` |
| Ruta del gateway | `/ventas/**` hacia `lb://pedidos-dev-service` |

`spring.application.name` y el Service Kubernetes no son intercambiables; el gateway usa su propia
base del nombre. El plan lista archivos viejos/nuevos y campos a cambiar: los recursos viejos
siguen en el clúster hasta que **tú los borres**; prepara los secrets con los nombres nuevos, sin valores.

Un servicio desplegable sin base de datos distinto del gateway se bloquea: no hay plantilla para él.
Con DevOps, un JAR cuyo nombre de artefacto difiere de `rootProject.name` entra al plan para alinearlo;
`NOMBRE_JAR` bloquea en cierre/estricto si sigue distinto. Un JAR no determinable también impide generar.

`getServices()` se lee del disco sin ejecutar Gradle. Para un servicio en disco, `name`/`directory`
incoherentes bloquean; una carpeta `directory` inexistente solo avisa. Las diferencias se proponen en un
plan; claves repetidas o entradas de ejemplo también bloquean la validación.

##### SonarQube por servicio

Compara la clave y su origen mostrados por `servicios.py nombres` con tu proyecto SonarQube.
El orden es: systemProp del servicio, propiedad literal del build, `group:nombre`, o nombre.
Con DevOps, un `-Dsonar.projectKey` en Jenkinsfile deja la clave sin determinar. Una propiedad externa
al repositorio puede cambiar la clave efectiva y este cálculo no la ve.

Si la clave no se puede determinar, se informa el motivo y el análisis local sigue **sin projectKey**.
Ese mensaje es distinto de «proyecto ausente»; no crees un proyecto adivinando la clave.
Para la dirección del servidor, `SONARQUBE_URL` tiene prioridad sobre `sonarqube.url`.

La revisión solo cuenta si ejecutó el gate: deja un recibo con los archivos analizados y el workflow lo
comprueba con `sonar-diff-gate.mjs --comprobar-recibo`. Si el gate no puede ejecutarse, la revisión queda
`BLOCKED (infraestructura)`, no se aprueba a mano. Si el error dice `CancellationException`, el mensaje te
indica revisar el log del MCP de SonarQube y, si su base local está dañada, renombrarla y reintentar.

##### Archivos que aplicas tú

Revisa las rutas que el plan propone crear. En `devops/<carpeta>/account/`, solo se siembran archivos
ausentes y aprobados; los existentes no se abren ni sobrescriben, incluidos los enlaces.

| Archivo | Qué prepara la IA | Qué haces tú |
|---|---|---|
| `secrets-<base>-<sufijo>.yaml` | Secret de base de datos con cinco campos vacíos. | Rellenas valores en tu entorno y lo aplicas. |
| `rbac.yaml` | Cuenta y permisos de discovery al generar gateway. | Lo aplicas una vez por clúster y ajustas permisos. |
| `jenkins-account.yaml` | Cuenta Jenkins y sus permisos. | Lo aplicas una vez por clúster y ajustas permisos. |
| `secrets-jenkins-account.yaml` | Solicitud de token de cuenta, sin token ni datos incluidos. | Lo aplicas, obtienes el token y configuras kubeconfig/credencial Jenkins. |

Solo los secrets exigen ignore de Git. `bash .agents/scripts/preparar-proyecto.sh` añade la línea
`devops/*/account/` al `.gitignore` y el preflight la exige. RBAC y la cuenta Jenkins no lo exigen.
Si ya hay secrets en el índice, el script lo avisa con una línea que empieza por `Usuario:` y la lista
de rutas; no toca el índice ni lee los archivos. Tú los sacas con `git rm --cached <ruta>` y haces commit.
`git rm --cached` no borra el historial: si llegaron a un remoto, rota esas credenciales.

Los cinco nombres de variables de base de datos son `DB_HOST_<SUFIJO>`, `DB_PORT_<SUFIJO>`,
`DB_NAME_<SUFIJO>`, `USER_NAME_DB_<SUFIJO>` y `PASSWORD_DB_<SUFIJO>`.
El servicio de gestión puede añadir `CLERK_SECRET_KEY`, `CLERK_WEBHOOK_SIGNING_SECRET` y, con
organizaciones, `CLERK_DEFAULT_INVITER_USER_ID`, conforme al contrato aprobado. No se crea por ello un
secret separado de Clerk. Si el archivo ya existe, tú añades las claves necesarias.

Tú aplicas los archivos, obtienes el token y configuras kubeconfig; la IA no ejecuta esos pasos.
Como alternativa para secrets, tú completas el comando de creación que imprime actualizar.py.

#### Servicios y gateway

Trae el primer servicio de Initializr con los datos de tu stack que da la IA: Gradle Groovy, Java, Jar,
versiones, group, artifact, paquete y dependencias de tus opciones. El paquete usa group y base del
nombre sin guiones; consulta `.agents/skills/service-creator/references/servicio-initializr.md`.
Si no ofrece tu versión, elige la más cercana; incorporar propone los ajustes. Descomprime una carpeta
por servicio en la raíz y pide incorporate-service. Los siguientes puedes traerlos igual o pedirlos
con implement-microservice-feature, que copia el wrapper de uno existente sin sobrescribir negocio.

Puedes ver servicios sin puerto declarado con:

```bash
python3 -I -B .agents/scripts/servicios.py listar
```

La salida identifica servicio, nombre, base del nombre, group, contexto y puertos. Si `puerto:` queda vacío,
falta un puerto declarado que incorporar al plan; no supongas un valor por defecto.

Si hay dos o más servicios y `backend.gateway` es `null`, el plan puede proponer un gateway con
nombre, carpeta y puerto. Revisa antes CORS y, con Clerk, issuer. El gateway nuevo se crea sin Lombok;
si incorporas uno con dependencia Lombok sin usar, el plan te pregunta si quitarla.

Tras crear el gateway, el workflow te pedirá actualizar `backend.gateway` y regenerar: **hazlo**.
También puede pedirlo al completar CORS/issuer, aunque las fichas no lo exijan por esos valores solos.
Las rutas siguen al context-path: `servicios.py validar-gateway` compara path, destino y `X-Gateway`
opcional; el plan corrige sin duplicar y sustituye sufijos a mano por los del perfil.

`{AliasPascal}` es la base del nombre del servicio en PascalCase: con `pedidos`, el patrón
`nomenclatura.clase_aplicacion` da `PedidosServiceApplication`. Una clase antigua ligada al contexto
puede aparecer como diferencia legítima; tú decides su cambio en el plan.

##### Perfiles y variables

Elige `backend.perfil_local` distinto de los sufijos de entorno: por ejemplo feature frente a dev/prod.
`application.yaml` activa el local y conserva lo compartido; se prepara `application-<perfil_local>.yaml`
y, con Kubernetes, uno por sufijo. Sin infraestructura bastan el compartido y el local.
Si faltan perfiles del servicio tocado, entran siempre al plan aunque hubiera un «no»; en los demás,
eliges sí/no/para revisión. Change-version solo los informa, no los crea. Las variables se listan por
entorno y nombre; tú configuras valores en la terminal o en secrets.

#### Compilar en local

Declara en `backend.jdk_ruta_desarrollo` la ruta de un JDK instalado compatible con `backend.java`,
por ejemplo `/opt/jdks/jdk-27`. Es independiente del JDK de Jenkins y también existe sin DevOps.
Si solo cambia la carpeta, pide implement-microservice-feature; si cambia Java, change-version.

El plan escribe solo `org.gradle.java.installations.paths` en el `gradle.properties` versionado,
sin mostrar otras propiedades. El comando acepta uno o varios servicios aprobados:

```bash
python3 -I -B .agents/scripts/servicios.py escribir-jdk-ruta <servicio>...
```

Con `null` no escribe, modifica, compara ni borra la línea anterior. Rechaza continuaciones de varias
líneas, formatos no soportados y escritura mediante enlace simbólico; su corrección pasa por el plan.
La IA espera que confirmes la ruta nueva: no inventa una instalación.

Autoriza Gradle cuando la tarea lo necesite. Antes de pedirlo, change-version informa del perfil activo
y las variables por nombre. Separa fallos de compilación de entorno, como una base de datos inaccesible;
que compile no demuestra que las pruebas con conexiones reales puedan ejecutarse.

### Front: gestor de paquetes

Declara tu gestor en `frontend.gestor_paquetes`. Elige conservar el detectado si no quieres migrar.
El preflight selecciona el ejecutor local de revisión según ese gestor y comprueba dependencias.

| Gestor | Lockfile de la raíz |
|---|---|
| npm | `package-lock.json` |
| pnpm | `pnpm-lock.yaml` |
| Yarn | `yarn.lock` |

Varios locks producen conflicto aunque uno coincida; sin lock no se determina el gestor por esa evidencia.
Yarn PnP usa `.pnp.cjs` en vez de necesitar `node_modules`.

Cambiar la clave no migra dependencias ni locks. Pide implement-feature para proponer comandos según
la versión del gestor, lock final, retirada de locks incompatibles, scripts/CI/documentación y pruebas.
La tarea no instala el gestor por su cuenta; instalar o descargar dependencias requiere tu permiso.
No se marca aplicado hasta verificar un único lock correcto.

Puedes pegar este prompt de migración y concretar la petición en implement-feature:

```text
Quiero migrar este front al gestor declarado en frontend.gestor_paquetes de stack.yaml. Comprueba registro y lockfiles raíz; presenta detectado/destino, conflictos y archivos. Prepara con implement-feature un plan con comandos exactos compatibles con la versión del gestor, lock final, retirada de locks incompatibles y verificación. Pide aprobación y permiso antes de instalar o descargar. No edites stack.yaml ni instales el gestor; registra sí / no / para revisión y aplicado solo tras verificar.
```

Las rutas de feature, `file-writer` y el cierre usan el gestor de `frontend.gestor_paquetes` para
instalar, compilar, arrancar y elegir el lockfile. Limitación conocida: `test-engineer` y algunos
ejemplos usan `npm test`; con pnpm o Yarn, la IA debe adaptar esas órdenes al gestor declarado.

### SQL: versión y pruebas

Declara solo conexiones que permitas usar en `conexiones`. Con una entrada se usa esa; con dos o más
la IA pregunta cuál. Con `{}` no se llama a la base de datos real, aunque el servidor MCP exponga otras.
Los pasos que necesitan ejecutar en ella se detienen; el trabajo local de change-version puede seguir.

En las entradas de build-database-feature, add-user-management y change-version se solicita
`SELECT VERSION()` en solo lectura **antes del preflight**, si hay conexión. Se extrae la versión
normalizada sin guardar ni pasar la respuesta cruda. El dato real es efímero.

Si falla una conexión declarada, feature y add-user-management se detienen. Change-version informa
que no pudo comprobar la versión y sigue sin ese dato. Si la respuesta no permite normalizar versión,
se avisa y se omite el dato, sin adivinarlo.

La precisión declarada importa: `8.10` admite parches de esa serie; `8.10.1` exige ese parche.
Se conserva el texto de la versión, sin convertir `8.10` en `8.1`. Los workflows documentales y los
cierres no vuelven a pedir ese dato como condición universal.

Antes de ejecutar SQL, un control automático revisa los objetos tocados y bloquea los problemas nuevos.
Lo que no sabe interpretar se lista aparte en la comprobación del registro (`registro-stack.py`);
que no haya hallazgos no significa que se revisara todo.

Los notebooks se persisten con las herramientas del flujo, no editando su YAML a mano. La IA excluye
datos de prueba antes de leer; los programas del sandbox pueden cargarlos internamente para probar.

Las pruebas en contenedor requieren permiso e imagen **ya local**. Si falta, tú preparas la imagen;
la IA no descarga otra por su cuenta. Si `SQL_SANDBOX_IMAGE` fuerza una diferente, te pide retirarla
o alinearla con el stack, sin editar configuraciones privadas de herramientas.

### Varios stacks

#### Gestión de usuarios con Clerk

Elige el mismo modelo de `integraciones.gestion_usuarios` en tus proyectos; back/front exigen Clerk.
Si trabajas solo con un stack y no hay contrato anterior, el diseño declara sus supuestos.

| Valor | Resultado |
|---|---|
| `ninguna` | No instala gestión. Con Clerk, el front puede tener su núcleo de acceso y envío de token. |
| `organizaciones` | Cada perfil pertenece a una organización; la invitación y el evento de membresía lo vinculan. SQL pregunta si usar tabla de organizaciones nueva o existente. |
| `aplicacion` | Invita a la aplicación sin organizaciones; el evento de usuario creado lo vincula. |

Los perfiles tienen campos mínimos y estados PENDIENTE, INVITADO_A_CLERK, ACTIVO e INACTIVO; el
pre-registro público crea pendiente sin darlo de alta en Clerk. Configura Clerk **solo por invitación**:
sin roles, cualquier sesión administra perfiles; inactivarlos no cierra sesiones abiertas de Clerk.

Usa add-user-management en orden **SQL → back → front**: lleva el contrato de nombres físicos de SQL
al back y su contrato API al front para capas/pantallas; no buscan contratos en otros repositorios.

Tú exportas las variables requeridas y, con Kubernetes, completas/aplicas los secrets listados en
[Archivos que aplicas tú](#archivos-que-aplicas-tú). Para activar después o retirar la integración,
sigue [Activar autenticación o gestión de usuarios](#activar-autenticación-o-gestión-de-usuarios).

#### Documentación con Open Notebook

Prepara Open Notebook con modelos predeterminados de chat, transformación y embeddings. Declara
`documentacion.url_api` y el nombre de variable de contraseña en `documentacion.variable_password`;
los `documentacion.modelo_*` en null usan predeterminados. La IA no cambia modelos ni protección.

Consulta la API sin MCP documental, con preguntas genéricas: nunca código, tablas, datos ni decisiones
del proyecto. El preflight comprueba cobertura y fuentes; no las carga.

Pide preparar-documentacion: apruebas fuentes por tecnología/versión y crea o reutiliza su notebook.
Comprueba correspondencia y descarta otra serie o notas de otro parche aunque las aprobaras;
lista fuentes aceptadas, descartadas y pendientes.

Antes de asociar o archivar, la IA te muestra la vista previa (qué cambia en el registro y, al archivar,
qué servicios aún usan el notebook); solo con tu aprobación lo confirma. Al terminar, haces tú el commit
de los archivos del registro antes del preflight de cierre.

Los servicios de igual versión comparten notebook. El script mantiene `.agents/documentacion.json`
y `.agents/documentacion.md`: no los edites. Solo se archiva si nadie usa el notebook; no se borra,
y al volver atrás se reactiva sin duplicarlo.

Usa «Ampliar el catálogo del proyecto» para otra librería detectada: apruebas detector/fuentes y diff;
el script escribe `.agents/catalogo-proyecto.json`, protegido del generador. No redefine tecnologías
del catálogo inicial; SQL solo admite añadir fuentes MySQL, no habilitar otro motor.

Lombok está gestionado por BOM: resuelve su versión con `documentacion.py resolver-bom`, con aprobación.
En preparar-documentacion se hace antes del notebook; en change-version, después de escribir los builds.
Si falta una fuente válida, aporta URL HTTPS o archivo público externo: apruebas procedencia y hash;
una correspondencia ambigua pide confirmación separada y una versión incompatible se rechaza.

La carga espera procesamiento/indexación y avisa si sigue pendiente. Las notas verificadas no consumen
modelo; solo las citas verificadas entran al plan y lo no comprobable se muestra aparte.

| Diagnóstico de documentación | Qué revisas |
|---|---|
| `API_CAIDA` | API y acceso local; si está arrancada, aislamiento de la herramienta. |
| `AUTENTICACION` | Nombre de variable y configuración de contraseña, sin compartir valores. |
| `MODELO_CONFIG` | Modelo disponible y configurado en Open Notebook/proveedor. |
| `LIMITE_USO` | Cuota o límite del proveedor. |
| `MODELO_TIMEOUT` | Espera del modelo; no se reintenta automáticamente. |

Para acceso y espera, consulta [Conexión, permisos y SonarQube](#conexión-permisos-y-sonarqube); la API sin contraseña se avisa para que tú decidas su protección.

#### Cambiar versiones

Pide `.agents/workflows/change-version.md` para coordinar versión, documentación y los archivos
afectados. Vale para **back, front y SQL**. No alinees a mano builds/manifiestos para saltar el plan.

Por ejemplo, declaras Java 27 y Spring Boot 4.1.2 mientras el código usa 26/4.0.6. El workflow propone
el destino declarado con tabla antes/después. Si prefieres conservar el código, ajusta tú las claves de versión de `stack.yaml` para que coincidan con las del código.
Si ya coinciden y quieres otra versión, el plan enumera qué líneas del stack editarás tú y espera.
El mismo criterio se usa para Next y el destino MySQL, con sus diferencias de alcance.

Back alinea versiones compartidas entre servicios mediante inventario estático; front usa manifiestos/lock.
Prepara documentación de destino antes de escribir, pero la asocia después; [Open Notebook](#documentación-con-open-notebook) explica BOM.

Apruebas el plan completo. No edita `stack.yaml`: tú haces los cambios que indique (en SQL, cambiar
`base_de_datos.version` no exige regenerar). Si cambia Java, confirmas JDK local y DevOps; autorizas instalaciones y comprobaciones.

Verifica solo su cambio: versiones, compilación/tipos u objetos afectados y documentación propia.
Las pruebas completas son opcionales en back/front; fallos de entorno se informan aparte.
Perfiles, puertos y otros avisos ajenos quedan como pendientes con remedio; no se ocultan como éxito.
SQL no actualiza la base de datos real. Change-version no hace commit ni preflight de cierre:
tú haces commit y ejecutas `bash .agents/scripts/preflight.sh`.

## 6. Referencia

### Dónde vive cada cosa

| Lugar | Qué guarda / quién lo mantiene |
|---|---|
| `<KIT>/sources/<carpeta de tu stack>/.agents/` | Fuentes completas de cada stack, con opciones y marcas de filtrado; se mantienen en dotagents-kit. |
| `<tu proyecto>/.agents/` | Copia filtrada según stack.yaml; el generador prepara sus instrucciones. |
| `.agents/stack.yaml` | Decisiones del proyecto: las editas tú. |
| `.agents/rules/project.md` | Información particular del proyecto; se completa y mantiene fuera de la regeneración. |
| `.agent-runs/` | Planes, propuestas, informes e historial de ejecución de tareas. |
| `docs/decisiones-stack.md` | Decisiones sobre diferencias del código, escritas por la tarea dentro de un plan aprobado. |

El generador prepara instrucciones; las tareas escriben código/artefactos aprobados. Tú configuras
credenciales, servidores y despliegues.
Para las plantillas nuevas, consulta [el aviso del preflight](#si-pide-regenerar-o-avisa-de-plantillas-nuevas).

| Stack | Carpeta del stack | Opciones filtradas |
|---|---|---|
| `springboot` | `springboot-back` | Persistencia JPA/JDBC, Lombok, autenticación, DevOps y gestión de usuarios. |
| `nextjs` | `nextjs-front` | Notificaciones, API desde navegador/servidor, autenticación y gestión de usuarios. |
| `mysql` | `mysql-sql` | Gestión de usuarios. |

Los valores permitidos están en `.agents/config/opciones.yaml`. Back y front también tienen
`.agents/config/requisitos.yaml`: gestión de usuarios activa exige Clerk. SQL no tiene ese archivo.
Si una opción no está activa, sus archivos y ramas específicas no llegan al proyecto.

Cada `.agents` es independiente: puedes trabajar solo con SQL, back o front. Los scripts no garantizan
que proyectos separados coincidan entre sí; tú mantienes compatibles nombres, contratos y modelos.
Por ejemplo, cambiar la estrategia JPA del back no renombra las tablas de tu proyecto SQL.

### actualizar.py en detalle

Usa el comando de [Regenerar un proyecto existente](#regenerar-un-proyecto-existente).
El script elige fuentes por `proyecto.stack`, valida opciones/requisitos y prepara las instrucciones
según tu nomenclatura, incluido AGENTS.md; te muestra qué crea, modifica o retira antes de confirmar.

| Opción | Efecto |
|---|---|
| `--kit <ruta>` | Indica la carpeta que contiene sources; sin ella, pregunta la ruta. |
| `--simular` | Valida y muestra cambios/diffs sin escribir. |
| `--si` | Acepta sobrescrituras y confirmación final; no rellena ruta ni stack. No lo fuerces al regenerar. |
| `--proyecto <ruta>` | Elige el destino; sin ella, usa la carpeta actual de la terminal. |
| `--comprobar-referencias` / `--comprobar-cobertura` | Validan y siguen con la generación normal; combínalas con `--simular` para no escribir. |
| `--comprobar-fuentes <ruta>` | Solo valida las marcas de la carpeta de fuentes indicada y termina. |

`.agents/.generado.json` guarda las huellas; las confirmaciones de archivos editados están en
[Regenerar un proyecto existente](#regenerar-un-proyecto-existente).

El generador no sobrescribe tu stack ni un `rules/project.md` existente. Si este último falta, lo crea
con secciones «por completar». Protege también documentacion.json, documentacion.md y
catalogo-proyecto.json del proyecto.

#### Primera generación manual sin guía

Si prefieres configurar sin IA, crea `<tu proyecto>/.agents/` y ejecuta desde la raíz del proyecto:

```bash
python3 -I -B <KIT>/sources/<carpeta de tu stack>/.agents/actualizar.py \
  --kit <KIT>
```

Sin stack.yaml, pregunta el stack en terminal interactiva y se detiene: copia tú la plantilla de sources,
cambia los datos y vuelve a ejecutar; no la copia automáticamente. La generación incluye actualizar.py
para usar luego el comando corto. Sin carpeta `.agents/`, se para.

### Variables y avisos de credenciales

Revisa nombres y estado «definida/no definida» en el entorno del generador; tú configuras los valores fuera del chat y del stack.

- En back lista variables de servicios y autenticación cuando corresponde; con Kubernetes muestra
  ayuda por entorno para preparar secrets.
- En front lista autenticación y la URL API según navegador/servidor: `NEXT_PUBLIC_API_BASE_URL`
  o `API_BASE_URL`, para que prepares el entorno local.
- En SQL no solicita variables de credenciales de base por esta salida.

No pide, guarda ni imprime valores de variables. Si muestra «riesgo en claro» con archivo/línea/clave,
te señala una credencial literal para sustituirla por una variable y rotarla si era real.
«Riesgo:respaldo» significa que una variable de credencial tiene un valor alternativo escrito en el archivo: quítalo.

### Nomenclatura, fichas y datos del proyecto

Usa `.agents/config/claves.md` para consultar patrones, efectos y alternativas de cada clave.
SQL define nombres de tablas/columnas y prefijos; back, estrategia JPA/clase; front, capas y UI.
Conserva los comodines de los patrones; [Cambiar algo después](#4-cambiar-algo-después) indica cómo adaptarlos.

Completa `.agents/rules/project.md` con estructura, integraciones sin credenciales, estado del grafo y
archivos sensibles; el generador lo crea una vez y no lo sobrescribe. Puedes consultar como referencia
`<KIT>/ejemplos/<carpeta de tu stack>/project.md`: es un proyecto ficticio completado; no tienes que tocarlo.

### El índice de Codebase Memory

El índice vive en la caché de tu cuenta (`~/.cache/codebase-memory-mcp`), fuera del repositorio, y se crea una vez por cada copia del repositorio (clon o worktree). El preflight lo comprueba y, al empezar las tareas de código (grupo E), lo reindexa hasta 120 s; si no termina a tiempo, avisa y sigue con el índice anterior. Puedes ver el nombre del proyecto con `python3 -I -B .agents/scripts/codebase-memory.py --resolver` y listar los índices con `codebase-memory-mcp cli list_projects`. Un índice que sobra, por ejemplo de un clon borrado o movido, se borra con `codebase-memory-mcp cli delete_project --project <nombre>`.

### Migración a Codebase Memory

Renombra `herramientas.graphify` a `herramientas.codebase_memory` en `stack.yaml`. Ejecuta `bash .agents/scripts/preparar-proyecto.sh` para crear `.cbmignore`: copia también tus exclusiones de `.graphifyignore`. Revisa y confirma `.cbmignore` en Git; después puedes borrar `graphify-out/` y `.graphifyignore`. El índice es local: se crea una vez por cada copia del repositorio (clon o worktree).

Versión probada de la CLI: 0.12.1. Para actualizar, `codebase-memory-mcp update -y` imprime el comando del instalador que debes ejecutar.
