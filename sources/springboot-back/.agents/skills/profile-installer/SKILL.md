---
name: profile-installer
description: Añade perfiles mínimos, invitaciones y webhooks verificados al esqueleto de un servicio, según un contrato aprobado.
---
<!-- si-archivo integraciones.gestion_usuarios=organizaciones|aplicacion -->

# Gestión de usuarios

## Entrada

`OUT_DIR`, plan aprobado y contrato de base con nombres físicos y procedimientos. Si no hay contrato, exige que el plan apruebe explícitamente los nombres recomendados y ese supuesto. No lee otro proyecto. Solo propone los archivos enumerados en el plan en OUT_DIR/propuesta y code-changes.md; no modifica código de producción.

## Implementación

Aplica `.agents/rules/architecture-rules.md` y `.agents/rules/project.md`. Materializa los assets en OUT_DIR/propuesta para el servicio ya creado, quitando la cabecera del generador. El código de producción se entrega como code-changes.md; las pruebas se entregan a su fase de ejecución. Sustituye `__PAQUETE__`, todos los `__SP_*__` y los marcadores de tabla/columna usando la tabla del contrato, sin inferir nombres de otro stack. Java usa constantes PENDIENTE=1, INVITADO_A_CLERK=2, ACTIVO=3, INACTIVO=4. No expone Data REST ni contraseñas ni roles. La creación usa el ID real del procedimiento. Pre-registro tiene su propio DTO y fuerza pendiente sin llamar a Clerk. El webhook verifica Svix antes de parsear; las respuestas de error usan ExceptionResponse y api_error, sin trazas. No copia mensajes crudos del SDK a la API.

Las dependencias y configuración se integran desde los assets sin duplicar bloques. Quita únicamente del build del nuevo servicio las dependencias Data REST heredadas; conserva persistencia y web, y elimina spring.data.rest de la configuración de este servicio nuevo. El control JWT del servicio protege también el acceso directo; no depende de que haya gateway. Resuelve el issuer desde integraciones.clerk_issuer_uri, sin valores propios en la plantilla. No modifica plantillas de otros servicios. Nombres de credenciales, nunca valores; `${VARIABLE}` sin respaldos. Los DTO administrativos no aceptan ClerkUserId. No registra cuerpo del webhook ni datos personales. Reconciliación consulta el SDK y la vinculación impide reemplazar un usuario por otro.

<!-- si integraciones.gestion_usuarios=organizaciones -->
La invitación usa organización y org:member. El SDK documenta public_metadata de invitación en la membresía: el webhook lee data.public_metadata.perfilId y valida la organización del perfil; reconciliación consulta los mismos metadatos. El invitador del request o CLERK_DEFAULT_INVITER_USER_ID debe estar configurado; no inventes un ID.
<!-- si integraciones.gestion_usuarios=aplicacion -->
La invitación es a la aplicación. El webhook user.created lee data.public_metadata.perfilId; reconciliación consulta usuarios.
<!-- fin -->

<!-- si devops.infraestructura=jenkins-kubernetes -->
Para un servicio nuevo, prepara exclusivamente en OUT_DIR/propuesta el contenido de los assets k8s con campos de base y Clerk vacíos y el fragmento env-clerk. No escribe artefactos DevOps en el proyecto. No lee account ni secretos existentes, no modifica los assets DevOps comunes ni extiende otros servicios. No ejecuta kubectl. Si la política de siembra vigente no admite esta plantilla, devuelve bloqueado; no eludas sus límites con otra fase.
<!-- fin -->

## Salida

`OUT_DIR/profiles-report.md` con frontmatter artefacto, skill: profile-installer, estado: ok|fallo|bloqueado; archivos, marcadores resueltos, diferencias de dependencias y comandos/salidas literales. Marcador pendiente es fallo. No ejecuta Gradle sin permiso; no llama a Clerk real durante las pruebas.
<!-- si devops.infraestructura=jenkins-kubernetes -->
## Propuestas por entorno

Marcadores de las plantillas Clerk: `__BASE__` = `base` de `servicios.py nombres <servicio>`; si el servicio aún no existe, usa la base aprobada en el plan, `rootProject.name` sin un `-service` final. `__ENTORNO__` es el sufijo de la entrada de `devops.entornos`, `__ENTORNO_MAYUS__` su mayúscula y `__CARPETA_ENTORNO__` el nombre de esa entrada.

Solo para entradas de `devops.entornos` con `desplegar: true`, prepara en OUT_DIR/propuesta/<carpeta>/ la plantilla de Secret vacío y su fragmento env con las variables de base del sufijo y los nombres de Clerk del contrato. Registra carpeta, sufijo, tipo_servicio, servicio, plantilla_secret y fragmento_env. Usa `assets/application-clerk-entorno.fragment.yaml` para proponer el documento público k8s de cada `application-<sufijo>.yaml` que corresponda a un destino desplegable, con su issuer; el issuer global sigue valiendo en local. Estas propuestas no escriben en account/ ni leen ningún Secret existente. El usuario completa las claves y aplica los archivos.
<!-- fin -->
