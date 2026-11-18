# Decisiones sobre código existente

Antes de aprobar el plan, conserva los recordatorios y avisos del registro obtenidos por el preflight o por `python3 -I -B .agents/scripts/registro-stack.py comprobar`. Cuando conozcas los servicios de la tarea, ejecuta la comprobación de solo lectura con `--servicios` y el nombre de tu workflow mediante `--workflow` para precisar el alcance. Para un cambio pendiente sin decisión vigente, ofrece «sí» (incluirlo en este plan), «no» (registrar esa decisión y recordarla en una línea) y «para revisión» (recordar clave y servicios con opción de aplicarlo después). Ofrece `--completo` si el usuario pide más detalle. Una decisión «no» vigente no se vuelve a proponer. Especifica en el plan el valor canónico, los servicios explícitos, la respuesta, la modificación del registro y, si procede, los archivos de código. Escribe el registro solo tras aprobar el plan; al verificar lo aplicado guarda «aplicado» y conserva la decisión anterior como «sustituido». Los avisos ajenos al alcance de tu workflow se muestran como pendientes; no autorizan reparaciones. Si una fila es inválida, propone corregirla en vez de duplicarla.

El registro vive en `docs/decisiones-stack.md`, versionado fuera de `.agents`; no lo escribe el preflight ni el generador. Inclúyelo en la lista de archivos de approved-plan y comparar-plan.py. Para deshacer un «no», el usuario pide «quiero revisar los cambios registrados» y el plan lo pasa a «para revisión».

Cabecera inicial del archivo:

```markdown
# Decisiones sobre el stack

Este registro conserva decisiones del usuario sobre el código existente para un valor de stack.yaml.
Lo actualiza el agente únicamente dentro de un plan aprobado; no se edita a mano.
El alcance contiene una lista JSON explícita de servicios; «todos» es solo texto mostrado.
«aplicado» y «sustituido» son historial y no evitan nuevas comprobaciones.

| clave | valor | decisión | alcance | fecha |
|---|---|---|---|---|
```

Escalares en forma canónica del lector del stack; listas/mapas como JSON compacto con claves ordenadas. Escapa contrabarras y barras verticales de la columna valor. Fecha AAAA-MM-DD, alcance JSON explícito; `["*"]` identifica solo el hallazgo de proyecto, nunca todos los servicios. No solapes filas vigentes: una fila sin nombres cubre toda la clave/servicio/valor; con nombres, cada nombre solo puede quedar en una fila vigente. Divide el alcance al cambiar solo parte de sus servicios, conservando la decisión de los demás. No marques aplicado sin verificar. Una decisión para otro valor no evita volver a comprobar. No amplíes servicios cubiertos al incorporar uno nuevo.

Las clases y remedios se definen solo en `.agents/config/codigos.yaml`: continúa solo con exit 0, revisa avisos, partes del plan y omitidos; exit 1 detiene salvo la excepción autorizada de preparación; exit 2 exige corregir la invocación. Un control omitido no demuestra que su infraestructura esté disponible. En change-version, los avisos ajenos solo van a pendientes; verifica su documentación propia por servicio, tecnología y versión, dejando lo no atribuible como pendiente. Solo los workflows que resuelven el código pueden incorporarlo al plan aprobado.

En los workflows que escriben servicios (implement-microservice-feature en ambas rutas, incorporate-service, add-authentication y add-user-management), el servicio tocado entra **siempre** en el plan con los perfiles que falten, aunque exista un «no» en el registro. Usa `servicios.py perfiles <servicio>` y crea los archivos desde `application-entorno.template.yaml`; deja en `application.yaml` solo lo compartido y activa `backend.perfil_local`. Si la conexión está escrita en el base, propón sustituirla por variables sin leer ni copiar sus valores. Enumera solo nombres de variables agrupados por entorno: local para exportar en la terminal y, cuando corresponda, Kubernetes para el secret de cada entorno. Para los demás servicios aplica el registro. Repite la comprobación con `--servicios` al fijar el alcance; al cierre E, un servicio tocado sin perfiles bloquea.
<!-- si devops.infraestructura=jenkins-kubernetes -->
Ofrece las diferencias DevOps del registro antes de aprobar esos planes: con «sí», el plan enumera los artefactos para **todos los servicios y el gateway**, y el workflow invoca `devops-engineer` con `modo: generar` después de la escritura y antes de comparar el plan. Incluye cada carpeta de entorno y sus destinos. incorporate-service ofrece esta generación para todos los servicios que aún no tengan los artefactos, además del que incorpora. Las diferencias de valores aprobadas abarcan los artefactos del proyecto; no basta regenerar `.agents`. Los «no» y «para revisión» conservan su alcance explícito por hallazgo.
<!-- fin -->
En change-version, perfiles y DevOps solo se informan con su remedio en pendientes; no se crean perfiles ni se incorporan estas reparaciones a su plan.


La tabla admite cinco columnas o una sexta opcional `nombres`: lista JSON compacta ordenada y sin duplicados. Ausente o [] conserva cobertura de toda la clave; con nombres solo acepta los identificadores señalados para ese valor y alcance. En nomenclatura.clase_aplicacion se guardan las rutas de clases. nomenclatura.estrategia_fisica_jpa se decide por clave entera, sin nombres. Para no o para revisión se recuerdan los nombres aceptados y se comparan los nuevos; el cambio de valor invalida la fila. Varias filas de nombres disjuntos son válidas; no solapes sus nombres ni mezcles una fila parcial con otra de clave completa. Un no_determinable nunca se oculta por la resta de nombres: permanece como aviso. Incluye la escritura del registro en el plan aprobado.

Con autenticación o gestión ninguna, las diferencias se ofrecen como STACK_CODIGO en los workflows E genéricos; no se remite a un workflow add-* no generado.

La aceptación por nombres solo se admite en las comprobaciones declaradas con `"por_nombre": true` en `config/registro-stack.json` (nomenclatura que devuelve nombres concretos). En las demás claves, incluida estrategia_fisica_jpa, usa la fila de cinco columnas o `nombres` vacío. Una lista no vacía produce «fila no válida: <clave> no admite nombres; usa la fila sin la sexta columna» y no cubre la comparación.

La comparación de backend.jdk_ruta_desarrollo se omite con null. Con ruta, ofrece sí/no/para revisión por servicio para escribir solo org.gradle.java.installations.paths con el valor aprobado, sin leer ni mostrar otras propiedades.

<!-- si devops.infraestructura=jenkins-kubernetes -->
Con NOMBRE_JAR como parte del plan, incluye igualar el nombre del JAR a rootProject.name antes de escribir artefactos DevOps. El cierre y la comprobación estricta bloquean si sigue distinto; no se suprime mediante una decisión del registro.
<!-- fin -->
