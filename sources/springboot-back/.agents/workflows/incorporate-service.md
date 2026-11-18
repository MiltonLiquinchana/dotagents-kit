---
description: Revisa un servicio pegado desde Initializr y propone adaptarlo al stack antes de escribir.
---

# Incorporar un servicio existente

Preparación del ZIP: [.agents/skills/service-creator/references/servicio-initializr.md](.agents/skills/service-creator/references/servicio-initializr.md).


## Control documental estricto antes de trabajar en código

Al entrar, antes de diseñar, generar o adaptar código, ejecuta estos controles en orden y detente al primer fallo. No uses --diagnostico ni omitas el control porque la infraestructura completa aún no esté preparada. Esta entrada comprueba solo documentación; conserva los demás controles del workflow y el preflight completo al cierre.

```bash
python3 -I -B .agents/scripts/documentacion.py comprobar-conexion || exit 1
python3 -I -B .agents/scripts/comprobar-documentacion.py || { echo "BLOCKED: Resuelve el bloqueo documental indicado. Si falta documentación de la versión del servicio incorporado, lanza .agents/workflows/preparar-documentacion.md antes de repetir incorporate-service.md." >&2; exit 1; }
python3 -I -B .agents/scripts/documentacion.py comprobar-existencia || exit 1
```

## Entrada y diagnóstico

1. Comprueba `git rev-parse --show-toplevel` y ejecuta
   `node .agents/scripts/stack.mjs validate`. Si cualquiera falla, bloqueado y detente.
   Recibe la carpeta exacta del servicio; si hay varios candidatos pide al usuario
   identificarlo. Crea RUN_DIR fuera de `.agents/` con request.md literal y manifest
   de fases, intentos, estados y archivos. No ejecutes todavía el preflight completo:
   requiere preparación, árbol limpio y ejecuta Gradle. No ejecutes archivos recibidos.
   Inventaría `git status --short`: identifica la importación y cualquier cambio ajeno,
   sin borrar, guardar ni commitear los cambios del usuario.
2. `context-analyzer` produce context.md del servicio pegado y servicios existentes,
   comparando `build.gradle`, settings y wrapper sin ejecutar Gradle; usa
   `python3 -I -B .agents/scripts/servicios.py listar` y `siguiente-puerto`.
   Lee configuración solo por claves necesarias y nombres de variables, ocultando
   respaldos antes de mostrar resultados. Nunca leas secretos, `.env*` ni archivos de `devops/*/account/`.
   Una expresión dinámica de group/versiones que no se pueda resolver requiere
   confirmación; no la evalúes como código.

## Diseño y aprobación

