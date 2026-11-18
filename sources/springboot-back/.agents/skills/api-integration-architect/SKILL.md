---
name: api-integration-architect
description: Implementa el patrón de exposición de APIs Spring Boot decidido en el plan aprobado, usando el Grafo de Conocimiento (Codebase Memory) para localizar contratos existentes antes de crear nuevos.
---

# API Integration Architect (Spring Boot)

Rol: Implementa el patrón de exposición recibido en `approved-plan.md`. No toma la decisión de patrón; la recibe como input vinculante.

## Entrada

Recibes `OUT_DIR` (carpeta donde escribes tu salida) y las rutas de estos archivos:

| Artefacto | Obligatorio | Contenido |
|---|---|---|
| `approved-plan.md` | sí | Plan aprobado con el campo `aprobacion` literal del usuario y el patrón de exposición elegido. |
| `feedback.md` | no | Correcciones pedidas sobre un intento anterior tuyo. Si existe, corrige solo lo que indica. |

Trabaja solo con estos archivos y con el código del proyecto. No asumas contexto fuera de ellos.
Si falta un artefacto obligatorio, no trabajes: escribe la salida con `estado: bloqueado` y la causa.
Si el patrón de `approved-plan.md` es Capas Estrictas, escribe `estado: ok` con cuerpo "No aplica".

## Tareas

1. **Tarea 1 — Localizar contratos existentes**: Antes de crear clases nuevas, usa `codebase-memory-mcp cli search_graph --project "<proyecto>" --name-pattern ".*<símbolo>.*"` y `codebase-memory-mcp cli trace_path --project "<proyecto>" --function-name "<símbolo>" --direction inbound` para verificar si existe un contrato reutilizable. Si existe, reutilízalo.
2. **Tarea 2 — Implementar según patrón**:
<!-- si backend.persistencia=jpa -->
   - **Data REST**: Configura `@RepositoryRestResource` con `path` y `collectionResourceRel`.
   - **Híbrido**: Expón CRUD base vía Data REST. Marca métodos internos con `@RestResource(exported = false)`.
<!-- fin -->
   - **Capas Estrictas**: emite `estado: ok` con cuerpo "No aplica" (el plan no requiere este esqueleto para ese patrón).
3. **Tarea 3 — Proyecciones**: Implementa `interface projection` para respuestas de solo lectura. Cada getter debe incluir comentario de índice (`// Índice 0: columna`).
4. **Tarea 4 — DTOs de entrada**: Implementa `record` con `@Valid` para request bodies.
5. **Tarea 5 — Validación de flujo**: Confirma vía `codebase-memory-mcp cli trace_path --project "<proyecto>" --function-name "<símbolo>" --direction inbound` que la cadena de capas es correcta.
6. **Tarea 6 — Exposición controlada**: Asegura que solo se exponen los endpoints definidos en el plan aprobado. No agregues endpoints extra no solicitados.

## Reglas

Antes de escribir código, aplica las comprobaciones del gate en `references/sonarqube-gate.md`, incluidas complejidad máxima 10 por función cuando aplique, imports no usados y todas las reglas de SonarQube citadas allí. No dupliques sus reglas.

- Aplica `.agents/rules/architecture-rules.md` y `.agents/rules/project.md`.
- El patrón de `approved-plan.md` es vinculante. No lo redefinas ni contradigas.
<!-- si backend.persistencia=jpa -->
- No dupliques un caso de uso con `@RepositoryRestResource` y `@RestController` en paralelo.
<!-- fin -->
- Usa proyecciones para consultas de solo lectura. No uses DTOs para SELECT.
- No reindexes (`python3 -I -B .agents/scripts/codebase-memory.py --indexar`) desde aquí.

<!-- si backend.persistencia=jpa -->
## Plantillas

### Data REST simple

```java
@RepositoryRestResource(path = "pedidos", collectionResourceRel = "pedidos")
public interface PedidosRepository extends JpaRepository<Pedido, Integer> {
}
```

### Repositorio con SP oculto

```java
@RestResource(exported = false)
@Query(value = "CALL sp_listar_pedidos_filtrados(:pedidoId, :dynamicSearchField)", nativeQuery = true)
List<ResumenPedidoProjection> findBySpListarPedidosFiltrados(
        @Param("pedidoId") Integer pedidoId,
        @Param("dynamicSearchField") String dynamicSearchField
);
```
<!-- fin -->

## Comprobación de versiones (antes de proponer código)

Antes de escribir cualquier código propuesto, responde internamente estas cuatro preguntas (comprobación interna; no añade una sección al plan):

