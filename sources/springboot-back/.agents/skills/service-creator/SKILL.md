---
name: service-creator
description: Siembra el esqueleto de un servicio Spring Boot nuevo o de un gateway a partir de plantillas, con los parámetros del proyecto y los puertos del disco; no implementa lógica de negocio.
---

# Service Creator

Rol: crear el esqueleto de un servicio o del gateway a partir de plantillas canónicas.
No implementa lógica de negocio: deja clases vacías de configuración y el manejador de
errores, y el resto se implementa después.

## Entrada

Recibes `OUT_DIR` (carpeta donde escribes tu salida) y las rutas de estos archivos:

| Artefacto | Obligatorio | Contenido |
|---|---|---|
| `approved-plan.md` | sí | Plan aprobado con su aprobación literal. La creación de servicios solo está autorizada en una sección `## Servicio nuevo`. |
| `feedback.md` | no | Correcciones pedidas sobre un intento anterior tuyo. Si existe, corrige solo lo que indica. |

La sección `## Servicio nuevo` del plan declara: carpeta, rootProject.name, base, context-path, motivo, el
puerto propuesto con `servicios.py` y la lista de archivos. Solo escribes los archivos que
el plan lista en `## Archivos a crear o modificar`; si falta la sección `## Servicio nuevo`,
no crees nada: escribe la salida con `estado: bloqueado` y la causa.

<!-- si integraciones.autenticacion=clerk -->
## Modo autenticacion

Si la invocación declara modo autenticacion, aplica `references/autenticacion.md` y omite el contrato completo de creación (entrada, tareas, reglas y salida); produce propuestas para un gateway existente sin escribir producción. Con seguridad existente solo informa y no propone cambios aplicables.

<!-- fin -->
## Tareas

1. **Precondición del repositorio**: el repositorio debe tener al menos un servicio
   existente (carpeta con `build.gradle` y `settings.gradle`). Si no tiene ninguno,
   `estado: bloqueado`: "crea el primer servicio con Spring Initializr; `service-creator`
   solo añade servicios a un repositorio que ya tiene uno; sigue
   `references/servicio-initializr.md` y solicita incorporar la carpeta".
   Detecta esta condición antes de obtener puertos o escribir cualquier archivo.
<!-- si devops.infraestructura=jenkins-kubernetes -->
2. **Puerto**: ejecuta `python3 -I -B .agents/scripts/servicios.py siguiente-puerto` y usa
   ese puerto y su nodePort. Si el plan declara otro puerto y está libre (ningún perfil lo
   declara según `servicios.py listar`), usa el del plan; si declara uno ocupado,
   `estado: bloqueado`. Nunca tocas los puertos de los servicios existentes.
<!-- si devops.infraestructura=ninguna -->
2. **Puerto**: ejecuta `python3 -I -B .agents/scripts/servicios.py siguiente-puerto` y usa
   ese puerto. Si el plan declara otro puerto y está libre (ningún perfil lo
   declara según `servicios.py listar`), usa el del plan; si declara uno ocupado,
   `estado: bloqueado`. Nunca tocas los puertos de los servicios existentes.
<!-- fin -->
3. **Parámetros del proyecto**: lee con `node .agents/scripts/stack.mjs get <clave>` cada
   marcador `<clave>`. Marcadores de servicio:
   - `__SERVICIO__`: solo carpeta del servicio nuevo; `__NOMBRE__` es su `rootProject.name` aprobado. Para uno nuevo suelen coincidir.
   - `__BASE__`: `base` de `servicios.py nombres`: `rootProject.name` sin un `-service` final, también para el gateway. Siembra primero los settings/build aprobados para poder consultarlo, antes de las clases y artefactos que dependan de esos nombres.
   - `__GROUP__`: `backend.group`, de `node .agents/scripts/stack.mjs get backend.group`;
     compara los groups descubiertos: si difieren, avisa y propón el cambio en el plan, sin cambiar otros servicios;
   - `__PAQUETE__`: `__GROUP__` + `.` + base sin guiones (paquete de las clases);
     si la base no forma un identificador Java válido o colisiona con otro paquete, devuelve `bloqueado`;
   - `__CONTEXT_PATH__`: `/` + base, salvo otro context-path aprobado; el gateway WebFlux conserva vacío si no usa prefijo;
<!-- si devops.infraestructura=jenkins-kubernetes -->
   - `__PUERTO__`: del paso anterior; el nodePort se obtiene de `red.node_port` de `servicios.py nombres` para su entorno;
     lo usan las plantillas de DevOps, no estas. `__BASE__` y `__PUERTO__` son solo del servicio que se crea;
