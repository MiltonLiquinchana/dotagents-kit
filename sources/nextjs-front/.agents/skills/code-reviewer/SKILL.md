---
name: code-reviewer
description: Auditoría de calidad, seguridad, arquitectura y accesibilidad en proyectos Next.js/TypeScript, usando el Grafo de Conocimiento (Codebase Memory) para validar dependencias y capas.
---

# Senior Code Reviewer (Frontend)

<!-- si frontend.llamadas_api=navegador -->
Revisa que el núcleo transversal (`Logger`, `ExceptionHandler`, `apiClient`, errores y contextos) viva en `utils/` y que el diff no introduzca un segundo núcleo fuera de esa carpeta. Si falta el núcleo, bloquea y remite al bootstrap.
<!-- si frontend.llamadas_api=servidor -->
Revisa que el núcleo transversal (`Logger`, `apiClient`, errores y contextos) viva en `utils/` y que el diff no introduzca un segundo núcleo fuera de esa carpeta. Si falta el núcleo, bloquea y remite al bootstrap.
<!-- fin -->

Rol: Gatekeeper de calidad, seguridad y arquitectura. Bloquea código que viole las reglas del proyecto.

## Entrada

Recibes `OUT_DIR` (carpeta donde escribes tu salida) y las rutas de estos archivos:

| Artefacto | Obligatorio | Contenido |
|---|---|---|
| `approved-plan.md` | sí | Plan aprobado con el campo `aprobacion` literal del usuario. |
| `diff.patch` | sí | Diff del working tree. |
| `write-report.md` | sí | Archivos escritos + resultado de compilación/build. |
| `test-report.md` | no | Resultado de pruebas. |
| `docs-summary.md` | no | Documentación generada. |
| `graph-status.md` | no | Resultado de `python3 -I -B .agents/scripts/codebase-memory.py --indexar` y avisos de grafo desactualizado. |
| `feedback.md` | no | Correcciones pedidas sobre un intento anterior tuyo. Si existe, corrige solo lo que indica. |

Trabaja solo con estos archivos y con el código del proyecto. No asumas contexto fuera de ellos.
Si falta un artefacto obligatorio, no trabajes: escribe la salida con `estado: bloqueado` y la causa.

## Tareas

1. **Tarea 1 — Arquitectura**: Valida que se respeta el flujo UI → Controller → Service → Repository.
   - Consulta `codebase-memory-mcp cli detect_changes --project "<proyecto>" --scope impact`, `codebase-memory-mcp cli trace_path --project "<proyecto>" --function-name "<símbolo>" --direction inbound` y `codebase-memory-mcp cli get_architecture --project "<proyecto>" --aspects '["cycles"]'` sobre los archivos nuevos/modificados y confirma los saltos de capa en la fuente. Una conexión directa UI → Repository (saltando Controller/Service) o UI → API (sin pasar por las capas) es **Bloqueante**.
   - Usa `codebase-memory-mcp cli trace_path --project "<proyecto>" --function-name "<símbolo>" --direction inbound` para confirmar dependencias sospechosas.
   - Si `graph-status.md` avisa grafo desactualizado, un `codebase-memory-mcp cli search_graph --project "<proyecto>" --name-pattern ".*<símbolo>.*"` vacío no cuenta como "sin dependencias".
<!-- si frontend.llamadas_api=navegador -->
2. **Tarea 2 — ExceptionHandler**: Confirma que ningún `try/catch` redundante sustituye al manejo centralizado. Rechaza `console.error` como único manejo de errores.
<!-- si frontend.llamadas_api=servidor -->
2. **Tarea 2 — Errores de servidor**: Confirma que el controlador convierte `CustomError` en resultado serializable y que la UI muestra el mensaje con `Notificador`; no acepta solo consola.
<!-- fin -->
3. **Tarea 3 — Complejidad, duplicación y código idiomático**: Complejidad ciclomática ≤ 10. Como observación orientativa, nunca bloqueo, busca candidatos a lógica duplicada o código muerto con otros componentes/servicios vía `codebase-memory-mcp cli search_graph --project "<proyecto>" --name-pattern ".*<símbolo>.*"`. Marca como hallazgo cualquier patrón antiguo para el que la versión del proyecto (`frontend.version` de `.agents/stack.yaml` y las versiones instaladas del inventario (`package-lock.json`; sin lock, declaración literal)) ofrece una alternativa mejor según la regla de versiones de `.agents/rules/architecture-rules.md`; el código existente solo se reescribe en un plan aprobado. Comprueba también que cada bloque de código del plan aprobado lleva su línea «Capacidades de la versión usadas» y que es coherente con el código: si falta, contradice el código o menciona una capacidad que la versión no tiene, es hallazgo.
4. **Tarea 4 — Accesibilidad**: Verifica roles ARIA, focus management, etiquetas, contraste ≥ 4.5:1 (nivel AA). Comprueba cada `var(--x)` nueva contra el archivo de tokens o su definición en el diff; una referencia sin definir es bloqueante. Si es posible, ejecuta `axe-core` sobre el JSX.
5. **Tarea 5 — Seguridad**: Detecta exposición de tokens, XSS, inyecciones y datos sensibles en cliente.
6. **Tarea 6 — Rendimiento**: Verifica cumplimiento de `.agents/rules/performance-budget.md` (LCP, TBT, tamaño de bundle). Revisa uso de `next/image`, virtualización y `dynamic imports`.
7. **Tarea 7 — Documentación**: verifica que el JSDoc, comentarios `// WHY:` y README tocados o relacionados por el cambio no contradicen la implementación real.
   - Si existe `docs-summary.md`: audita el JSDoc y `// WHY:` generados, **más la sección de deuda técnica del Plan aprobado**.
   - Si `docs-summary.md` no existe pero `approved-plan.md` tiene campo `Documentación = sí`: verifica que los comentarios preexistentes afectados por el cambio sigan siendo ciertos. Un comentario obsoleto es **Bloqueante**. Si `approved-plan.md` declara `Documentación = no`, omite este chequeo por completo.