1. ¿Qué versiones aplican? El lenguaje, el framework y las librerías implicadas, con su origen: `backend.java` y `backend.spring_boot` de `.agents/stack.yaml`, y las librerías según los `build.gradle`.
2. ¿Hay en esas versiones alguna función, método, anotación o sintaxis que resuelva esto con menos código o de forma más clara?
3. ¿Todo lo que voy a usar existe en la versión del proyecto, y no solo en una posterior?
4. ¿Hay algo obsoleto (deprecated) en esa versión que deba evitar?

Fuentes de la comprobación, en este orden, sin duplicar lo que ya consultaste: primero tu consulta al grafo (condicionada por `herramientas.codebase_memory` de `.agents/stack.yaml`: qué existe ya en el código y qué patrón usa, para reutilizarlo o respetarlo; el grafo no contiene dependencias ni versiones), después tgrep sobre `knowledge-base/` (decisiones y correcciones previas que limiten la solución), luego las versiones, y por último la documentación, solo si te quedan dudas sobre qué ofrece esa versión.

- **Si el patrón del proyecto choca con lo idiomático de la versión**: el código nuevo es idiomático salvo que `knowledge-base/` registre una decisión de mantener el patrón; el código existente no se reescribe fuera del plan aprobado. Si la incoherencia importa, señálala en una línea del plan para que el usuario decida.
- **Sin inventar**: si no estás seguro de que algo exista en la versión del proyecto, consulta Open Notebook mediante el script de documentación; si faltan fuentes, detén la propuesta y solicita su preparación con aprobación; si sigues sin certeza, dilo en una línea y pregunta al usuario antes de proponerlo. Nunca lo des por hecho.
- **Documentación**: usa `python3 .agents/scripts/documentacion.py preguntar TECNOLOGIA "PREGUNTA_GENERICA" --servicio NOMBRE` con la asociación del servicio (raíz: `.`); la versión sale del registro cotejado con el inventario local. Solo preguntas genéricas: notas verificadas sin modelo → resúmenes → texto completo (mayor coste); con embeddings utilizables, esa alternativa. Usa únicamente citas que el script haya comprobado literalmente en una fuente válida; si no hay evidencia, pregunta antes de proponerla.
- **Tecnologías fuera del catálogo**: si tu tarea usa una tecnología que el preflight señala como no catalogada, añádela al catálogo con la sección "Ampliar el catálogo del proyecto" de preparar-documentacion.md antes de proponer capacidades de su versión. No las supongas.
- **Privacidad de las consultas**: solo preguntas genéricas sobre la librería y su versión; nunca código del proyecto, nombres de tablas, datos, rutas internas ni credenciales.

## Salida

Escribe **un único archivo**: `OUT_DIR/exposure-code.md`, con este formato:

```markdown
---
artefacto: exposure-code.md
skill: api-integration-architect
estado: ok | fallo | bloqueado
entradas_leidas: [approved-plan.md]   # las que leíste completas
fecha: <ISO-8601>
---

## Esqueleto de Exposición

(Si Capas Estrictas: "No aplica".)

### Contratos reutilizados
(con la query usada)

### Esqueleto implementado
(anotaciones, endpoints, wiring — listo para completar lógica de negocio; debajo de cada bloque de código, la línea **Capacidades de la versión usadas** con lo que aprovecha y desde qué versión existe, según `stack.yaml` y los `build.gradle`)

### Endpoints con contratos de entrada/salida
...

## Archivos tocados
- ruta/EntidadRepository.java
```


## Dependencias nuevas completas

El plan lista todas las dependencias nuevas que usará el código, incluidas las de validación y pruebas. Si durante el desarrollo se descubre que falta una, no la añadas: devuelve `estado: bloqueado` nombrando la dependencia que falta, para que el plan se enmiende con la aprobación del usuario.


Consulta y actualización condicional del grafo: usa Codebase Memory solo cuando `herramientas.codebase_memory` en `.agents/stack.yaml` sea `true`; con `false`, omite las consultas y actualizaciones al grafo. Resuelve `<proyecto>` con `python3 -I -B .agents/scripts/codebase-memory.py --resolver` (exit 0) antes de consultar. Un resultado vacío no demuestra ausencia: usa `check_index_coverage` y, si hay dudas, busca en la fuente. Para rutas y dependencias existentes usa `codebase-memory-mcp cli get_architecture --project "<proyecto>" --aspects '["routes","dependencies"]'` y `codebase-memory-mcp cli trace_path --project "<proyecto>" --function-name "<símbolo>" --direction inbound`. Para Spring Data REST busca `@RepositoryRestResource`.

Ejemplos de clientes y pedidos: ejemplo con la convención recomendada; las convenciones efectivas se leen de `.agents/stack.yaml`.
