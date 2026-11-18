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
- **Servicio:** cada carpeta de aplicación con su `build.gradle`; reúne el código y las dependencias de una aplicación del back.
- **Gateway:** servicio de entrada que recibe peticiones y las dirige a los demás servicios del back.
- **Perfil de Spring:** nombre que selecciona una configuración de ejecución, por ejemplo `qa` usa `application-qa.yaml`.
- **CORS:** permiso que necesita el navegador para llamar a una API situada en otro origen, es decir, otra combinación de protocolo, servidor o puerto.
- **Etiqueta de nodo:** nombre con el que Jenkins selecciona una máquina para una etapa, por ejemplo `principal`.
- **Ejecutor:** plaza para un trabajo simultáneo en un nodo Jenkins; una máquina puede tener varias.
- **Script Path:** ruta del Jenkinsfile que la tarea de Jenkins debe ejecutar, por ejemplo `devops/Jenkinsfile`.
- **Gradle y `gradle.properties`:** Gradle compila el proyecto; `gradle.properties` declara propiedades de esa compilación, como la carpeta del JDK.
- **JAR:** archivo `.jar` que reúne el código Java compilado del servicio.
- **Clave de proyecto de SonarQube:** identificador con que SonarQube guarda el análisis de un servicio; se calcula desde el `build.gradle`, por ejemplo `com.ejemplo:pedidos`; ya no se declara en `stack.yaml`.
- **JDK:** herramientas de Java necesarias para compilar y ejecutar los servicios.
- **JPA:** forma de acceso a datos que relaciona objetos Java con tablas; Hibernate realiza esa correspondencia en estas plantillas.
- **JDBC:** acceso a la base de datos mediante llamadas SQL desde Java.
- **Jenkins:** servidor que automatiza pasos como compilar, construir imágenes y desplegar; esa secuencia es su pipeline.
- **Kubernetes:** sistema que mantiene aplicaciones ejecutándose en máquinas de un clúster, el conjunto de máquinas que comparten ese trabajo.
- **Imagen y contenedor:** la imagen empaqueta la aplicación y su entorno; el contenedor es una ejecución de ese paquete.
- **DevOps:** aquí, los archivos y pasos para construir imágenes y desplegar los servicios con Jenkins y Kubernetes.
- **Nodo:** máquina donde se ejecuta un trabajo de Jenkins o parte del clúster de Kubernetes.
- **Token:** dato que acredita la sesión de una persona al llamar a la API; se configura y maneja sin mostrar su contenido.
- **JWT:** tipo de token cuya identidad y emisor puede comprobar el back antes de aceptar una petición.
- **Clerk:** servicio de identidad que permite iniciar sesión y comprobar quién hace una petición.
- **SonarQube:** servidor que analiza el código y comunica problemas de calidad.
- **Base:** nombre de `rootProject.name` sin un `-service` final; identifica archivos y recursos también del gateway. El context-path solo forma URL.
- **`{AliasPascal}`:** hueco sustituido por la base con sus palabras empezando en mayúscula; por ejemplo `pedidos` da `Pedidos`.
- **Manifiesto:** archivo que describe un recurso que Kubernetes debe mantener, como las copias de un servicio.
- **Artefactos de DevOps:** archivos del despliegue, por ejemplo `Dockerfile`, el archivo indicado por `devops.jenkinsfile` y manifiestos.
- **Promover:** usar en un entorno posterior una imagen ya construida y probada, sin volver a construirla.
- **Kubeconfig:** archivo que permite a Jenkins conectarse al clúster; aquí solo se declara el ID de su credencial, no su contenido.
- **nodePort:** puerto por el que un recurso de Kubernetes queda accesible desde fuera del clúster.
- **Commit:** versión guardada de tus archivos en Git.
- **Rama:** línea de trabajo de Git, por ejemplo `development` o `feature/pedidos`.

Estas fichas explican tus decisiones de `stack.yaml`. Los ejemplos se adaptan a tu proyecto. Las alternativas siguen visibles y las claves sin uso se ocultan según tus opciones.

## version_esquema

**En resumen:** Identifica el formato de `stack.yaml`; déjalo como viene en el `stack.yaml` de ejemplo (`1`).

**Dónde se ve en tu proyecto:** Solo aparece en `stack.yaml`, por ejemplo `version_esquema: 1`. No es la versión de tu aplicación. El validador exige que exista la clave; cambiar el número no convierte un archivo de otro formato.

**Respaldo:** `scripts/stack.mjs`.

## proyecto.nombre

**En resumen:** Da una etiqueta reconocible a tu proyecto, por ejemplo `pedidos-back`.

**Dónde se ve en tu proyecto:** En `stack.yaml`, por ejemplo `nombre: pedidos-back`. Es una etiqueta para reconocer tu proyecto, no una orden para renombrar carpetas, paquetes o servicios.

**Para qué se usa:**
- El validador exige que exista la clave al revisar la configuración.
- Permite identificar el proyecto al leer su configuración; el nombre del código se decide en sus archivos.
- Las instrucciones de documentación de persistencia usan esta etiqueta para identificar el proyecto.

**Qué pasa si está mal:** Si falta, el validador impide continuar. Una etiqueta equivocada puede confundirte al revisar la configuración, aunque no renombre tu aplicación.

**Cambiarla después:** Edita `stack.yaml`; no requiere regenerar ni ejecutar otra tarea por esta etiqueta.

**Si conservas el dato confirmado (por ejemplo, `pedidos-back`):** Por ejemplo, reconoces este proyecto como `pedidos-back` cuando revisas `stack.yaml`. Recomendado: un nombre que identifique el proyecto que ya tienes; confirma el detectado antes de usarlo.

**Respaldo:** `scripts/stack.mjs`.

<!-- si backend.persistencia=jpa -->
**Respaldo adicional:** skills/jpa-data-expert/SKILL.md.

<!-- fin -->
## proyecto.stack

**En resumen:** Identifica el tipo de proyecto al que pertenece este `.agents`; conserva `springboot`.

**Dónde se ve en tu proyecto:** En `stack.yaml`, por ejemplo `stack: springboot`. El generador elige sus plantillas con este dato y el validador rechaza otro tipo de proyecto. Cambiarlo no transforma la tecnología del código existente.

**Respaldo:** `actualizar.py`; `scripts/stack.mjs`.

## backend.group

**En resumen:** Define la raíz de los paquetes Java y el identificador de grupo de tus servicios.

**Dónde se ve en tu proyecto:** En `build.gradle`, por ejemplo `group = "com.ejemplo"`; un servicio de base `pedidos` propone paquetes como `com.ejemplo.pedidos`; la base se añade sin guiones. Spring Initializr, la página que crea un servicio inicial, utiliza ese grupo al prepararlo. Por ejemplo, `package com.ejemplo.pedidos;` utiliza ese paquete.

**Para qué se usa:**
- Se usa al crear servicios y al adaptar uno incorporado a las convenciones del proyecto.
- Si difiere `backend.group` del código, la tarea te ofrece corregir group en su plan, conservar la diferencia o dejarla para revisión.

**Qué pasa si está mal:** Un grupo con guiones o segmentos inválidos detiene el validador. Uno diferente del código requiere cambiar paquetes y referencias mediante un plan aprobado.

**Cambiarla después:** Edita `stack.yaml`, sin regenerar. Usa la tarea `implement-microservice-feature` (propone cambios del back y espera tu aprobación) o la tarea `incorporate-service` (adapta un servicio con un plan aprobado) para llevarlo al código.

**Si conservas el dato confirmado (por ejemplo, `com.ejemplo`):** Por ejemplo, el grupo y los paquetes de pedidos empiezan por `com.ejemplo`. Recomendado: conserva el grupo detectado en tus servicios para evitar renombrar todos sus paquetes; sin servicios, acuerda la raíz de tu organización.

**Respaldo:** `scripts/stack.mjs`; `skills/service-creator/SKILL.md`; `workflows/incorporate-service.md`; `scripts/registro_detectores.py`.

## backend.java

**En resumen:** Fija la versión mayor de Java que deben declarar todos los servicios.

**Dónde se ve en tu proyecto:** En `build.gradle`, por ejemplo `JavaLanguageVersion.of(27)` corresponde a `java: 27`. Es el número mayor, no la ruta del JDK, las herramientas necesarias para compilar y ejecutar Java.

**Para qué se usa:**
- Las plantillas de servicios y las instrucciones de Spring Initializr, la página que crea el servicio inicial, usan esa versión.
- La comprobación previa compara las versiones declaradas y comprueba que haya un JDK adecuado para compilar.
- El inventario señala versiones no resolubles; la comparación también detecta diferencias de versiones literales de librerías, plugins y BOM compartidos entre servicios; si difieren, se detiene la revisión.
- El control compara el wrapper de Gradle de cada servicio con el mínimo para ejecutar esa Java de `config/gradle-java.json`. Subir Java puede exigir subir también todos los wrappers afectados. Sin DevOps se aplica el mismo mínimo: puede ser más estricto de lo necesario si Gradle corre con otro Java y solo compila con el toolchain declarado.

**Qué pasa si está mal:** Si un servicio declara otra versión o falta el JDK necesario, la comprobación previa se detiene. Cambiar el número no instala Java ni actualiza los archivos del servicio.

**Cambiarla después:** Edita `stack.yaml`, sin regenerar por esta clave, y usa la tarea `change-version` (propone alinear Java y su documentación con un plan aprobado). Revisa también `backend.jdk_ruta_desarrollo`. Con Jenkins y Kubernetes, revisa en el mismo cambio las rutas y descarga del JDK. Incluye el wrapper de cada servicio en la revisión de compatibilidad y en el cambio aprobado si necesita actualizarse.

**Si declaras la versión de tus servicios:** Por ejemplo, copias el `27` de `JavaLanguageVersion.of(27)` si tu código usa esa versión. Recomendado: conserva la versión detectada si no buscas actualizar: evita cambiar compatibilidad y herramientas sin necesidad.

**Si declaras otra versión mayor:** Por ejemplo, actualizas los servicios de pedidos y sus herramientas a otra versión acordada. Conviene si necesitas sus capacidades y aprobarás el cambio coordinado del código, JDK y documentación.

**Respaldo:** `scripts/preflight_stack.py`; `scripts/comprobar-versiones.mjs`; `config/gradle-java.json`; `workflows/change-version.md`; `skills/service-creator/assets/servicio/build.template.gradle`.

## backend.spring_boot

**En resumen:** Fija la versión de Spring Boot que deben usar los servicios del proyecto.

**Dónde se ve en tu proyecto:** En `build.gradle`, por ejemplo `id "org.springframework.boot" version "3.4.2"`. Esa cifra es la versión del plugin de Spring Boot, no la de Java ni la de Gradle.

**Para qué se usa:**
- Las plantillas proponen esa versión al crear servicios.
- La comprobación previa compara las declaraciones de los servicios y su coincidencia con `stack.yaml`; las versiones compartidas no se cambian por separado.
- El inventario señala versiones no resolubles; la comparación también detecta diferencias de versiones literales de librerías, plugins y BOM compartidos entre servicios; si difieren, se detiene la revisión.

**Qué pasa si está mal:** Una versión diferente del código detiene la comprobación previa. Una declaración calculada que no pueda interpretarse se informa y requiere confirmar la versión declarada.

**Cambiarla después:** Edita `stack.yaml`, sin regenerar por esta clave, y usa la tarea `change-version` (alinea servicios, dependencias y documentación con un plan aprobado). Prepara fuentes sobre las capacidades y compatibilidad de la versión nueva.

**Si declaras la versión detectada:** Por ejemplo, copias `3.4.2` si es la versión literal que usan tus servicios. Recomendado: conserva la versión del código si no quieres actualizar; mantienes las dependencias y compatibilidad existentes.

**Si declaras otra versión de destino:** Por ejemplo, todos los servicios afectados de pedidos cambian de versión en la misma tarea. Conviene si quieres actualizar Spring Boot y revisar también sus cambios de compatibilidad y pruebas.

**Respaldo:** `scripts/comprobar-versiones.mjs`; `scripts/inventario-versiones.mjs`; `workflows/change-version.md`.

## backend.build

**En resumen:** Identifica Gradle como la herramienta de construcción de cada servicio; conserva `gradle`.

**Dónde se ve en tu proyecto:** Cada carpeta de servicio tiene `build.gradle` y `settings.gradle`, por ejemplo `pedidos-service/build.gradle`. No hay una construcción global seleccionable con esta clave. Cambiar su texto no convierte los servicios a otra herramienta. Al crear un servicio inicial se elige Gradle con Groovy.

