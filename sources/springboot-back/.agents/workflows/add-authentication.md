---
description: Añade autenticación Clerk a un gateway existente mediante un plan aprobado y sin sobrescribir seguridad existente.
---
<!-- si-archivo integraciones.autenticacion=clerk -->

# Añadir autenticación al gateway

### Paso 1: Precondiciones e inventario

Ejecuta `bash .agents/scripts/preflight.sh --workflow add-authentication --fase entrada`. Con bloqueo no avances. Crea RUN_DIR fuera de `.agents/` y manifest.md. Lee `backend.gateway` con `node .agents/scripts/stack.mjs get backend.gateway`; debe identificar un gateway existente. Si es null o no se identifica de forma segura, informa y detente: este workflow no crea servicios. El usuario ya habrá elegido Clerk y regenerado; nunca edites stack.yaml.

Localiza SecurityConfig y cualquier SecurityWebFilterChain equivalente, sin depender solo del nombre del archivo. Si ya hay seguridad, informa del estado y termina sin escribir en el proyecto; su adaptación exige un plan específico. Inventaría build.gradle, paquete, configuración pública y perfiles. Para application*.yaml usa únicamente búsquedas de las claves públicas necesarias (issuer-uri y activación de perfiles), nunca archivos completos ni valores de variables o credenciales. No leas .env, secretos, kubeconfig ni account/.

### Paso 2: Plan y aprobación

Invoca `microservices-architect` con request.md y context.md para producir plan.md. El plan identifica modo autenticacion, gateway, paquete, dependencia `org.springframework.boot:spring-boot-starter-oauth2-resource-server` si falta, clase nueva y configuración global de issuer. Lista cada ruta en `## Archivos a crear o modificar`. Solo se publica lo aprobado: enumera incluso los matchers de Actuator de la plantilla y pide aprobación expresa de cualquier ruta adicional por método y prefijo; nunca publiques CRUD administrativo ni añadas roles.
<!-- si devops.infraestructura=jenkins-kubernetes -->
Enumera sufijos de todos los perfiles locales y documentos activados por k8s solo para entradas con desplegar true. El issuer local sale de integraciones.clerk_issuer_uri y el de cada destino de devops.entornos.<carpeta>.clerk_issuer_uri. Conserva rutas, CORS y recursos existentes. No se modifica Jenkinsfile ni se generan cuentas en esta instalación.
<!-- fin -->
Pide aprobación literal antes de producir cambios aplicables; escribe approved-plan.md con el plan completo y esa aprobación.

### Paso 3: Propuesta y escritura

Invoca `service-creator` en modo autenticacion con approved-plan.md para producir code-changes.auth.md y service-report.md. No crea servicio ni asigna puertos. Si detecta seguridad preexistente, termina informando y no llames a escritura. Si la propuesta está ok, invoca `file-writer` con ella y el plan aprobado; produce write-report.md y aplica únicamente archivos autorizados. No reemplaces application.yaml completo, no siembres rutas/CORS de nuevo, no dupliques dependencia o documento de perfil.

### Paso 4: Comparación, pruebas y revisión

Ejecuta comparar-plan.py con la lista completa aprobada según su CLI; un desajuste vuelve a escritura. Genera diff.patch con `git add -N` para archivos nuevos aprobados y `git diff HEAD` antes de pruebas. Invoca `test-engineer`: pide permiso antes del primer Gradle y usa `./gradlew --offline compileJava test`; JWT y servicios externos simulados, sin Clerk real. Comprueba rechazo sin token, aceptación con JWT simulado, CORS y únicamente los matchers públicos aprobados. Ejecuta el gate local del flujo habitual y `code-reviewer`; el orquestador acepta `APPROVED` o `APPROVED WITH RECOMMENDATIONS` solo tras `node .agents/scripts/sonar-diff-gate.mjs --comprobar-recibo RUN_DIR/gate-recibo.json` y, si falla, repite la revisión sin consumir iteración. Si una comprobación necesita acceso no autorizado, detente y registra el bloqueo. No instales ni descargues dependencias sin permiso.

### Paso 5: Documentación

Invoca `tech-writer` y entrega docs-summary.md, manifest y resultados. Informa del issuer público de cada perfil configurado, sin copiar valores privados. Una segunda instalación debe detectar la seguridad existente y no escribir. No alteres el contrato de errores.

## Transiciones y entrega

Cada fase se ejecuta según `.agents/workflows/references/ejecutar-fase.md`. Valida su artefacto y estado antes de avanzar y registra fase, intento y resultado en manifest.md. `fallo` vuelve a esa misma fase con feedback.md, máximo dos intentos; si se agotan o hay `bloqueado`, detente. Si el fallo de pruebas o revisión exige código, vuelve a propuesta y escritura aprobadas y repite pruebas, gate y revisión. Una ampliación de archivos o dependencias requiere una enmienda aprobada. No hagas commits automáticos.

La entrega enumera archivos realmente modificados, rutas públicas aprobadas, resultados y salidas literales; no da por ejecutadas comprobaciones que no se hayan podido hacer. El usuario configura los valores de las variables fuera de stack.yaml; nunca se solicitan, leen ni publican credenciales.

Antes de aprobar cualquier plan, sigue `.agents/workflows/references/decisiones-stack.md`; consulta clases, remedios y códigos que resuelve este workflow en `.agents/config/codigos.yaml`.
