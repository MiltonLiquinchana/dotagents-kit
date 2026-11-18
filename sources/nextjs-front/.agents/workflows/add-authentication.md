---
description: Integra Clerk en un front ya inicializado mediante cambios mínimos y un plan aprobado.
---
<!-- si-archivo integraciones.autenticacion=clerk -->

# Añadir autenticación al front

### Paso 1: Precondiciones e inventario

Ejecuta `bash .agents/scripts/preflight.sh --workflow add-authentication --fase entrada`; con bloqueo detente. Crea RUN_DIR fuera de `.agents/` y manifest.md. El usuario debe haber elegido Clerk y regenerado; ningún agente edita stack.yaml. Revisa package.json, proxy, layout, páginas de acceso y cliente API. No leas ni edites .env*, secretos o configuraciones de herramientas. Si ya hay autenticación incompatible, informa y detente; no la sustituyas por la plantilla ni vuelvas a ejecutar todo el bootstrap.

### Paso 2: Plan y aprobación

Invoca `api-integration-architect` en modo contratos y `frontend-developer` para el diseño de integración. Produce un plan con cada archivo permitido, dependencia @clerk/nextjs compatible con las versiones del proyecto, proxy, matchers públicos, páginas de acceso/registro ausentes y diff de inserción de ClerkProvider conservando metadata, estilos y providers. Incluye ClerkToken y el cambio mínimo del interceptor. La instalación de paquetes requiere permiso específico, no se deduce del plan. Pide aprobación literal y prepara approved-plan.md.
<!-- si frontend.llamadas_api=navegador -->
Incluye app/ui/auth/ClerkTokenSetup.tsx y su montaje dentro de ClerkProvider; el getter se registra y retira mediante el efecto de React, sin guardar tokens.
<!-- si frontend.llamadas_api=servidor -->
Usa ClerkToken con server-only y auth() por petición; no montes un getter global del servidor ni un componente de inyección del navegador.
<!-- fin -->
<!-- si integraciones.gestion_usuarios=organizaciones|aplicacion -->
Respeta las rutas de pre-registro del contrato aprobado. Advierte en plan y salida: Clerk en registro restringido, solo invitados; sin roles cualquier sesión administra. Sign-up acepta invitaciones y pre-registro no pasa por Clerk. No instales gestión por el mero hecho de activar autenticación.
<!-- fin -->

### Paso 3: Propuestas y escritura

Invoca `api-integration-architect` en modo implementacion para code-changes.auth-api.md y `frontend-developer` para code-changes.auth-ui.md. Usan los assets existentes y devuelven propuestas, sin escribir producción. Valida ambos artefactos y luego invoca `file-writer`; aplica únicamente el diff aprobado y produce write-report.md. No reemplaces proxy ni layout completos a ciegas ni elimines providers. Si la instalación es compatible y ya está completa, informa sin duplicar middleware/interceptores/providers.

### Paso 4: Comparación, pruebas y revisión

Ejecuta comparar-plan.py con la lista completa según su CLI y genera diff.patch incluyendo archivos nuevos mediante `git add -N` y `git diff HEAD`. Invoca `test-engineer` para `npx --no-install tsc --noEmit` y las pruebas locales del proyecto sin Clerk real: rutas públicas/privadas y envío Bearer, preservación del layout y la variante de transporte activa. Nunca descargues dependencias implícitamente. Gate habitual y `code-reviewer` antes de entrega; el orquestador acepta `APPROVED` o `APPROVED WITH RECOMMENDATIONS` solo tras `node .agents/scripts/sonar-diff-gate.mjs --comprobar-recibo RUN_DIR/gate-recibo.json` y, si falla, repite la revisión sin consumir iteración. Si una comprobación no está disponible, registra el bloqueo y detente.

### Paso 5: Documentación

Invoca `tech-writer`; entrega docs-summary.md, resultados y manifest. Enumera solo los nombres de integraciones.variables_autenticacion para que el usuario configure su entorno, sin leer ni escribir .env*. No cambies el contrato de error de la API.

## Transiciones y entrega

Cada fase se ejecuta según `.agents/workflows/references/ejecutar-fase.md`. Valida su artefacto y estado antes de avanzar y registra fase, intento y resultado en manifest.md. `fallo` vuelve a esa misma fase con feedback.md, máximo dos intentos; si se agotan o hay `bloqueado`, detente. Si el fallo de pruebas o revisión exige código, vuelve a propuesta y escritura aprobadas y repite pruebas, gate y revisión. Una ampliación de archivos o dependencias requiere una enmienda aprobada. No hagas commits automáticos.

La entrega enumera archivos realmente modificados, rutas públicas aprobadas, resultados y salidas literales; no da por ejecutadas comprobaciones que no se hayan podido hacer. El usuario configura los valores de las variables fuera de stack.yaml; nunca se solicitan, leen ni publican credenciales.

Antes de aprobar cualquier plan, sigue `.agents/workflows/references/decisiones-stack.md`; consulta clases, remedios y códigos que resuelve este workflow en `.agents/config/codigos.yaml`.
