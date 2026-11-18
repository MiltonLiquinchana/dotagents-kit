# Artefactos DevOps canónicos

Se preparan archivos para Jenkins; el agente no despliega ni ejecuta Docker o Kubernetes.

## Nombres

Obtén la tabla calculada con `python3 -I -B .agents/scripts/servicios.py nombres [servicio] [--entorno CARPETA]`. Es la fuente de archivos y recursos para generar y validar; no los derives a mano. Cada fila identifica `servicio` (carpeta), `nombre` (`rootProject.name`), `base` (nombre sin un `-service` final), `group`, JAR, clave Sonar y `context_path`. El gateway usa la misma base; su tratamiento sin base de datos y sus sondas WebFlux siguen siendo específicos.

Símbolos: D = carpeta; N = `rootProject.name`; B = base; E = nombre de entrada de `devops.entornos`; S = su `sufijo`; U = S en mayúsculas; C = `context_path`; P = puerto efectivo de S o del base; R = `devops.registry`. Ejemplo: D=N=`pedidos-service`, B=`pedidos`, E=`development`, S=`dev`, C=`/pedidos`, P=`8082`, R=`registro-ejemplo`. C solo participa en URL, nunca en identidades Kubernetes. `spring.application.name` conserva N-S.

### Valores y destinos

| Marcador | Origen | Destino |
|---|---|---|
| `__SERVICIO__` | `servicio`, carpeta D | directorios y rutas de archivos |
| `__NOMBRE__` | `nombre`, N | imagen, comentarios de identidad, settings y nombre de Spring |
| `__BASE__` | `base`, B | archivos y recursos según la tabla siguiente |
| `__CONTEXT_PATH__` | `context_path`, C; vacío en gateway WebFlux sin prefijo | URL de sondas/health check |
| `__CARPETA_ENTORNO__` | E, entrada de `devops.entornos` | carpeta y etiqueta `environment` |
| `__ENTORNO__`, `__ENTORNO_MAYUS__` | S y U | sufijos y nombres de variables |
| `__JAR__` | `jar` de nombres | COPY del Dockerfile |
| `__PUERTO__` | puerto efectivo del servicio (`listar`/`validar-entornos`); el Dockerfile único requiere puerto compatible entre perfiles | EXPOSE y health check del Dockerfile; puertos de contenedor/Service/sondas por perfil |
| `__NODE_PORT__` | `red.node_port` de `servicios.py nombres` para el entorno | nodePort del Service |
| `__SERVICIOS_JENKINS__` | `servicios.py entradas-jenkins` | `getServices()`, sin campos añadidos |
| `<devops.registry>` | lector de stack, R | namespace de imágenes y catálogo |
| `<devops.nodos.general>` | lector de stack | valor de la declaración `NODO_GENERAL` del pipeline (etiqueta del agente general) |
| `<devops.nodos.compilacion>` | lector de stack | valor de la declaración `NODO_COMPILACION` del pipeline (etiqueta de compilación y análisis) |
| `<devops.nodos.docker>` | lector de stack | valor de la declaración `NODO_DOCKER` del pipeline (etiqueta Docker) |

El pipeline declara cada nodo una sola vez al principio (`NODO_GENERAL`, `NODO_COMPILACION`, `NODO_DOCKER`) y usa esas constantes en `agent`, `node(label: ...)` y en los mensajes. Cambiar de nodo es editar la declaración correspondiente con un plan aprobado.
| `<devops.jenkinsfile>` | lector de stack | ruta del pipeline; `Script Path` en Jenkins |
| `<devops.java_home_nodo>` | lector de stack | ruta común del JDK que compila |
| `<devops.java_home_contenedor>`, `<devops.jdk_url>` | lector de stack | JAVA_HOME y descarga del JDK de la imagen |
| `<devops.slack_canal>` | lector de stack; null → texto vacío | canal; sin valor no envía avisos |
| `<devops.credencial_bd_pruebas>` | lector de stack; null → texto vacío | ID de credencial Jenkins (usuario/contraseña) para inyectar la base de pruebas en el build; sin valor no se inyecta |
| `<backend.java>` | lector de stack | comentario de versión Java |
| `<backend.perfil_local>` | lector de stack; por defecto `feature` | perfil `<P>` (mayúsculas) de las variables de base de pruebas usadas en compilación |
| `__REPLICAS__`, `__CPU_PETICION__`, `__CPU_LIMITE__`, `__MEMORIA_PETICION__`, `__MEMORIA_LIMITE__` | entrada E | réplicas, requests y limits |

