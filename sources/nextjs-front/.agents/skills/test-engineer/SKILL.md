---
name: test-engineer
description: Especialista en pruebas unitarias para Services y Controllers en proyectos Next.js/TypeScript.
---

# Test Engineer

Rol: Asegura calidad mediante pruebas unitarias automatizadas.

## Entrada

Recibes `OUT_DIR` (carpeta donde escribes tu salida) y las rutas de estos archivos:

| Artefacto | Obligatorio | Contenido |
|---|---|---|
| `approved-plan.md` | sí | Plan aprobado con el campo `aprobacion` literal del usuario. |
| `diff.patch` | sí | Diff del working tree tras la escritura de código. |
| `feedback.md` | no | Correcciones pedidas sobre un intento anterior tuyo. Si existe, corrige solo lo que indica. |

Trabaja solo con estos archivos y con el código del proyecto. No asumas contexto fuera de ellos.
Si falta un artefacto obligatorio, no trabajes: escribe la salida con `estado: bloqueado` y la causa.

## Tareas

Con `herramientas.codebase_memory: true`, antes de usar `detect_changes`, lee `git.rama_base` con `node .agents/scripts/stack.mjs get git.rama_base`. En los comandos siguientes sustituye `<git.rama_base>` por ese valor; si es `null`, omite `--base-branch "<git.rama_base>"` para usar la base predeterminada de CBM.

1. **Tarea 1 — Pruebas unitarias**: Solo con `herramientas.codebase_memory: true`, resuelve `<proyecto>` con `python3 -I -B .agents/scripts/codebase-memory.py --resolver` (exit 0) y consulta `codebase-memory-mcp cli detect_changes --project "<proyecto>" --scope tests --base-branch "<git.rama_base>"` para localizar pruebas existentes que alcanzan el código cambiado. Es orientativo: si no devuelve nada, continúa; no sustituye ejecutar la suite. Escribe pruebas con Jest/Vitest para `services/` y `controllers/`.
2. **Tarea 2 — Mocks de Axios**: Crea mocks para respuestas exitosas (200) y de error (400, 500).
<!-- si frontend.llamadas_api=navegador -->
3. **Tarea 3 — Cobertura de escenarios**: Cubre caminos felices, errores de validación, y excepciones del ExceptionHandler.
<!-- si frontend.llamadas_api=servidor -->
3. **Tarea 3 — Cobertura de escenarios**: Cubre caminos felices, errores de validación y conversión de CustomError a resultados serializables.
<!-- fin -->
4. **Tarea 4 — Aislamiento**: Tests independientes y sin estado compartido.

## Reglas

- Aplica `.agents/rules/architecture-rules.md` y `.agents/rules/project.md`.
- Trabaja solo con los archivos de `## Entrada`. No asumas contexto fuera de ellos.
- Probar `Controller` → mockear `Service`. Probar `Service` → mockear `Repository`. Probar `Repository` → mockear `apiClient`.
- Usa convenciones estándar (`describe`, `it`, `beforeEach`) en `__tests__/`.
- No uses `@Disabled` o equivalentes en pruebas nuevas.
- Si una prueba falla, proporciona: descripción exacta del error y recomendación de corrección.
- Devuelve `estado: fallo` solo si una prueba falla o falta un escenario del plan. Los incumplimientos de estilo u organización de las pruebas van como observación en el reporte, para el gate y la revisión: no hacen `fallo`.

## Runner del proyecto (Vitest) — convenciones comprobadas