3. `spring-architect` prepara architecture-decision.md y `microservices-architect`
   inter-service-design.md si corresponde. Compara contra las plantillas de
   `service-creator` sin sembrarlas sobre el importado. El plan incluye una tabla
   antes/después, motivo y archivos exactos para:
   - Java y plugin Boot frente a `backend.java` y `backend.spring_boot`, versiones
     de los otros plugins y dependencias, incluidas las de pruebas;
     el plan alinea las librerías, plugins y BOM compartidos con los servicios existentes,
     usando el inventario estático para que el preflight posterior pase;
   - wrapper de Gradle: incluye actual, destino y mínimo para ejecutar `backend.java` según `.agents/config/gradle-java.json`, citando su `fuente` y `verificado`, sin preparar ni asociar documentación de Gradle. El destino debe admitir el JDK del nodo y el local que ejecutarán Gradle. Si hace falta subirlo, incluye `gradlew`, `gradlew.bat`, `gradle/wrapper/gradle-wrapper.jar` y `gradle/wrapper/gradle-wrapper.properties` del servicio en la lista de archivos, la suma SHA-256 publicada y su fuente, y `./gradlew wrapper --gradle-version <X> --gradle-distribution-sha256-sum <suma publicada>` desde su carpeta con permiso de Gradle y red. Ejecuta la actualización con un JDK que admita el wrapper actual, aunque el Java destino ya esté instalado. Si no se alinea, el preflight de cierre bloquea con `VERSIONES`; si la versión no es resoluble/comparable o Java queda fuera de tabla, declara la limitación y acuerda la compatibilidad antes de aprobar el destino, sin inventar mínimos.
   - group frente a `backend.group`, paquete `<backend.group>.<base sin guiones>`,
     rutas/imports y clase según `nomenclatura.clase_aplicacion`;
   - dependencias que faltan o sobran según persistencia y Lombok, sin retirar
     librerías adicionales usadas por el servicio sin aprobación explícita; al revisar
     el `build.gradle` de un gateway incorporado: si declara `org.projectlombok:lombok` o
     `annotationProcessor 'org.projectlombok:lombok'` y ningún archivo `.java` del servicio
     importa una anotación de Lombok, inclúyelo en el plan como **dependencia sobrante** con
     el motivo "Lombok declarado pero no importado en ningún archivo Java del gateway". El
     usuario decide si retirarlo;
   - puerto libre, base y context-path independientes, perfiles y spring.application.name; aplica la regla de `references/decisiones-stack.md` (el servicio tocado entra siempre con los perfiles que falten). Obtén `python3 -I -B .agents/scripts/servicios.py nombres <servicio>` y la salida JSON literal de `python3 -I -B .agents/scripts/servicios.py perfiles <servicio>`, e incluye en el plan, por cada entrada de `faltan`, su `archivo_esperado` en `## Archivos a crear o modificar`. Los perfiles esperados son los de `servicios.py` (todas las entradas de `devops.entornos`, no solo las desplegables); «Entornos del plan aprobado» sigue enumerando los datos de destino solo para `desplegar: true`. La base proviene de rootProject.name sin `-service` final, también para el gateway. NOMBRE_SERVICIO avisa de convención; con DevOps, NOMBRE_JAR entra en el plan para igualar el artefacto al nombre antes de generar.
     Si un servicio no gateway no tiene context-path, propone `/<base>` para aprobación. spring.application.name conserva N-S, independiente del nombre del Service Kubernetes.
     si se convierte application.properties a YAML, incluir archivo origen/destino y cada
     propiedad conservada, eliminada o pendiente de decisión del usuario, que se resuelve antes de aprobar. Los perfiles que incorpora (local y por entorno) usan los nombres de la plantilla: `DB_HOST_<P>`, `DB_PORT_<P>`, `DB_NAME_<P>`, `USER_NAME_DB_<P>` y `PASSWORD_DB_<P>` (con `<P>` en mayúsculas según el perfil), en formato `${VARIABLE}` sin respaldo. Si el servicio ya usa otros nombres, el plan del servicio muestra antes/después y pide decisión;
   - ExceptionResponse y manejador según api_error, sin traza, códigos por tipo;
   - `.gitignore`/`.dockerignore`: conservar los recibidos y proponer ajustes; si faltan,
     usar `.agents/skills/service-creator/assets/gitignore.template` y
     `.agents/skills/service-creator/assets/dockerignore.template`.
   El servicio común no recibe OAuth2 Resource Server por la opción de autenticación.
<!-- si integraciones.autenticacion=clerk -->
   El gateway sí lleva OAuth2 Resource Server y la validación JWT de las plantillas.
<!-- fin -->
<!-- si integraciones.gestion_usuarios=organizaciones|aplicacion -->
   Solo el servicio de gestión identificado en el plan recibe las dependencias y
   protección directa JWT de `profile-installer`, sin Data REST. Instalar su lógica
   completa requiere el contrato y el workflow add-user-management; no se infiere del ZIP.
<!-- fin -->
4. Distingue estos estados antes de pedir aprobación:
   - Si al incorporar hay dos o más servicios y `backend.gateway` es null, prepara un borrador con `## Antes de crear el gateway`: carpeta propuesta, nombre, base, context-path vacío, puerto libre y motivo. Pide al usuario declarar `backend.gateway: <carpeta propuesta>` antes de crearla. No crees todavía el gateway ni adaptes el servicio incorporado.