**Respaldo:** `scripts/stack.mjs`; `skills/service-creator/SKILL.md`.

## backend.gateway

**En resumen:** Nombra la carpeta del gateway existente o pendiente de crear; `null` indica que todavía no se ha acordado una carpeta.

**Dónde se ve en tu proyecto:** Por ejemplo, `gateway: entrada-service` identifica la carpeta y su futuro o actual `settings.gradle`. No es la URL del navegador. Su dependencia es `spring-cloud-starter-gateway-server-webflux`.

**Para qué se usa:**
- Guía las propuestas de comunicación y rutas. Declara la carpeta antes de crearla; durante ese intervalo el aviso «backend.gateway declarado; carpeta pendiente de crear» es informativo y no pide volver a null.
<!-- si devops.infraestructura=jenkins-kubernetes -->
- Distingue el gateway sin base de datos de los demás servicios; la base sale de `rootProject.name` sin `-service`. Decláralo junto con `gateway_nodo_puerto` y `cors_origenes` de cada entorno con `desplegar: true`. Sus fichas por entorno solo aparecen al regenerar con gateway declarado.
<!-- si devops.infraestructura=ninguna -->
- Identifica el punto de entrada local; no hay claves por entorno.
<!-- fin -->
- Si ya hay carpeta y difiere del código, la tarea propone alinear el gateway para tu aprobación; una carpeta pendiente de crear se conserva declarada.

**Qué pasa si está mal:** Un nombre equivocado dirige cambios a otra carpeta. `servicios.py nombres` devuelve la identidad; `validar-gateway` comprueba las rutas solo cuando existe la carpeta. Una errata permanente también queda como aviso informativo: revisa el nombre.

**Cambiarla después:** Si se propone crear el gateway, la primera ejecución entrega «Antes de crear el gateway» y termina bloqueada antes de aprobar o escribir archivos del proyecto. Edita tú stack.yaml y relanza la tarea: la segunda ejecución rehace el plan completo y propone crear la carpeta ya declarada. No es obligatorio regenerar para validar estas claves; regenerar solo actualiza sus fichas. Para cambiar un gateway existente, edita stack.yaml y pide un plan de adaptación aprobado con `incorporate-service` o `implement-microservice-feature`.
<!-- si devops.infraestructura=jenkins-kubernetes -->
Declara en cada entorno desplegable su puerto explícito y los orígenes públicos del front. Elige 30080, 30680... de la plantilla si está entre 30000 y 32767, fuera de todos los rangos de servicios desplegables y distinto de los otros gateways; si no, desde `nodo_puerto_base - 1` baja de uno en uno hasta cumplirlo. Cada rango va de `nodo_puerto_base + min(0, offsets)` a `nodo_puerto_base + max(0, offsets)`, con `offset = puerto efectivo - 8080`, incluidos los servicios del plan. Si no hay puerto admisible, detente. El plan muestra el cálculo y pide los orígenes desconocidos, sin inventarlos.
<!-- si devops.infraestructura=ninguna -->
Antes de crear la carpeta solo se declara `backend.gateway`; acuerda también CORS global e issuer cuando apliquen.
<!-- fin -->

**Si conservas lo detectado en tu código (por ejemplo, `entrada-service`):** Conserva el gateway real. Si no hay ninguno, usa null mientras no se haya propuesto una carpeta; cuando la tarea te presente «Antes de crear el gateway», declara la carpeta propuesta y relanza antes de aprobar la creación.

**Si eliges `null`:** Aún no hay una carpeta acordada para el punto de entrada. Al pasar a varios servicios, la tarea puede proponerla y pedir que la declares antes de crearla. No vuelvas a null para silenciar el aviso de carpeta pendiente.

**Respaldo:** `scripts/stack.mjs`; `scripts/servicios.py`; `scripts/registro_detectores.py`; `workflows/incorporate-service.md`.

## backend.cors_origenes

**En resumen:** Enumera desde qué direcciones del front puede llamar el navegador al gateway en local.

**Dónde se ve en tu proyecto:** Por ejemplo, `[http://localhost:3100]` permite el origen donde abres pedidos. Se propone en `CorsConfig.java`, en llamadas `corsConfig.addAllowedOrigin(...)`.

**Para qué se usa:**
- El gateway propuesto permite esas direcciones mediante CORS.
- Con Kubernetes, esta lista sigue valiendo en local; cada entorno usa sus propios `cors_origenes`.
- Si difiere `backend.cors_origenes` del código, la tarea te ofrece corregir cors origenes en su plan, conservar la diferencia o dejarla para revisión.

**Qué pasa si está mal:** Una dirección incorrecta deja al navegador bloqueando las llamadas. `[]` no permite todos los sitios: falta acordar los orígenes antes de crear el gateway.

**Cambiarla después:** Edita `stack.yaml`, sin regenerar, y usa la tarea `implement-microservice-feature` (propone cambios del back y espera tu aprobación) para adaptar el gateway; regenerar instrucciones no cambia su configuración Java.

**Si declaras `[http://localhost:3100]`:** Por ejemplo, el navegador permite llamar al gateway desde el front de pedidos abierto en ese origen. Recomendado: usa los orígenes reales de tu front, detectados o confirmados; no añadas sitios que no necesitan acceso.

**Si eliges `[]`:** Por ejemplo, no autorizas ningún origen mediante esa lista y la propuesta de crear el gateway pide completarla. Conviene si todavía no tienes gateway ni has acordado dónde se abrirá el front; tendrás que resolverlo antes de crearlo.

**Respaldo:** `skills/service-creator/assets/gateway/CorsConfig.template.java`; `scripts/registro_detectores.py`; `workflows/incorporate-service.md`.

## backend.persistencia

**En resumen:** Decide cómo acceden los servicios a sus datos: mediante JPA o JDBC.

**Dónde se ve en tu proyecto:** En `build.gradle`, por ejemplo la dependencia `spring-boot-starter-data-jpa` identifica JPA; `spring-boot-starter-jdbc`, JDBC. La opción debe corresponder al código de acceso a datos de tus servicios.

**Para qué se usa:**
- Selecciona instrucciones, dependencias y plantillas de persistencia.
- Si difiere `backend.persistencia` del código, la tarea te ofrece corregir persistencia en su plan, conservar la diferencia o dejarla para revisión.

**Qué pasa si está mal:** Una opción ajena al código puede producir propuestas con dependencias o formas de acceso que el servicio no usa. Cambiarla no convierte los repositorios existentes.

**Cambiarla después:** Edita `stack.yaml` y regenera. Para migrar el código, usa la tarea `implement-microservice-feature` (propone cambios del back y espera tu aprobación) y aprueba su plan.

**Si conservas lo detectado en tu código (por ejemplo, `jdbc`):** Por ejemplo, pedidos ejecuta SQL mediante JDBC en lugar de preparar entidades y repositorios JPA. Recomendado: mantén la forma de acceso que ya utiliza el servicio para evitar una migración innecesaria.

**Si eliges `jpa`:** Por ejemplo, pedidos utiliza entidades Java y repositorios de JPA; sus propiedades se relacionan con tablas y columnas. Conviene si no hay código de persistencia previo: la plantilla usa `jpa` para entidades y repositorios.

**Respaldo:** `config/opciones.yaml`; `rules/architecture-rules.md`; `scripts/registro_detectores.py`; `skills/service-creator/assets/servicio/build.template.gradle`.

## backend.lombok

**En resumen:** Decide si los servicios usan Lombok para generar código repetitivo a partir de anotaciones.

**Dónde se ve en tu proyecto:** Por ejemplo, `@RequiredArgsConstructor` evita escribir un constructor para los campos que necesita una clase; `build.gradle` declara Lombok y su procesador.

**Para qué se usa:**
- Selecciona anotaciones, dependencias y la forma de escribir constructores y registro de mensajes.
- La comprobación previa compara su presencia en los servicios; el gateway queda exceptuado porque sus plantillas no usan Lombok. Si difiere `backend.lombok` del código, la tarea te ofrece corregir lombok en su plan, conservar la diferencia o dejarla para revisión.

**Qué pasa si está mal:** Si se proponen anotaciones sin la dependencia, el servicio no compila. Quitar Lombok no sustituye por sí solo el código que esas anotaciones generaban.

**Cambiarla después:** Edita `stack.yaml` y regenera. Usa la tarea `implement-microservice-feature` (propone cambios del back y espera tu aprobación) para adaptar las clases y dependencias existentes.

**Si conservas lo detectado en tu código (por ejemplo, `false`):** Por ejemplo, escribes los constructores y el registro de mensajes de pedidos sin anotaciones Lombok y se omite su dependencia. Recomendado: mantén la decisión detectada en las dependencias y clases para no reescribirlas sin necesidad.

**Si eliges `true`:** Por ejemplo, la clase de pedidos recibe su constructor mediante una anotación y su construcción incluye el procesador Lombok. Conviene si empiezas sin clases previas: la plantilla usa `true` para generar constructores mediante anotaciones.

**Respaldo:** `config/opciones.yaml`; `scripts/registro_detectores.py`; `rules/architecture-rules.md`; `skills/service-creator/assets/servicio/build.template.gradle`.

## backend.prueba_viva

**En resumen:** Decide si la tarea intenta arrancar el servicio y probarlo después de revisar el código.

**Dónde se ve en tu proyecto:** El resultado queda en el archivo de ejecución `RUN_DIR/live-test.md`, dentro de la carpeta de ejecución, por ejemplo para comprobar una petición al servicio de pedidos en un entorno de pruebas autorizado.

**Para qué se usa:**
- Las tareas de cambios y correcciones consultan esta decisión después de la revisión.
- Esta prueba es adicional: no sustituye la compilación ni las pruebas anteriores.

**Qué pasa si está mal:** Con `true`, sin un entorno accesible no se puede confirmar el comportamiento en ejecución. La tarea debe informar el fallo o bloqueo, no presentarlo como una prueba correcta.

**Cambiarla después:** Edita `stack.yaml`; se lee al realizar la tarea, sin regenerar. Preparar el entorno y autorizar su uso sigue siendo una decisión tuya.

**Si eliges `true`:** Por ejemplo, se arranca pedidos y se intenta su comprobación en ejecución usando el entorno acordado. Recomendado: es la opción de la plantilla cuando tienes un entorno de pruebas autorizado, porque verifica el servicio funcionando.

**Si eliges `false`:** Por ejemplo, la tarea registra esa prueba como omitida y conserva las comprobaciones anteriores. Conviene si no dispones de un entorno donde puedas arrancar el servicio de forma autorizada.

**Respaldo:** `scripts/stack.mjs`; `workflows/references/full-route.md`; `workflows/references/correction-route.md`.

## backend.perfil_local

**En resumen:** Nombra el perfil de Spring que se activa para ejecutar localmente cada servicio.

**Dónde se ve en tu proyecto:** Por ejemplo, `feature` activa ese nombre en `application.yaml` y espera `application-feature.yaml`, con nombres como `DB_HOST_FEATURE` para la configuración local.

**Para qué se usa:**
- Las propuestas crean el perfil local además de los perfiles de entornos si hay Kubernetes.
- La comprobación previa detecta archivos de perfiles que faltan. En el servicio que modifica la tarea deben entrar en su plan aprobado; para otros servicios conserva tu respuesta en el registro `docs/decisiones-stack.md`.
- Sin Kubernetes se proponen solo `application.yaml` y el archivo local; con Kubernetes se añaden los archivos de cada sufijo de entorno.

**Qué pasa si está mal:** Si falta la clave se propone `feature` y se avisa. El validador rechaza un nombre inválido o, con Jenkins y Kubernetes, uno igual al sufijo de un entorno.

**Cambiarla después:** Edita `stack.yaml`, sin regenerar, y usa la tarea `implement-microservice-feature` (propone cambios del back y espera tu aprobación) para crear o adaptar los perfiles del código. Los valores de conexión los configuras tú fuera del archivo de decisiones.

**Si conservas lo detectado en tu código (por ejemplo, `local`):** Por ejemplo, solo cambian los nombres de la configuración local: `application-local.yaml` y `DB_HOST_LOCAL`, en lugar de los de `feature`. Recomendado: mantén el perfil local del código para no cambiar los nombres de su configuración.

**Si eliges `feature`:** Por ejemplo, la ejecución local de pedidos usa `application-feature.yaml`. Conviene si empiezas sin perfil local: la plantilla usa `feature` y nombres con `FEATURE`.

**Respaldo:** `scripts/stack.mjs`; `scripts/servicios.py`; `scripts/preflight_stack.py`; `skills/service-creator/SKILL.md`.