<!-- si devops.infraestructura=ninguna -->
   - `__PUERTO__`: del paso anterior; `__BASE__` y `__PUERTO__` son solo del servicio que se crea;
<!-- fin -->
   - `__CLASE_PRINCIPAL__`: el patrón `<nomenclatura.clase_aplicacion>`, sustituyendo `{AliasPascal}` por la base en PascalCase;
<!-- si devops.infraestructura=jenkins-kubernetes -->
   - `__ENTORNO__` y `__ENTORNO_MAYUS__`: para el archivo local `application-<perfil_local>.yaml`, `<backend.perfil_local>`; para cada archivo Kubernetes, el `sufijo` de su entrada de `devops.entornos` (mayúsculas para los nombres de variables `DB_HOST_<ENTORNO>`);
<!-- si devops.infraestructura=ninguna -->
   - `__ENTORNO__` y `__ENTORNO_MAYUS__`: para el perfil local usa `<backend.perfil_local>` (y su mayúscula para nombres de variables `DB_HOST_<ENTORNO>`);
<!-- fin -->
<!-- si devops.infraestructura=jenkins-kubernetes -->
   - `__VERSION_DEP_MANAGEMENT__` y `__VERSION_SONARQUBE__`: copia las versiones del `build.gradle` de un servicio existente. Para el gateway, exige que el plan incluya `__BOM_CLOUD__` y `__VERSION_GRPC__`, cada uno con su fuente o expresamente marcado provisional y su comprobación pendiente; si falta, `estado: bloqueado` sin inventar valores. Una BOM sin evidencia de compatibilidad no se considera verificada ni habilita saltarse una precondición del plan. No busques un gateway previo como requisito para obtener grpc.
<!-- si devops.infraestructura=ninguna -->
   - `__VERSION_DEP_MANAGEMENT__` y `__VERSION_SONARQUBE__`: copia las versiones del `build.gradle` de un servicio existente. Para el gateway, exige que el plan incluya `__BOM_CLOUD__` con su fuente o expresamente marcado provisional y su comprobación pendiente; si falta, `estado: bloqueado` sin inventar valores. Una BOM sin evidencia de compatibilidad no se considera verificada ni habilita saltarse una precondición del plan. Esta variante no usa `__VERSION_GRPC__`.
<!-- fin -->
4. **Siembra las plantillas** de `assets/` a la ruta destino con el nombre final:
   - `*.template.gradle` → `<servicio>/<nombre sin ".template">`;
   - `*.template.yaml` → `<servicio>/src/main/resources/`;
   - Excepción: `*Tests.template.java` → `<servicio>/src/test/java/<paquete>/`, con el nombre final de la clase de prueba (`__CLASE_PRINCIPAL__Tests.java` para el gateway). No se siembra bajo main.
   - Los demás `*.template.java` → `<servicio>/src/main/java/<paquete>/...` (en la carpeta que corresponde: `configuration/` para el manejador, `configuration/customexception/` para las excepciones, la raíz del paquete para la clase principal).
   Las marcas `si clave=valor` ya están resueltas en las plantillas por el bootstrap del
   proyecto: no las toques, siembra el archivo tal cual queda.
<!-- si devops.infraestructura=jenkins-kubernetes -->
   El `application-entorno.template.yaml` trae `spring.application.name` y la conexión del
   perfil; crea `application-<perfil_local>.yaml` para local y un `application-<sufijo>.yaml` por entrada de `devops.entornos`, con las variables de base correspondientes. `application.yaml` activa `<backend.perfil_local>`. No deduzcas el perfil de la rama ni de la carpeta.
   En el gateway siembra también `GatewayProperties.template.java` en `config/`. El sufijo y CORS llegan por propiedades del perfil; no sustituyas un sufijo en el Java de rutas. Solo para entradas con `desplegar: true`, añade `assets/gateway/application-k8s.fragment.yaml` al final de su perfil, sustituyendo issuer y repitiendo el origen por cada `cors_origenes` del entorno. Ese segundo documento se activa solo con k8s; en local se mantienen el issuer global y la lista CORS global de application.yaml. El marcador de lista CORS global se expande como una entrada YAML por origen. Sin autenticación, el fragmento no lleva issuer.
<!-- si devops.infraestructura=ninguna -->
   El `application-entorno.template.yaml` trae `spring.application.name` y la conexión del
   perfil; el perfil local es `<backend.perfil_local>` y se siembra `application-<perfil_local>.yaml`. `application.yaml` activa ese único perfil local.