Un servicio desplegable que no sea el gateway y tenga `recursos.secret_base: null` queda `estado: bloqueado`: no hay plantilla para él sin base de datos. No se improvisan variantes.

### Archivos y recursos

Usa los campos `archivos`, `recursos`, `red` y `ruta_gateway` de `nombres`. La columna patrón explica su origen; la sustitución utiliza la salida calculada. Para el ejemplo, `B-S` es `pedidos-dev`. Los destinos de manifiestos/cuentas solo existen con `desplegar: true`; un constructor sin despliegue conserva pipeline/Dockerfile sin manifiestos ni cuentas. Un valor null significa que no corresponde crear ese archivo o recurso.

| Archivo o campo | Patrón y origen | Ejemplo |
|---|---|---|
| Pipeline | valor de `devops.jenkinsfile` | `devops/Jenkinsfile` |
| Dockerfile | `D/Dockerfile` | `pedidos-service/Dockerfile` |
| Deployment, también gateway | `devops/E/D/deployment-B.yaml` | `devops/development/pedidos-service/deployment-pedidos.yaml` |
| Service, también gateway | `devops/E/D/service-B.yaml` | `devops/development/pedidos-service/service-pedidos.yaml` |
| PV / PVC, solo servicio con base de datos/volumen | `devops/E/D/persistence-volume.yaml` / `persistence-volume-claim.yaml` | mismos nombres fijos bajo la carpeta D |
| Secret de base/contrato Clerk, ruta | `devops/E/account/secrets-B-S.yaml` | `devops/development/account/secrets-pedidos-dev.yaml` |
| Cuentas de Jenkins, rutas fijas por E | `devops/E/account/jenkins-account.yaml` y `secrets-jenkins-account.yaml` | en `devops/development/account/` |
| RBAC, solo gateway | `devops/E/account/rbac.yaml` | `devops/development/account/rbac.yaml` |
| Deployment `metadata.name` | `B-S-deployment` | `pedidos-dev-deployment` |
| Service `metadata.name` | `B-S-service` | `pedidos-dev-service` |
| PVC `metadata.name` / Deployment `claimName` | `B-S-claim` | `pedidos-dev-claim` |
| PV `metadata.name` | `B-S-volume` | `pedidos-dev-volume` |
| Contenedor, también gateway | `B-S-service-container` | `pedidos-dev-service-container` |
| Secret de base y todos sus `secretKeyRef.name`, incluidos Clerk | `B-S-service-db-secret` | `pedidos-dev-service-db-secret` |
| Volumen del pod y `volumeMounts.name` | `B-volume`, sin S | `pedidos-volume` |
| PV `hostPath.path` | `/mnt/data/B-S` | `/mnt/data/pedidos-dev` |
| Montaje de logs | fijo `/app/logs` | `/app/logs` |
| `labels.app` de recursos/pod y selectores Deployment/Service/PVC | `B-S` | `pedidos-dev` |
| `environment` en labels y selector PVC→PV | E | `development` |
| PVC `usage-purpose` | `B-S-log-storage` | `pedidos-dev-log-storage` |
| Nombre del puerto Service | `B-S-port` | `pedidos-dev-port` |
| Namespace de objetos con ámbito namespace | fijo `default`; PV y ClusterRole/Binding conservan ámbito clúster | `default` |
| Imagen, también `docker.build` | `R/N`; el pipeline añade el tag | `registro-ejemplo/pedidos-service` |
| JAR de COPY | `jar` calculado; nombre de artefacto igual a N con DevOps | `pedidos-service-1.0.0.jar` |
| EXPOSE, port, targetPort, containerPort y puerto de sondas | P | `8082` |
| nodePort de servicio | `nodo_puerto_base + (P - 8080)` | `30082` con base `30080` |
| nodePort de gateway | `gateway_nodo_puerto` de E | valor aprobado del entorno |
| Sondas/health de servicio | `C/actuator/health` | `/pedidos/actuator/health` |
| Sondas/health de gateway WebFlux | fijo `/actuator/health` | `/actuator/health` |
| Variables y `secretKeyRef.key` de base | `DB_HOST_U`, `DB_PORT_U`, `DB_NAME_U`, `USER_NAME_DB_U`, `PASSWORD_DB_U` | nombres con `DEV`; nunca valores |
| Variables Clerk | nombres del contrato aprobado, referidos al secret calculado | nombres públicos; valores vacíos en propuestas |
| `SPRING_PROFILES_ACTIVE` | `docker,k8s,S` | `docker,k8s,dev` |
| `spring.application.name` en perfil | `N-S`, no nombre de recurso Kubernetes | `pedidos-service-dev` |
| Gateway id de destino | `B-service-route` | `pedidos-service-route` |
| Gateway URI de destino | `lb://B-S-service`, S del perfil activo | `lb://pedidos-dev-service` |
| Gateway path de destino | `C/**` | `/pedidos/**` |
| Gateway cabecera `X-Gateway` | `api-B-S` | `api-pedidos-dev` |
| Cuenta/Role/RoleBinding Jenkins y referencias | fijo `jenkins` | `jenkins` |
| ClusterRoleBinding / ClusterRole Jenkins | fijos `jenkins-crb` / `jenkinsclusterrole` | mismos |
| Secret del token / anotación de cuenta | fijos `jenkins-token` / `jenkins` | mismos |
| RBAC discovery cuenta / rol / binding y referencias | fijos `discovery-service-account`, `discovery-cluster-role`, `discovery-cluster-role-binding` | mismos |

