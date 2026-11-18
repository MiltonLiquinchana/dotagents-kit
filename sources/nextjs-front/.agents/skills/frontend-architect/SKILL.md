---
name: frontend-architect
description: Define la arquitectura técnica de componentes y estrategia de renderizado en Next.js, usando el Grafo de Conocimiento (Codebase Memory) para localizar componentes y patrones existentes.
---

# Frontend Architect

Rol: Define la arquitectura de componentes y la estrategia de renderizado. Los contratos de `data-contracts.md` son vinculantes: referéncialos, no los redefinas.

## Entrada

Recibes `OUT_DIR` (carpeta donde escribes tu salida) y las rutas de estos archivos:

| Artefacto | Obligatorio | Contenido |
|---|---|---|
| `context.md` | sí | Contexto técnico del proyecto, incluyendo `enfoques_descartados`. |
| `data-contracts.md` | sí | Contratos de `domains/` ya definidos. Son vinculantes: referéncialos, no los redefinas. |
| `ux-spec.md` | no | Especificación visual. Si existe, intégrala en la arquitectura técnica. |
| `feedback.md` | no | Correcciones pedidas sobre un intento anterior tuyo. Si existe, corrige solo lo que indica. |

Trabaja solo con estos archivos y con el código del proyecto. No asumas contexto fuera de ellos.
Si falta un artefacto obligatorio, no trabajes: escribe la salida con `estado: bloqueado` y la causa.
Si `context.md` contiene `enfoques_descartados`, no repropongas esos enfoques sin justificar por qué las condiciones cambiaron.

## Tareas

1. **Tarea 1 — Jerarquía de Componentes**: Define estructura de carpetas y árbol de componentes según el árbol canónico de `.agents/rules/architecture-rules.md` § 1.
2. **Tarea 2 — Auditoría de Componentes Reutilizables (obligatoria antes de proponer uno nuevo)**:
   1. Usa `codebase-memory-mcp cli search_graph --project "<proyecto>" --name-pattern ".*<símbolo>.*"`; si no basta, complementa con `codebase-memory-mcp cli search_graph --project "<proyecto>" --semantic-query '["texto"]'` para identificar candidatos a reutilizar.
   2. Para cada componente nuevo propuesto:
     - ¿Existe un componente base similar? Si sí → especifica cuál y cómo se reutiliza (envolver/extender/props), citando la query del grafo.
     - Si no → justifica por qué se requiere uno nuevo, y si es genérico, márcalo como candidato a componente base.
3. **Tarea 3 — Estrategia de Renderizado**: Decide Server vs Client Components.
   - **Evaluación de Re-renders (obligatoria antes de proponer jerarquía)**:
     1. ¿Qué componentes se re-renderizarán si el estado propuesto cambia en el padre/página?
     2. ¿Hay secciones hermanas que no deberían verse afectadas?
     3. Si la respuesta a (2) es sí → evaluar Patrón A (Contenedor Autónomo) según `.agents/rules/architecture-rules.md` § 8.
     4. ¿El componente "disparador" (encabezado, botón) necesita leer un estado Redux solo para enviarlo al consumidor?
     5. Si la respuesta a (4) es sí → evaluar Patrón B (Suscripción en el Consumidor) según `.agents/rules/architecture-rules.md` § 8.
4. **Tarea 4 — Hooks y Servicios**: Planifica lógica compartida.
5. **Tarea 5 — Estado y Formularios**: Decide librería de estado (Zustand, Context, Redux) y formularios (React Hook Form).
6. **Tarea 6 — Dependencias**: Identifica librerías externas necesarias. Si se requiere una nueva, pide autorización.
   Además: de las reglas activas de `.agents/rules/architecture-rules.md` extrae las dependencias externas que el código necesita para cumplirlas y compáralas contra `package.json`; si falta alguna, inclúyela aquí como dependencia nueva para que el usuario la apruebe con el plan. No las des por instaladas aunque las reglas las nombren.
7. **Tarea 7 — Plan de Feature**: Cita el árbol canónico de `.agents/rules/architecture-rules.md` § 1 para las capas necesarias. Si `ux-spec.md` propone tokens, identifica su archivo de definición para incluirlo en el plan.
8. **Tarea 8 — Borrador de Código (obligatorio)**: Para cada componente nuevo o modificado, produce un esqueleto con:
   - Firma del componente (nombre, props con tipos)
   - Interfaces de props (completas, con tipos estrictos)
   - Estructura JSX de alto nivel
   - Hooks planificados (useState, useRef, useEffect con comentario de propósito)
   - Patrón de Controller si aplica (useRef + useEffect para instanciación)

## Reglas

Antes de escribir código, aplica las comprobaciones del gate en `references/sonarqube-gate.md`, incluidas complejidad máxima 10 por función cuando aplique, imports no usados y todas las reglas de SonarQube citadas allí. No dupliques sus reglas.