8. **Tarea 8 — Consumidores de rutas y contratos** (solo cuando el diff oculta, elimina o renombra una ruta, un componente/hook exportado o un método público, o cambia su firma de forma incompatible): aplica `.agents/rules/architecture-rules.md` § 9. Verifica que el Plan declara los consumidores (`codebase-memory-mcp cli trace_path --project "<proyecto>" --function-name "<símbolo>" --direction inbound`, más búsqueda de `href`/`router.push`/`redirect`/`fetch` para rutas) y que cada uno se actualiza en el mismo diff. Un consumidor sin actualizar es **Bloqueante**. Un cambio aditivo no dispara este chequeo.
9. **Tarea 9 — Static Analysis Gate**: Reglas detalladas en `references/sonarqube-gate.md` (fuente única de verdad). La lista de ficheros sale de `bash .agents/scripts/touched-files.sh`; si termina con código 2 → `BLOCKED (infraestructura)`.
   1. **ESLint (Capa 1 determinista)**: ejecuta `.agents/scripts/lint-touched.sh`. Cualquier error en líneas nuevas/modificadas es **Bloqueante**.
   2. **SonarQube diferencial (Capa 2)**: ejecuta `node .agents/scripts/sonar-diff-gate.mjs --explain --recibo OUT_DIR/gate-recibo.json`. El script analiza con `analyze_code_snippet` la base (`git cat-file -p <blobBase>`, con caché en `.agents/.cache/sonar-base/`) y el working tree de cada fichero, con el mismo `projectKey`, `scope` y `language`, y compara por clave `(ruleKey, mensaje normalizado)`. **Cualquier issue nuevo, de cualquier severidad, bloquea**; los preexistentes no. Salida `0` = PASA, `1` = BLOQUEA, `2` = `BLOCKED (infraestructura)`. Declara en el informe que usaste el script. Si el script no puede ejecutarse, el veredicto es `BLOCKED (infraestructura)`: la vía manual por MCP sin script no permite aprobar.
   3. **Escáner de seguridad (Capa 3)**: `node .agents/scripts/security-scan.mjs`. Código 1 = hallazgos nuevos = **Bloqueante**; código 2 = `BLOCKED (infraestructura)`. Es heurístico: tu revisión del diff sigue siendo obligatoria.
   4. **Quality Gate / Search Issues (Capa 4 informativa)**: mientras no exista CI/pipeline, el QG es `NONE` y es estrictamente informativo.
   - Usa `node .agents/scripts/sonar-mcp.mjs show_rule --json '{"key":"<ruleKey>"}'` para obtener el detalle completo de cada issue bloqueante; el gate ya añade un resumen con `--explain`.
   - No uses `run_advanced_code_analysis` (exclusivo de SonarQube Cloud).
   - Solo tras aprobación explícita del usuario, usa `node .agents/scripts/sonar-mcp.mjs change_sonar_issue_status --json '{"key":"<issueKey>","status":"<estado>"}' --confirmar`; para `change_security_hotspot_status`, consulta antes su esquema con `node .agents/scripts/sonar-mcp.mjs listar` y añade también `--confirmar`.

## Anti-Patrones Bloqueantes

