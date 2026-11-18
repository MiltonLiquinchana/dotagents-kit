---
trigger: model_decision
description: Reglas de arquitectura Spring Boot, Java, microservicios, proyecciones JPA, Data REST y persistencia.
---

# Reglas de Arquitectura (Spring Boot & Java)

Las versiones (Java, Spring Boot) no se declaran aquí: son parámetros del proyecto y se leen de `.agents/stack.yaml` (`backend.java`, `backend.spring_boot`).

**OBLIGATORIO — Versiones del proyecto**: escribe código compatible con `backend.java` y `backend.spring_boot` de `.agents/stack.yaml` (las librerías, plugins y BOM según el inventario de cada servicio, con versiones compartidas alineadas), sin APIs de otras versiones. Y **idiomático** para esas versiones: si el lenguaje, el framework o una librería ofrece una forma más simple, segura o clara de resolver algo (con menos código), úsala en lugar del patrón antiguo. Ejemplos: fechas con `java.time` en lugar de `Date`/`SimpleDateFormat`; colecciones con `List.of`/`Map.of` en lugar de llenarlas con `add` en un bucle; la anotación vigente del framework en lugar de la que esa versión deprecó. La regla se aplica a todo el código que se escriba, conforme al plan o al completar la implementación. Si al escribir surge una duda sobre si algo existe en la versión del proyecto, consulta Open Notebook mediante el script de documentación; si faltan fuentes, detén la propuesta y solicita su preparación con aprobación; si sigue la duda, pregunta al usuario antes de usarla, y solo con preguntas genéricas sobre la librería y su versión (nunca código, datos ni rutas del proyecto). No cambies versiones de Java, Spring Boot ni dependencias de ningún `build.gradle` si el plan aprobado no enumera esos cambios. Actualizar la versión del proyecto lo decide el usuario en `stack.yaml` y regenerando el `.agents`; la adaptación de los builds debe quedar aprobada en el plan.
El preflight comprueba la conexión con Open Notebook por GET y coteja el registro local: las tecnologías del catálogo requieren documentación activa y válida de su versión; una versión catalogada no resoluble bloquea. Las tecnologías fuera del catálogo avisan; si la tarea las usa, se requiere añadirlas al catálogo con la sección "Ampliar el catálogo del proyecto" de preparar-documentacion.md, sin suponer capacidades de su versión. Una retirada propone archivar solo sin usuarios. El usuario decide entre otra documentación/fuente o cambiar versiones mediante un plan aprobado.

## 1. Estándares de Java y Calidad

- **Clean Code**: Aplica SOLID, DRY, YAGNI. Complejidad ciclomática ≤ 10.
- **Records**: Usa `record` para DTOs y clases de transporte de datos inmutables.
- **Pattern Matching**: Usa `instanceof` y `switch` con pattern matching donde simplifique el código.
- **Jerarquías**: Usa `sealed` para jerarquías cerradas y `Optional` en lugar de `null`.
- **Virtual Threads**: Diséñalas en endpoints con llamadas bloqueantes a BD o a otros servicios (I/O-bound), donde la concurrencia alta es esperada.
<!-- si backend.lombok=true -->
- **Constructor Injection**: Usa `@RequiredArgsConstructor`. No uses `@Autowired` en campos.
<!-- fin -->
<!-- si backend.lombok=false -->
- **Constructor Injection**: Inyección por constructor explícito con campos `private final`; no uses Lombok. No uses `@Autowired` en campos.
<!-- fin -->
- **Testing Obligatorio**: Todo cambio de lógica de negocio requiere tests unitarios y/o de integración.

## 2. Arquitectura de Microservicios

Las decisiones de exposición interna definen el alcance de cada microservicio; las decisiones de comunicación entre servicios definen los contratos y la integración del sistema.

### Reglas críticas de Proyecciones

