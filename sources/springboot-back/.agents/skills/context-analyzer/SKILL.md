---
name: context-analyzer
description: Analiza el contexto técnico de microservicios Java/Spring Boot usando el Grafo de Conocimiento (Codebase Memory).
---

# Java Context Analyzer

Rol: Mapea el contexto técnico del microservicio antes de construir o modificar funcionalidad. Usa el índice de CBM como fuente primaria.

## Entrada

Recibes `OUT_DIR` (carpeta donde escribes tu salida) y las rutas de estos archivos:

| Artefacto | Obligatorio | Contenido |
|---|---|---|
| `request.md` | sí | Solicitud del usuario, literal. |
| `feedback.md` | no | Correcciones pedidas sobre un intento anterior tuyo. Si existe, corrige solo lo que indica. |

Trabaja solo con estos archivos y con el código del proyecto. No asumas contexto fuera de ellos.
Si falta un artefacto obligatorio, no trabajes: escribe la salida con `estado: bloqueado` y la causa.
Si `tgrep` no está disponible, termina con `estado: bloqueado` y la causa. Salvo en los estados que `.agents/rules/tgrep.md` define como válidos y que no son fallo: exit 1 sin coincidencias, el aviso `falling back to local index` con `Indexing: complete`, `Server: not running` con `knowledge-base/.tgrep/serve.json` existente y `knowledge-base` vacía (entonces registra "sin historial (`knowledge-base` vacío)").

## Tareas

1. **Tarea 1 — Búsqueda literal previa (tgrep, primer paso, sin costo)**: extrae 2-4 términos clave de la feature/bug actual y búscalos en `knowledge-base/` antes de consultar el grafo (ver `.agents/rules/tgrep.md`).
2. **Tarea 2 — Consulta al Grafo (fuente primaria)**:
   - Usa `codebase-memory-mcp cli search_graph --project "<proyecto>" --name-pattern ".*<símbolo>.*"` y `codebase-memory-mcp cli trace_path --project "<proyecto>" --function-name "<símbolo>" --direction inbound`; si la búsqueda por nombre no basta, complementa con `codebase-memory-mcp cli search_graph --project "<proyecto>" --semantic-query '["texto"]'` para completar el contexto. Resuelve capas existentes y dependencias con los símbolos y las trazas. No leas archivos completos ni listes directorios si el grafo puede responder.
   - Consulta `codebase-memory-mcp cli get_architecture --project "<proyecto>" --aspects '["hotspots","cycles"]'` para el contexto relevante.
3. **Tarea 3 — Dependencias, versiones y JDK (no están en el grafo)**: lee directamente `<servicio>/build.gradle` (y su `settings.gradle` / `gradle.properties` si hace falta). El índice no contiene las dependencias ni versiones de los `build.gradle` (ver `.agents/rules/codebase-memory.md`).
4. **Tarea 4 — Verificación de archivos clave** (solo si el grafo no tiene la información):
   - `application*.yaml` — puertos, gateway. Nunca leas ni cites `application-feature.yaml` (contiene credenciales conocidas; ver `.agents/rules/project.md`).
   - Handler de excepciones global (`@RestControllerAdvice`).
<!-- si backend.persistencia=jpa -->
5. **Tarea 5 — Preparación para la feature**: Confirma vía `codebase-memory-mcp cli search_graph --project "<proyecto>" --name-pattern ".*<símbolo>.*"` si ya existen controllers, services, repositories o proyecciones relacionados. Detecta el patrón arquitectónico actual (Data REST, Capas Estrictas, Híbrido).
<!-- si backend.persistencia=jdbc -->
5. **Tarea 5 — Preparación para la feature**: Confirma vía `codebase-memory-mcp cli search_graph --project "<proyecto>" --name-pattern ".*<símbolo>.*"` si ya existen controllers, services, repositories o proyecciones relacionados. Detecta el patrón arquitectónico actual (Capas Estrictas).
<!-- fin -->
6. **Tarea 6 — Historial de correcciones (vinculante)**: para cada fichero que la feature vaya a tocar, comprueba por **ruta completa** si existe su nota de correcciones (no busques por nombre base: hay clases homónimas en varios servicios).
   Si `knowledge-base/` solo contiene `.gitkeep` o no tiene ninguna nota `.md`, registra en la salida "sin historial (`knowledge-base` vacío)" en lugar de `enfoques_descartados` y continúa sin usar tgrep (no hay nada que buscar):
   ```bash
   test -f "knowledge-base/<ruta relativa del código sin extensión>-fixes.md" && echo existe
   ```
   Si existe, léela. Si el historial reporta enfoques fallidos, inclúyelos en `enfoques_descartados` de la salida.
