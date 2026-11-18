---
name: context-analyzer
description: Analiza el contexto técnico usando el grafo de código (Graphify) y el historial de conocimiento (tgrep sobre knowledge-base/).
---

# Analizador de Contexto

Rol: Mapea el contexto técnico del proyecto antes de construir o modificar funcionalidad. Usa `graphify-out/graph.json` (solo código) como fuente primaria de arquitectura, y `knowledge-base/` vía `tgrep` como fuente primaria de historial y decisiones previas. Son fuentes separadas — ver `.agents/rules/graphify.md` y `.agents/rules/tgrep.md`.

## Entrada

Recibes `OUT_DIR` (carpeta donde escribes tu salida) y las rutas de estos archivos:

| Artefacto | Obligatorio | Contenido |
|---|---|---|
| `request.md` | sí | Solicitud del usuario, literal. |
| `feedback.md` | no | Correcciones pedidas sobre un intento anterior tuyo. Si existe, corrige solo lo que indica. |

Trabaja solo con estos archivos y con el código del proyecto. No asumas contexto fuera de ellos.
Si falta un artefacto obligatorio, no trabajes: escribe la salida con `estado: bloqueado` y la causa.

## Tareas

1. **Tarea 1 — Búsqueda literal previa (tgrep, primer paso, sin costo)**: extrae 2-4 términos clave de la feature/bug actual y búscalos en `knowledge-base/` antes de consultar el grafo (ver `.agents/rules/tgrep.md`).
2. **Tarea 2 — Consulta al Grafo de código (fuente primaria de arquitectura)**:
   - Usa `graphify query "..."` y `graphify path "A" "B"` para resolver relaciones entre capas existentes, flujo de datos y dependencias de código. No leas archivos completos ni listes directorios si el grafo puede responder.
   - Consulta `graphify-out/GRAPH_REPORT.md`, si existe, para god nodes y surprising connections relevantes.
3. **Tarea 3 — Verificación de stack, dependencias y configuración**: el stack, versiones de librerías y scripts se leen directamente de `package.json`, `tsconfig.json` y `tailwind.config.ts` (el grafo indexa AST de código, no resuelve dependencias de paquetes; ver `.agents/rules/project.md`). Confirmar capas base (`app/`, `controllers/`, `services/`, `repository/`, `domains/`).
4. **Tarea 4 — Preparación para la feature**: confirma vía `graphify query` si ya existen controllers, services, repositories o componentes UI relacionados.
5. **Tarea 5 — Evaluación de riesgo de re-renders (si la feature involucra UI con estado)**:
   1. Identifica qué componentes comparten el mismo padre/página.
   2. ¿El estado propuesto viviría en el padre y provocaría re-renders de hermanos que no lo necesitan?
   3. ¿Existe un componente "disparador" (encabezado, botón de filtro) que podría terminar suscrito a Redux solo para pasar el estado al consumidor?
   Si se detecta riesgo, indicarlo en la `Conclusión` con: `⚠️ Riesgo de re-renders: evaluar Patrones A/B (.agents/rules/architecture-rules.md § 8)`.
6. **Tarea 6 — Historial de correcciones (vinculante)**:
   Si `knowledge-base/` solo contiene `.gitkeep` o no tiene ninguna nota `.md`, registra en la salida "sin historial (`knowledge-base` vacío)" en lugar de `enfoques_descartados` y continúa sin usar tgrep (no hay nada que buscar).
   **Vía principal**: comprueba directamente si existe el archivo por ruta completa sin extensión
   (`test -f "knowledge-base/<ruta-relativa-sin-extension>-fixes.md"`). No depende del contenido de la nota.
   **Complemento**, solo si necesitas listar todas las notas de correcciones que mencionan un fichero:
   ```bash
   tgrep -F "fichero: <ruta-relativa-del-codigo>" knowledge-base/ -g "*-fixes.md"
   ```
   Esta búsqueda solo encuentra notas cuyo frontmatter declare `fichero:` (la plantilla de `-fixes.md` lo exige desde ahora; una nota anterior que no lo tenga no aparecerá). Un resultado vacío aquí **no** prueba que no haya historial: verifica siempre con la ruta completa.
   (No buscar solo por nombre base para evitar colisiones con `page.tsx` o `layout.tsx`).
   Si el historial reporta enfoques fallidos, inclúyelos en `enfoques_descartados` de la salida.
7. **Tarea 7 — Notas de conocimiento (vía tgrep)**:
   ```bash
   tgrep -F "fichero: {ruta}" knowledge-base/ -l
   ```
   Si existe, léela e incorpórala como contexto de decisiones previas.

## Reglas

- Aplica `.agents/rules/architecture-rules.md`, `.agents/rules/project.md`, `.agents/rules/graphify.md`, `.agents/rules/tgrep.md` y `.agents/rules/knowledge-base.md`.
- **El grafo de código es la fuente primaria de arquitectura. Prohibido leer archivos individuales si el grafo puede responder.**
- **`knowledge-base/` nunca se consulta vía graphify** — siempre vía `tgrep` (precondición bloqueante).
- No asumas librerías, versiones ni patrones.
- No generes ni actualices `graphify-out/graph.json`.
- Si `tgrep` no está disponible, termina con `estado: bloqueado` y la causa. Salvo en los estados que `.agents/rules/tgrep.md` define como válidos y que no son fallo: exit 1 sin coincidencias, el aviso `falling back to local index` con `Indexing: complete`, `Server: not running` con `knowledge-base/.tgrep/serve.json` existente y `knowledge-base` vacía (entonces registra "sin historial (`knowledge-base` vacío)").

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

## Contexto del Proyecto

### Stack detectado
- Framework: (nombre y versión según `package.json` / `.agents/stack.yaml`)
- Router: (según la estructura de `app/`)
- Estilos: (según las dependencias de `package.json`)
- Estado: (ej. Zustand, Redux, Context)
- Design Tokens activos: (ej. colores HSL en tailwind.config.ts)

### Capas existentes para la feature solicitada
- Controllers: (rutas o "Ninguno")
- Services: (rutas o "Ninguno")
- Repository: (rutas o "Ninguno")
- Domains: (modelos/requests/responses relevantes o "Ninguno")
- UI: (componentes en app/ui/ relevantes o "Ninguno")

### Hallazgos del Grafo (código)
- God nodes relevantes: (o "N/A")
- Surprising connections relevantes: (o "N/A")

### Hallazgos de knowledge-base (tgrep)
- Correcciones previas relevantes: (fichero, resumen del enfoque que falló, o "N/A")
- Notas de decisión relevantes: (fichero, resumen, o "N/A")

### Conclusión
- (Extender código existente o crear estructura nueva)
```


Consulta y actualización condicional del grafo: usa graphify solo cuando `herramientas.graphify` en `.agents/stack.yaml` sea `true`; con `false`, omite las consultas y actualizaciones al grafo.