<!-- fin -->
<!-- si devops.infraestructura=jenkins-kubernetes -->
5. **Vectores con listas**: expande `backend.cors_origenes` como lista YAML local y `devops.entornos.<carpeta>.cors_origenes` como lista YAML del documento k8s solo en entradas con `desplegar: true`; CorsConfig recibe las propiedades del perfil
<!-- si devops.infraestructura=ninguna -->
5. **Vectores con listas**: donde una plantilla trae un marcador de lista, escribe una
   línea por cada valor: `backend.cors_origenes` (una línea `addAllowedOrigin` por origen)
<!-- fin -->
   y las rutas del gateway (un bloque `.route(...)` por servicio que no sea el gateway,
   a partir de `servicios.py nombres`). Sus marcadores son distintos de los del servicio creado:
<!-- si devops.infraestructura=jenkins-kubernetes -->
   - `__BASE_RUTA__`: base del destino de `servicios.py nombres`; se usa en id, X-Gateway y lb://. `__CONTEXT_PATH_RUTA__`: context_path completo del destino, con `/` inicial; se usa solo en path.
<!-- si devops.infraestructura=ninguna -->
   - `__BASE_RUTA__`: base del destino de `servicios.py nombres`; se usa en id y X-Gateway. `__CONTEXT_PATH_RUTA__`: context_path completo del destino, con `/` inicial; se usa solo en path.
<!-- fin -->
<!-- si devops.infraestructura=ninguna -->
   - `__PUERTO_RUTA__`: puerto del perfil local (`<backend.perfil_local>`) de ese servicio, o el base si no tiene override; se usa en http://localhost:.
<!-- fin -->
<!-- si devops.infraestructura=jenkins-kubernetes -->
   La URI lb:// usa el sufijo de GatewayProperties del perfil activo; las rutas y X-Gateway lo comparten.
<!-- si devops.infraestructura=ninguna -->
   La plantilla usa la URI http://localhost: con el puerto de destino.
<!-- fin -->
6. **Wrapper de Gradle**: copia `gradlew`, `gradle/wrapper/` y con ellos la versión de
   Gradle, desde un servicio existente. No copies ni abras `gradle.properties`: ejecuta `python3 -I -B .agents/scripts/servicios.py escribir-jdk-ruta <servicio>` con el servicio aprobado; con ruta crea o actualiza solo esa propiedad y con `null` no escribe. Una continuación rechazada debe corregirse mediante el plan.
7. **`.gitignore` y `.dockerignore`**: copia del servicio existente que ya los trae,
   solo si sus rutas están aprobadas. Si falta alguno, usa `assets/gitignore.template`
   o `assets/dockerignore.template`, respectivamente. No sobrescribas ignores existentes
   sin aprobación; comprueba que el JAR final sigue incluido en el contexto Docker.
8. **Gateway**: se crea solo si el plan lo lista en `## Servicio nuevo` y su carpeta coincide con `backend.gateway`, que debe estar declarado antes de crearla. Si es null o difiere, `estado: bloqueado`, sin crear el gateway: el usuario debe corregir stack.yaml y relanzar el flujo. Ningún agente edita stack.yaml; no se exige regenerar por esa clave.
<!-- si devops.infraestructura=jenkins-kubernetes -->
   La declaración previa incluye `gateway_nodo_puerto` y `cors_origenes` por entorno desplegable; comprueba `python3 -I -B .agents/scripts/servicios.py validar-entornos` antes de sembrar y detente si bloquea.
<!-- si devops.infraestructura=ninguna -->
   No hay claves por entorno que declarar.
<!-- fin -->
9. **Ruta del servicio nuevo**:
   - Si existe gateway, añade su ruta en GatewayConfig solo si ese archivo está aprobado.
<!-- si devops.infraestructura=jenkins-kubernetes -->
   - Usa el mismo bloque de plantilla con `__BASE_RUTA__` y `__CONTEXT_PATH_RUTA__`, resueltos
     desde el servicio nuevo con las reglas anteriores; conserva los datos propios del gateway.
<!-- si devops.infraestructura=ninguna -->
   - Usa el mismo bloque de plantilla con `__BASE_RUTA__`, `__CONTEXT_PATH_RUTA__` y `__PUERTO_RUTA__`, resueltos
     desde el servicio nuevo con las reglas anteriores; conserva los datos propios del gateway.
<!-- fin -->
<!-- si devops.infraestructura=ninguna -->
   - Usa el puerto del perfil aplicable, o base si no hay override.
<!-- fin -->
<!-- si devops.infraestructura=jenkins-kubernetes -->
   - Con Kubernetes usa base y sufijo del entorno; no escribas URLs del proyecto en las plantillas.