- Los getters de la `interface projection` coinciden exactamente con los alias del SELECT del Stored Procedure.
- Documenta el índice del SP en un comentario encima de cada getter.
- Mapea a tipos Java compatibles. No hagas conversiones implícitas que causen pérdida de precisión, overflow o unboxing null-unsafe.
- No modifiques datos desde una proyección — son solo lectura.
- Referencia el Stored Procedure en el Javadoc de la proyección o método del repositorio.

### Patrón de decisión de exposición

| Patrón | Cuándo usar | Ejemplo |
|--------|-------------|---------|
<!-- si backend.persistencia=jpa -->
| **Data REST puro** | Entidad simple (sin cálculos, sin SP), catálogo o referencia estable, sin validación de negocio, sin orquestación de múltiples repositorios. Usa `@RepositoryRestResource(path="...", collectionResourceRel="...", exported=true)`. | Repositorio de un catálogo (p. ej. uno de clientes) |
<!-- fin -->
| **Capas Estrictas** | Endpoint consume un Stored Procedure, filtros dinámicos complejos, validación de negocio, transformación de DTOs, u orquesta múltiples repositorios. Usa `Controller → Service (interface) → ServiceImpl → Repository`. | Endpoint de negocio con SP detrás (p. ej. uno de pedidos) |
<!-- si backend.persistencia=jpa -->
| **Data REST Híbrido** | CRUD base expuesto vía Data REST, con métodos internos ocultos vía `@RestResource(exported=false)`. | `PedidosRepository.findBySpListarPedidosResumen()` |
<!-- fin -->

<!-- si backend.persistencia=jpa -->
**REGLA CRÍTICA**: No expongas el mismo caso de uso por dos rutas (Data REST + Controller paralelo).
<!-- fin -->

<!-- si backend.persistencia=jpa -->
**Exportación de repositorios por Data REST (declararla siempre)**: `spring-boot-starter-data-rest` usa por defecto la estrategia de detección `DEFAULT`, que exporta **todo repositorio `public`** salvo que se marque `exported = false` **a nivel de tipo**. Marcar solo un método con `@RestResource(exported = false)` no basta: el repositorio sigue exportándose con su CRUD completo. Todo repositorio nuevo declara su exposición a nivel de tipo con `@RepositoryRestResource(...)`: `exported = false` si solo lo usan las capas (caso de un SP detrás de un Controller), o `path`/`collectionResourceRel` explícitos si se quiere Data REST. **Si la entidad contiene credenciales o datos sensibles (p. ej. `Clientes.Email`), nunca se exporta.** Cómo verificarlo sin base de datos: un test de `@SpringBootTest` con la URL de la base apuntando a un puerto cerrado puede pedir `GET /api` (raíz de Data REST), que lista los recursos exportados; Spring pluraliza el nombre (`Clientes` → `clienteses`). Origen: un Plan que solo ocultaba el método exponía `/api/clienteses`; se detectó leyendo la configuración y se confirmó con esa sonda. Un test unitario con mocks no puede detectarlo.
<!-- fin -->

**Consumidores antes de tocar una ruta existente**: no se puede ocultar (`@RestResource(exported = false)`), renombrar ni retirar una ruta ya expuesta sin comprobar antes quién la consume; esa comprobación se realiza durante el diseño antes de persistir. Busca el path en el frontend hermano (ruta declarada en `.agents/rules/project.md`; los clientes del repositorio del frontend siguen las rutas con el prefijo del gateway, p. ej. `/api/pedidos/...`), en el gateway (`SecurityConfig`, `GatewayConfig`) y en el resto de servicios del proyecto. Si hay consumidores, la ruta **no se retira**: se elige otra opción (p. ej. reutilizar un SP ya en capas para un caso de uso distinto) o se declara el cambio de contrato y espera confirmación explícita del usuario. Origen: un plan de diseño proponía ocultar `/api/pedidos/search/obtenerresumenpedidoreporte`, que el frontend consume (su implementación de repositorio); solo se detectó al comprobarlo.