7. **Tarea 7 — Consumidores de rutas existentes**: si la feature podría modificar, ocultar o retirar una ruta ya expuesta, busca su path en el frontend hermano y en el gateway (ambos declarados en `.agents/rules/project.md`) y repórtalo en el output (ver `.agents/rules/architecture-rules.md`, "Consumidores antes de tocar una ruta existente").
8. **Tarea 8 — Notas de conocimiento (vía tgrep)**:
   ```bash
   tgrep -F "fichero: {ruta}" knowledge-base/ -l
   ```
   Si existe, léela e incorpórala como contexto de decisiones previas: patrón elegido, responsabilidades y "por qué se creó". No contradigas esas decisiones sin documentar el cambio de condiciones.

## Reglas

- Aplica `.agents/rules/architecture-rules.md`, `.agents/rules/project.md`, `.agents/rules/codebase-memory.md`, `.agents/rules/tgrep.md` y `.agents/rules/knowledge-base.md`.
- **`knowledge-base/` nunca se consulta vía Codebase Memory** — siempre vía `tgrep` (precondición bloqueante, sin fallback a `grep`/`rg`; ver `.agents/rules/tgrep.md`).
- **El grafo es la fuente primaria. Está prohibido leer archivos individuales para mapear contexto si el grafo puede responder.** Solo lee archivos si el grafo no existe, no responde o la información es insuficiente.
- No asumas librerías, versiones ni patrones. Verifica con el grafo o archivos de configuración.
- No reindexes (`python3 -I -B .agents/scripts/codebase-memory.py --indexar`) desde aquí.

## Salida

Escribe **un único archivo**: `OUT_DIR/context.md`, con este formato:

```markdown
---
artefacto: context.md
skill: context-analyzer
estado: ok | fallo | bloqueado
entradas_leidas: [request.md]
fecha: <ISO-8601>
enfoques_descartados: []
---

## Contexto del Microservicio

### Stack detectado
- Java: (ej. 25)
- Spring Boot: (ej. 3.x)
- Spring Cloud: (ej. 2023.x / No detectado)
<!-- si backend.persistencia=jpa -->
- Persistencia: (ej. Spring Data JPA + Hibernate)
<!-- si backend.persistencia=jdbc -->
- Persistencia: (ej. Spring JDBC sobre Stored Procedures)
<!-- fin -->
- Base de datos: (ej. MySQL / SQL Server / PostgreSQL)
- Mensajería: (ej. RabbitMQ / No detectado)

### Patrón arquitectónico actual del servicio
<!-- si backend.persistencia=jpa -->
- (Data REST / Capas Estrictas / Híbrido / No determinado)
<!-- si backend.persistencia=jdbc -->
- (Capas Estrictas / No determinado)
<!-- fin -->

### Handler de excepciones global
- (Existe: `NombreClase.java` / No existe)

### Capas existentes para la feature solicitada
- Controllers: (rutas o "Ninguno")
- Services: (rutas o "Ninguno")
- Repository: (rutas o "Ninguno")
- Proyecciones/DTOs: (rutas o "Ninguno")

### Hallazgos del Grafo
- God nodes relevantes: (módulos centrales que la feature tocará, o "N/A")
- Surprising connections relevantes: (acoplamientos inesperados cerca de la feature, o "N/A")

### Correcciones previas relevantes
- (fichero, resumen del enfoque que falló, o "N/A")

### Conclusión
- (Extender código existente o crear estructura nueva)

### Recomendación de diseño
<!-- si backend.persistencia=jpa -->
- Patrón sugerido: (Data REST / Capas Estrictas / Híbrido)
<!-- si backend.persistencia=jdbc -->
- Patrón sugerido: (Capas Estrictas)
<!-- fin -->
- Razón: ...
```


Consulta y actualización condicional del grafo: usa Codebase Memory solo cuando `herramientas.codebase_memory` en `.agents/stack.yaml` sea `true`; con `false`, omite las consultas y actualizaciones al grafo. Resuelve `<proyecto>` con `python3 -I -B .agents/scripts/codebase-memory.py --resolver` (exit 0) antes de consultar. Un resultado vacío no demuestra ausencia: usa `check_index_coverage` y, si hay dudas, busca en la fuente.