<!-- fin -->
10. **Contrato de error**:
   - Las excepciones admiten código propio opcional: NO_ENCONTRADO o CONFLICTO por defecto;
     validación usa DATOS_INVALIDOS y el genérico ERROR_INTERNO. Nunca devuelvas null si hay campo de código.
   - Si `api_error.campo_codigo` es null, sustituye `__CODIGO_COMPONENTE__`,
     `__CODIGO_ARGUMENTO__` y `__NORMALIZAR_CODIGO__` por texto vacío en ExceptionResponse.
   - Si declara un nombre, el componente es `, String <campo_codigo>`, el argumento
     `, codigo` y la normalización `if (<campo_codigo> == null || <campo_codigo>.isBlank()) <campo_codigo> = "ERROR_INTERNO";`.
   - Son sustituciones completas de sitios Java; no crees una opción nueva de generación.
     El mensaje se nombra según `api_error.campo_mensaje`.
11. **Comprobación final**: con `rg`, solo sobre los archivos sembrados desde `assets/`:
   - Comprueba que no queda ningún marcador sin sustituir (`<clave.ruta>` con el patrón
     `<[a-z_]+\.[a-z_.]+>` ni `__MAYÚSCULAS__` con `__[A-Z_]+__`).
   - Comprueba que no hay valores de respaldo en credenciales ni ningún `${VARIABLE:valor}`.
   - Excluye `gradlew` y `gradle/`, copiados del servicio existente: las expansiones del
     wrapper como `${APP_HOME:-./}` no son respaldos de credenciales.

## Reglas

- No crea lógica de negocio, no edita `stack.yaml` ni el `AGENTS.md`, solo modifica la ruta del gateway existente si está aprobada en la lista del plan; no toca otros servicios
  existentes y no escribe nada fuera de los archivos del plan.
- No lee secretos ni archivos de configuración de credenciales; las variables las nombra,
  sus valores los exporta el usuario.
- No ejecuta Gradle; compilar le toca a la fase de escritura del proyecto.
  Si falta la toolchain, informa la ruta de `backend.jdk_ruta_desarrollo` para que el usuario confirme su instalación o edite esa clave. Usa `servicios.py escribir-jdk-ruta` dentro del plan; con `null` no cambia la propiedad. Nunca pide una ruta adicional ni inventa una instalación.
- Si una plantilla no encaja con el plan (p. ej. un servicio sin base o con otro motor),
  `estado: bloqueado` con la causa: no improvises variantes de plantilla.

## Salida

Escribe **un único archivo**: `OUT_DIR/service-report.md`, con este formato:

```markdown
---
artefacto: service-report.md
skill: service-creator
estado: ok | fallo | bloqueado
entradas_leidas: [approved-plan.md]   # los que leíste completos
fecha: <ISO-8601>
---

## Servicio creado

- carpeta: <carpeta> · nombre: <rootProject.name> · base: <base> · con_base: <sí | no> · gateway: <sí | no>
<!-- si devops.infraestructura=jenkins-kubernetes -->
- puerto: <puerto> · nodePort: <nodePort> · contexto: <context-path>
<!-- si devops.infraestructura=ninguna -->
- puerto: <puerto> · contexto: <context-path>
<!-- fin -->
- archivos escritos: (lista literal)

## Parámetros resueltos

<tabla marcador → origen → valor, excepto valores de variables de entorno, que solo se nombran>

## Avisos

- (gateway creado → carpeta `<carpeta>` coincide con `backend.gateway`, declarado antes de crearla)
- (variables de entorno que el usuario debe configurar, solo por nombre)
<!-- si devops.infraestructura=jenkins-kubernetes -->
- (versiones: dependency-management y sonarqube copiadas; BOM de Spring Cloud y grpc con valor, fuente o condición provisional y comprobación pendiente del plan)
<!-- si devops.infraestructura=ninguna -->
- (versiones: dependency-management y sonarqube copiadas; BOM de Spring Cloud con valor, fuente o condición provisional y comprobación pendiente del plan)
<!-- fin -->
<!-- si devops.infraestructura=jenkins-kubernetes -->
- (con jenkins-kubernetes: ruta del secret de base sembrado —tú lo rellenas, lo compruebas con `python3 -B -E .agents/scripts/servicios.py comprobar-secreto <ruta>` y lo aplicas con `kubectl apply -f <ruta>` antes del primer despliegue; la IA no lo abre—, o motivo por el que no se sembró)
- (al crear un gateway con jenkins-kubernetes: sus artefactos DevOps incluyen el RBAC)
- (con jenkins-kubernetes: las cuentas de Jenkins se preparan con los artefactos DevOps; el usuario aplica los archivos sembrados, obtiene el token y configura su credencial)
<!-- fin -->
```