## sonarqube.url

**En resumen:** Indica la dirección de SonarQube donde la comprobación previa verifica si el análisis está disponible.

**Dónde se ve en tu proyecto:** En `stack.yaml`, por ejemplo `url: https://calidad.example.invalid`. Es la dirección de tu servidor de análisis, no la de la aplicación ni una credencial.

**Para qué se usa:**
- La comprobación previa consulta si ese servidor está listo para analizar.
- La clave de proyecto se calcula por servicio; consulta «Clave de proyecto de SonarQube» en el glosario.
- La variable de entorno `SONARQUBE_URL`, si existe, tiene prioridad para esta comprobación; la conexión MCP del análisis se configura por separado.

**Qué pasa si está mal:** Una dirección incorrecta o un servidor que no esté listo puede impedir continuar según la tarea. La dirección no debe llevar usuario, contraseña ni token.

**Cambiarla después:** Edita `stack.yaml`, sin regenerar. Si defines `SONARQUBE_URL`, cambiar solo esta clave no cambia la dirección consultada.

**Si conservas el dato confirmado (por ejemplo, `https://calidad.example.invalid`):** Por ejemplo, la comprobación previa consulta esa instalación antes de revisar pedidos. Recomendado: usa la dirección confirmada por quien mantiene tu SonarQube, porque una dirección de ejemplo no demuestra dónde está tu servidor.

**Respaldo:** `scripts/preflight_stack.py`; `scripts/stack.mjs`.

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

**Dónde se ve en tu proyecto:** En los perfiles de pedidos: con organizaciones cada persona pertenece a una; sin organizaciones se invita directamente a la aplicación. El back recibe el contrato SQL y prepara la API que utiliza el front.

**Para qué se usa:**
- Selecciona las plantillas y la tarea del modelo elegido.
- Si difiere `integraciones.gestion_usuarios` del código, la tarea te ofrece corregir gestion usuarios en su plan, conservar la diferencia o dejarla para revisión.
- El registro de Clerk admite solo invitados; el pre-registro crea un perfil local pendiente. Marcarlo `INACTIVO` no revoca sus sesiones.
- Con organizaciones, el invitador viene de la petición o de `CLERK_DEFAULT_INVITER_USER_ID`. En Kubernetes recibes Secrets vacíos autorizados; tú los rellenas y aplicas.

**Qué pasa si está mal:** Un modelo distinto del contrato cambia los datos y las invitaciones esperadas. En el back exige Clerk y su configuración. Con gestión activa, Clerk debe restringir el registro a invitados; como no se implementan roles, cualquier usuario con sesión puede administrar.

**Cambiarla después:** Edita `stack.yaml` y regenera. Usa la tarea `add-user-management` (prepara perfiles con un plan aprobado). Prepara primero el proyecto SQL, entrega su contrato al back y después lleva el contrato de la API al front. Elegir `ninguna` no borra código ni datos. Retirarlo exige la tarea `implement-microservice-feature` (propone cambios del back y espera tu aprobación).

**Si conservas lo detectado en tu código (por ejemplo, `organizaciones`):** Por ejemplo, el administrador selecciona la organización del perfil y la invitación se dirige a esa organización de Clerk. Sin código previo, la plantilla usa `ninguna`. Recomendado: conserva el modelo del contrato instalado para que SQL, API y pantallas sigan intercambiando los mismos datos.

**Si eliges `ninguna`:** Por ejemplo, pedidos no incorpora el módulo de perfiles. Conviene si no hay módulo previo: `ninguna` es la plantilla; elige `organizaciones` para perfiles asociados o `aplicacion` para una lista común.

**Si eliges `aplicacion`:** Por ejemplo, el administrador invita a pedidos sin seleccionar organización. Conviene si no hay módulo previo: `ninguna` es la plantilla; elige `organizaciones` para perfiles asociados o `aplicacion` para una lista común.

**Respaldo:** `config/opciones.yaml`; `workflows/add-user-management.md`; `scripts/registro_detectores.py`.

## integraciones.autenticacion

**En resumen:** Decide si el proyecto comprueba la identidad de sus usuarios con Clerk.

**Dónde se ve en tu proyecto:** En la seguridad JWT del gateway, por ejemplo su dependencia `spring-boot-starter-oauth2-resource-server`; el servicio de perfiles también recibe esa integración cuando se instala, no todos los servicios por defecto.

**Para qué se usa:**
- Selecciona las plantillas de autenticación y la obtención o validación del token según este stack.
- Si difiere `integraciones.autenticacion` del código, la tarea te ofrece corregir autenticacion en su plan, conservar la diferencia o dejarla para revisión.

**Qué pasa si está mal:** Con Clerk faltan datos si no has declarado su configuración. Sin Clerk no puedes activar gestión de usuarios en este stack. La autenticación no añade permisos por roles.

**Cambiarla después:** Edita `stack.yaml` y regenera. Al activar Clerk añade las claves que pida el generador y usa la tarea `add-authentication` (propone la integración con un plan aprobado). Al retirarlo, quita las claves sin uso y pide la tarea `implement-microservice-feature` (te enseña un plan de cambios del back y espera tu sí).

**Si conservas lo detectado en tu código (por ejemplo, `clerk`):** Por ejemplo, una persona inicia sesión con Clerk antes de usar pedidos. Sin código previo, la plantilla usa `clerk`. Recomendado: conserva el proveedor instalado para no cambiar el inicio de sesión ni el contrato de identidad.

**Si eliges `ninguna`:** Por ejemplo, pedidos permite el acceso sin integrar Clerk. Conviene si has acordado ese proveedor para el código nuevo; la plantilla usa `clerk`, mientras `ninguna` omite esa integración.

**Respaldo:** `config/opciones.yaml`; `config/requisitos.yaml`; `workflows/add-authentication.md`; `scripts/registro_detectores.py`; `scripts/stack.mjs`.

<!-- si integraciones.autenticacion=clerk -->
## integraciones.clerk_issuer_uri

**En resumen:** Indica qué instancia de Clerk emite los tokens que acepta el back.

**Dónde se ve en tu proyecto:** Por ejemplo, `https://identidad.example.invalid` es una dirección pública de emisor confirmada para tu proyecto; no es la URL del front ni una contraseña. Se propone como `issuer-uri` en gateway y perfiles.

**Para qué se usa:**
- El gateway y el servicio de perfiles propuestos validan tokens de ese emisor.
- Con Kubernetes, esta clave se usa en local y cada entorno tiene su emisor propio.
- Si difiere `integraciones.clerk_issuer_uri` del código, la tarea te ofrece corregir el emisor de Clerk en su plan, conservar la diferencia o dejarla para revisión.

**Qué pasa si está mal:** Esta clave configura el emisor local y solo comprueba texto no vacío; una URL HTTP o una barra final no se rechazan aquí. Para un entorno Kubernetes se comprueba además HTTPS sin barra final. Son contratos de validación distintos: aceptar el texto local no confirma que el emisor exista o que el token sea válido.

**Cambiarla después:** Edita `stack.yaml`, sin regenerar. Usa la tarea `add-authentication` (propone la integración con un plan aprobado) o la tarea `implement-microservice-feature` (propone cambios del back y espera tu aprobación) para llevarlo al código. Sin Clerk quita la clave; al activarlo añádela cuando el generador la pida.

**Si declaras el emisor de tu instancia:** Por ejemplo, pedidos acepta los tokens de la instancia de Clerk cuyo emisor confirmaste. Recomendado: usa el dato público confirmado de tu instancia, porque otro emisor identificaría usuarios de una instalación distinta.

**Respaldo:** `scripts/stack.mjs`; `scripts/registro_detectores.py`; `skills/service-creator/SKILL.md`.

<!-- fin -->
<!-- si integraciones.autenticacion=clerk -->
## integraciones.variables_autenticacion

**En resumen:** Enumera nombres de variables de entorno de autenticación, nunca sus valores.

**Dónde se ve en tu proyecto:** En `stack.yaml`, por ejemplo `[CLERK_SECRET_KEY]`. Es el nombre que necesita la integración de pedidos: el valor se configura fuera de este archivo.

**Para qué se usa:**
- El generador informa los nombres y si están definidos en su terminal, sin mostrar el contenido.
- La tarea que prepara la integración usa los nombres declarados; una lista no crea ni configura las credenciales.
- Los nombres deben comenzar por letra mayúscula, seguir con mayúsculas, cifras o guiones bajos y tener como máximo `64` caracteres; se rechazan textos que parezcan credenciales.

**Qué pasa si está mal:** Un token escrito en lugar de su nombre es un error. El validador rechaza nombres no permitidos; una lista incompleta puede dejar la integración sin las variables que necesita. Solo se usa con `integraciones.autenticacion: clerk` y gestión de usuarios distinta de `ninguna`; el gateway valida JWT con el emisor sin necesitar estas variables secretas.

**Cambiarla después:** Edita `stack.yaml`; no requiere regenerar por esta lista. Para adaptar la integración usa la tarea `add-authentication` (propone autenticación con un plan aprobado) o la tarea `implement-microservice-feature` (te enseña un plan de cambios del back y espera tu sí). Si su condición no se cumple, quítala; al activar la opción vuelve a añadirla cuando el generador la pida.

**Si conservas el dato confirmado (por ejemplo, `[CLERK_SECRET_KEY]`):** Por ejemplo, declaras únicamente ese nombre si es el que necesita tu integración de pedidos. Recomendado: los nombres que consume tu proyecto, sin copiar valores ni una lista ajena.

**Respaldo:** `actualizar.py`; `scripts/stack.mjs`; `workflows/`.

<!-- fin -->
## herramientas.codebase_memory

**En resumen:** Decide si el agente usa Codebase Memory para relacionar archivos y símbolos del código mediante su CLI.

**Dónde se ve en tu proyecto:** Se declara en `stack.yaml`. El índice vive en la caché local de CBM, no en el repositorio; se crea una vez por cada copia del repositorio (clon o worktree). `.cbmignore` acompaña a `.agents/` y excluye `knowledge-base/` y `.agents/`.

**Para qué se usa:**
- El preflight comprueba la CLI `codebase-memory-mcp` y el índice real del proyecto; si el índice existe, lo reindexa en la entrada de las tareas de código (grupo E), con un límite de 120 s, para incorporar los cambios. En el cierre solo comprueba su estado.
- Las consultas del código y sus actualizaciones se condicionan a esta clave. Las decisiones documentadas en `knowledge-base/` se consultan con `tgrep`.

**Qué pasa si está mal:** Si falta la CLI, informa `HERRAMIENTA`; si falta el proyecto o el índice no está listo, informa `GRAFO`. Un índice vacío, degradado al indexar o que no se pudo actualizar produce `GRAFO_AVISO`. El tratamiento depende del workflow según el catálogo de códigos. La falta de preparación de `.cbmignore` se informa como `PREPARACION`. Desactivar la clave omite el grafo y conserva los demás controles.

**Cambiarla después:** Edita `stack.yaml`; esta clave no requiere regenerar. Al activarla, usa la tarea `codebase-memory` para indexar el proyecto antes de `preparar-documentacion`. La clave antigua `herramientas.graphify` sigue aceptándose como alias cuando falta la nueva; si existen ambas, gana `herramientas.codebase_memory`. Renombra la antigua para retirar el aviso de validación.

**Si conservas lo detectado en tu código (por ejemplo, `false`):** Trabajas en pedidos sin preparar el índice. Mantén la decisión y las herramientas del proyecto; activar el grafo añade su preparación y sus controles.

**Si eliges `true`:** Consultas las relaciones del código de pedidos en el índice local. La plantilla de este stack lo activa al empezar. El índice no proporciona dependencias ni versiones de Gradle: se leen de `<servicio>/build.gradle`. A diferencia del código Java, los notebooks SQL `.dbcnb` no quedan cubiertos por CBM; en el stack SQL se usa `db-index.py` y CBM es complementario.

**Respaldo:** `.agents/scripts/codebase-memory.py`; `.agents/scripts/preflight.py`; `.agents/rules/codebase-memory.md`; `.agents/workflows/codebase-memory.md`; `.agents/scripts/stack.mjs`.

## git.rama_base

**En resumen:** Elige desde qué punto de Git quieres revisar los cambios de tu tarea.

**Dónde se ve en tu proyecto:** En `stack.yaml`, por ejemplo `rama_base: development`, si creaste `feature/pedidos` desde esa rama. No aparece en el código de tu aplicación.

**Para qué se usa:**
- Selecciona los archivos Java que se revisan; también incluye archivos nuevos sin añadir a Git.
- Con una rama se toma el punto donde ambas historias se separaron; `--base` permite indicar otra base.