`getServices()` conserva `directory=D`, `name` como nombre de artefacto, `displayName` como palabras capitalizadas y clave de primera palabra o camelCase de B si choca. No se añaden campos. `NOMBRE_JAR` exige igualar el artefacto a N antes de escribir DevOps; el cierre/estricto bloquean si no se ha hecho. Las convenciones de sufijo y B distinta de C solo avisan.

El pipeline se siembra en la ruta configurada, con `__MAPA_ENTORNOS__` desde `servicios.py entornos` y `__SERVICIOS_JENKINS__` desde `entradas-jenkins`, sin entrada de ejemplo. Si ya existe, solo se cambia la lógica o mapa que enumere un diff aprobado. Escapa cada valor para Groovy, YAML o Dockerfile, sin interpolarlo en comandos shell. Conserva comentarios, capacidad/acceso de PV/PVC, seguridad y recursos de las plantillas.

## Responsabilidad del usuario en Jenkins

Configura las rutas JDK, acceso al registry, etiquetas de devops.nodos y la integración SonarQube con el nombre de instalación `SonarQubeServer` (`withSonarQubeEnv` del Jenkinsfile). No se crea una herramienta JDK en Jenkins. Con una etiqueta para las tres tareas hacen falta al menos tres ejecutores disponibles. Conserva los IDs `dockerhub_integration_credentials` y `sonarqube-webhook-integration-secret`. Para kubeconfig usa los IDs declarados en `devops.entornos.<nombre>.credencial_kubeconfig` (credenciales de tipo archivo, solo las usa Jenkins). El bloque withCredentials y la variable KUBECONFIG permanecen intactos; el agente no lee ni escribe kubeconfig.

En modo generar, si el plan lo lista y git ignora el destino, el agente siembra
`k8s/secret.template.yaml` en `devops/<carpeta>/account/secrets-__BASE__-__ENTORNO__.yaml`.
El nombre es `__BASE__-__ENTORNO__-service-db-secret`; namespace y etiquetas app/environment
coinciden con el deployment. stringData lleva `DB_HOST___ENTORNO_MAYUS__`,
`DB_PORT___ENTORNO_MAYUS__`, `DB_NAME___ENTORNO_MAYUS__`, `USER_NAME_DB___ENTORNO_MAYUS__`
y `PASSWORD_DB___ENTORNO_MAYUS__`, todas con `""`, iguales a los secretKeyRef del deployment.
El usuario rellena los valores en texto plano en local (sin Base64 en `stringData`; si copia desde un
Secret con `data:`, debe decodificarlos o usar `data:`), con el sufijo de ese entorno igual al de las
`secretKeyRef` del deployment. Tú rellenas el archivo, lo compruebas con `python3 -B -E .agents/scripts/servicios.py comprobar-secreto <ruta>` y lo aplicas con `kubectl apply -f <archivo>` antes del primer despliegue; el pipeline no lo aplica, el archivo no se sube al repositorio y la IA no lo abre.
Como alternativa, puede usar los comandos `kubectl create secret` con valor vacío que imprime
`actualizar.py`, completándolos él mismo.