<!-- si devops.infraestructura=jenkins-kubernetes -->
     Ejecuta `python3 -I -B .agents/scripts/servicios.py entornos` y `listar`. Por cada entorno con `desplegar: true`, muestra también `gateway_nodo_puerto` y `cors_origenes`. Calcula el rango de servicios de cada entorno como `nodo_puerto_base + min(0, offsets)` a `nodo_puerto_base + max(0, offsets)`, con `offset = puerto efectivo - 8080`, incluido el servicio que se incorpora y los puertos propuestos en el plan. Usa el puerto de la plantilla (30080, 30680...) solo si está entre 30000 y 32767, fuera de los rangos de TODOS los entornos desplegables y distinto de los otros puertos de gateway. Si no sirve, prueba `nodo_puerto_base - 1` y baja de uno en uno hasta cumplirlo; si bajas de 30000, bloqueado sin inventar un puerto. Muestra los offsets, rangos, candidatos rechazados y valor elegido. Los `cors_origenes` son los orígenes públicos del front de ese entorno: si faltan, pídelos; nunca los inventes.
<!-- si devops.infraestructura=ninguna -->
     Solo se declara `backend.gateway`; no hay claves por entorno.
<!-- fin -->
     Integra aquí la corrección de `backend.cors_origenes` si está vacío: sin los orígenes locales acordados el navegador bloquearía llamadas del front.
<!-- si integraciones.autenticacion=clerk -->
     Integra aquí la corrección de `integraciones.clerk_issuer_uri` si falta; nunca inventes el issuer ni omitas validate.
<!-- fin -->
     Deja el borrador y el manifest con `estado: bloqueado` y el remedio «edita `stack.yaml` con esos valores y relanza el workflow». Termina esta ejecución antes del punto 5, sin aprobación ni escritura de archivos del proyecto, tampoco del servicio incorporado. Ningún agente edita stack.yaml. No es obligatorio regenerar: solo actualizaría claves.md para estas claves. La siguiente ejecución rehace el plan completo.
   - Si `backend.gateway` está declarado y su carpeta no existe, no ejecutes `validar-gateway`. Ejecuta `node .agents/scripts/stack.mjs validate`.
<!-- si devops.infraestructura=jenkins-kubernetes -->
     Ejecuta además `python3 -I -B .agents/scripts/servicios.py validar-entornos`: un bloqueo se muestra y detiene el plan. Hasta crear el gateway son esperados los avisos `no_determinable` de CORS y de sus valores por entorno; no son permiso para ignorar bloqueos.
<!-- si devops.infraestructura=ninguna -->
     Hasta crear el gateway es esperado el aviso `no_determinable` de CORS; no es permiso para ignorar bloqueos.
<!-- fin -->
     Propón crearlo en `## Servicio nuevo` con esa carpeta declarada, nombre, base, context-path vacío, puerto libre, motivo y lista exacta de archivos, incluido `<gateway>/src/test/java/<paquete>/__CLASE_PRINCIPAL__Tests.java` con el nombre de clase ya resuelto, obtenido de `assets/gateway/AplicacionTests.template.java`. Repite esos destinos en `## Archivos a crear o modificar`.
   - Si la carpeta del gateway existe, ejecuta `python3 -I -B .agents/scripts/servicios.py validar-gateway` sobre todas sus rutas, también al incorporar el propio gateway. Propón añadir la ruta del servicio incorporado y sustituir en `GatewayConfig.java` las rutas desfasadas, sin duplicarlas. Lista como sobrantes las de servicios inexistentes para decisión del usuario.
   En cualquier propuesta de creación comprueba CORS global e issuer aplicable antes de aprobarla; si faltan, añade las correcciones a `## Antes de crear el gateway` y termina bloqueado con el mismo remedio, sin escribir archivos del proyecto.
   Para `__BOM_CLOUD__`, reutiliza el tren de un servicio con Spring Cloud y comprueba su compatibilidad. Si no existe ninguno, propón el tren con cita verificada de `python3 -I -B .agents/scripts/documentacion.py preguntar spring-cloud "¿Qué tren GA admite Spring Boot <major.minor> y qué compatible-boot-versions declara su spring-cloud-commons?"`, o con una fuente aportada por el usuario. El tren debe admitir el major.minor de `backend.spring_boot` según `spring.cloud.compatibility-verifier.compatible-boot-versions` de su commons; no desactives ese verificador. Solo GA: si únicamente hay -M* o -RC*, avisa y pide decisión expresa. Sin cita verificada, decláralo pendiente y no des el valor por bueno ni apruebes su uso por una supuesta alineación típica.
