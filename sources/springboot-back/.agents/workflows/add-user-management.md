---
description: Instala gestión de perfiles desde el contrato SQL y entrega el contrato de API al front.
---
<!-- si-archivo integraciones.gestion_usuarios=organizaciones|aplicacion -->

# Añadir gestión de usuarios al back

1. Ejecuta `bash .agents/scripts/preflight.sh --workflow add-user-management --fase entrada`, crea RUN_DIR fuera de `.agents/` y manifest con fases, intentos y resultados. Con bloqueo no avances. Recibe del usuario la ruta de contrato SQL; no busques en otro proyecto. Si no hay contrato, el diseño propone nombres recomendados y registra ese supuesto.
2. Diseño con `microservices-architect`: el plan enumera servicio nuevo, `rootProject.name: <base>-service`, base `user-management` y context-path propuesto `/<base>`, puerto de servicios.py, archivos, procedimientos/DTO, rutas y publicación mínima del gateway. **Advierte en el plan: Clerk debe estar en registro restringido, solo personas invitadas; sin roles cualquier usuario con sesión puede administrar. Sign-up solo acepta invitaciones; el pre-registro no pasa por Clerk.** No implementes roles. Pide aprobación del plan completo y de cada matcher público antes de escribir. Crear, editar, listar y reconciliar exigen JWT.
<!-- si integraciones.gestion_usuarios=organizaciones -->
Solo solicitar-acceso, webhook y catálogo mínimo de organizaciones son públicos.
<!-- si integraciones.gestion_usuarios=aplicacion -->
Solo solicitar-acceso y webhook son públicos.
<!-- fin -->
<!-- si devops.infraestructura=jenkins-kubernetes -->
Antes de pedir aprobación del plan, registra para los destinos con `desplegar: true` `modo: generar`, la sección `## Archivos a crear o modificar` con cada destino DevOps y estos campos por cada carpeta y sufijo:

```yaml
tipo_servicio: gestion_usuarios
servicio: <nombre exacto del servicio que se crea>
plantilla_secret: RUN_DIR/propuesta/<carpeta>/secret-clerk.yaml
fragmento_env: RUN_DIR/propuesta/<carpeta>/env-clerk.yaml
```