Antes de crear el archivo se comprueba `git check-ignore -q <ruta>`; si no está ignorado,
se bloquea y se pide añadir `devops/<carpeta>/account/` al `.gitignore` y sacar del índice
los secretos versionados (`git rm --cached`). Si existe, se informa "existente, sin tocar",
sin abrirlo, leerlo ni sobrescribirlo. En validar solo se comprueba su existencia con `test -e <ruta> || test -L <ruta>`.
<!-- si integraciones.autenticacion=clerk -->
Salvo rbac.yaml y las cuentas de Jenkins en las condiciones descritas abajo, el resto de account/, kubeconfig.yaml, el secret de MySQL y los de Clerk quedan fuera de alcance:
<!-- si integraciones.autenticacion=ninguna -->
Salvo rbac.yaml y las cuentas de Jenkins en las condiciones descritas abajo, el resto de account/, kubeconfig.yaml, el secret de MySQL quedan fuera de alcance:
<!-- fin -->
no se leen ni escriben. Nunca se copian valores a la plantilla ni al informe.

La asignación de puertos de servicios nuevos requiere un diseño aprobado. Las cuatro plantillas de servicio cubren servicios con base de datos y volumen; el gateway usa las variantes específicas descritas abajo.


## Gateway y RBAC

El gateway declarado por `backend.gateway` o creado como tal por el plan usa
`k8s/deployment-gateway.template.yaml` y `k8s/service-gateway.template.yaml` en
`devops/<carpeta>/<servicio>/deployment-<base>.yaml` y `service-<base>.yaml`.
El Deployment utiliza `discovery-service-account`, sin variables ni secret de base,
volúmenes, PV ni PVC; sus sondas y el health check del Dockerfile van a `/actuator/health`.
El Service propio mantiene las etiquetas gateway. Su `__NODE_PORT__` sale de `gateway_nodo_puerto` de la entrada del entorno, no de la fórmula de servicios. Si falta o choca, se bloquea. Un cambio de un manifiesto existente debe estar enumerado en el plan.

Al generar artefactos del gateway, si el plan lista la ruta y falta el archivo,
`k8s/rbac.template.yaml` se siembra en `devops/<carpeta>/account/rbac.yaml`. No es un secreto
ni requiere git check-ignore. Si existe, se anota "existente, sin tocar", sin abrirlo ni
sobrescribirlo. En validar solo se comprueba su existencia con `test -e devops/<carpeta>/account/rbac.yaml || test -L devops/<carpeta>/account/rbac.yaml` y el uso del
ServiceAccount en el Deployment. El usuario aplica RBAC una vez por clúster con
`kubectl apply -f <archivo>` y ajusta los permisos según su clúster; el agente no ejecuta
ese comando. La plantilla concede get/list/watch sobre services, endpoints y pods.


## Cuentas de Jenkins

En la primera generación de artefactos DevOps de cualquier servicio, si el plan lista las rutas,
se siembran `k8s/jenkins-account.template.yaml` como `devops/<carpeta>/account/jenkins-account.yaml`
y `k8s/secret-jenkins-account.template.yaml` como `devops/<carpeta>/account/secrets-jenkins-account.yaml`.
El primero conserva ServiceAccount, Role, RoleBinding, ClusterRole y ClusterRoleBinding del original;
el usuario ajusta los permisos a su clúster. No exige git check-ignore. El segundo es un Secret de
tipo kubernetes.io/service-account-token, con nombre jenkins-token y anotación de la cuenta jenkins,
sin data/stringData ni token. Su creación exige `git check-ignore -q <ruta>` con exit 0;
si no está ignorado, se bloquea el secret con el aviso de gitignore, pero se crea la cuenta aprobada.