<!-- si devops.infraestructura=jenkins-kubernetes -->
   Para `__VERSION_GRPC__`, sin gateway previo usa el `io.grpc:grpc-api` que resuelve el cliente de Kubernetes del tren elegido. Cita la resolución o marca el valor expresamente provisional en el plan para su aprobación y comprobación posterior; nunca uses una versión «típica». La plantilla conserva una versión explícita de grpc-netty aunque una BOM pudiera gestionarla.
<!-- si devops.infraestructura=ninguna -->
   Esta variante no añade grpc-netty ni necesita resolver `__VERSION_GRPC__`.
<!-- fin -->
   El plan registra valor, fuente, compatibilidad y comprobaciones pendientes de cada versión; una versión pendiente no se presenta como verificada.
   El plan enumera una petición GET de comprobación por cada ruta a través de la dirección pública del gateway, con el endpoint que devuelve enlaces y la autenticación necesaria si aplica. La ejecuta el usuario o la IA con permiso. Esperado: código 200 y cada enlace devuelto comienza por la dirección pública del gateway (esquema, host y puerto públicos), nunca por una IP de pod. Si no existe endpoint que devuelva enlaces, declara esa comprobación pendiente en vez de inventar una respuesta. Comprueba además que el health desplegado no liste servicios internos.
5. Pide aprobación del plan completo. approved-plan.md conserva la aprobación literal,
   sección `## Archivos a crear o modificar` completa y eliminaciones expresas. No
   reescribas lo no aprobado. `## Archivos a crear o modificar` solo admite crear, modificar o borrar; cada ruta con su acción. Lo que no cambia va en una sección aparte cuyo título no contenga `archivo`, `objeto` ni `afectados` (`## Artefactos DevOps sin cambios`, con su motivo). Prohibidas las entradas condicionales o pendientes (`a concretar`, `solo si requiere ajuste`, `si procede`): si la IA no puede decidir, pregunta antes de pedir aprobación. Un group distinto en un servicio existente se avisa y propone sin migración automática; muestra además la clave Sonar calculada por servicios.py nombres para compararla con SonarQube.
<!-- si devops.infraestructura=jenkins-kubernetes -->
   Incluye los artefactos DevOps y `modo: generar` para el servicio y gateway que se
   creen/adapten; si la incorporación causa un choque de clave en `getServices()`, el plan
   enumera el renombre en el archivo indicado por `devops.jenkinsfile` en el mismo diff. No leas archivos de `devops/*/account/` ni secretos existentes, tampoco para compararlos. La IA solo crea el Secret desde la plantilla tras comprobar que no existe con `test -e <ruta> || test -L <ruta>`; tú rellenas el archivo, lo compruebas con `python3 -B -E .agents/scripts/servicios.py comprobar-secreto <ruta>` y lo aplicas con `kubectl apply -f <ruta>` antes del primer despliegue; la IA no lo abre.
<!-- fin -->

## Aplicación y verificación

6. `backend-developer` produce code-changes.md; `file-writer` aplica solo lo aprobado
   a la carpeta existente del importado y compila desde ella. Pide permiso antes del
   primer Gradle. Nunca uses `service-creator` para sobrescribir el importado.
   Si el plan incluye subir el wrapper, ejecuta el comando aprobado con su suma publicada y el JDK compatible con el wrapper actual, tras obtener permiso para Gradle y red. Revisa los cuatro archivos aprobados y exige `OK` del wrapper en `node .agents/scripts/comprobar-versiones.mjs`; confirma que el nuevo wrapper admite los JDK local y del nodo y declara las verificaciones del nodo pendientes del usuario.
   Si hay gateway nuevo aprobado, `service-creator` crea solo ese esqueleto en la carpeta ya declarada en `backend.gateway`, copiando wrapper del servicio ya incorporado; `file-writer` aplica las rutas existentes aprobadas. Confirma que la carpeta creada coincide con `backend.gateway`; no se declara después ni se exige regenerar por esa clave.
