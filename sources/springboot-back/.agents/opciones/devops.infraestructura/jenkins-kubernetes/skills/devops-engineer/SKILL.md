---
name: devops-engineer
description: Prepara o valida artefactos DevOps de servicios existentes con Jenkins y Kubernetes, sin desplegar. Modo validar por defecto; generar requiere plan aprobado explícito.
---

# DevOps Engineer

Rol: Prepara artefactos reproducibles a partir de plantillas o comprueba su coherencia. El servidor Jenkins construye y despliega; esta fase no lo hace.

## Entrada

Recibes `OUT_DIR`, el modo de invocación (`validar` por defecto, o `generar`), el nombre exacto de salida y las rutas de estos archivos:

| Artefacto | Obligatorio | Contenido |
|---|---|---|
| `approved-plan.md` | sí | Plan aprobado, su aprobación literal y archivos permitidos. |
| `diff.patch` | modo validar | Diff completo que se audita, incluidos los artefactos ya generados. |
| `write-report.md` | modo generar | Escritura de producción terminada con éxito. |
| `feedback.md` | no | Incoherencias o errores concretos del intento anterior. |

El modo de invocación tiene prioridad: una invocación `validar` nunca genera aunque el plan autorice generación. `generar` solo se acepta si el plan dice `modo: generar` y lista cada artefacto en `## Archivos a crear o modificar`. Si falta autorización, una entrada obligatoria o la lista de rutas, devuelve `estado: bloqueado` con la causa.

Trabaja con las entradas y con los archivos permitidos del servicio; no asumas contexto fuera de ellos. Lee claves concretas mediante `node .agents/scripts/stack.mjs get <clave>`; para la tabla completa usa `python3 -I -B .agents/scripts/servicios.py entornos`, que delega en el lector genérico del generador. No analices stack.yaml por tu cuenta.

## Tareas

1. **Configuración del servicio**: Solo con `herramientas.codebase_memory: true`, resuelve `<proyecto>` con `python3 -I -B .agents/scripts/codebase-memory.py --resolver` (exit 0) y usa `codebase-memory-mcp cli trace_path --project "<proyecto>" --function-name "<Service o Deployment>" --mode run` o `--mode topology` como contexto orientativo de imagen, Dockerfile, programa y nombres de variables de entorno (nunca valores). Los pasos del `Jenkinsfile` no se enlazan; si no devuelve nada, continúa con la comprobación actual. Obtén `python3 -I -B .agents/scripts/servicios.py nombres <servicio>` y `entornos`. Consume `archivos`, `recursos`, `red` y `ruta_gateway` según Nombres de `assets/README.md`. `servicio` es carpeta; `nombre` es rootProject.name; `base` identifica recursos también del gateway; `context_path` solo define URL. No derives nombres a mano ni ejecutes Gradle. NOMBRE_SERVICIO solo avisa; NOMBRE_JAR debe corregirse en el plan antes de escribir artefactos. Si faltan context-path, JAR o puerto efectivo necesarios, bloquea sin inventarlos y propone incluirlos en el plan. Para nombres de variables usa `servicios.py variables-json`: nunca leas application*.yaml completos ni valores de credenciales.
   Si el servicio desplegable no es el gateway y `recursos.secret_base` es `null`, devuelve `estado: bloqueado`: no hay plantilla para un servicio desplegable sin base de datos. No improvises una variante.
   Si los puertos efectivos difieren entre perfiles, muestra la diferencia y bloquea la generación del Dockerfile único hasta que el usuario apruebe cómo resolverla. No cambies puertos ni elijas uno implícitamente.