Cada archivo existente se anota "existente, sin tocar", sin abrirlo ni sobrescribirlo.
En validar se comprueban ambos solo con `test -e <ruta> || test -L <ruta>`. El usuario aplica estas cuentas una vez por clúster,
obtiene después el token con kubectl, prepara el kubeconfig y crea en Jenkins las credenciales de tipo archivo
con los IDs declarados en `devops.entornos.<nombre>.credencial_kubeconfig`. El agente nunca ejecuta estos pasos ni lee token o kubeconfig.
En Avisos se listan los archivos sembrados que el usuario debe aplicar: RBAC, cuentas de Jenkins,
Secret del token y secrets de base. Las únicas creaciones permitidas en account/ son rbac.yaml,
jenkins-account.yaml, secrets-jenkins-account.yaml y secrets-<base>-<entorno>.yaml,
siempre desde sus plantillas, con autorización del plan y sin sobrescritura.

El pipeline generado vigente es el archivo indicado por `devops.jenkinsfile`. Ante dudas sobre stages, trabaja sobre ese archivo del repositorio.

## Valores por entorno y promoción

`__REPLICAS__`, `__CPU_PETICION__`, `__CPU_LIMITE__`, `__MEMORIA_PETICION__` y `__MEMORIA_LIMITE__` salen de la entrada del entorno. `__NODE_PORT__` usa su base y el puerto efectivo del perfil; el gateway usa `gateway_nodo_puerto`. PV/PVC conservan capacidad y acceso, pero sus nombres y hostPath incluyen el sufijo. RBAC y cuentas de Jenkins conservan sus nombres fijos y el mismo contenido, también con clúster compartido. Nunca se leen cuentas existentes.

El modo `imagen` admite construir o promover; ninguna no es una combinación válida; `desplegar` controla el despliegue. Solo un entorno puede construir. El constructor guarda y reutiliza su tag exacto `X.Y.Z-<sha>`; `git rev-parse --short=7 HEAD` puede alargarlo hasta doce caracteres. El incremento mantiene el acarreo decimal actual: 1.0.9 pasa a 1.1.0. Los tags antiguos sin commit cuentan para numerar, pero no se promueven: cada servicio necesita una imagen nueva desde el entorno constructor.

La promoción recorre todas las páginas del catálogo con page_size=100 y page creciente sobre la misma URL base (máximo 1000 páginas). Un 404 del repositorio en la primera página equivale a catálogo vacío; otros errores se detienen. Ordena numéricamente y elige un commit ancestro de HEAD que contenga el último cambio del servicio, incluida igualdad. Un SHA ausente localmente se salta en un clon completo; un clon superficial o un error de Git se detiene. Revisa todos los tags del número elegido para detectar VERSION_AMBIGUA y no evalúa los inferiores. Sin imagen válida no se despliega. Un cambio solo de manifiestos usa esa misma regla, salvo la migración limitada al constructor descrita abajo. Si solo cambia Dockerfile y falta el stash del JAR, se compila y guarda antes de construir la imagen.

JAVA_OPTS usa porcentajes: 75/37.5 en servicios y 37.5/18.75 en gateway. Cambia con el límite de memoria del entorno, sin editar la imagen por entorno. Dockerfile activa docker y cada deployment añade k8s y su sufijo.


### Migración de tags históricos en el constructor

Solo con imagen: construir, si el servicio no construyó imagen en este build y el catálogo no contiene ningún tag X.Y.Z-sha, un cambio solo de manifiestos puede desplegar el X.Y.Z histórico más alto. Jenkins imprime «MIGRACION: se despliega el tag histórico X; la próxima imagen llevará commit». En cuanto exista algún tag con sha, se aplica la comprobación normal, incluso si ninguno resulta elegible. Con imagen: promover nunca se usa este respaldo: main requiere una imagen nueva con commit de cada servicio antes de su primer despliegue. Los objetos blob/tree que compartan prefijo se ignoran; dos commits con ese prefijo siguen siendo un error.

### Primer build y reconstrucción manual

Sin GIT_PREVIOUS_SUCCESSFUL_COMMIT o GIT_COMMIT, el pipeline lista los archivos
versionados del directorio en HEAD con git ls-tree; no compara con HEAD~1. Aplica
los filtros habituales: .java/.gradle/.yaml y, para imagen/despliegue, Dockerfile.
Un directorio vacío no activa trabajo. Con commit anterior conserva el diff normal;
un cambio solo de README.md ya no compila, analiza ni despliega el servicio, salvo
cambios independientes en sus manifiestos. Sin filtros pasa todo; con filtros basta
una coincidencia de extensión o nombre base, y un filtro ausente no cuenta.

