---
trigger: always_on
---

# Datos del proyecto

## Stack y estructura
- Las versiones de Java y Spring Boot se leen de `.agents/stack.yaml` (`backend.java`, `backend.spring_boot`). Cada microservicio es un build Gradle independiente (sin `build.gradle` en la raíz).
- Los servicios se descubren por carpeta (una por `build.gradle` + `settings.gradle` en el primer nivel); `servicios.py listar` los enumera con sus puertos. En este proyecto: `gateway-service` (valida la autenticación), `pedidos-service`, `catalogo-service` y `clientes-service`.
- Cada servicio gestiona su configuración en `src/main/resources/application*.yaml`.

## Integraciones y seguridad
- **SonarQube**: un proyecto por servicio; el `projectKey` sale de `.agents/stack.yaml`.
- **Codebase Memory y tgrep**: `knowledge-base/` está excluida de Codebase Memory vía `.cbmignore` e indexada por `tgrep`.

<!-- si integraciones.autenticacion=clerk -->
### Clerk
- La autenticación se valida solo en `gateway-service` (Spring Security OAuth2 Resource Server contra el `issuer-uri` de Clerk, que se lee de `application.yaml`). Los servicios internos no validan JWT y no se exponen fuera del gateway.
- El `issuer-uri` concreto no se copia en documentación ni en tests.
<!-- fin -->

## Grafo de conocimiento: estado actual
- `knowledge-base/` y `.agents/` están excluidos vía `.cbmignore`. Con `python3 -I -B .agents/scripts/codebase-memory.py --indexar`, la reindexación aplica `.cbmignore` al índice local.

## Archivos sensibles y protegidos
- **Secretos**: `devops/*/secrets-*.yaml`, cualquier kubeconfig y cualquier `.env*`. No se leen ni se citan en notas o informes; el token de SonarQube se usa siempre como `$SONARQUBE_TOKEN`.
- **Persistencia protegida**: no sobrescribir `application.yaml` ni `build.gradle` sin confirmación explícita.
- **Migraciones**: las destructivas (DROP, ALTER que trunque datos, renombrados sin migración) requieren confirmación explícita.