**Qué pasa si está mal:** Solo en la selección de archivos, una rama inexistente o sin historia común detiene el análisis con un mensaje que identifica la referencia.

**Cambiarla después:** Edita `stack.yaml`; se lee en cada análisis, sin regenerar. Solo al cerrar tareas que escriben código, la comprobación de perfiles puede contar también tus commits: con `null` prueba la rama remota asociada y luego `main`, `master` y `develop`; una referencia inexistente se omite sin detener esa comprobación.

**Si eliges `null`:** Por ejemplo, se revisa el cambio de `Pedido.java` que todavía no está en un commit. Recomendado si dejas que el agente haga los cambios y tú haces el commit al final.

**Si eliges `development`:** Por ejemplo, la selección Java incluye los commits de `feature/pedidos` desde que se separó de `development`. Conviene si haces commits durante la tarea; la rama debe existir y compartir historia.

**Respaldo:** `scripts/touched-files.sh`; `scripts/preflight_stack.py`.

## api_error.campo_mensaje

**En resumen:** Nombra el campo que lleva el texto del error que verá la persona usuaria.

**Dónde se ve en tu proyecto:** En `configuration/ExceptionResponse.java`, por ejemplo el componente `String message` del record que produce `{"message":"Pedido no encontrado"}`.

**Para qué se usa:**
- Los servicios nuevos preparan `ExceptionResponse` y su manejador con ese campo de mensaje; el código existente necesita un plan aprobado para adaptarlo.
- Si difiere `api_error.campo_mensaje` del código, la tarea te ofrece corregir el campo del mensaje en su plan, conservar la diferencia o dejarla para revisión.
- La respuesta de error también incluye `timestamp`, la fecha del error.

**Qué pasa si está mal:** Si falta o está vacío, el validador se detiene. Si el back envía `message` y el front busca `detalle`, la interfaz puede mostrar un mensaje genérico en lugar de «Pedido no encontrado».

**Cambiarla después:** Edita `stack.yaml`; no requiere regenerar. Para llevar el contrato al código existente, usa la tarea `implement-microservice-feature` (te enseña un plan de cambios del back y espera tu sí). Si aún no hay manejador de errores, acuerda el contrato desde ahora; no se instala solo por declarar esta clave.

**Si conservas lo detectado en tu código (por ejemplo, `detalle`):** Por ejemplo, `{"detalle":"Pedido no encontrado"}` usa `detalle`. Recomendado: conserva el campo que ya comparte tu contrato; cambiarlo exige adaptar la respuesta y su lectura.

**Si eliges `message`:** Por ejemplo, el texto de `{"message":"Pedido no encontrado"}` se lee en `message`. Conviene si aún no hay contrato de errores: la plantilla propone `message`.

**Respaldo:** `scripts/stack.mjs`; `scripts/registro_detectores.py`; `skills/service-creator/assets/servicio/ExceptionResponse.template.java`.

## api_error.campo_codigo

**En resumen:** Nombra el campo opcional del código de negocio del error.

**Dónde se ve en tu proyecto:** En `ExceptionResponse.java`, por ejemplo `String code`; con `null` las propuestas nuevas omiten ese campo.

**Para qué se usa:**
- Permite distinguir casos sin comparar mensajes.
- Si difiere `api_error.campo_codigo` del código, la tarea te ofrece corregir el campo del código en su plan, conservar la diferencia o dejarla para revisión.

**Qué pasa si está mal:** Un nombre distinto del contrato hace perder ese código al consumidor. El validador exige la clave: acepta `null` o texto no vacío. Un campo publicado se prepara como texto no nulo.

**Cambiarla después:** Edita `stack.yaml`, sin regenerar. Para adaptarlo en código existente, usa la tarea `implement-microservice-feature` (te enseña un plan de cambios del back y espera tu sí). Acuerda el mismo contrato en back y front.

**Ejemplo del cuerpo de error:** Si los campos acordados son `message` y `code`, una respuesta puede ser `{"status":404,"message":"El pedido no existe","code":"PEDIDO_NO_ENCONTRADO"}`. Con `campo_codigo: null` sería `{"status":404,"message":"El pedido no existe"}`. `status` es el estado HTTP; el código permite distinguir el caso sin comparar el texto. Los nombres de mensaje y código salen de tu contrato.

El código sale de `CustomNotFoundException`, la excepción de «no encontrado» que incluye la plantilla: `new CustomNotFoundException("El pedido no existe")` usa `NO_ENCONTRADO`; con segundo argumento `"PEDIDO_NO_ENCONTRADO"` usa ese código propio. Los genéricos por tipo son `NO_ENCONTRADO` (404), `CONFLICTO` (409), `DATOS_INVALIDOS` (400) y `ERROR_INTERNO` (500). Con `null` las excepciones conservan el código pero no se publica; puedes acordar publicarlo después. No cambia el comportamiento de los manejadores existentes.

**Si conservas lo detectado en tu código (por ejemplo, `code`):** Por ejemplo, `"code":"PEDIDO_NO_ENCONTRADO"` distingue el caso sin comparar el mensaje. Recomendado: conserva el contrato detectado, incluido `null` si no publica ese campo, para no romper a quien recibe los errores.

**Si eliges `null`:** Por ejemplo, el error de pedido solo lleva mensaje y estado HTTP. Conviene si la API no publica código de negocio; `null` es el inicio de la plantilla.

**Respaldo:** `scripts/stack.mjs`; `scripts/registro_detectores.py`; `skills/service-creator/assets/servicio/ExceptionResponse.template.java`.

## devops.infraestructura

**En resumen:** Decide si preparas construcción de imágenes y despliegue con Jenkins y Kubernetes.

**Dónde se ve en tu proyecto:** Por ejemplo, con esa opción el proyecto de pedidos prepara `Dockerfile`, el archivo indicado por `devops.jenkinsfile` y manifiestos bajo `devops/<entorno>/`.

**Para qué se usa:**
- Selecciona instrucciones y plantillas de construcción y despliegue.
- Si difiere `devops.infraestructura` del código, la tarea te ofrece corregir infraestructura en su plan, conservar la diferencia o dejarla para revisión.
- Con Jenkins, `getServices()` enumera todos los servicios con carpeta, nombre de JAR, nombre visible y clave única. La ayuda muestra exportaciones locales y destinos de Secrets solo para los entornos que despliegan.

**Qué pasa si está mal:** Activar la opción no crea los artefactos ni configura Jenkins o el clúster. Un conjunto incompleto puede dejar el proyecto sin una construcción o un despliegue utilizable.

**Cambiarla después:** Edita `stack.yaml` y regenera. Usa la tarea `implement-microservice-feature` (propone cambios del back y espera tu aprobación) con un plan aprobado de artefactos. Si activas Jenkins y Kubernetes después, añade las claves que nombre el generador. Con `ninguna`, quita las demás `devops.*` y conserva esta clave.

**Si conservas lo detectado en tu código (por ejemplo, `ninguna`):** Por ejemplo, pedidos conserva ejecución local, con su perfil local y rutas locales del gateway, sin preparar imágenes ni manifiestos Kubernetes. Recomendado: conserva la infraestructura detectada; añadir otra requiere preparar artefactos y datos de despliegue.

**Si eliges `jenkins-kubernetes`:** Por ejemplo, Jenkins puede construir imágenes de pedidos y desplegarlas usando los entornos acordados y el descubrimiento de servicios del clúster. Conviene si empiezas sin despliegue y has elegido el de la plantilla: `jenkins-kubernetes` prepara imágenes y manifiestos.

**Respaldo:** `config/opciones.yaml`; `scripts/stack.mjs`; `scripts/registro_detectores.py`.

<!-- si devops.infraestructura=jenkins-kubernetes -->
## devops.registry

**En resumen:** Nombra el espacio donde Jenkins publica las imágenes de tus servicios.

**Dónde se ve en tu proyecto:** Por ejemplo, `registry: equipo-ejemplo` produce una referencia como `equipo-ejemplo/pedidos-service` en el pipeline, la secuencia de pasos de Jenkins, y los manifiestos.

**Para qué se usa:**
- Se usa al construir, publicar y buscar imágenes; no crea una cuenta ni guarda su contraseña.
- Si difiere `devops.registry` del código, la tarea te ofrece corregir registry en su plan, conservar la diferencia o dejarla para revisión.
- Se utiliza con `devops.infraestructura: jenkins-kubernetes`.

**Qué pasa si está mal:** Otro espacio puede hacer que se publiquen o busquen imágenes ajenas. Debe coincidir con tu registro de imágenes autorizado.

**Cambiarla después:** Edita `stack.yaml`, sin regenerar por este dato. Usa la tarea `implement-microservice-feature` (propone cambios del back y espera tu aprobación) para actualizar los artefactos con un plan aprobado. Si no se cumple su condición, quita la clave y añádela al activar la opción.

**Si conservas el dato confirmado (por ejemplo, `equipo-ejemplo`):** Por ejemplo, pedidos publica y busca sus imágenes dentro de ese espacio. Recomendado: usa el espacio confirmado por quien mantiene tu registro; evita publicar en el de otra instalación.

**Respaldo:** `scripts/stack.mjs`; `scripts/registro_detectores.py`; `skills/devops-engineer/assets/README.md`.

<!-- fin -->
<!-- si devops.infraestructura=jenkins-kubernetes -->
## devops.entornos.{nombre}

**En resumen:** Define una entrada por entorno que construye o despliega, con sus decisiones de rama e imagen.

**Dónde se ve en tu proyecto:** Por ejemplo, la entrada `qa` genera manifiestos en `devops/qa/` si despliega; su rama puede llamarse de otra forma.

**Para qué se usa:**
- Cada entrada selecciona rama, sufijo, imagen y credencial. Solo las que despliegan necesitan recursos y manifiestos.
- Una rama sin entrada sigue compilando y pasando su análisis; no necesita un entorno sin acciones.
- Se utiliza con `devops.infraestructura: jenkins-kubernetes`.

**Qué pasa si está mal:** El nombre debe ser alfanumérico minúsculo empezando por letra. Una entrada sin acción de imagen o despliegue se rechaza. Cambiar su nombre no mueve automáticamente carpetas existentes.

**Cambiarla después:** Edita `stack.yaml`, sin regenerar por este dato. Usa la tarea `implement-microservice-feature` (propone cambios del back y espera tu aprobación) para actualizar los artefactos con un plan aprobado. Si no se cumple su condición, quita la clave y añádela al activar la opción.

**Si declaras `development` y `main`:** Por ejemplo, pedidos construye en `development` y puede promover la imagen probada en `main`. Recomendado: es la organización de la plantilla si empiezas con esas ramas; separa construcción de promoción sin reconstruir.

**Si declaras solo `qa`:** Por ejemplo, una sola entrada construye y, si lo eliges, despliega pedidos en `devops/qa/`. Conviene si tu proyecto solo tiene ese destino y no necesita una segunda carpeta de manifiestos.

**Respaldo:** `scripts/stack.mjs`; `scripts/registro_detectores.py`; `skills/devops-engineer/assets/README.md`.

<!-- fin -->
<!-- si devops.infraestructura=jenkins-kubernetes -->
## devops.entornos.{nombre}.rama

**En resumen:** Selecciona qué rama o familia de ramas ejecuta las acciones de este entorno.

**Dónde se ve en tu proyecto:** Por ejemplo, `rama: development` aparece en `getEnvironments()` de el archivo indicado por `devops.jenkinsfile` y se compara con la rama que ejecuta Jenkins.

**Para qué se usa:**
- Se admite una rama exacta o un prefijo terminado en `/*`. Dos entradas no pueden seleccionar la misma rama.
- Si difiere `devops.entornos.{nombre}.rama` del código, la tarea te ofrece corregir rama en su plan, conservar la diferencia o dejarla para revisión.
- Se utiliza con `devops.infraestructura: jenkins-kubernetes`.

**Qué pasa si está mal:** Ramas solapadas o nombres inválidos detienen el validador. Una rama no seleccionada no recibe las acciones de ese entorno.

**Cambiarla después:** Edita `stack.yaml`, sin regenerar por este dato. Usa la tarea `implement-microservice-feature` (propone cambios del back y espera tu aprobación) para actualizar los artefactos con un plan aprobado. Si no se cumple su condición, quita la clave y añádela al activar la opción.

**Si conservas lo detectado en este entorno (por ejemplo, `qa`):** Por ejemplo, este entorno de pedidos sigue seleccionando su rama `qa`. Recomendado: conserva el dato real de este entorno para no cambiar su selección de rama.

