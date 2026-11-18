---
name: microservices-architect
description: Orquesta la comunicación global, seguridad y patrones distribuidos del ecosistema, usando el Grafo de Conocimiento. Solo se invoca cuando la feature requiere comunicación entre servicios.
---

# Microservices Architect

Rol: Diseña la comunicación y fronteras entre microservicios.

## Entrada

Recibes `OUT_DIR` (carpeta donde escribes tu salida) y las rutas de estos archivos:

| Artefacto | Obligatorio | Contenido |
|---|---|---|
| `request.md` | sí | Solicitud del usuario, literal. |
| `context.md` | sí | Contexto técnico del proyecto. |
| `architecture-decision.md` | sí | Decisión de patrón vinculante del servicio. |
| `feedback.md` | no | Correcciones pedidas sobre un intento anterior tuyo. Si existe, corrige solo lo que indica. |

Trabaja solo con estos archivos y con el código del proyecto. No asumas contexto fuera de ellos.
Si falta un artefacto obligatorio, no trabajes: escribe la salida con `estado: bloqueado` y la causa.

## Tareas

1. **Tarea 1 — Comunicación entre servicios**: Elige REST síncrono con el cliente HTTP idiomático para la versión del proyecto (por ejemplo, clientes de interfaz `@HttpExchange` llamados con `RestClient`; respeta el cliente que el proyecto ya usa, según el grafo y `knowledge-base/`: cambiarlo solo con aprobación del usuario), o mensajería asíncrona (RabbitMQ) para eventos y desacoplamiento. Define timeouts, retries, circuit breakers y bulkhead.
2. **Tarea 2 — Seguridad**: Valida que las llamadas atraviesan el Gateway. El Gateway centraliza autenticación y ruteo.
3. **Tarea 3 — Bounded Contexts**: Define qué datos y responsabilidades pertenecen a cada servicio. Usa `graphify query` para descubrir integraciones existentes antes de proponer nuevas.
4. **Tarea 4 — Plan maestro**: Para cambios multi-servicio, define el contrato de comunicación (endpoints, esquema de mensajes, patrón de resiliencia) antes de tocar código.
5. **Tarea 5 — Servicio nuevo**: Si la petición necesita un servicio que no existe, propón `## Servicio nuevo` con carpeta, `rootProject.name`, base, context-path, motivo, puerto libre obtenido con `python3 -I -B .agents/scripts/servicios.py siguiente-puerto` o justificado, y lista exacta de archivos. Esos destinos entran también en `## Archivos a crear o modificar`; tú no creas el esqueleto.
   Para el gateway distingue dos condiciones:
   - Si el proyecto pasará a tener dos o más servicios y `backend.gateway` es null, no propongas crearlo en esta ejecución: entrega `estado: bloqueado` con `## Antes de crear el gateway` y pide declarar `backend.gateway: <carpeta propuesta>` antes de crear la carpeta.
<!-- si devops.infraestructura=jenkins-kubernetes -->
     Obtén `servicios.py entornos` y `listar`. Por cada entorno con `desplegar: true`, pide también `gateway_nodo_puerto` y los `cors_origenes` públicos del front, sin inventarlos. Calcula todos los rangos como `nodo_puerto_base + min(0, offsets)` a `nodo_puerto_base + max(0, offsets)`, con `offset = puerto efectivo - 8080`, incluyendo los servicios propuestos. Usa 30080, 30680... de la plantilla si el candidato está entre 30000 y 32767, fuera de TODOS los rangos desplegables y distinto de los otros puertos de gateway; si no, desde `nodo_puerto_base - 1` baja de uno en uno hasta cumplirlo. Si bajas de 30000, bloqueado. Muestra offsets, rangos, descartes y elección.
<!-- si devops.infraestructura=ninguna -->
     Solo se declara `backend.gateway`, sin claves por entorno.
<!-- fin -->
     Incluye aquí la corrección de `backend.cors_origenes` si está vacío y advierte que el navegador bloquearía llamadas sin orígenes locales acordados.
<!-- si integraciones.autenticacion=clerk -->
     Incluye aquí la corrección de `integraciones.clerk_issuer_uri` si falta; nunca inventes un issuer.
<!-- fin -->
     Remedio literal: «edita `stack.yaml` con esos valores y relanza la tarea». La ejecución termina antes de aprobar el plan, sin crear ni adaptar archivos del proyecto, tampoco otro servicio solicitado. No es obligatorio regenerar: solo actualizaría claves.md para estas claves. Ningún agente edita stack.yaml; la siguiente ejecución rehace el plan completo. Deja toda esta sección en inter-service-design.md para que la fase invocante registre el bloqueo en su manifest.
   - Si `backend.gateway` está declarado y su carpeta no existe, propón crearlo con esa carpeta en `## Servicio nuevo`. No ejecutes `validar-gateway`; ejecuta `node .agents/scripts/stack.mjs validate`.
<!-- si devops.infraestructura=jenkins-kubernetes -->
     Ejecuta también `python3 -I -B .agents/scripts/servicios.py validar-entornos`; si bloquea, muestra el diagnóstico y detente. Hasta crear el gateway son esperados los `no_determinable` de CORS y de sus valores por entorno.
<!-- si devops.infraestructura=ninguna -->
     Hasta crear el gateway es esperado el `no_determinable` de CORS.