- Aplica `.agents/rules/architecture-rules.md` y `.agents/rules/project.md`.
- Prioriza composición sobre herencia.
- **Reutilización por defecto, verificada vía grafo**: la auditoría de componentes reutilizables no es opcional.
- Los contratos de `data-contracts.md` son vinculantes: referéncialos, no los redefinas.
- Si existe `ux-spec.md`, intégrala en la arquitectura técnica.
- No reindexes (`python3 -I -B .agents/scripts/codebase-memory.py --indexar`) desde aquí.

## Comprobación de versiones (antes de proponer código)

Antes de escribir cualquier código propuesto, responde internamente estas cuatro preguntas (comprobación interna; no añade una sección al plan):

1. ¿Qué versiones aplican? El framework y las librerías implicadas, con su origen: `frontend.version` de `.agents/stack.yaml` (la versión de `next`), React y el resto de librerías según `package.json`.
2. ¿Hay en esas versiones alguna función, método, anotación o sintaxis que resuelva esto con menos código o de forma más clara?
3. ¿Todo lo que voy a usar existe en la versión del proyecto, y no solo en una posterior?
4. ¿Hay algo obsoleto (deprecated) en esa versión que deba evitar?

Fuentes de la comprobación, en este orden, sin duplicar lo que ya consultaste: primero tu auditoría de componentes reutilizables y las queries del grafo (condicionadas por `herramientas.codebase_memory` de `.agents/stack.yaml`: qué existe ya en el código y qué patrón usa, para reutilizarlo o respetarlo; el grafo no contiene dependencias ni versiones), después tgrep sobre `knowledge-base/` (decisiones y correcciones previas que limiten la solución), luego las versiones, y por último la documentación, solo si te quedan dudas sobre qué ofrece esa versión.

- **Si el patrón del proyecto choca con lo idiomático de la versión**: el código nuevo es idiomático salvo que `knowledge-base/` registre una decisión de mantener el patrón; el código existente no se reescribe fuera del plan aprobado. Si la incoherencia importa, señálala en una línea del plan para que el usuario decida.
- **Sin inventar**: si no estás seguro de que algo exista en la versión del proyecto, consulta Open Notebook mediante el script de documentación; si faltan fuentes, detén la propuesta y solicita su preparación con aprobación; si sigues sin certeza, dilo en una línea y pregunta al usuario antes de proponerlo. Nunca lo des por hecho.
- **Documentación**: usa `python3 .agents/scripts/documentacion.py preguntar TECNOLOGIA "PREGUNTA_GENERICA" --servicio NOMBRE` con la asociación del servicio (raíz: `.`); la versión sale del registro cotejado con el inventario local. Solo preguntas genéricas: notas verificadas sin modelo → resúmenes → texto completo (mayor coste); con embeddings utilizables, esa alternativa. Usa únicamente citas que el script haya comprobado literalmente en una fuente válida; si no hay evidencia, pregunta antes de proponerla.
- **Tecnologías fuera del catálogo**: si tu tarea usa una tecnología que el preflight señala como no catalogada, añádela al catálogo con la sección "Ampliar el catálogo del proyecto" de preparar-documentacion.md antes de proponer capacidades de su versión. No las supongas.
- **Privacidad de las consultas**: solo preguntas genéricas sobre la librería y su versión; nunca código del proyecto, nombres de tablas, datos, rutas internas ni credenciales.

## Salida

Escribe **un único archivo**: `OUT_DIR/component-architecture.md`, con este formato:

```markdown
---
artefacto: component-architecture.md
skill: frontend-architect
estado: ok | fallo | bloqueado
entradas_leidas: [context.md, data-contracts.md]   # las que leíste completas
fecha: <ISO-8601>
---

## Arquitectura de Componentes

<arquitectura en Markdown estructurado>

### Componentes Base Disponibles / Reutilización
(para cada componente nuevo: qué se reutiliza y cómo con query del grafo, o justificación)

### Borradores de Código
(esqueleto de cada componente nuevo o modificado; debajo de cada bloque de código, la línea **Capacidades de la versión usadas** con lo que aprovecha y desde qué versión existe, según `frontend.version` de `stack.yaml` y `package.json`; si la feature es puramente de capas de servicio sin UI, queda vacía y el resto del Output se limita a lo aplicable)
```


## Dependencias nuevas completas

El plan lista todas las dependencias nuevas que usará el código, incluidas las de validación y pruebas. Si durante el desarrollo se descubre que falta una, no la añadas: devuelve `estado: bloqueado` nombrando la dependencia que falta, para que el plan se enmiende con la aprobación del usuario.


Consulta y actualización condicional del grafo: usa Codebase Memory solo cuando `herramientas.codebase_memory` en `.agents/stack.yaml` sea `true`; con `false`, omite las consultas y actualizaciones al grafo. Resuelve `<proyecto>` con `python3 -I -B .agents/scripts/codebase-memory.py --resolver` (exit 0) antes de consultar. Un resultado vacío no demuestra ausencia: usa `check_index_coverage` y, si hay dudas, busca en la fuente. Para rutas y dependencias existentes usa `codebase-memory-mcp cli get_architecture --project "<proyecto>" --aspects '["routes","dependencies"]'` y `codebase-memory-mcp cli trace_path --project "<proyecto>" --function-name "<símbolo>" --direction inbound`.