### Proyecciones

<!-- si backend.persistencia=jpa -->
- Usa `interface projection` (recomendado) para mapear resultados de SPs y consultas JPA optimizadas.
<!-- si backend.persistencia=jdbc -->
- Usa `interface projection` (recomendado) para mapear resultados de SPs.
<!-- fin -->
- Documenta el índice/campo exacto de origen en cada getter.
- Ejemplo:
```java
  public interface ResumenPedidoProjection {
      // Índice 0: pe.PedidoId
      Integer getPedidoId();
      // Índice 1: pe.PedidoCode
      String getPedidoCode();
  }
```
<!-- si backend.persistencia=jpa -->
  Ver ejemplos en proyecciones JPA.
<!-- fin -->

### DTOs

- **Entrada (@RequestBody)**: Solo para POST/PUT/PATCH. Valida con `@Valid`.
<!-- si backend.persistencia=jpa -->
- **Salida (Respuesta)**: Usa proyecciones JPA para lectura. Usa DTOs solo si la transformación es compleja.
<!-- si backend.persistencia=jdbc -->
- **Salida (Respuesta)**: Usa proyecciones para lectura. Usa DTOs solo si la transformación es compleja.
<!-- fin -->
- **REGLA CRÍTICA**: No uses DTOs como reemplazo de proyecciones en consultas SELECT.

## 3. Persistencia y consultas

<!-- si backend.persistencia=jpa -->
- **JPA**: Usa `FetchType.LAZY`. Usa `JOIN FETCH` para evitar N+1.
<!-- fin -->
<!-- si backend.persistencia=jpa -->
- **Queries nativas**: Úsalas solo cuando JPA no cubra el caso. Mapea resultados a `interface projection`.
<!-- fin -->
- **Transacciones**: Aplica `@Transactional` en la capa de servicio.
- **Repositorio limpio**: Los repositorios contienen solo consultas — cero lógica de negocio.

## 4. API y manejo de errores

- **Endpoints REST**: Usa verbos HTTP correctos, rutas claras y códigos de estado coherentes con la operación.
- **Validación**: Usa Bean Validation (`@Valid`, `@NotNull`, `@Size`, `@Pattern`). Rechaza payloads inválidos antes de la capa de negocio.
- **Excepciones centralizadas**: Usa un `@RestControllerAdvice` para transformar excepciones en respuestas estándar.
- **Manejador genérico**: El `@RestControllerAdvice` incluye un manejador de última instancia que responde el mismo contrato de error de la API, con el campo de mensaje indicado por `api_error.campo_mensaje` de `.agents/stack.yaml` y, solo si `api_error.campo_codigo` no es `null`, el campo de código indicado por esa clave; con `null`, el contrato solo lleva el mensaje: ningún error no controlado sale con el cuerpo por defecto del framework (`timestamp`/`status`/`error`/`path`).
- **Resiliencia**: Aplica timeouts, retries y circuit breakers en todo cliente que llame a otro microservicio.

## 5. Seguridad y contrato

<!-- si integraciones.autenticacion=clerk -->
- **Clerk**: La URL concreta de `issuer-uri` es específica de la instancia de Clerk del proyecto; consúltala en `integraciones.clerk_issuer_uri` de `.agents/stack.yaml`, no la hardcodees en documentación ni tests. `clerk` (router) es el punto de entrada y enruta a la skill adecuada.
<!-- fin -->
<!-- si devops.infraestructura=jenkins-kubernetes -->
- **Configuración por entorno**: Los CORS e issuer globales corresponden a local; en Kubernetes los sustituye el documento k8s de application-<sufijo>.yaml, usando las propiedades públicas de devops.entornos.<carpeta>. No se escriben en Java ni se obtienen de account/.
<!-- fin -->