<!-- fin -->
     Declara nombre, base, context-path vacío, motivo, puerto libre y lista exacta de archivos del esqueleto, incluido `<gateway>/src/test/java/<paquete>/<clase principal>Tests.java` desde `assets/gateway/AplicacionTests.template.java`, con paquete y clase ya resueltos. Incluye esos destinos en la lista de archivos del plan.
   Antes de aprobar cualquier creación de gateway, comprueba CORS global e issuer aplicable; si faltan, devuelve la sección de correcciones y el remedio anteriores con `estado: bloqueado`.
   El plan del gateway incluye `__BOM_CLOUD__` con valor y fuente. Si no hay un servicio con Spring Cloud del que copiar, propone un tren con cita verificada obtenida mediante `python3 -I -B .agents/scripts/documentacion.py preguntar spring-cloud "¿Qué tren GA admite Spring Boot <major.minor> y qué compatible-boot-versions declara su spring-cloud-commons?"`, o una fuente aportada por el usuario. Comprueba que el `major.minor` de `backend.spring_boot` aparece admitido por `spring.cloud.compatibility-verifier.compatible-boot-versions` de su commons. Solo GA; si solo existe -M* o -RC*, advierte y pide decisión expresa. Sin cita verificada, registra el valor pendiente y no lo presentes como válido; no desactives el verificador.
<!-- si devops.infraestructura=jenkins-kubernetes -->
   Incluye `__VERSION_GRPC__` igual al `io.grpc:grpc-api` que resuelve el cliente de Kubernetes del tren elegido, con cita de resolución o expresamente provisional para aprobación. En este último caso deja en el plan la comprobación posterior `./gradlew dependencyInsight --dependency io.grpc:grpc-api`, con permiso para Gradle en la fase de pruebas, y la autorización de ajustar solo esa versión a la resuelta. Nunca una versión «típica». La plantilla mantiene grpc-netty con versión explícita.
<!-- si devops.infraestructura=ninguna -->
   No se añade grpc-netty ni se requiere `__VERSION_GRPC__`.
<!-- fin -->
   Incluye la necesidad de documentación del tren detectado después de sembrar el gateway y el test de arranque en los destinos exactos del plan.
   El plan enumera una petición GET de comprobación por cada ruta a través de la dirección pública del gateway, con el endpoint que devuelve enlaces y la autenticación necesaria si aplica. La ejecuta el usuario o la IA con permiso. Esperado: código 200 y cada enlace devuelto comienza por la dirección pública del gateway (esquema, host y puerto públicos), nunca por una IP de pod. Si no existe endpoint que devuelva enlaces, declara esa comprobación pendiente en vez de inventar una respuesta. Comprueba además que el health desplegado no liste servicios internos.


## Reglas

Antes de escribir código, aplica las comprobaciones del gate en `references/sonarqube-gate.md`, incluidas complejidad máxima 10 por función cuando aplique, imports no usados y todas las reglas de SonarQube citadas allí. No dupliques sus reglas.

- Aplica `.agents/rules/architecture-rules.md` y `.agents/rules/project.md`.
- Consulta el grafo (`graphify query`) antes de proponer nuevas integraciones.
- La comunicación entre servicios debe documentarse en el output (endpoint, payload, códigos de error).
- No comiences implementación hasta que el plan esté aprobado.

## Comprobación de versiones (elección de tecnología)

Antes de elegir la tecnología de comunicación, responde internamente estas preguntas (comprobación interna; no añade una sección al plan): ¿qué versiones aplican y qué ofrecen para esa comunicación (`backend.java` y `backend.spring_boot` de `.agents/stack.yaml`, y las librerías según los `build.gradle`)?, ¿existe en esa versión lo que vas a usar y hay algo obsoleto (deprecated) que debas evitar?, y ¿qué patrón usa ya el proyecto (según tu consulta al grafo, condicionada por `herramientas.graphify`, y tus búsquedas en `knowledge-base/` con tgrep), para reutilizarlo o respetarlo? Se aplican también las reglas del flujo: si dudas de que algo exista en la versión, consulta Open Notebook; si faltan fuentes, detén la propuesta y pide prepararlas con aprobación antes de proponer capacidades, nunca lo des por hecho, y solo pregunta a fuentes externas cosas genéricas sobre la librería y su versión (nunca código, datos ni rutas del proyecto).

Si la tarea usa una tecnología que no está en el catálogo, añádela al catálogo con la sección "Ampliar el catálogo del proyecto" de preparar-documentacion.md y no supongas capacidades de su versión.

## Salida

Escribe **un único archivo**: `OUT_DIR/inter-service-design.md`, con este formato:

```markdown
---
artefacto: inter-service-design.md
skill: microservices-architect
estado: ok | fallo | bloqueado
entradas_leidas: [request.md, context.md, architecture-decision.md]   # las que leíste completas
fecha: <ISO-8601>
---

## Diseño de Comunicación entre Servicios

### Mapa de comunicación
...

### Patrón de integración elegido
(REST con el cliente HTTP elegido / Eventos / Mensajería; y una línea con la tecnología elegida y por qué es la idiomática para la versión del proyecto)

### Contratos de comunicación
(endpoint, payload, códigos de error)

### Recomendaciones para independencia entre servicios
...
```


## Dependencias nuevas completas

El plan lista todas las dependencias nuevas que usará el código, incluidas las de validación y pruebas. Si durante el desarrollo se descubre que falta una, no la añadas: devuelve `estado: bloqueado` nombrando la dependencia que falta, para que el plan se enmiende con la aprobación del usuario.


Consulta y actualización condicional del grafo: usa graphify solo cuando `herramientas.graphify` en `.agents/stack.yaml` sea `true`; con `false`, omite las consultas y actualizaciones al grafo.
