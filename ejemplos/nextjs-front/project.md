---
trigger: always_on
---

# Datos del proyecto

## Stack y estructura
- Next.js (App Router) con TypeScript y Tailwind CSS. La versión del framework está en `frontend.version` de `.agents/stack.yaml`.
- Código visual en `app/` y `app/ui/`.
- Capas: `controllers/`, `services/`, `repository/`, `domains/`, `utils/`, `lib/`, `hooks/` y `__tests__/`.

## Integraciones y seguridad
- **API de pedidos**: el front llama al gateway del back; su URL base se lee de una variable de entorno pública, nunca escrita en el código.
- **SonarQube**: el `projectKey` está en `sonarqube.project_key` de `.agents/stack.yaml` y en `sonar-project.properties`.
- **Codebase Memory y tgrep**: `knowledge-base/` y `.agents/` están excluidos de Codebase Memory vía `.cbmignore`; `knowledge-base/` está indexada por `tgrep`.

<!-- si integraciones.autenticacion=clerk -->
### Clerk
- Gestiona el inicio de sesión. Ante cambios de autenticación usa la skill externa `clerk` y actualiza el grafo.
<!-- fin -->

## Grafo de conocimiento: estado actual
- `knowledge-base/` está excluida vía `.cbmignore`. Con `python3 -I -B .agents/scripts/codebase-memory.py --indexar`, la reindexación aplica `.cbmignore` al índice local.

## Archivos sensibles y protegidos
- **Secretos**: cualquier `.env*`. No se leen ni se citan en informes o notas; el token de SonarQube se usa como `$SONARQUBE_TOKEN`.
- **Persistencia protegida**: no sobrescribir `next.config.ts`, `package.json`, `tsconfig.json` ni `.env*` sin confirmación explícita.