La fase de instalación materializa los dos archivos de propuesta en esas rutas desde sus assets, con las claves vacías y los marcadores resueltos. El nombre del servicio debe coincidir con el de la invocación DevOps; los demás servicios no usan esta excepción. La aprobación incluye esos campos y los destinos, nunca valores de credenciales.
<!-- fin -->
3. Ejecuta `service-creator` para el esqueleto, después `profile-installer` para materializar los assets en RUN_DIR/propuesta y producir code-changes.md; la fase `file-writer` aplica esos cambios al servicio según el contrato de escritura. La fase de pruebas escribe las pruebas propuestas en src/test/**. Sin Data REST en este servicio. Propaga api_error a ExceptionResponse mediante el mecanismo existente. Cada fase ok avanza; fallo vuelve a esa fase con feedback, máximo dos intentos; si agotados o falta dato, bloqueado y detente. Una modificación del código ajeno al plan requiere nuevo plan aprobado.
<!-- si devops.infraestructura=jenkins-kubernetes -->
La fase de instalación prepara el contenido en RUN_DIR/propuesta, sin escribir account/. La fase DevOps es la única que puede sembrar artefactos. Antes de invocarla, verifica que su política de generación admite la plantilla de Secret de base con las claves Clerk vacías, exclusivamente para el servicio de gestión identificado en el plan aprobado. Si esa política exige la plantilla común sin Clerk o excluye esas claves, detente con estado bloqueado y propón la ampliación específica; no uses otra fase para saltar la restricción. Con esa ampliación aprobada, invoca `devops-engineer` en modo generar, con el plan, write-report y la propuesta; solo la fase DevOps crea el Secret nuevo, ignorado y aprobado, con apertura exclusiva, e integra env-clerk en el deployment. Si el Secret existe no se abre ni se sobrescribe; tú rellenas el Secret, lo compruebas con `python3 -B -E .agents/scripts/servicios.py comprobar-secreto <ruta>` y lo aplicas con `kubectl apply -f <ruta>` antes del primer despliegue; la IA no lo abre. Los demás servicios conservan la plantilla común y el comportamiento habitual.
<!-- fin -->
4. Si hay gateway, la fase `file-writer` aplica únicamente los matchers y ruta aprobados, por método y prefijo final. No publiques todo el prefijo. Genera diff.patch incluyendo archivos nuevos con `git add -N` y `git diff HEAD` antes de pruebas y revisión.
5. Pruebas con `test-engineer`: pide permiso antes del primer Gradle y ejecuta `./gradlew compileJava test`. SDK simulado, secreto Svix generado por prueba, sin Clerk/Svix reales. Firma válida/inválida/sin cabeceras, evento propio/ajeno, reconciliación, pendiente y correo duplicado son obligatorios. Si la compilación falla, registra su salida literal y no declares éxito. Ejecuta el gate de `.agents/scripts/sonar-diff-gate.mjs` como en el flujo normal y revisión con `code-reviewer`; fallos vuelven a implementación con feedback y repiten pruebas/gate/revisión, máximo dos iteraciones.
6. Documentación con `tech-writer`, resultados en manifest y contrato completado con API, métodos, DTO, alias, códigos, matchers aprobados, eventos y variables por nombre. Entrega `RUN_DIR/contrato-gestion-usuarios.md` para llevar al front. **Repite en la salida: registro restringido de Clerk; todos los usuarios con sesión administran; sign-up solo para invitaciones, pre-registro local.** Informa riesgos de abuso/enum de correo y estado local inactivo; no hagas commits automáticos.
<!-- si devops.infraestructura=jenkins-kubernetes -->

## Avisos de entrega

Recuerda al usuario que debe rellenar él las claves de Clerk del Secret, comprobarlo con `python3 -B -E .agents/scripts/servicios.py comprobar-secreto <ruta>` y aplicarlo él en el clúster antes del primer despliegue. Indica la ruta creada o, si ya existía, que no se leyó ni se modificó y debe añadir las claves por su cuenta. No muestres, solicites ni escribas sus valores; no ejecutes kubectl, no apliques el Secret y no lo abras. Repite este aviso en la salida final del workflow.
<!-- fin -->
<!-- si devops.infraestructura=jenkins-kubernetes -->
## Entornos del plan aprobado

Antes de pedir aprobación, ejecuta `python3 -I -B .agents/scripts/servicios.py entornos` y `validar-entornos`. Enumera la tabla completa de `devops.entornos` para el pipeline. Solo para entradas con `desplegar: true`, enumera los datos de destino: carpeta, rama, sufijo, credencial_kubeconfig (solo ID), imagen, desplegar, puerto efectivo, nodePort, réplicas, recursos y los perfiles y artefactos que se crearán o modificarán. Los nombres de carpeta son libres y no se obtienen de la rama. El gateway usa gateway_nodo_puerto; sus perfiles llevan sufijo, CORS e issuer públicos de cada entorno y mantienen los valores globales en local.

Si el proyecto solo tiene una carpeta, lista las que faltan para aprobación; no alteres un entorno existente fuera del plan. Para migrar el Jenkinsfile existente, incluye su diff aprobado de lógica y mapa de entornos; no lo reemplaces automáticamente. RBAC y cuentas de Jenkins mantienen nombres fijos y contenido idéntico si comparten clúster; nunca leas los archivos existentes de account/. Las nuevas cuentas y Secrets vacíos requieren sus rutas aprobadas por carpeta y las comprobaciones de ausencia e ignore vigentes.

Con modo generar, DevOps corre después de la escritura exitosa y antes de comparar-plan.py, git add -N, git diff HEAD, pruebas, gate y revisión. Lo activa el plan aunque el diff previo no tocara DevOps. Un fallo de artefactos vuelve a DevOps con feedback.md (máximo dos intentos); solo codigo_diff vuelve a escritura. En la revisión posterior se invoca modo validar. Con modo validar inicial se conservan la comparación temprana y la condición posterior del diff.
<!-- fin -->
<!-- si devops.infraestructura=jenkins-kubernetes -->
Registra por entorno `carpeta`, `sufijo`, `tipo_servicio`, `servicio`, `plantilla_secret` y `fragmento_env`. Las propuestas de profile-installer son independientes para cada carpeta con `desplegar: true`; un constructor sin despliegue no recibe propuestas de Secret ni env Kubernetes. DevOps integra solo las de ese servicio de gestión. En Avisos y en la entrega, recuerda al usuario que debe completar las claves de Clerk del Secret de cada entorno, comprobarlo con `python3 -B -E .agents/scripts/servicios.py comprobar-secreto <ruta>` y aplicarlo él antes del primer despliegue; la IA no lo abre.
<!-- fin -->

Antes de aprobar cualquier plan, sigue `.agents/workflows/references/decisiones-stack.md`; consulta clases, remedios y códigos que resuelve este workflow en `.agents/config/codigos.yaml`.