**Si partes de la plantilla para este entorno:** Por ejemplo, la rama con el mismo nombre que la entrada selecciona el entorno; la plantilla usa `development` → `development` y `main` → `main`. Conviene si preparas este entorno sin artefactos anteriores y confirmas estos datos para tu clúster.

**Respaldo:** `scripts/stack.mjs`; `scripts/registro_detectores.py`; `skills/devops-engineer/assets/README.md`.

<!-- fin -->
<!-- si devops.infraestructura=jenkins-kubernetes -->
## devops.entornos.{nombre}.sufijo

**En resumen:** Da un nombre corto al perfil de Spring y a los recursos de un entorno.

**Dónde se ve en tu proyecto:** Por ejemplo, `qa` usa `application-qa.yaml`; `pedidos-service` → base `pedidos` → `pedidos-qa-service`. La base sale de `rootProject.name` sin `-service`, no del context-path ni de la carpeta.

**Para qué se usa:**
- Distingue nombres de servicios y volúmenes, y nombres de variables como `DB_HOST_QA`.
- Si difiere `devops.entornos.{nombre}.sufijo` del código, la tarea te ofrece corregir sufijo en su plan, conservar la diferencia o dejarla para revisión.
- Se utiliza con `devops.infraestructura: jenkins-kubernetes`.
- La comprobación de entornos rechaza un nombre final calculado de recurso que exceda `63` caracteres; un sufijo largo reduce el espacio disponible para el nombre del servicio.
- Separa rutas `hostPath` y volúmenes.

**Qué pasa si está mal:** Solo se valida con Jenkins y Kubernetes. Debe ser único, minúsculo alfanumérico y diferente de `backend.perfil_local`. Si falta `application-qa.yaml`, se avisa; si la tarea modifica ese servicio, su plan aprobado tendrá que crearlo.

**Cambiarla después:** Edita `stack.yaml`, sin regenerar por este dato. Usa la tarea `implement-microservice-feature` (propone cambios del back y espera tu aprobación) para actualizar los artefactos con un plan aprobado. Si no se cumple su condición, quita la clave y añádela al activar la opción.

**Si conservas lo detectado en este entorno (por ejemplo, `qa`):** Por ejemplo, pedidos conserva `application-qa.yaml` y los nombres de recursos con `qa`. Recomendado: conserva el dato real de este entorno para no cambiar su perfil y sus recursos.

**Si partes de la plantilla para este entorno:** Por ejemplo, la plantilla usa `dev` para `development` y `prod` para `main`: archivos `application-dev.yaml` y `application-prod.yaml`. Conviene si preparas este entorno sin artefactos anteriores y confirmas estos datos para tu clúster.

**Respaldo:** `scripts/stack.mjs`; `scripts/registro_detectores.py`; `skills/devops-engineer/assets/README.md`.

<!-- fin -->
<!-- si devops.infraestructura=jenkins-kubernetes -->
## devops.entornos.{nombre}.credencial_kubeconfig

**En resumen:** Identifica en Jenkins la credencial que da acceso al clúster de este entorno.

**Dónde se ve en tu proyecto:** Por ejemplo, `jenkins-kubeconfig-file` es el ID que aparece en `getEnvironments()` y `withCredentials` de el archivo indicado por `devops.jenkinsfile`; no es el archivo ni su contenido.

**Para qué se usa:**
- El despliegue usa ese ID para obtener su conexión autorizada. Un entorno que solo construye conserva el ID en su mapa, aunque no lo use.
- Si difiere `devops.entornos.{nombre}.credencial_kubeconfig` del código, la tarea te ofrece corregir credencial kubeconfig en su plan, conservar la diferencia o dejarla para revisión.
- Se utiliza con `devops.infraestructura: jenkins-kubernetes`.

**Qué pasa si está mal:** Un ID que no existe en Jenkins impide conectar con el clúster. El validador comprueba su forma, no que tu credencial exista.

**Cambiarla después:** Edita `stack.yaml`, sin regenerar por este dato. Usa la tarea `implement-microservice-feature` (propone cambios del back y espera tu aprobación) para actualizar los artefactos con un plan aprobado. Si no se cumple su condición, quita la clave y añádela al activar la opción.

**Si conservas lo detectado en este entorno (por ejemplo, `kubeconfig-qa`):** Por ejemplo, el entorno de pedidos conserva el acceso del ID `kubeconfig-qa`; dos entornos pueden compartir un ID si comparten clúster. Recomendado: conserva el dato real de este entorno para no cambiar su conexión de despliegue.

**Si partes de la plantilla para este entorno:** Por ejemplo, la plantilla usa `jenkins-kubeconfig-file` en `development` y `jenkins-kubeconfig-main` en `main`; son IDs, no los archivos de acceso. Conviene si preparas este entorno sin artefactos anteriores y confirmas estos datos para tu clúster.

**Respaldo:** `scripts/stack.mjs`; `scripts/registro_detectores.py`; `skills/devops-engineer/assets/README.md`.

<!-- fin -->
<!-- si devops.infraestructura=jenkins-kubernetes -->
## devops.entornos.{nombre}.imagen

**En resumen:** Decide si el entorno construye una imagen nueva o utiliza una ya probada.

**Dónde se ve en tu proyecto:** En `getEnvironments()` de el archivo indicado por `devops.jenkinsfile`, por ejemplo `imagen: construir` en el entorno que publica la imagen de pedidos.

**Para qué se usa:**
- Solo un entorno construye. Publica una etiqueta con versión y commit, por ejemplo `1.2.0-a1b2c3d`. Puede construir sin desplegar, sin manifiestos, cuentas, puertos ni recursos.
- Promover exige `desplegar: true` e historial completo: el commit de la imagen debe pertenecer a la historia de la rama e incluir el último cambio del servicio; no se reconstruye.
- Si difiere del pipeline, la tarea te ofrece corregir la acción de este entorno en su plan, conservarla o dejarla para revisión.

**Qué pasa si está mal:** `ninguna` no forma una combinación válida: con despliegue no selecciona imagen y sin despliegue no añade acciones. Elimina esa entrada si solo necesitas compilar y analizar la rama.

**Cambiarla después:** Edita `stack.yaml`, sin regenerar por este dato. Usa la tarea `implement-microservice-feature` (propone cambios del back y espera tu aprobación) para actualizar los artefactos con un plan aprobado. Si no se cumple su condición, quita la clave y añádela al activar la opción.

**Si conservas lo detectado en este entorno (por ejemplo, `promover`):** Por ejemplo, un entorno posterior de pedidos conserva `promover` y reutiliza la imagen probada. Recomendado: conserva el dato real de este entorno para no cambiar su posición en la cadena de imágenes.

**Si partes de la plantilla para este entorno:** Por ejemplo, el primer entorno de la cadena (`development` en la plantilla) usa `construir`; un entorno posterior (`main`) usa `promover`. Conviene si preparas este entorno sin artefactos anteriores y confirmas estos datos para tu clúster.

**Respaldo:** `scripts/stack.mjs`; `scripts/registro_detectores.py`; `skills/devops-engineer/assets/README.md`.

<!-- fin -->
<!-- si devops.infraestructura=jenkins-kubernetes -->
## devops.entornos.{nombre}.desplegar

**En resumen:** Decide si Jenkins aplica los manifiestos de este entorno en Kubernetes.

**Dónde se ve en tu proyecto:** En el mapa de el archivo indicado por `devops.jenkinsfile`, por ejemplo `desplegar: true` habilita la etapa que despliega pedidos.

**Para qué se usa:**
- Con despliegue se preparan manifiestos y se exigen réplicas, recursos y puertos del entorno.
- Si difiere `devops.entornos.{nombre}.desplegar` del código, la tarea te ofrece corregir desplegar en su plan, conservar la diferencia o dejarla para revisión.
- Se utiliza con `devops.infraestructura: jenkins-kubernetes`.

**Qué pasa si está mal:** `false` solo es válido con `imagen: construir`; `promover` exige `true`. Preparar archivos no los aplica al clúster.

**Cambiarla después:** Edita `stack.yaml`, sin regenerar por este dato. Usa la tarea `implement-microservice-feature` (propone cambios del back y espera tu aprobación) para actualizar los artefactos con un plan aprobado. Si no se cumple su condición, quita la clave y añádela al activar la opción.

**Si eliges `true`:** Por ejemplo, Jenkins despliega la imagen de pedidos con los manifiestos de la carpeta del entorno. Recomendado: es la opción de los entornos de la plantilla cuando su clúster está preparado y quieres actualizar el servicio ejecutado.

**Si eliges `false`:** Por ejemplo, Jenkins construye y publica pedidos, pero no prepara manifiestos ni exige recursos de despliegue para esa entrada. Conviene si solo quieres producir una imagen para desplegarla más adelante desde otro entorno.

**Respaldo:** `scripts/stack.mjs`; `scripts/registro_detectores.py`; `skills/devops-engineer/assets/README.md`.

<!-- fin -->
<!-- si devops.infraestructura=jenkins-kubernetes -->
## devops.entornos.{nombre}.replicas

**En resumen:** Fija cuántas copias de cada servicio pide Kubernetes.

**Dónde se ve en tu proyecto:** En el Deployment, el manifiesto que solicita las copias del servicio; por ejemplo `spec.replicas: 1` para pedidos.

**Para qué se usa:**
- Se escribe en `spec.replicas` de los manifiestos del entorno.
- Si difiere `devops.entornos.{nombre}.replicas` del código, la tarea te ofrece corregir replicas en su plan, conservar la diferencia o dejarla para revisión.
- Se utiliza con Jenkins y Kubernetes y `desplegar: true`.

**Qué pasa si está mal:** Un entero menor que uno se rechaza. Más copias consumen más recursos; con un clúster compartido se suman las de todos los entornos.

**Cambiarla después:** Edita `stack.yaml`, sin regenerar por este dato. Usa la tarea `implement-microservice-feature` (propone cambios del back y espera tu aprobación) para actualizar los artefactos con un plan aprobado. Si no se cumple su condición, quita la clave y añádela al activar la opción.

**Si conservas lo detectado en este entorno (por ejemplo, `1`):** Por ejemplo, el servicio de pedidos tiene una copia ejecutándose si conserva `1`. Recomendado: mantiene el número de copias ejecutándose y la reserva total de CPU y memoria.

**Si partes de la plantilla para este entorno:** Por ejemplo, la plantilla pide `1` en `development` y `2` en `main`: durante un reinicio, otra copia lista puede seguir respondiendo; se reserva el doble de CPU y memoria. Conviene si preparas este entorno sin artefactos anteriores y confirmas estos datos para tu clúster.

**Respaldo:** `scripts/stack.mjs`; `scripts/registro_detectores.py`; `skills/devops-engineer/assets/README.md`.

<!-- fin -->
<!-- si devops.infraestructura=jenkins-kubernetes -->
## devops.entornos.{nombre}.cpu_peticion

**En resumen:** Reserva una cantidad de procesador para cada copia del servicio.

**Dónde se ve en tu proyecto:** En el Deployment, el manifiesto que solicita las copias del servicio; por ejemplo `resources.requests.cpu: 250m` para pedidos.

**Para qué se usa:**
- Se escribe en `resources.requests.cpu` de los manifiestos del entorno.
- Si difiere `devops.entornos.{nombre}.cpu_peticion` del código, la tarea te ofrece corregir la reserva de CPU en su plan, conservar la diferencia o dejarla para revisión.
- Se utiliza con Jenkins y Kubernetes y `desplegar: true`.

**Qué pasa si está mal:** La cantidad debe ser positiva y llevar `m`, milésimas de núcleo; no puede superar `cpu_limite`. Una reserva excesiva puede impedir encontrar sitio para la copia.

**Cambiarla después:** Edita `stack.yaml`, sin regenerar por este dato. Usa la tarea `implement-microservice-feature` (propone cambios del back y espera tu aprobación) para actualizar los artefactos con un plan aprobado. Si no se cumple su condición, quita la clave y añádela al activar la opción.

**Si conservas lo detectado en este entorno (por ejemplo, `250m`):** Por ejemplo, cada copia de pedidos reserva `250m`, un cuarto de núcleo, si conserva ese dato. Recomendado: mantiene la CPU reservada para cada copia.

**Si partes de la plantilla para este entorno:** Por ejemplo, la plantilla reserva `250m` por copia en `development` y `500m`, medio núcleo, en `main`. Conviene si preparas este entorno sin artefactos anteriores y confirmas estos datos para tu clúster.