2. **Modo validar, sin escritura**:
   - Determina el alcance con la base del diff y el árbol actual. Un servicio está tocado si cambia su carpeta (incluido su Dockerfile), un archivo de `devops/<carpeta>/` que le corresponde según `servicios.py nombres`, o su entrada de `getServices()` (añadida, cambiada o quitada). Son registrados los presentes en `getServices()` en la base o en el árbol actual. Valida los tocados; añade todos los registrados si cambia el archivo de `devops.jenkinsfile`, un archivo compartido de `devops/` o cualquier archivo ajeno a un servicio, como el `settings.gradle` raíz. Si el alcance queda vacío, valida todos los registrados. Lista en `devops-report.md` como «no incorporado» todo servicio en disco fuera del alcance: nunca produce `bloqueado` ni `fallo`.
   - Recorre todos los destinos con `desplegar: true`, no solo la rama actual. Informa de los entornos sin despliegue como omitidos: no requieren manifiestos, recursos, nodePorts ni cuentas. Usa `python3 -I -B .agents/scripts/servicios.py entornos` y `validar-entornos` para comprobar la tabla y los puertos. Cada resultado identifica carpeta y sufijo. Un entorno existente no se modifica sin estar listado en el plan; propone por separado los que faltan.
   - Dockerfile: JAR, EXPOSE, usuario no-root, JAVA_HOME y descarga declarados en el stack; health check en `<context-path>/actuator/health` (en el gateway, `/actuator/health`, sin context-path).
   - Servicios con base de datos, los cuatro manifiestos: puertos, nodePort, imagen R/nombre calculada por nombres, sondas, volumen y referencia del secret de base con los mismos nombres de variables `${...}` del perfil. El health check expone `/actuator/health`; no exige métricas adicionales.
   - Gateway: valida Deployment y Service específicos: sin secret de base, volúmenes ni PVC, sondas en `/actuator/health`, `serviceAccountName: discovery-service-account` y RBAC existente con `test -e devops/<carpeta>/account/rbac.yaml || test -L devops/<carpeta>/account/rbac.yaml`, sin abrir su contenido.
   - Para servicios con base de datos, el secret es un artefacto del servicio: comprueba solo su existencia con
     `test -e devops/<carpeta>/account/secrets-<base>-<sufijo>.yaml || test -L devops/<carpeta>/account/secrets-<base>-<sufijo>.yaml`; nunca abras su contenido. El usuario rellena el archivo, lo comprueba con `python3 -B -E .agents/scripts/servicios.py comprobar-secreto <ruta>` y lo aplica con `kubectl apply -f <ruta>` antes del primer despliegue; la IA no lo abre.
   - Cuentas de Jenkins: comprueba solo existencia con
     `test -e devops/<carpeta>/account/jenkins-account.yaml || test -L devops/<carpeta>/account/jenkins-account.yaml` y
     `test -e devops/<carpeta>/account/secrets-jenkins-account.yaml || test -L devops/<carpeta>/account/secrets-jenkins-account.yaml`, sin abrirlos.
   - La entrada del servicio en `getServices()` mediante `python3 -I -B .agents/scripts/servicios.py validar-jenkins`: name (JAR), directory (carpeta) y sin entrada de ejemplo ni claves repetidas; displayName o clave distinta solo avisan.
   - Distingue mediante la base del diff las incoherencias nuevas de las preexistentes. Compara el nombre del archivo y metadata.name con nombres, además de selectores app/environment, contenedor, imagen, puertos, volumen/hostPath, claim y referencias públicas de secrets de base/Clerk. Solo una incoherencia causada por código del diff produce `fallo` con `causa: codigo_diff` y una lista verificable. Un artefacto ausente o preexistente incorrecto es una observación, nunca fallo de código: propone generar mediante enmienda; si falta un artefacto de un servicio en alcance, devuelve bloqueado con esa propuesta.
