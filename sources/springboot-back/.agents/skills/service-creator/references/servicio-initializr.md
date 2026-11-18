# Traer un servicio desde Spring Initializr

Para el primer servicio, el usuario obtiene el ZIP en Spring Initializr y lo pega en
el workspace. No hay una versión de Gradle en stack: Initializr fija el wrapper del
primero y los servicios posteriores copian ese wrapper de un servicio existente.

## Parámetros y nombres

Lee cada parámetro con `node .agents/scripts/stack.mjs get <clave>`; los marcadores
se resuelven desde `.agents/stack.yaml`, no son valores para pegar literalmente.

| Campo | Valor |
|---|---|
| Project | Gradle - Groovy |
| Language | Java |
| Spring Boot | `<backend.spring_boot>` |
| Java | `<backend.java>` |
| Packaging | Jar |
| Group | `<backend.group>` |
| Artifact y Name | El nombre aprobado; recomendado `<base>-service`, por ejemplo `clientes-service` |
| Package name | `<backend.group>.<base sin guiones>` |

Aprueba primero `rootProject.name` (recomendado `<base>-service`) y su carpeta. La base es ese nombre sin un `-service` final, también para el gateway; no proviene del context-path. La base sin guiones debe ser un identificador Java válido y no colisionar con otro paquete. La clase aplica `<nomenclatura.clase_aplicacion>` con `{AliasPascal}` = base en PascalCase. El context-path propuesto es `/<base>` salvo otro aprobado. Un nombre sin el sufijo o base distinta de la URL solo avisa. Tras pegar el servicio, consulta `servicios.py nombres` para esos valores.

## Servicio con base de datos: selecciones

Los rótulos siguientes no se han verificado por red y pueden variar según la versión
de Initializr. Comprueba cada selección por su coordenada; no elijas una alternativa
de tecnología por semejanza del nombre. No copies versiones de otro proyecto.

| Rótulo orientativo | Coordenada |
|---|---|
| Spring Boot Actuator | `org.springframework.boot:spring-boot-starter-actuator` |
| Validation | `org.springframework.boot:spring-boot-starter-validation` |
| Spring Boot DevTools | `org.springframework.boot:spring-boot-devtools` |
| MySQL Driver | `com.mysql:mysql-connector-j` |
<!-- si backend.persistencia=jpa -->
| Spring Data JPA | `org.springframework.boot:spring-boot-starter-data-jpa` |
| Rest Repositories, solo servicio común | `org.springframework.boot:spring-boot-starter-data-rest` |
<!-- si backend.persistencia=jdbc -->
| JDBC API | `org.springframework.boot:spring-boot-starter-jdbc` |
| Spring Web | `org.springframework.boot:spring-boot-starter-web` |
<!-- fin -->
<!-- si backend.lombok=true -->
| Lombok | `org.projectlombok:lombok` |
<!-- fin -->

El servicio común no añade OAuth2 Resource Server por la opción de autenticación:
se reserva al gateway y, cuando esté habilitado, al servicio específico de gestión.
No añadas dependencias de gateway o discovery al servicio con base de datos.
<!-- si integraciones.gestion_usuarios=organizaciones|aplicacion -->

Solo si el plan identifica este servicio como gestión de usuarios, omite Rest
Repositories y añade Spring Web (`org.springframework.boot:spring-boot-starter-web`)
y OAuth2 Resource Server (`org.springframework.boot:spring-boot-starter-oauth2-resource-server`).
Su instalación añade Spring Security (`org.springframework.boot:spring-boot-starter-security`),
Clerk SDK (`com.clerk:backend-api`) y Svix (`com.svix:svix`) desde los assets aprobados;
los dos SDK no son selecciones de Initializr. No extiendas esas dependencias a los
demás servicios. Los rótulos también pueden variar según la versión de Initializr.
<!-- fin -->

## Si se trae un gateway

No lleva base. Selecciona Spring Boot Actuator
(`org.springframework.boot:spring-boot-starter-actuator`), Spring Boot DevTools
(`org.springframework.boot:spring-boot-devtools`) y **Reactive Gateway**, variante
Server WebFlux (`org.springframework.cloud:spring-cloud-starter-gateway-server-webflux`).
También aquí el rótulo puede variar según la versión de Initializr.
<!-- si backend.lombok=true -->
Selecciona Lombok (`org.projectlombok:lombok`).
<!-- fin -->
<!-- si integraciones.autenticacion=clerk -->
Selecciona OAuth2 Resource Server
(`org.springframework.boot:spring-boot-starter-oauth2-resource-server`); comprueba
Spring Security (`org.springframework.boot:spring-boot-starter-security`) al adaptar.
<!-- fin -->
<!-- si devops.infraestructura=jenkins-kubernetes -->
El plan de incorporación adapta Kubernetes Client
(`org.springframework.cloud:spring-cloud-starter-kubernetes-client-all`) y
`io.grpc:grpc-netty`; su versión se copia del gateway existente, o se pide al usuario
si no existe. No inventes una versión ni instales discovery en los servicios con base de datos.
<!-- fin -->
La BOM `org.springframework.cloud:spring-cloud-dependencies` se toma de un servicio
existente con Cloud o se confirma con el usuario. Las dependencias de test y los
plugins dependency-management y SonarQube se revisan por coordenada en el plan,
no mediante supuestas selecciones de Initializr.

## Versiones no disponibles y ubicación

Si no se ofrece la versión de Boot o Java configurada, elige la más cercana disponible
para obtener el ZIP. En la incorporación, propón ajustar expresamente las líneas
`id 'org.springframework.boot' version '<backend.spring_boot>'` y
`languageVersion = JavaLanguageVersion.of(<backend.java>)` del build al stack.
No cambies las versiones del stack para acomodar el ZIP. Si su wrapper es incompatible,
detente y pide una decisión; no lo sustituyas automáticamente ni añadas una clave Gradle.

Descomprime la carpeta en la raíz del proyecto: un directorio por servicio con
`build.gradle`, `settings.gradle`, `gradlew` y `gradle/wrapper/`. No añadas un build
multimódulo en la raíz. Después pide al agente que incorpore el servicio al proyecto.
Conserva los ignores del ZIP; si faltan, la incorporación propone las plantillas
propias del `.agents`, nunca asegura que Initializr entregue `.dockerignore`.