CONSTRUIR_TODO es booleano, false por defecto, y se lee con params. Con true revisa
todos los servicios con esos mismos filtros: en construir compila y publica imágenes
con número nuevo; en promover vuelve a promover y desplegar imágenes elegibles,
sin construir imágenes ni usar tags históricos; en feature/* analiza todos en Sonar.
El despliegue sigue dependiendo de desplegar: true. La compilación Java común sigue
evaluándose en todas las ramas. En multibranch el parámetro aparece en «Build with
Parameters» después del primer build de cada rama. Cada feature/* o PR nueva activa
el listado y la compilación inicial de sus servicios relevantes; Sonar conserva el
when feature/* existente. Hay hasta seis consultas de cambios por servicio, además
de las comprobaciones de historial. ls-tree funciona en clones superficiales, pero
la construcción Docker, migración y promoción siguen exigiendo historial completo.

Sin imagen en construir, el error propone «Build with Parameters» con
CONSTRUIR_TODO=true; el parámetro no repara fuentes, Dockerfile o manifiestos ausentes.
Con código relevante y sin manifiestos, se conserva el fallo «Deployment no encontrado»
con la ruta y la petición de generar o renombrar mediante plan aprobado. En promover,
sin imagen elegible se indica desplegar antes la rama constructora obtenida del mapa
de entornos. Slack anuncia envío solo con canal configurado y conserva los estados
SUCCESS, FAILURE, UNSTABLE y ABORTED con sus colores correspondientes.

El preflight avisa con DEVOPS_VALORES si el Jenkinsfile configurado no contiene
CONSTRUIR_TODO, incluso si es un pipeline original sin marcas. Es una detección mínima:
una cadena en comentarios o una migración parcial no certifican la lógica completa.
Regenerar .agents no actualiza ese archivo. En modo generar, migrar solo los bloques
de detección/filtros, parámetro, errores y Slack exige un plan con su diff aprobado;
conserva getServices(), getEnvironments() y los valores del proyecto.

### Despliegue, base de pruebas y JDK del nodo

Tras `kubectl apply`, el pipeline espera `kubectl rollout status -f <ruta del deployment>` con un
timeout definido en el propio Jenkinsfile, dentro del mismo contexto de credenciales. Si el despliegue
no queda listo, emite diagnóstico con `kubectl get pods -l app=<base>-<sufijo>,tier=application -o wide`
y `kubectl describe -f <ruta del deployment>` (sin mostrar valores de Secret ni usar `logs`, `get secret`
o `describe secret`) y termina con `DESPLIEGUE_NO_LISTO`. Los servicios se despliegan en serie: el tiempo
total es servicios × timeout y un fallo deja sin desplegar los siguientes. El resumen del build distingue Compilados, Analizados, Construidos y Desplegados; cada grupo se registra también con fallos parciales, y muestra «Sin servicios con cambios» solo si no hay ninguno, sin cambiar el resultado.

Antes de compilar o analizar, el pipeline comprueba que `JAVA_HOME` del nodo tenga `javac`; si falta,
falla con `JAVA_HOME_NODO_INVALIDO` indicando el nodo y la clave `devops.java_home_nodo`.

Para los tests del build, `devops.credencial_bd_pruebas` (ID Jenkins «Username with password», o `null`)
inyecta `USER_NAME_DB_<P>` y `PASSWORD_DB_<P>`; el perfil `<P>` sale de `backend.perfil_local` en
mayúsculas (por defecto `feature`). Cuando hay credencial, el nodo de compilación debe definir
`DB_HOST_<P>`, `DB_PORT_<P>` y `DB_NAME_<P>` en el formato que espera la URL del perfil; si falta alguna,
el build falla con `BD_PRUEBAS_INCOMPLETA` nombrando las variables, sin mostrar valores. Sin credencial,
el build se ejecuta sin inyección, como antes. Varios servicios comparten las mismas variables del nodo
(misma base de pruebas por perfil); el aislamiento por servicio queda fuera de alcance.

El catálogo de imágenes de Docker Hub se pagina de forma robusta ante respuestas con `next` nulo o
ausente; un 404 solo en la primera página se trata como servicio nunca publicado.