<!-- si devops.infraestructura=jenkins-kubernetes -->
   Tras sembrarlo, repite `python3 -I -B .agents/scripts/servicios.py validar-entornos` antes de `devops-engineer` en modo generar. Si bloquea, detente y muestra el diagnóstico.
<!-- si devops.infraestructura=ninguna -->
   Tras sembrarlo, conserva los controles de configuración y rutas del gateway antes de continuar.
<!-- fin -->
   Tras crear el gateway, prevé `preparar-documentacion` para el tren de Spring Cloud y las versiones de módulo de Gateway que resuelve `resolver-bom`.
<!-- si devops.infraestructura=jenkins-kubernetes -->
   Incluye las versiones de módulo de Kubernetes que resuelve `resolver-bom` cuando se use.
<!-- fin -->
   El control documental pedirá sus notebooks. Resuelve ese control antes de continuar con fases que lo exijan.
<!-- si devops.infraestructura=jenkins-kubernetes -->
7. Tras escritura correcta, `devops-engineer` en modo generar, antes de comparación y
   pruebas, incluso si el diff anterior no tocaba DevOps: lo activa el plan aprobado.
   Usa los assets comunes sin cambios; la excepción de gestión solo puede usarse con
   la identificación exacta y los campos aprobados en add-user-management. Un fallo
   vuelve a DevOps con feedback.md, consume intento de ese ciclo (máximo dos), salvo
   causa de código, que vuelve a su productora. No ejecutes kubectl ni apliques archivos.
<!-- fin -->
8. Ejecuta `comparar-plan.py` con la lista completa del plan y genera diff.patch con
   `git add -N` para nuevos aprobados y `git diff HEAD`. Una discrepancia vuelve a la
   fase productora; un destino no aprobado requiere enmienda, no escritura adicional.
   `test-engineer` ejecuta pruebas de cada servicio afectado con permiso para Gradle;
   usa `./gradlew compileJava test`.
<!-- si devops.infraestructura=jenkins-kubernetes -->
   Si el plan aprobó grpc provisional, `test-engineer`, con permiso de Gradle, ejecuta `./gradlew dependencyInsight --dependency io.grpc:grpc-api` desde el gateway sembrado y registra versión y origen resueltos. Si difiere, vuelve a `file-writer` con feedback.md para cambiar solo `__VERSION_GRPC__` por esa resolución ya autorizada como provisional, sin enmienda; repite comparación, compilación y pruebas.
<!-- fin -->
   La fase de revisión de todo el diff se asigna a `.agents/skills/code-reviewer/SKILL.md`, cuyo gate es `node .agents/scripts/sonar-diff-gate.mjs` (análisis por MCP, sin subir análisis al servidor); el orquestador acepta `APPROVED` o `APPROVED WITH RECOMMENDATIONS` solo tras `node .agents/scripts/sonar-diff-gate.mjs --comprobar-recibo RUN_DIR/gate-recibo.json` y, si falla, repite la revisión sin consumir iteración. No se ejecuta `./gradlew sonar` en ningún paso: el análisis en el servidor lo hace el pipeline. Fallos vuelven a la fase productora, y repiten comparación/pruebas/gate/revisión.
<!-- si devops.infraestructura=jenkins-kubernetes -->
   En la comprobación posterior de coherencia, `devops-engineer` usa modo validar si
   el diff afecta configuración/artefactos DevOps; ya se generaron antes de las pruebas.
<!-- fin -->
9. `tech-writer` produce docs-summary.md; actualiza el grafo solo si herramientas.graphify
   es true. Registra las salidas literales y estados en manifest. Cada fase ok avanza;
   fallo vuelve con feedback, máximo dos intentos por ciclo; agotamiento o dato ausente
   implica bloqueado. No declares éxito con comandos pendientes ni pruebas fallidas.