- **Credenciales fuera del agente**: En `application*.yml`, toda credencial aparece solo como `${VARIABLE}` — una variable de entorno que exporta el usuario. Ningún agente escribe ni lee el valor: el plan y los artefactos nombran la variable, no el valor, y el que exporta la variable es el usuario al arrancar el servicio. Si la variable no existe al arrancar, el servicio falla con un mensaje que la nombra. La `${VARIABLE}` no lleva valor de respaldo: una credencial escrita como `${VARIABLE:valor}` con valor no vacío está prohibida, porque publicaría el valor en el repositorio y haría arrancar el servicio sin datos reales; la corrección es quitar el respaldo y dejar `${VARIABLE}`.
<!-- si devops.infraestructura=jenkins-kubernetes -->
- **Archivos secretos fuera del agente**: Ningún agente lee `.env*`, valores de credenciales, archivos de secretos existentes ni kubeconfig. La única escritura permitida en `devops/<carpeta>/account/` corresponde a `devops-engineer` en modo `generar`, con el plan aprobado: crear desde su plantilla y solo si no existen `rbac.yaml`, `jenkins-account.yaml`, `secrets-jenkins-account.yaml` y los secrets de base vacíos (`secrets-<base>-<sufijo>.yaml`, según `servicios.py nombres`). Nunca lee ni sobrescribe los existentes. El usuario pone los valores y aplica los archivos; el código solo referencia sus nombres.
<!-- si devops.infraestructura=ninguna -->
- **Archivos secretos fuera del agente**: Ningún agente lee `.env*` ni valores de credenciales; el usuario los configura y el código solo referencia sus nombres.
<!-- fin -->
- **Gateway central**: El Gateway centraliza la seguridad y el ruteo cuando existe.
- **Contratos claros**: Todo cambio en API pública se documenta y se revisa por compatibilidad.
- **Auditoría de cambios**: Documenta cambios de comunicación entre servicios en Javadoc/README. El Grafo de Conocimiento (`GRAPHIFY_BACKEND=none graphify . --update`) indexa automáticamente los nuevos contratos y dependencias.

## 6. Migraciones de Esquema

- Todo cambio de esquema (tabla, columna, índice, constraint) va en un script de migración versionado (Flyway/Liquibase) — nunca aplicado manualmente ni vía `ddl-auto=update`.
- Migraciones destructivas (DROP, ALTER que trunque datos, rename sin migración de datos) requieren confirmación explícita del usuario antes de persistirse — mismo tratamiento que `application.yml`/`build.gradle`.
- Se verifica que toda migración nueva es aditiva/retrocompatible con la versión de código previamente desplegada, salvo excepción documentada en el plan.

Ejemplos de clientes y pedidos: ejemplo con la convención recomendada; las convenciones efectivas se leen de `.agents/stack.yaml`.
<!-- si integraciones.gestion_usuarios=organizaciones|aplicacion -->
## Gestión de usuarios y registro restringido

La instancia de Clerk debe tener registro restringido, solo personas invitadas. Sin roles, cualquier usuario con sesión puede usar las operaciones de administración. La página de registro solo sirve para aceptar invitaciones; el pre-registro crea un perfil local PENDIENTE y no pasa por Clerk. No se implementa autorización por roles. PENDIENTE=1, INVITADO_A_CLERK=2, ACTIVO=3, INACTIVO=4 se expresan como constantes con nombre; el contrato registra la correspondencia final. INACTIVO es estado local y no revoca sesiones de Clerk. No hay contraseñas locales ni tabla de roles.
<!-- fin -->

Si surge una duda de API en diseño, desarrollo o revisión, consulta mediante `python3 .agents/scripts/documentacion.py preguntar TECNOLOGIA "PREGUNTA_GENERICA" --version VERSION`. La referencia debe corresponder a la serie del proyecto (major.minor; JDK: mayor) y las notas al parche exacto. Solo se usa una cita verificada literalmente. Sin evidencia, pregunta; no envíes código, tablas, datos, rutas ni credenciales. Las decisiones del proyecto siguen en knowledge-base/ con tgrep.