**Respaldo:** `scripts/stack.mjs`; `scripts/registro_detectores.py`; `skills/devops-engineer/assets/README.md`.

<!-- fin -->
<!-- si devops.infraestructura=jenkins-kubernetes -->
## devops.entornos.{nombre}.cpu_limite

**En resumen:** Limita el procesador que puede usar cada copia del servicio.

**Dónde se ve en tu proyecto:** En el Deployment, el manifiesto que solicita las copias del servicio; por ejemplo `resources.limits.cpu: 500m` para pedidos.

**Para qué se usa:**
- Se escribe en `resources.limits.cpu` de los manifiestos del entorno.
- Si difiere `devops.entornos.{nombre}.cpu_limite` del código, la tarea te ofrece corregir el límite de CPU en su plan, conservar la diferencia o dejarla para revisión.
- Se utiliza con Jenkins y Kubernetes y `desplegar: true`.

**Qué pasa si está mal:** Debe llevar `m` y cubrir la petición. Un límite bajo puede ralentizar el servicio; uno alto permite mayor consumo compartido.

**Cambiarla después:** Edita `stack.yaml`, sin regenerar por este dato. Usa la tarea `implement-microservice-feature` (propone cambios del back y espera tu aprobación) para actualizar los artefactos con un plan aprobado. Si no se cumple su condición, quita la clave y añádela al activar la opción.

**Si conservas lo detectado en este entorno (por ejemplo, `500m`):** Por ejemplo, cada copia de pedidos tiene como máximo `500m`, medio núcleo, si conserva ese límite. Recomendado: mantiene el máximo de CPU permitido a cada copia.

**Si partes de la plantilla para este entorno:** Por ejemplo, la plantilla limita cada copia a `500m` en `development` y `1000m`, un núcleo, en `main`. Conviene si preparas este entorno sin artefactos anteriores y confirmas estos datos para tu clúster.

**Respaldo:** `scripts/stack.mjs`; `scripts/registro_detectores.py`; `skills/devops-engineer/assets/README.md`.

<!-- fin -->
<!-- si devops.infraestructura=jenkins-kubernetes -->
## devops.entornos.{nombre}.memoria_peticion

**En resumen:** Reserva memoria para cada copia del servicio.

**Dónde se ve en tu proyecto:** En el Deployment, el manifiesto que solicita las copias del servicio; por ejemplo `resources.requests.memory: 256Mi` para pedidos.

**Para qué se usa:**
- Se escribe en `resources.requests.memory` de los manifiestos del entorno.
- Si difiere `devops.entornos.{nombre}.memoria_peticion` del código, la tarea te ofrece corregir la reserva de memoria en su plan, conservar la diferencia o dejarla para revisión.
- Se utiliza con Jenkins y Kubernetes y `desplegar: true`.

**Qué pasa si está mal:** Debe ser un entero positivo con unidad `Ki`, `Mi`, `Gi` o `Ti`, cantidades binarias de memoria; no puede superar `memoria_limite`.

**Cambiarla después:** Edita `stack.yaml`, sin regenerar por este dato. Usa la tarea `implement-microservice-feature` (propone cambios del back y espera tu aprobación) para actualizar los artefactos con un plan aprobado. Si no se cumple su condición, quita la clave y añádela al activar la opción.

**Si conservas lo detectado en este entorno (por ejemplo, `256Mi`):** Por ejemplo, cada copia de pedidos reserva `256Mi` si conserva esa petición. Recomendado: mantiene la memoria reservada para cada copia.

**Si partes de la plantilla para este entorno:** Por ejemplo, la plantilla reserva `256Mi` por copia en `development` y `512Mi` en `main`; duplicar réplicas duplica esa reserva. Conviene si preparas este entorno sin artefactos anteriores y confirmas estos datos para tu clúster.

**Respaldo:** `scripts/stack.mjs`; `scripts/registro_detectores.py`; `skills/devops-engineer/assets/README.md`.

<!-- fin -->
<!-- si devops.infraestructura=jenkins-kubernetes -->
## devops.entornos.{nombre}.memoria_limite

**En resumen:** Limita la memoria que puede usar cada copia del servicio.

**Dónde se ve en tu proyecto:** En el Deployment, el manifiesto que solicita las copias del servicio; por ejemplo `resources.limits.memory: 512Mi` para pedidos.

**Para qué se usa:**
- Se escribe en `resources.limits.memory` de los manifiestos del entorno.
- El heap, la memoria de objetos de Java, usa máximo/inicial `75 %`/`37.5 %` del límite en servicios y `37.5 %`/`18.75 %` en gateway; el almacenamiento no cambia.
- Si difiere `devops.entornos.{nombre}.memoria_limite` del código, la tarea te ofrece corregir el límite de memoria en su plan, conservar la diferencia o dejarla para revisión.
- Se utiliza con Jenkins y Kubernetes y `desplegar: true`.

**Qué pasa si está mal:** Debe cubrir la petición y usar `Ki`, `Mi`, `Gi` o `Ti`. Un límite insuficiente puede hacer que Kubernetes termine el proceso; aumentar copias multiplica el máximo total.

**Cambiarla después:** Edita `stack.yaml`, sin regenerar por este dato. Usa la tarea `implement-microservice-feature` (propone cambios del back y espera tu aprobación) para actualizar los artefactos con un plan aprobado. Si no se cumple su condición, quita la clave y añádela al activar la opción.

**Si conservas lo detectado en este entorno (por ejemplo, `512Mi`):** Por ejemplo, cada copia de pedidos conserva su máximo de `512Mi` si ese era el límite configurado. Recomendado: mantiene el máximo de memoria y los tamaños del heap de Java.

**Si partes de la plantilla para este entorno:** Por ejemplo, la plantilla fija `512Mi` por copia en `development` y `1024Mi` en `main`; el máximo total se multiplica por el número de copias. Conviene si preparas este entorno sin artefactos anteriores y confirmas estos datos para tu clúster.

**Respaldo:** `scripts/stack.mjs`; `scripts/registro_detectores.py`; `skills/devops-engineer/assets/README.md`.

<!-- fin -->
<!-- si devops.infraestructura=jenkins-kubernetes -->
## devops.entornos.{nombre}.nodo_puerto_base

**En resumen:** Fija la base para calcular los puertos públicos de los servicios del entorno.

**Dónde se ve en tu proyecto:** Por ejemplo, base `31100` y puerto de aplicación `8082` producen `nodePort: 31102` en el manifiesto del servicio.

**Para qué se usa:**
- Usa la fórmula base más puerto efectivo menos `8080`; el gateway tiene su puerto explícito.
- La comprobación previa detecta puertos no resolubles y colisiones entre rangos o manifiestos.
- Se utiliza con Jenkins y Kubernetes y `desplegar: true`.

**Qué pasa si está mal:** Los puertos deben quedar entre `30000` y `32767` y no chocar con otros. Una colisión impide asignar el acceso público correctamente.

**Cambiarla después:** Edita `stack.yaml`, sin regenerar por este dato. Usa la tarea `implement-microservice-feature` (propone cambios del back y espera tu aprobación) para actualizar los artefactos con un plan aprobado. Si no se cumple su condición, quita la clave y añádela al activar la opción.

**Si conservas lo detectado en este entorno (por ejemplo, `30800`):** Por ejemplo, pedidos con puerto `8082` queda en `30802` si conserva la base `30800`. Recomendado: mantiene los puertos públicos calculados para los servicios de este entorno.

**Si partes de la plantilla para este entorno:** Por ejemplo, la plantilla usa base `30800` en `development` y `31400` en `main`; con puerto `8082`, quedan `30802` y `31402`. Conviene si preparas este entorno sin artefactos anteriores y confirmas estos datos para tu clúster.

**Respaldo:** `scripts/stack.mjs`; `scripts/registro_detectores.py`; `skills/devops-engineer/assets/README.md`.

<!-- fin -->
<!-- si devops.infraestructura=jenkins-kubernetes -->
## devops.entornos.{nombre}.gateway_nodo_puerto

**En resumen:** Da el puerto público explícito del gateway en este entorno.

**Dónde se ve en tu proyecto:** Por ejemplo, `nodePort: 30380` en `devops/qa/<gateway>/service-gateway.yaml` permite entrar al gateway por ese puerto.

**Para qué se usa:**
- No usa la fórmula de los demás servicios; cada gateway recibe el puerto declarado.
- Si difiere `devops.entornos.{nombre}.gateway_nodo_puerto` del código, la tarea te ofrece corregir gateway nodo puerto en su plan, conservar la diferencia o dejarla para revisión.
- Se utiliza con Jenkins y Kubernetes, `desplegar: true` y gateway declarado.

**Qué pasa si está mal:** Debe estar entre `30000` y `32767`, sin repetirse ni chocar con los rangos de servicios. Otro puerto en uso impide publicar el gateway correctamente.

**Cambiarla después:** Edita `stack.yaml`, sin regenerar por este dato. Usa la tarea `implement-microservice-feature` (propone cambios del back y espera tu aprobación) para actualizar los artefactos con un plan aprobado. Si no se cumple su condición, quita la clave y añádela al activar la opción.

**Si conservas lo detectado en este entorno (por ejemplo, `30080`):** Por ejemplo, el gateway de pedidos conserva su acceso por `30080` si ese era su puerto. Recomendado: mantiene el puerto público de entrada de este entorno.

**Si partes de la plantilla para este entorno:** Por ejemplo, la plantilla publica el gateway en `30080` para `development` y `30680` para `main`, sin la fórmula de los otros servicios. Conviene si preparas este entorno sin artefactos anteriores y confirmas estos datos para tu clúster.

**Respaldo:** `scripts/stack.mjs`; `scripts/registro_detectores.py`; `skills/devops-engineer/assets/README.md`.

<!-- fin -->
<!-- si devops.infraestructura=jenkins-kubernetes -->
## devops.entornos.{nombre}.cors_origenes

**En resumen:** Permite los orígenes del front que pueden llamar al gateway desplegado en este entorno.

**Dónde se ve en tu proyecto:** Por ejemplo, `[https://pedidos.example.invalid]` se propone en `gateway.cors-origenes` del documento de Kubernetes de `application-qa.yaml`.

**Para qué se usa:**
- Los manifiestos activan el perfil y el gateway usa sus orígenes; la lista local `backend.cors_origenes` permanece independiente.
- Si difiere `devops.entornos.{nombre}.cors_origenes` del código, la tarea te ofrece corregir cors origenes en su plan, conservar la diferencia o dejarla para revisión.
- Se utiliza con Jenkins y Kubernetes, `desplegar: true` y gateway declarado.

**Qué pasa si está mal:** Se exige una lista no vacía de direcciones HTTP o HTTPS sin ruta, barra final ni credenciales. Un origen equivocado deja al navegador bloqueando la llamada.

**Cambiarla después:** Edita `stack.yaml`, sin regenerar por este dato. Usa la tarea `implement-microservice-feature` (propone cambios del back y espera tu aprobación) para actualizar los artefactos con un plan aprobado. Si no se cumple su condición, quita la clave y añádela al activar la opción.

**Si conservas el dato confirmado (por ejemplo, `[https://pedidos.example.invalid]`):** Por ejemplo, el navegador que abre pedidos en ese sitio puede llamar al gateway de `qa`. Recomendado: usa los orígenes confirmados de ese entorno; evita autorizar sitios que no necesitan acceder.

**Si declaras varios orígenes autorizados:** Por ejemplo, añades otro sitio de pedidos aprobado y ambos pueden llamar a ese gateway. Conviene si la misma API sirve a más de un front y necesitas permitir cada origen explícitamente.

**Respaldo:** `scripts/stack.mjs`; `scripts/registro_detectores.py`; `skills/devops-engineer/assets/README.md`.

<!-- fin -->
<!-- si devops.infraestructura=jenkins-kubernetes -->
## devops.entornos.{nombre}.clerk_issuer_uri

**En resumen:** Identifica la instancia de Clerk cuyos tokens acepta este entorno desplegado.

**Dónde se ve en tu proyecto:** Por ejemplo, `https://identidad-qa.example.invalid` se propone como `issuer-uri` en el documento Kubernetes del perfil del entorno.

**Para qué se usa:**
- Separa el emisor de ese entorno del emisor general utilizado en local.
- Si difiere `devops.entornos.{nombre}.clerk_issuer_uri` del código, la tarea te ofrece corregir el emisor de Clerk en su plan, conservar la diferencia o dejarla para revisión.
- Se utiliza con Jenkins y Kubernetes, `desplegar: true` y autenticación Clerk.