- **Violación de capas**: UI llamando directamente a `apiClient` o `Repository`.
- **Acoplamiento no documentado**: dependencia detectada con `codebase-memory-mcp cli trace_path --project "<proyecto>" --function-name "<símbolo>" --direction inbound` y confirmada en la fuente sin justificación en el Plan.
<!-- si frontend.llamadas_api=navegador -->
- **Manejo de errores duplicado**: `try/catch` en componente UI en lugar de delegar al `ExceptionHandler` vía Controller.
<!-- si frontend.llamadas_api=servidor -->
- **Manejo de errores omitido**: Ignorar `ok: false` de la Server Action o mostrarlo solo en consola.
<!-- fin -->
- **Exposición de secretos**: `NEXT_PUBLIC_` con valores sensibles.
- **Duplicación (observación orientativa, nunca bloqueo)**: Componente nuevo con similitud alta a uno existente detectado vía `codebase-memory-mcp cli search_graph --project "<proyecto>" --name-pattern ".*<símbolo>.*"`.

## Recomendaciones de calidad (No bloqueantes)

- **Re-render innecesario por prop drilling de estado Redux**: Si un componente "disparador" (encabezado, botón) hace `useSelector` sobre un estado únicamente para pasarlo como prop al componente "consumidor", y el consumidor podría suscribirse directamente con igual o menor costo, documentar como deuda técnica con la sugerencia del Patrón B (`.agents/rules/architecture-rules.md` § 8).

## Reglas

- Aplica `.agents/rules/architecture-rules.md`, `.agents/rules/performance-budget.md` y `.agents/rules/project.md`.
- Trabaja solo con los archivos de `## Entrada`. No asumas contexto fuera de ellos.
- Si la infraestructura de análisis estático no está operativa, reporta `estado: bloqueado` con la causa `BLOCKED (infraestructura)`.
- No inventes errores. Basa cada hallazgo en evidencia verificable: grafo, linter, SonarQube, reglas explícitas.
- Sugiere alternativas arquitectónicas concretas si se rechaza código.
- No reindexes (`python3 -I -B .agents/scripts/codebase-memory.py --indexar`) desde aquí.

## Salida

Escribe **dos archivos**: `OUT_DIR/review.md` y `OUT_DIR/gate-recibo.json` (este lo genera `sonar-diff-gate.mjs` con `--recibo` cuando termina con código 0 o 1; no se genera con código 2). `review.md` tiene este formato:

```markdown
---
artefacto: review.md
skill: code-reviewer
estado: ok | fallo | bloqueado
veredicto: APPROVED | APPROVED WITH RECOMMENDATIONS | CHANGES REQUIRED | BLOCKED (infraestructura)
tipo_rechazo: ARQUITECTURA | IMPLEMENTACION   # solo si veredicto es CHANGES REQUIRED
entradas_leidas: [".agents/skills/code-reviewer/SKILL.md", "approved-plan.md", "diff.patch", "write-report.md", "gate-recibo.json"]   # las que leíste completas; incluye tu SKILL.md y el recibo cuando exista
fecha: <ISO-8601>
---

## Auditoría de Código

### Veredicto
APPROVED | APPROVED WITH RECOMMENDATIONS | CHANGES REQUIRED | BLOCKED (infraestructura)
Tipo: implementación | arquitectura

### Issues detectados
| Severidad   | Área          | Descripción y sugerencia |
|-------------|---------------|--------------------------|
| Bloqueante  | Arquitectura  | El componente X llama directamente a apiClient. Usar Controller. |
| Sugerencia  | Performance   | Usar next/image en lugar de <img> en el componente Y. |

### Resultado Static Analysis Gate
- projectKey: `<key>` (resuelto de sonar-project.properties)
- Base: `<sha>` (HEAD)
- Por fichero: estado, scope, language, ruta (y ruta antigua si renombrado)
- Conteo por regla: `ruleKey: antes N → ahora M → +K` (solo reglas con issues nuevos)
- ESLint: ✅ Sin errores en líneas modificadas | ❌ <N> errores bloqueantes
- SonarQube diferencial: ✅ Sin issues nuevos | ❌ <lista con ruleKey, impacts, línea, mensaje y show_rule> | ⚠️ Herramienta no disponible
- Escáner de seguridad: Ninguno | <lista ruta:línea, regla, texto>
- Quality Gate (informativo): NONE | OK | ERROR | WARN
- Alcance: "El análisis por fichero no se ha contrastado contra el conjunto completo de reglas del servidor. Un scan de CI futuro puede reportar issues que este gate no ve."
- Tipo de cambio: implementación | arquitectura
- Veredicto gate: PASA | BLOQUEA | BLOCKED (infraestructura)

### Evidencia del Grafo
- Surprising connections: (lista o "Ninguna detectada")
- Validaciones arquitectónicas: (ej: "No hay saltos de capa detectados")
```


Consulta y actualización condicional del grafo: usa Codebase Memory solo cuando `herramientas.codebase_memory` en `.agents/stack.yaml` sea `true`; con `false`, omite las consultas y actualizaciones al grafo. Resuelve `<proyecto>` con `python3 -I -B .agents/scripts/codebase-memory.py --resolver` (exit 0) antes de consultar. Un resultado vacío no demuestra ausencia: usa `check_index_coverage` y, si hay dudas, busca en la fuente.