10. Antes de declarar la entrega lista, ejecuta el **preflight completo**:
    `bash .agents/scripts/preflight.sh --workflow incorporate-service --fase cierre`, con permiso antes de su Gradle si aún no existe.
    No omitas ni simules controles. Si falta preparación, pide autorización para
    `bash .agents/scripts/preparar-proyecto.sh` y vuelve a ejecutar. Si el árbol sucio
    de la incorporación lo bloquea, entrega el diagnóstico y espera a que el usuario
    resuelva el estado git; no hagas commits, no escondas cambios ni relajes el control.
    Un bloqueo de infraestructura o configuración deja la entrega pendiente, incluso
    si compilación y revisión han pasado. Registra el preflight que pase antes de
    declarar lista la entrega. La salida enumera lo adaptado, pendientes y variables
    por nombre, nunca valores, y no ejecuta commits automáticos.
<!-- si devops.infraestructura=jenkins-kubernetes -->
## Entornos del plan aprobado

Antes de pedir aprobación, ejecuta `python3 -I -B .agents/scripts/servicios.py entornos` y `validar-entornos`. Enumera la tabla completa de `devops.entornos` para el pipeline. Solo para entradas con `desplegar: true`, enumera los datos de destino: carpeta, rama, sufijo, credencial_kubeconfig (solo ID), imagen, desplegar, puerto efectivo, nodePort, réplicas, recursos y los perfiles y artefactos que se crearán o modificarán. Con `jenkins-kubernetes`, la lista DevOps sale de los campos `archivos` de `servicios.py nombres <servicio> --entorno <carpeta>` para cada entorno afectado. Los nombres de carpeta son libres y no se obtienen de la rama. El gateway usa gateway_nodo_puerto; sus perfiles llevan sufijo, CORS e issuer públicos de cada entorno y mantienen los valores globales en local.

Si el proyecto solo tiene una carpeta, lista las que faltan para aprobación; no alteres un entorno existente fuera del plan. Para migrar el Jenkinsfile existente, incluye su diff aprobado de lógica y mapa de entornos; no lo reemplaces automáticamente. RBAC y cuentas de Jenkins mantienen nombres fijos y contenido idéntico si comparten clúster; nunca leas los archivos existentes de account/. Las nuevas cuentas y Secrets vacíos requieren sus rutas aprobadas por carpeta y las comprobaciones de ausencia e ignore vigentes. Tú rellenas el Secret, lo compruebas con `python3 -B -E .agents/scripts/servicios.py comprobar-secreto <ruta>` y lo aplicas con `kubectl apply -f <ruta>` antes del primer despliegue; la IA no lo abre.

Con modo generar, DevOps corre después de la escritura exitosa y antes de comparar-plan.py, git add -N, git diff HEAD, pruebas, gate y revisión. Lo activa el plan aunque el diff previo no tocara DevOps. Un fallo de artefactos vuelve a DevOps con feedback.md (máximo dos intentos); solo codigo_diff vuelve a escritura. En la revisión posterior se invoca modo validar. Con modo validar inicial se conservan la comparación temprana y la condición posterior del diff.
<!-- fin -->

Antes de aprobar cualquier plan, sigue `.agents/workflows/references/decisiones-stack.md`; consulta clases, remedios y códigos que resuelve este workflow en `.agents/config/codigos.yaml`.

En la entrada especial, antes del plan, ejecuta `python3 -I -B .agents/scripts/registro-stack.py comprobar` sin preflight completo; conserva la entrada documental estricta existente y no exijas commit de la importación para diseñar.

<!-- si devops.infraestructura=jenkins-kubernetes -->
Antes de aprobar DevOps, compara archivos y recursos con servicios.py nombres. Si difieren, enumera cada ruta vieja/nueva (git mv) y campo a editar, con su diff aprobado. En Avisos explica que los recursos viejos siguen en el clúster hasta que el usuario los borre. Lista los nombres nuevos de secrets de base y Clerk desde referencias públicas, nunca sus valores ni el contenido de account/. Tú rellenas, compruebas con `python3 -B -E .agents/scripts/servicios.py comprobar-secreto <ruta>` y aplicas los Secret con `kubectl apply -f <ruta>` antes del primer despliegue; la IA no los abre ni ejecuta kubectl.
<!-- fin -->