**Qué pasa si está mal:** Para el entorno Kubernetes se exige una URL HTTPS sin barra final, credenciales ni parámetros; esa comprobación adicional no se hace para el emisor local. Si el emisor no corresponde a la instancia de Clerk, se rechazan los tokens de sus usuarios.

**Cambiarla después:** Edita `stack.yaml`, sin regenerar por este dato. Usa la tarea `implement-microservice-feature` (propone cambios del back y espera tu aprobación) para actualizar los artefactos con un plan aprobado. Si no se cumple su condición, quita la clave y añádela al activar la opción.

**Si declaras el emisor de `qa`:** Por ejemplo, pedidos desplegado en `qa` acepta los tokens de esa instancia confirmada de Clerk. Recomendado: usa el emisor público de tu instancia del entorno; no copies el de otra instalación.

**Respaldo:** `scripts/stack.mjs`; `scripts/registro_detectores.py`; `skills/devops-engineer/assets/README.md`.

<!-- fin -->
<!-- si devops.infraestructura=jenkins-kubernetes -->
<!-- fin -->
<!-- si devops.infraestructura=jenkins-kubernetes -->
## devops.java_home_nodo

**En resumen:** Indica dónde está el JDK del nodo de Jenkins que compila los servicios.

**Dónde se ve en tu proyecto:** Por ejemplo, `PIPELINE_JAVA_HOME = "/opt/jdks/jdk-27.0.1.0.3"` en el archivo indicado por `devops.jenkinsfile`; la ruta debe existir en el nodo que compila (`devops.nodos.compilacion`).

**Para qué se usa:**
- Jenkins busca el JDK que compila pedidos en esa ruta del nodo de compilación.
- El pipeline comprueba antes de Gradle que exista `javac` en esa ruta; si falta, falla con un error que indica el nodo y esta clave.
- Ese JDK ejecuta Gradle en el nodo y, por convención, corresponde a `backend.java`: el wrapper de cada servicio debe admitirlo según `config/gradle-java.json`. En local Gradle puede ejecutarse con otro Java y compilar con el toolchain declarado, ocultando una incompatibilidad que aparecerá en Jenkins.
- El validador avisa si los datos del JDK no parecen corresponder a `backend.java`; no comprueba que la instalación exista en un nodo remoto.
- Si `devops.nodos.compilacion` no es esta máquina, la ruta no se puede comprobar desde aquí: debes indicarla tal como existe en ese nodo.
- Se utiliza con `devops.infraestructura: jenkins-kubernetes`.

**Qué pasa si está mal:** Una ruta inexistente o un JDK incompatible impide compilar en el nodo. La ruta de ese nodo no tiene que coincidir con la del JDK del contenedor.

**Cambiarla después:** Edita `stack.yaml`, sin regenerar por este dato. Si cambia Java, usa la tarea `change-version` (coordina JDK, servicios y documentación con un plan aprobado). Si no cambia Java, usa la tarea `implement-microservice-feature` (propone cambios del back y espera tu aprobación) con un plan aprobado de DevOps. Sin esa infraestructura se quita la clave.

**Si conservas la instalación detectada (`/opt/jdks/jdk-27.0.1.0.3`):** Por ejemplo, Jenkins sigue compilando pedidos con ese JDK de versión mayor `27`. Recomendado: conserva una ruta existente compatible con `backend.java` en el nodo de compilación; si cambia Java, confirma una instalación de la nueva versión.

**Si cambias la instalación del nodo:** Por ejemplo, seleccionas otra ruta existente para el JDK de pedidos en el nodo de compilación. Conviene si cambió la máquina o la instalación de Jenkins; no modifica la ubicación del JDK dentro de la imagen.

**Respaldo:** `scripts/stack.mjs`; `scripts/registro_detectores.py`; `skills/devops-engineer/assets/README.md`.

<!-- fin -->
<!-- si devops.infraestructura=jenkins-kubernetes -->
## devops.java_home_contenedor

**En resumen:** Indica dónde queda el JDK dentro de la imagen que ejecuta el servicio.

**Dónde se ve en tu proyecto:** Por ejemplo, un archivo `openjdk-27.0.1.0.3_linux-x64_bin.tar.gz` que crea `jdk-27.0.1.0.3/` bajo `/opt/` permite proponer `/opt/jdk-27.0.1.0.3` y pedir tu confirmación.

**Para qué se usa:**
- El `Dockerfile` de pedidos usa esa ruta en `ENV JAVA_HOME` dentro de la imagen.
- El validador avisa si los datos del JDK no parecen corresponder a `backend.java`; no comprueba que la instalación o descarga exista.
- La propuesta de `java_home_contenedor` usa la carpeta del tar de `jdk_url` bajo `/opt/` y pide tu confirmación; si el nombre no permite saberla, se pregunta sin descargar ni inventar la carpeta.
- Se utiliza con `devops.infraestructura: jenkins-kubernetes`.

**Qué pasa si está mal:** Una ruta inexistente, una versión incorrecta o un archivo de otra arquitectura puede impedir compilar o arrancar. La ruta del nodo es independiente de la del contenedor.

**Cambiarla después:** Edita `stack.yaml`, sin regenerar por este dato. Si cambia Java, usa la tarea `change-version` (coordina JDK, servicios y documentación con un plan aprobado). Si no cambia Java, usa la tarea `implement-microservice-feature` (propone cambios del back y espera tu aprobación) con un plan aprobado de DevOps. Sin esa infraestructura se quita la clave.

**Si conservas la ruta confirmada (`/opt/jdk-27.0.1.0.3`):** Por ejemplo, la imagen de pedidos conserva el JDK que su archivo comprimido extrae bajo `/opt/`. Recomendado: mantén la carpeta confirmada para esa descarga y la versión mayor `27` del ejemplo de `backend.java`.

**Si cambia la carpeta del archivo comprimido:** Por ejemplo, otra distribución del JDK de pedidos crea una carpeta diferente. Conviene si actualizaste la descarga: confirma esa carpeta antes de cambiar `JAVA_HOME` en la imagen.

**Respaldo:** `scripts/stack.mjs`; `scripts/registro_detectores.py`; `skills/devops-engineer/assets/README.md`.

<!-- fin -->
<!-- si devops.infraestructura=jenkins-kubernetes -->
## devops.jdk_url

**En resumen:** Indica la descarga del JDK que usa el Dockerfile al construir la imagen.

**Dónde se ve en tu proyecto:** Por ejemplo, una URL oficial de un archivo `openjdk-27.0.1.0.3_linux-x64_bin.tar.gz` que coincida con la versión mayor elegida y la arquitectura del contenedor.

**Para qué se usa:**
- El `Dockerfile` de pedidos descarga y extrae ese archivo cuando se construye la imagen, no al regenerar las instrucciones.
- El validador avisa si los datos del JDK no parecen corresponder a `backend.java`; no comprueba que la instalación o descarga exista.
- Se utiliza con `devops.infraestructura: jenkins-kubernetes`.

**Qué pasa si está mal:** Una URL incorrecta, una versión mayor distinta o una arquitectura incompatible puede impedir construir o arrancar la imagen. Regenerar no descarga el archivo ni verifica que la URL esté disponible.

**Cambiarla después:** Edita `stack.yaml`, sin regenerar por este dato. Si cambia Java, usa la tarea `change-version` (coordina JDK, servicios y documentación con un plan aprobado). Si no cambia Java, usa la tarea `implement-microservice-feature` (propone cambios del back y espera tu aprobación) con un plan aprobado de DevOps. Sin esa infraestructura se quita la clave.

**Si conservas la descarga confirmada del JDK:** Por ejemplo, la imagen de pedidos sigue construyéndose con el archivo `openjdk-27.0.1.0.3_linux-x64_bin.tar.gz`, coherente con `backend.java: 27`. Recomendado: conserva la descarga oficial acordada para esa versión y arquitectura.

**Si eliges otra distribución o revisión:** Por ejemplo, el archivo descargado de pedidos cambia aunque mantengas la versión mayor `27`. Conviene si necesitas esa distribución o revisión; confirma también la carpeta que crea y `java_home_contenedor`.

**Respaldo:** `scripts/stack.mjs`; `scripts/registro_detectores.py`; `skills/devops-engineer/assets/README.md`.

<!-- fin -->
<!-- si devops.infraestructura=jenkins-kubernetes -->
## devops.credencial_bd_pruebas

**En resumen:** Identifica en Jenkins la credencial de la base que el pipeline usa para ejecutar los tests del build.

**Dónde se ve en tu proyecto:** Por ejemplo, `bd-pruebas-ci` es el ID de una credencial «Username with password» en Jenkins; el pipeline la usa para inyectar usuario y contraseña durante la compilación.

**Para qué se usa:**
- Si hay credencial, el build inyecta `USER_NAME_DB_<P>` y `PASSWORD_DB_<P>` (con `<P>` = perfil local en mayúsculas, por defecto `FEATURE`) solo alrededor de Gradle.
- El nodo de compilación debe definir `DB_HOST_<P>`, `DB_PORT_<P>` y `DB_NAME_<P>` en el formato que espera la URL JDBC de la plantilla del perfil. Si falta alguna, el build falla indicando el nombre de la variable, sin mostrar valores.
- Con `null`, el build no inyecta credenciales ni variables de base de pruebas. Varios servicios comparten la misma base de pruebas de ese perfil en el nodo (sin aislamiento por servicio).
- Se utiliza con `devops.infraestructura: jenkins-kubernetes`.

**Qué pasa si está mal:** Un ID inexistente o mal escrito impide obtener la credencial en Jenkins. Variables del nodo vacías o con formato incorrecto hacen fallar los tests o la conexión.

**Cambiarla después:** Edita `stack.yaml`, sin regenerar por este dato. Usa la tarea `implement-microservice-feature` (propone cambios del back y espera tu aprobación) para actualizar los artefactos con un plan aprobado. Si no se cumple su condición, quita la clave y añádela al activar la opción.

**Si eliges `null`:** El pipeline compila y ejecuta tests sin inyectar credenciales de base de pruebas, como antes. Conviene si no tienes una base de pruebas disponible en CI.

**Si eliges un ID (por ejemplo, `bd-pruebas-ci`):** Jenkins inyecta usuario y contraseña de esa credencial en el build. Recomendado marcar *Treat username as secret* para que el usuario no salga en el log.

**Respaldo:** `scripts/stack.mjs`; `scripts/registro_detectores.py`; `skills/devops-engineer/assets/README.md`; `skills/devops-engineer/assets/Jenkinsfile`.

<!-- fin -->
<!-- si devops.infraestructura=jenkins-kubernetes -->
## devops.slack_canal

**En resumen:** Elige el canal donde Jenkins envía avisos o indica que no quieres esos avisos.

**Dónde se ve en tu proyecto:** Por ejemplo, `def slackChannel = "pedidos-ci"` en el archivo indicado por `devops.jenkinsfile`; con `null` la plantilla propone texto vacío.

**Para qué se usa:**
- El pipeline envía avisos solo si tiene canal; no configura la conexión de Slack en Jenkins.
- Si difiere `devops.slack_canal` del código, la tarea te ofrece corregir el canal de Slack en su plan, conservar la diferencia o dejarla para revisión.
- Se utiliza con `devops.infraestructura: jenkins-kubernetes`.

**Qué pasa si está mal:** Un canal equivocado puede mandar los avisos a otro sitio o impedir el envío. Con `null`, la comprobación previa informa que no habrá avisos.

**Cambiarla después:** Edita `stack.yaml`, sin regenerar por este dato. Usa la tarea `implement-microservice-feature` (propone cambios del back y espera tu aprobación) para actualizar los artefactos con un plan aprobado. Si no se cumple su condición, quita la clave y añádela al activar la opción.

**Si eliges `null`:** Por ejemplo, la construcción de pedidos no envía sus avisos de Slack. Recomendado: es adecuado mientras no tengas esa integración preparada; evita pedir un canal que no utilizas.

**Si eliges `pedidos-ci`:** Por ejemplo, Jenkins intenta enviar los avisos de pedidos a ese canal confirmado. Conviene si tienes Slack integrado en Jenkins y quieres recibir allí los resultados de construcción y despliegue.

**Respaldo:** `scripts/stack.mjs`; `scripts/registro_detectores.py`; `skills/devops-engineer/assets/README.md`.

<!-- fin -->
<!-- si backend.persistencia=jpa -->
## nomenclatura.estrategia_fisica_jpa

**En resumen:** Decide cómo Hibernate, la herramienta de JPA que relaciona objetos y tablas, interpreta sus nombres.