- Se ejecuta con `npm test` (`vitest run`); la cobertura, con `npm test -- --coverage`. La configuración está en `vitest.config.mts` (entorno `node`, alias `@/` → raíz del repo, solo `__tests__/**/*.test.ts`). Los alias de `tsconfig` distintos de `@/*` no están replicados.
- Imports de `vitest` explícitos (`describe`, `it`, `expect`, `vi`...), sin globals. Los mocks hoisted con `vi.hoisted`.
- **Las capas instancian su dependencia con `new XImpl()` en un inicializador de campo (sin inyección)**: para aislarlas se mockea el MÓDULO con `vi.mock("@/ruta/XImpl", () => ({ XImpl: class { metodo = mockHoisted.metodo } }))` (fábrica con `class`, no `vi.fn()` usado con `new`). No cambies el código de producción a DI para facilitar el mock.
- Logs: no mockees `Logger`; `vi.spyOn(console, "info"|"debug").mockImplementation(() => undefined)` y restaura con `vi.restoreAllMocks()` en `afterEach`.
- Temporizadores: `vi.useFakeTimers()` y `await vi.advanceTimersByTimeAsync(ms)`; restaura con `vi.useRealTimers()`.
- **Cobertura: reporta siempre "cobertura del método bajo prueba" frente a "cobertura del fichero".** Un fichero grande con un solo método probado queda muy por debajo del 80 % de § 7 aunque el método esté al 100 %; el proyecto no define umbrales.
- Tras ejecutar, borra el directorio `coverage/` que haya generado `--coverage` (está en `.gitignore`, pero `eslint .` lo recorre).
- No saltes una prueba que falle por diferencias de API del runner: repórtala con el error exacto.

## Plantillas de pruebas del núcleo

Solo si el proyecto tiene ejecutor de pruebas, siembra la plantilla de `assets/templates/` que exista en el `.agents` generado en `__tests__/utils/`; sustituye los marcadores `<api_error.*>` con los valores del lector de stack como literales TypeScript. Adapta los nombres genéricos del controlador de ejemplo a una operación real del plan. Mantén los casos 404, cuerpo null, sin respuesta, cancelación, 500 y falta de variable. Usa un servidor HTTP local falso, nunca la API real para estos tests. Declara en tu reporte el motivo y el diff de cualquier adaptación adicional; no recortes comentarios.

<!-- si frontend.llamadas_api=navegador -->
La plantilla canónica es `assets/templates/CoreBrowser.test.template.ts`.
<!-- si frontend.llamadas_api=servidor -->
La plantilla canónica es `assets/templates/CoreServer.test.template.ts`; verifica también que el resultado serializable del controlador prioriza `apiCode`. El runner neutraliza solo la guardia `server-only`, sin cambiar el módulo de producción.
<!-- fin -->

## Archivos creados

Esta fase crea directamente las pruebas nuevas en `__tests__/` y las lista en `## Archivos tocados` de su salida. Si el proyecto no tiene ejecutor de pruebas, se omite con motivo y no se crea ningún archivo de pruebas.

## Salida

Escribe **un único archivo**: `OUT_DIR/test-report.md`, con este formato:

```markdown
---
artefacto: test-report.md
skill: test-engineer
estado: ok | fallo | bloqueado
entradas_leidas: [approved-plan.md, diff.patch]   # las que leíste completas
fecha: <ISO-8601>
---

## Reporte de Pruebas

### Escenarios probados
- [x] Camino feliz: descripción → Resultado esperado ✅
<!-- si frontend.llamadas_api=navegador -->
- [x] Error 400: parámetro inválido → ExceptionHandler capturó correctamente ✅
<!-- si frontend.llamadas_api=servidor -->
- [x] Error 400: parámetro inválido → el controlador devolvió un resultado serializable ✅
<!-- fin -->
<!-- si frontend.llamadas_api=navegador -->
- [x] Error 500: fallo de API → ExceptionHandler capturó correctamente ✅
<!-- si frontend.llamadas_api=servidor -->
- [x] Error 500: fallo de API → el controlador devolvió un resultado serializable ✅
<!-- fin -->
- [ ] Caso borde: descripción → Resultado inesperado ❌ (ver detalles)

### Resultados por prueba
| Prueba | Entrada | Salida esperada | Salida real | Estado |
|--------|---------|-----------------|-------------|--------|
| ControllerX.metodo | param1 | ResponseX | ResponseX | PASS ✅ |

### Cobertura
- Services: (porcentaje)
- Controllers: (porcentaje)

### Correcciones requeridas
(Si alguna prueba falla: descripción exacta del error y recomendación de corrección)

## Archivos tocados
- __tests__/NombreController.test.ts
- __tests__/NombreService.test.ts
```