3. **Modo generar, escritura acotada**:
   - Los entornos que no despliegan no reciben directorios de manifiestos ni account/; registra su omisión. Jenkinsfile y Dockerfile de construcción siguen preparándose cuando el plan los autorice, aunque no haya destinos desplegables.
   - Recorre solo las entradas de `devops.entornos` con `desplegar: true` y prepara los artefactos aprobados en `devops/<carpeta>/<servicio>/` y las cuentas aprobadas en su `account/`. La carpeta es el nombre libre del mapa; no la deduzcas de `rama`. Usa sufijo, réplicas, CPU y memoria del entorno. El almacenamiento conserva la plantilla en todos ellos. Toma el nodePort de `red.node_port` de `servicios.py nombres` para ese servicio y entorno, también en el gateway; no repitas la fórmula. Ejecuta la validación de rangos antes de escribir.
   - Sustituye `__CARPETA_ENTORNO__`, `__REPLICAS__`, `__CPU_PETICION__`, `__CPU_LIMITE__`, `__MEMORIA_PETICION__`, `__MEMORIA_LIMITE__`, `__ENTORNO__` y su variante mayúscula por los campos de la entrada actual. Escapa cada valor según YAML, Groovy o shell.
   - Los nombres fijos de RBAC y Jenkins se conservan. Si varios entornos comparten clúster, aplicar el mismo contenido es idempotente; no añadas sufijos a esas identidades. Los nombres del servicio, Secret de base, PV, PVC y `/mnt/data/<base>-<sufijo>` sí llevan el sufijo. Nunca abras las cuentas existentes para compararlas.
   - Usa `assets/Jenkinsfile`, `assets/Dockerfile.template` y las plantillas de `assets/k8s/`; aplica la tabla única de Nombres de `assets/README.md`.
   - Identifica el gateway por `backend.gateway` o por la creación de gateway explícita en el plan.
     Usa `assets/k8s/deployment-gateway.template.yaml` y `service-gateway.template.yaml` para él;
     los demás conservan sus plantillas habituales. El gateway no recibe secret de base, PV ni PVC.
     Su Dockerfile usa health check `/actuator/health`, con context-path vacío.
   - Para el gateway, `__NODE_PORT__` sale de `devops.entornos.<carpeta>.gateway_nodo_puerto`;
     no apliques la fórmula de servicios. Si falta o choca, devuelve bloqueado.
   - RBAC: solo al generar artefactos del gateway y si el plan lista la ruta,
     siembra `assets/k8s/rbac.template.yaml` en `devops/<carpeta>/account/rbac.yaml` cuando no exista.
     Si existe (incluido un enlace), no lo abras ni sobrescribas: anota "existente, sin tocar".
     No exige git check-ignore porque no es un secreto; crea sin sobrescritura.
   - Cuentas de Jenkins: en la primera generación de artefactos DevOps de cualquier servicio,
     incluido uno que no sea gateway, crea las cuentas que falten solo si el plan lista sus rutas.
     Usa `assets/k8s/jenkins-account.template.yaml` para `devops/<carpeta>/account/jenkins-account.yaml`
     y `assets/k8s/secret-jenkins-account.template.yaml` para `devops/<carpeta>/account/secrets-jenkins-account.yaml`.
   - Trata cada cuenta de forma independiente: si ya existe (incluido un enlace), anota
     "existente, sin tocar", sin abrirla ni sobrescribirla. Crea sin sobrescritura primero
     jenkins-account.yaml, que no exige git check-ignore.
   - Antes de crear secrets-jenkins-account.yaml exige `git check-ignore -q <ruta>` con exit 0.
     Si no está ignorado, no crees ese secret y devuelve bloqueado con el mismo aviso de gitignore
     que el secret de base; la cuenta no secreta aprobada se crea igualmente. No cambies el índice.
     El Secret lleva solo nombre, namespace, anotación y tipo, nunca data/stringData ni token.
   - Comprueba con `rg -n "generado automáticamente"` que los artefactos sembrados no contengan la cabecera del generador (1 = sin coincidencias; 0 = fallo; ≥2 = error). Conserva los comentarios originales de las plantillas.
   - Siembra solo los artefactos listados por el plan. Conserva comentarios, recursos, sondas y seguridad del original. La imagen base es `redhat/ubi10-minimal`; la URL del JDK y ambos JAVA_HOME salen del stack, sin derivar uno de otro.
   - Sustituye `<devops.*>`, `<backend.java>`, `<backend.perfil_local>` y `__X__` con datos comprobados. `<backend.perfil_local>` usa por defecto `feature` si falta. `<devops.credencial_bd_pruebas>` y `<devops.slack_canal>` con valor null pasan a texto vacío (Groovy evita enviar el aviso de Slack y el build omite la inyección de credenciales de base de pruebas). Escapa cada valor para su lenguaje de destino.
   - Copia el Jenkinsfile cuando falte y el plan lo autorice. Sustituye `__MAPA_ENTORNOS__` por un mapa literal Groovy con todas las entradas (también el constructor sin despliegue), cada una con `carpeta`, `rama`, `sufijo`, `credencial_kubeconfig`, `imagen` y `desplegar`; no escribas valores de credenciales. Sustituye `__SERVICIOS_JENKINS__` con la salida de `python3 -I -B .agents/scripts/servicios.py entradas-jenkins` (una entrada por servicio en disco, sin entrada de ejemplo). Conserva la resolución única de rama en Checkout, el stash del tag exacto, la promoción con comprobación de historial y el acarreo de versión. Si el Jenkinsfile ya existe, solo se modifica el mapa `getServices()` añadiendo la entrada del servicio aprobado (o actualizando una clave si provoca choque en su grupo), o una declaración de nodo del pipeline cuando el plan aprobado enumera expresamente ese cambio y su diff; migrar su lógica o su mapa de entornos exige que el plan aprobado enumere expresamente ese cambio y su diff. No reemplaces un pipeline existente a ciegas.
   - Para actualizar un pipeline sin CONSTRUIR_TODO con diff aprobado, limita esta migración a detección/filtros, parámetro, errores y Slack; conserva getServices(), getEnvironments() y valores del proyecto. El preflight DEVOPS_VALORES detecta la ausencia de CONSTRUIR_TODO incluso sin marcas; una cadena presente no certifica una migración completa. Usa el modo generar existente, sin sobrescribir el pipeline entero.
   - Conserva el listado versionado completo sin commit anterior/con GIT_COMMIT ausente o params.CONSTRUIR_TODO == true, el diff normal en otro caso y los filtros corregidos (README solo no activa trabajo). CONSTRUIR_TODO es false por defecto: construir publica imágenes nuevas, promover reutiliza imágenes elegibles y feature/* analiza todos los servicios relevantes; despliegue según entorno. Aparece tras el primer build multibranch. Mantén los remedios por modo, el fallo por manifiestos ausentes y Slack con estado explícito y anuncio solo tras comprobar canal.
   - Tras `kubectl apply`, espera `kubectl rollout status` con timeout del pipeline dentro del mismo contexto de credenciales; si falla, diagnostica con `kubectl get pods -l app=<base>-<sufijo>,tier=application -o wide` y `kubectl describe -f <ruta del deployment>` (sin `logs`, `get secret` ni `describe secret`) y termina con error explícito. El resumen final distingue Compilados, Analizados, Construidos y Desplegados; cada grupo se registra también con fallos parciales, y muestra «Sin servicios con cambios» solo si no hay ninguno, sin alterar el resultado.
   - Antes de Gradle en compilación/análisis comprueba `javac` en el nodo (`JAVA_HOME_NODO_INVALIDO` si falta). Si hay credencial de base de pruebas, valida en el nodo `DB_HOST_<P>`, `DB_PORT_<P>` y `DB_NAME_<P>` (`BD_PRUEBAS_INCOMPLETA` sin mostrar valores) e inyecta `USER_NAME_DB_<P>`/`PASSWORD_DB_<P>` solo alrededor de Gradle; `<P>` deriva de `<backend.perfil_local>` en mayúsculas. Sin credencial, el build no inyecta variables. Los servicios comparten esas variables del nodo (misma base de pruebas por perfil); el aislamiento por servicio queda fuera de alcance.
   - Los Secrets de base/Clerk se rellenan en texto plano (`stringData`, sin Base64), con claves del sufijo del entorno. Tú rellenas el archivo, lo compruebas con `python3 -B -E .agents/scripts/servicios.py comprobar-secreto <ruta>` y lo aplicas con `kubectl apply -f <ruta>` antes del primer despliegue; el pipeline no lo aplica y la IA no lo abre. Consulta los límites y costes en assets/README.md.
   - Comprueba con `rg -n '__[A-Z_]+__|<devops\.|<backend\.'` todos los archivos sembrados: 1 = sin marcadores; 0 = fallo; ≥2 = error que se informa literalmente. Nunca dejes marcadores pendientes.
   - Comprueba que puerto y nodePort no pertenecen a otro servicio en el perfil aplicable ni en los manifiestos existentes. No cuenta como colisión el mismo puerto declarado en el Deployment y Service de su propietario. No inventes asignaciones de puertos ni artefactos del gateway o servicios nuevos.
   - Secret de base, solo para servicios con base de datos que no sean el gateway: si el plan lista `devops/<carpeta>/account/secrets-__BASE__-__ENTORNO__.yaml`,
     resuelve su ruta y comprueba si ya existe con `test -e <ruta> || test -L <ruta>` sin abrirlo. La IA solo crea el archivo desde la plantilla tras comprobar que no existe; si existe, anota "existente, sin tocar";
     nunca lo leas ni lo sobrescribas. Tampoco sustituyas una ruta existente que sea un enlace.
   - Antes de crear ese archivo, exige `git check-ignore -q <ruta>` con exit 0. Si no lo ignora,
     no crees nada y devuelve `bloqueado`: "añade `devops/<carpeta>/account/` al `.gitignore` y saca
     del índice los secretos ya versionados (`git rm --cached`)". No cambies el índice ni el ignore.
   - Con la ruta ausente, ignorada y aprobada, crea exclusivamente desde `assets/k8s/secret.template.yaml`,
     sin sobrescritura. Conserva las cinco claves en stringData con `""`, sin valores de credenciales.
     Informa la ruta sembrada o el motivo de no sembrarla. No ejecutes el comando de su cabecera. El usuario rellena el archivo, lo comprueba con `python3 -B -E .agents/scripts/servicios.py comprobar-secreto <ruta>` y lo aplica con `kubectl apply -f <ruta>` antes del primer despliegue; la IA no lo abre.
   - Un error de siembra devuelve `fallo`, `causa: artefactos` y su salida literal; si la causa es código del diff, declara `causa: codigo_diff`. No cambies código de aplicación para corregir la siembra.
4. **Reporte**: Si existen nombres distintos, enumera ruta vieja → nueva con git mv y cada campo/recurso a editar en el plan aprobado. En Avisos explica: los recursos con el nombre viejo siguen en el clúster hasta que el usuario los borre. Indica los nombres nuevos de secrets de base y Clerk desde referencias públicas, nunca sus valores. El usuario prepara y aplica sus secrets; el agente no ejecuta kubectl.
    Registra coherencia por archivo, observaciones preexistentes, propuestas de enmienda, comandos estáticos ejecutados y su salida literal, y archivos realmente escritos. No atribuyas resultados de Docker, Kubernetes o Jenkins que no se ejecutaron.

## Reglas

- Aplica `.agents/rules/architecture-rules.md` y `.agents/rules/project.md`.
- En `devops/<carpeta>/account/` solo se permite crear estos archivos ausentes desde su plantilla:
  `rbac.yaml`, `jenkins-account.yaml`, `secrets-jenkins-account.yaml` y `secrets-<base>-<sufijo>.yaml`.
  Todos requieren modo generar y estar listados por el plan; RBAC conserva su condición de gateway,
  las cuentas de Jenkins se preparan para cualquier servicio y el secret de base para servicios con base de datos.
  Solo los secrets exigen git check-ignore. Nunca abras ni leas un archivo existente de account/,
  ni lo sobrescribas; esto incluye los archivos permitidos. Nunca leas el kubeconfig.
- El resto de account/, kubeconfig.yaml y los demás archivos de secretos siguen prohibidos:
<!-- si integraciones.autenticacion=clerk -->
  ni leer ni escribir. El secret de MySQL en `devops/<carpeta>/mysql/` y los de Clerk quedan fuera de alcance.
<!-- si integraciones.autenticacion=ninguna -->
  ni leer ni escribir. El secret de MySQL en `devops/<carpeta>/mysql/` queda fuera de alcance.
<!-- fin -->
<!-- si integraciones.gestion_usuarios=organizaciones|aplicacion -->
- Excepción única a la plantilla exclusiva de base y a la exclusión de Clerk: en modo generar,
  solo si approved-plan.md identifica por entorno carpeta, sufijo, tipo_servicio: gestion_usuarios y el nombre exacto del
  servicio actual, usa la plantilla_secret y fragmento_env de ese entorno entregados como propuestas por ese plan.
  La plantilla conserva las cinco claves de base y añade solo los nombres de Clerk del contrato;
  todos los valores de stringData deben ser texto vacío. El destino sigue siendo el Secret de base
  permitido, ausente, ignorado y enumerado en el plan; crea con apertura exclusiva, sin leer ni
  sobrescribir un archivo existente. Integra las referencias del fragmento_env únicamente en el
  deployment aprobado de ese servicio y comprueba sus nombres contra el contrato, nunca contra
  el contenido de un Secret existente. En validar solo comprueba existencia y referencias públicas.
  Sin esa identificación exacta, conserva la plantilla y el comportamiento habituales de los demás
  servicios. Nunca crea un Secret separado de Clerk ni modifica los de otros servicios.
<!-- fin -->
- Nunca apliques archivos en el clúster: ni kubectl apply ni create. Aplicar RBAC, cuentas de Jenkins,
  secret del token y secrets de base corresponde al usuario. En Avisos lista los archivos sembrados
  que él debe aplicar; no obtengas el token ni crees kubeconfig ni credenciales de Jenkins.
- Nunca escribas valores de credenciales en la plantilla, archivos sembrados ni informes;
  el usuario los completa y aplica. En validar solo se comprueba existencia, sin lectura.
- Nunca ejecutes docker, kubectl, Jenkins ni despliegues. La configuración del servidor Jenkins, rutas JDK, credenciales y registry corresponde al usuario.
- Modo validar no modifica archivos del proyecto. Modo generar solo escribe los artefactos aprobados; una migración de lógica o mapa de entornos del pipeline requiere el diff y la aprobación específicos del plan.

## Salida

Escribe el reporte con el nombre exacto recibido (`devops-report.md` por defecto; `devops-generate-report.md` para conservar una generación previa):

```markdown
---
artefacto: devops-report.md | devops-generate-report.md
skill: devops-engineer
estado: ok | fallo | bloqueado
causa: ninguna | artefactos | codigo_diff | infraestructura
entradas_leidas: [approved-plan.md]  # lista real de entradas completas
fecha: <ISO-8601>
---

## Modo
validar | generar

## Coherencia comprobada
- Pipeline/getServices, Dockerfile/JAR/EXPOSE/health, manifiestos/puertos/variables: resultado real por archivo.

## Observaciones y propuesta de enmienda
- Ausencias o incoherencias preexistentes, sin atribuirlas al código del diff.

## Comandos y salida literal
- Comando, código de salida y salida real de cada comprobación estática.

## Archivos tocados
- Solo rutas escritas en modo generar; ninguna en modo validar.

## Avisos
- El usuario debe rellenar, comprobar con `python3 -B -E .agents/scripts/servicios.py comprobar-secreto <ruta>` y aplicar los Secret de base sembrados antes del primer despliegue (la IA no los abre). Lista los archivos sembrados que debe aplicar: (lista literal de rbac.yaml, jenkins-account.yaml,
  secrets-jenkins-account.yaml y secrets de base realmente creados; si no se creó ninguno, indícalo).
- (archivos existentes, sin tocar, o motivos de bloqueo; el agente nunca aplica ni obtiene el token)
```