**Dónde se ve en tu proyecto:** En la propiedad `physical-strategy` del servicio JPA; por ejemplo, `org.hibernate.boot.model.naming.PhysicalNamingStrategyStandardImpl` mantiene el nombre declarado de una tabla.

**Para qué se usa:**
- La propuesta de configuración del servicio usa esa clase para resolver nombres de tablas y columnas.
- Si difiere `nomenclatura.estrategia_fisica_jpa` del código, la tarea te ofrece corregir la estrategia de nombres de JPA en su plan, conservar la diferencia o dejarla para revisión.

**Qué pasa si está mal:** Una estrategia distinta puede buscar tablas o columnas con otro nombre. Solo se usa con JPA; con JDBC no modifica el SQL escrito.

**Cambiarla después:** Edita `stack.yaml` y regenera. Usa la tarea `implement-microservice-feature` (propone cambios del back y espera tu aprobación) para adaptar los servicios existentes. Con JDBC quítala; al activar JPA añádela cuando la pida el generador.

**Si conservas la estrategia detectada (por ejemplo, `org.hibernate.boot.model.naming.PhysicalNamingStrategyStandardImpl`):** Por ejemplo, un nombre declarado como `PedidoDetalle` se conserva sin transformarlo. Recomendado: conserva la estrategia detectada si corresponde a los nombres declarados; sin una previa, la plantilla usa esta clase.

**Si eliges `org.hibernate.boot.model.naming.CamelCaseToUnderscoresNamingStrategy`:** Por ejemplo, un nombre como `PedidoDetalle` se transforma a `pedido_detalle`. Conviene si tu base utiliza palabras en minúsculas separadas por guiones bajos y necesitas esa transformación.

**Respaldo:** `scripts/stack.mjs`; `scripts/registro_detectores.py`; `skills/service-creator/SKILL.md`.

<!-- fin -->
## nomenclatura.clase_aplicacion

**En resumen:** Da el patrón del nombre de la clase Java que arranca cada servicio.

**Dónde se ve en tu proyecto:** Por ejemplo, `{AliasPascal}ServiceApplication` y base `pedidos` producen `PedidosServiceApplication.java`, su declaración de clase y `SpringApplication.run(PedidosServiceApplication.class, args)`.

**Para qué se usa:**
- El generador incorpora el patrón a las instrucciones para servicios nuevos y su adaptación.
- Si difiere `nomenclatura.clase_aplicacion` del código, la tarea te ofrece corregir el patrón de la clase principal en su plan, conservar la diferencia o dejarla para revisión.

**Qué pasa si está mal:** Sin `{AliasPascal}` se detiene el validador. Cambiar solo la clave no renombra el archivo ni sus referencias en un servicio existente. Si el context-path era distinto de la base, el cálculo nuevo puede mostrar una diferencia legítima que se decide en el plan y el registro.

**Cambiarla después:** Edita `stack.yaml` y regenera. Usa la tarea `incorporate-service` (adapta un servicio con un plan aprobado) o la tarea `implement-microservice-feature` (propone cambios del back y espera tu aprobación) para renombrar código existente.

**Si conservas lo detectado en tu código (por ejemplo, `{AliasPascal}Aplicacion`):** Por ejemplo, la clase de entrada se llama `PedidosAplicacion`. Recomendado: conserva el patrón de las clases existentes para evitar cambiar sus puntos de entrada.

**Si eliges `{AliasPascal}ServiceApplication`:** Por ejemplo, pedidos arranca mediante `PedidosServiceApplication`. Conviene si empiezas sin nombres previos: la plantilla propone `{AliasPascal}ServiceApplication`.

**Respaldo:** `scripts/stack.mjs`; `scripts/registro_detectores.py`; `skills/service-creator/SKILL.md`; `workflows/incorporate-service.md`.

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

<!-- si devops.infraestructura=jenkins-kubernetes -->
## devops.jenkinsfile

**En resumen:** Indica la ruta del archivo que Jenkins ejecuta como pipeline del proyecto.

**Dónde se ve en tu proyecto:** Por ejemplo, `devops/Jenkinsfile-ci` es el `Script Path` de la tarea de Jenkins.

**Para qué se usa:** Lee, crea o valida el pipeline en esa ruta y compara sus etiquetas y valores con `stack.yaml`.

**Qué pasa si está mal:** Una ruta vacía, absoluta, con `..`, contrabarras, segmentos vacíos, `account/` o nombres `.env*` bloquea la validación.

**Cambiarla después:** Edita `stack.yaml` y usa `implement-microservice-feature` para adaptar el pipeline con un plan aprobado, sin regenerar por este valor. Cambiarla no renombra el archivo ni actualiza el `Script Path`: debes ajustarlo en Jenkins. Si `devops.infraestructura` es `ninguna`, quita esta clave; al activar `jenkins-kubernetes`, el generador te pedirá añadirla.

**Si conservas lo detectado (`devops/Jenkinsfile-ci`, por ejemplo):** Recomendado: Jenkins lo sigue ejecutando sin renombrar; confirma que el `Script Path` coincide.

**Si eliges `devops/Jenkinsfile`:** Conviene solo si aún no tienes pipeline; es la ruta propuesta para uno nuevo.

**Respaldo:** `scripts/stack.mjs`; `scripts/servicios.py`; `scripts/registro_detectores.py`; `skills/devops-engineer/assets/README.md`.

## devops.nodos.general

**En resumen:** Elige la etiqueta del nodo donde corre la parte general del pipeline.

**Dónde se ve en tu proyecto:** En el archivo indicado por `devops.jenkinsfile`, en la declaración `@Field final String NODO_GENERAL = 'principal'` y en su uso `agent { label "${NODO_GENERAL}" }`.

**Para qué se usa:** Selecciona dónde se hacen checkout, Quality Gate, aplicación de manifiestos y avisos de Slack.

**Qué pasa si está mal:** Una etiqueta inválida bloquea la validación; si no hay ejecutores libres, Jenkins espera. Si la etapa Docker no encuentra el JAR, vuelve a compilar dentro de su propio nodo y ocupa otro ejecutor; con las tres etiquetas iguales, ese nodo necesita al menos tres ejecutores libres.

**Cambiarla después:** Edita `stack.yaml` y la tarea `implement-microservice-feature` cambia la línea de la declaración del Jenkinsfile con un plan aprobado, sin regenerar por este valor. Si `devops.infraestructura` es `ninguna`, quita esta clave; al activar `jenkins-kubernetes`, el generador te pedirá añadirla.

**Si conservas lo detectado (`principal`, por ejemplo):** Recomendado: las etapas generales siguen en esa máquina; necesita acceso al repositorio y los permisos de despliegue y avisos configurados por ti.

**Si eliges otra etiqueta (`todo`, por ejemplo):** Traslada las etapas generales a esa máquina, que necesita esos accesos y ejecutores disponibles. Puede compartir etiqueta con compilación y Docker.

**Respaldo:** `scripts/stack.mjs`; `scripts/registro_detectores.py`; `skills/devops-engineer/assets/Jenkinsfile`.

## devops.nodos.compilacion

**En resumen:** Elige la etiqueta del nodo que compila y analiza los servicios.

**Dónde se ve en tu proyecto:** En el archivo indicado por `devops.jenkinsfile`, en la declaración `@Field final String NODO_COMPILACION = 'compilador'` y en sus usos `node(label: NODO_COMPILACION)` en `buildMicroservice` y `analyzeMicroservice`, así como en sus mensajes.

**Para qué se usa:** Ejecuta los builds y Sonar con el JDK de `devops.java_home_nodo`. Ambas funciones usan la misma etiqueta declarada.

**Qué pasa si está mal:** Una etiqueta inválida bloquea; etiquetas distintas entre los usos se informan como diferencia. Sin el JDK en la ruta indicada, no compila. Si la etapa Docker no encuentra el JAR, vuelve a compilar dentro de su propio nodo y ocupa otro ejecutor; con las tres etiquetas iguales, ese nodo necesita al menos tres ejecutores libres. Es la compilación de reserva.

**Cambiarla después:** Edita `stack.yaml` y la tarea `implement-microservice-feature` cambia la línea de la declaración del Jenkinsfile con un plan aprobado, sin regenerar por este valor. Si `devops.infraestructura` es `ninguna`, quita esta clave; al activar `jenkins-kubernetes`, el generador te pedirá añadirla.

**Si conservas lo detectado (`compilador`, por ejemplo):** Recomendado: compilación y análisis siguen en esa máquina; necesita el JDK compatible en `devops.java_home_nodo` y acceso a SonarQube.

**Si eliges otra etiqueta (`compilador`, por ejemplo):** Traslada compilación y análisis juntos a esa máquina; debe tener el mismo JDK y acceso a SonarQube.

**Respaldo:** `scripts/stack.mjs`; `scripts/registro_detectores.py`; `skills/devops-engineer/assets/Jenkinsfile`.

## devops.nodos.docker

**En resumen:** Elige la etiqueta del nodo que construye y publica imágenes.

**Dónde se ve en tu proyecto:** En el archivo indicado por `devops.jenkinsfile`, en la declaración `@Field final String NODO_DOCKER = 'docker'` y en su uso `node(label: NODO_DOCKER)` en `buildDockerImage`.

**Para qué se usa:** Selecciona la máquina que recibe el JAR y construye/publica su imagen. Si falta, se hace la compilación de reserva.

**Qué pasa si está mal:** Una etiqueta inválida bloquea; sin Docker o acceso al registry falla la publicación. Si la etapa Docker no encuentra el JAR, vuelve a compilar dentro de su propio nodo y ocupa otro ejecutor; con las tres etiquetas iguales, ese nodo necesita al menos tres ejecutores libres.

**Cambiarla después:** Edita `stack.yaml` y la tarea `implement-microservice-feature` cambia la línea de la declaración del Jenkinsfile con un plan aprobado, sin regenerar por este valor. Si `devops.infraestructura` es `ninguna`, quita esta clave; al activar `jenkins-kubernetes`, el generador te pedirá añadirla.

**Si conservas lo detectado (`docker`, por ejemplo):** Recomendado: construcción/publicación de imágenes sigue en esa máquina; necesita Docker, acceso al registry y el JDK para la compilación de reserva.

**Si eliges otra etiqueta (`todo`, por ejemplo):** Traslada esas etapas a otra máquina; prepara allí Docker, acceso al registry y el JDK de `devops.java_home_nodo` para la compilación de reserva.

**Respaldo:** `scripts/stack.mjs`; `scripts/registro_detectores.py`; `skills/devops-engineer/assets/Jenkinsfile`.

<!-- fin -->

## backend.jdk_ruta_desarrollo

**En resumen:** Le dice a Gradle en qué carpeta de tu máquina está el JDK con el que compila, por ejemplo `/opt/jdks/jdk-27`; con `null` no se toca esa línea.

**Dónde se ve en tu proyecto:** Por ejemplo, `org.gradle.java.installations.paths=/opt/jdks/jdk-27` en el `gradle.properties` de cada servicio, versionado junto al código.

**Para qué se usa:** Los servicios nuevos y los cambios de Java escriben esa ruta mediante `servicios.py escribir-jdk-ruta`. La comprobación previa compara esa línea de los servicios existentes, también sin DevOps.

**Qué pasa si está mal:** Una clave ausente, ruta relativa o lista con comas bloquea la validación. Una carpeta incorrecta puede impedir compilar. Si la propiedad ocupa varias líneas unidas con `\\`, el comando no la modifica y te avisa para incluir su corrección en el plan. Si la ruta no contiene el número de `backend.java`, se pide revisarla; no se comprueba la instalación con ese aviso.

**Cambiarla después:** Edita `stack.yaml`, sin regenerar por este valor. Si cambia Java, usa `change-version`; el plan espera que confirmes la ruta para la versión nueva. Si solo cambia la carpeta, usa `implement-microservice-feature` para adaptar los servicios con un plan aprobado. Esta clave existe aunque no uses DevOps.

**Si conservas lo detectado (`/opt/jdks/jdk-27`, por ejemplo):** Recomendado si esa carpeta contiene el JDK compatible con `backend.java`; el comando escribe únicamente `org.gradle.java.installations.paths`.

**Si eliges otra ruta absoluta:** Los servicios aprobados pasan a usar el JDK de esa carpeta; confirma su ubicación en tu máquina.

**Si eliges `null`:** No se escribe ni se modifica esa línea y la comprobación previa no compara esa línea. Tampoco se borra una ruta anterior; tú gestionas la instalación.

**Respaldo:** `scripts/stack.mjs`; `scripts/servicios.py`; `scripts/registro_detectores.py`; `skills/service-creator/SKILL.md`; `workflows/change-version.md`.
