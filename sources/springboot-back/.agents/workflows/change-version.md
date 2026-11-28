---
description: Planificar y aprobar un cambio coordinado de versión en todos los servicios.
---

# Cambiar una versión del back

Para toda la documentación de este workflow, antes y después de escribir, sigue la regla de ejecución
de `.agents/workflows/preparar-documentacion.md` (una orden que escribe por llamada, esperar y leer
su resultado antes de la siguiente).

1. **Preflight y diagnóstico inicial.**
   - Ejecuta `bash .agents/scripts/preflight.sh --workflow change-version --fase entrada`. Conserva salida y exit: los códigos y clases están en `.agents/config/codigos.yaml`. Exit 1 detiene; PREPARACION solo permite proponer el comando con permiso y repetir, nunca seguir como pendiente. Exit 2 es error de uso. Exit 0 permite elaborar el plan, sin dar por pasados controles omitidos.
   - Ejecuta `node .agents/scripts/inventario-versiones.mjs` y conserva su JSON para la tabla de cambios. No ejecutes Groovy ni resuelvas expresiones fuera del enlace literal local admitido.

2. **Destino desde `stack.yaml` y alcance.**
   - Compara `backend.java` y `backend.spring_boot` de `.agents/stack.yaml` con el inventario del código (`inventario-versiones.mjs`: Java declarada por servicio y Spring Boot/plugins observados).
   - Si difieren, propone por sí solo el cambio hacia lo que dice `stack.yaml`, con tabla antes/después por servicio y artefacto afectado, y pide confirmación. No preguntes la versión destino cuando `stack.yaml` ya la fija.
   - Solo pregunta la versión cuando el usuario quiere cambiar algo que `stack.yaml` no fija (una librería/coordenada concreta) o cuando `stack.yaml` y el código ya coinciden. En ese caso el plan enumera las líneas de `.agents/stack.yaml` que edita el usuario y la escritura espera a que el usuario las edite.
   - Si el usuario no quiere subir el código, la alternativa es que él vuelva `backend.java` y/o `backend.spring_boot` en `.agents/stack.yaml` a la versión del código.
   - `context-analyzer` identifica todos los servicios afectados por la dependencia, plugin, BOM o Java. `spring-architect` prepara un único plan; `microservices-architect` revisa compatibilidad entre servicios cuando corresponda. Alinea todas las versiones compartidas, incluidas pruebas y procesadores.
   - Si la tabla antes/después cambia `backend.java` o el control de versiones bloquea por el wrapper, incluye por servicio el wrapper actual (`gradle_wrapper` del inventario), el destino y el mínimo para ejecutar esa Java según `.agents/config/gradle-java.json`. El destino debe admitir el JDK del nodo y el JDK local que ejecutará Gradle; confirma sus versiones, sin confundirlas con el toolchain. Si Java no figura en la tabla o el wrapper no es resoluble/comparable, declara la limitación y pide al mantenedor que amplíe la tabla o al usuario que confirme la compatibilidad antes de aprobar el destino; no inventes un mínimo.

3. **Plan de documentación y citas (antes de escribir builds).**
   - Sigue la regla de ejecución de `.agents/workflows/preparar-documentacion.md`: una orden que escribe por llamada, espera y lee el resultado antes de seguir.
   - Para las versiones **literales de destino** aprobadas en la tabla (JDK, Spring Boot, plugins y dependencias con versión literal): prepara y carga documentación con `.agents/workflows/preparar-documentacion.md`, invocado con la excepción de change-version (versiones de destino aprobadas, no las del inventario actual) solo para `preparar` y `cargar`, nunca para `asociar`. Todas las URL, asociaciones, archivos y reactivaciones requieren aprobación.
   - Obtén citas de compatibilidad con `python3 -I -B .agents/scripts/documentacion.py preguntar TECNOLOGIA PREGUNTA --version V` y regístralas en el plan como `datos_verificados` (Spring Boot con Java: B14). Si falta concretar una URL, se aprueba como enmienda del mismo plan antes de cargarla.
   - Para Gradle/Java cita `.agents/config/gradle-java.json`: registra en el plan su `fuente`, `verificado` y el mínimo de `minimos` para ejecutar Gradle. Gradle se respalda con esa tabla, sin preparar, cargar ni asociar documentación de Gradle en el catálogo; esta compatibilidad queda exceptuada de la ampliación genérica indicada abajo.
   - Las tecnologías con `bom_propiedad` (Lombok; con gateway, Spring Cloud Gateway) cuya versión real depende del build se documentan **después** de escribir.
<!-- si devops.infraestructura=jenkins-kubernetes -->
     Incluye Spring Cloud Kubernetes cuando se use.
<!-- fin -->
     Usa `python3 -I -B .agents/scripts/documentacion.py resolver-bom --servicio NOMBRE --tecnologia TECNOLOGIA` (NOMBRE exacto del inventario; `.` para raíz si aplica), con red a repo1.maven.org; sin acceso y sin resolución vigente bloquea con BOM_RED. Revisa el diff y repite la orden completa con `--confirmar` tras aprobación. Al cambiar el tren de Spring Cloud hay que repetir `resolver-bom` para las tecnologías con `bom_propiedad` de esa BOM. El comportamiento bom_gestionado sigue usando la versión documental de la propia BOM. El plan declara que esa compatibilidad queda sin cita previa. Si `documentacion.py` responde `REGISTRO_SOLO_LECTURA` (es suyo, no del preflight ni de `config/codigos.yaml`), detente y pide al usuario que dé a la herramienta permiso de escritura sobre `.agents`; no repitas el comando hasta que lo confirme ni edites el registro a mano.
   - Si una compatibilidad no tiene fuente en el catálogo (p. ej. `io.spring.dependency-management` no catalogado), el plan lo dice explícitamente y propone ampliar el catálogo del proyecto (sección «Ampliar» de `preparar-documentacion.md`) o seguir sin cita; decide el usuario.

4. **Plan de cambios y datos de entorno (aprobación previa).**
   - Tabla antes/después de cada cambio de versión, con una columna «Cita» obligatoria por fila, motivos, archivos exactos y pruebas de cada servicio afectado. Formas válidas de «Cita»: la cita de `python3 -I -B .agents/scripts/documentacion.py preguntar` (`datos_verificados`), la entrada de `.agents/config/gradle-java.json` (para Gradle/Java) o «después de escribir» para las tecnologías con `bom_propiedad`. No se pide aprobación del plan mientras haya una fila sin ninguna de ellas.
   - Si se sube el wrapper, enumera por servicio `gradlew`, `gradlew.bat`, `gradle/wrapper/gradle-wrapper.jar` y `gradle/wrapper/gradle-wrapper.properties` entre los archivos a modificar. Incluye la versión destino, su suma SHA-256 publicada y la fuente de esa suma para aprobación, el JDK compatible con el wrapper actual que ejecutará la actualización y el permiso necesario para Gradle y red. Si el JDK local ya es el nuevo y el wrapper actual no lo admite, acuerda primero un JDK compatible para ejecutar el comando.
   - Si cambia Java, lee `backend.jdk_ruta_desarrollo`: con `null` no toques esa propiedad. Con ruta, incluye `python3 -I -B .agents/scripts/servicios.py escribir-jdk-ruta <servicio>...` para los servicios aprobados, sin abrir `gradle.properties`. Si la ruta no contiene la versión nueva, enumera la clave entre las que confirma y edita el usuario y espera antes de escribir. Nunca inventes rutas.
   - Si afecta `backend.java` o `backend.spring_boot` y `stack.yaml` y el código ya coinciden pero el usuario quiere otra versión, el plan enumera las líneas de `.agents/stack.yaml` que editará el usuario. Si `stack.yaml` ya trae el destino, no hay líneas que editar. Ningún agente edita el stack.
<!-- si devops.infraestructura=jenkins-kubernetes -->
   - Si cambia Java, el mismo plan enumera también `devops.java_home_nodo`, `devops.java_home_contenedor` y `devops.jdk_url`, con valores que confirma y edita el usuario. Incluye Dockerfile, Jenkinsfile y demás artefactos DevOps existentes que dependan de esas claves. Propón como `java_home_contenedor` la carpeta que crea el tar de `jdk_url` bajo `/opt/` (por ejemplo `/opt/jdk-27.0.1.0.3`) y pide confirmación; si el nombre no permite saber la carpeta, pregunta, sin descargar ni inventarla. No inventes instalaciones del nodo ni descargas. `devops-engineer` propone los cambios de artefactos dentro del mismo alcance aprobado. No leas secretos, account/ ni kubeconfig y no apliques manifiestos.
   - Antes de pedir aprobación ejecuta `python3 -I -B .agents/scripts/servicios.py entornos` y `python3 -I -B .agents/scripts/servicios.py validar-entornos`. Si `validar-entornos` falla por datos de un servicio (puerto no resoluble o varios puertos distintos), repórtalo con el remedio indicado por el script y **sigue**: inclúyelo en la lista de pendientes del plan (dentro de este bloque marcado) sin intentar arreglarlo ni bloquear el flujo de change-version por ello.
<!-- fin -->
   - Incluye la documentación de la nueva versión, los vínculos de cada servicio y qué notebooks anteriores podrán archivarse cuando no tengan usuarios.
   - **Perfiles (antes de pedir permiso para Gradle):** ejecuta `python3 -I -B .agents/scripts/servicios.py perfiles` por servicio afectado. Informa perfil activo, existencia de su archivo y **nombres** de variables que necesita (sin valores). Consulta `perfiles[].nombre`, `perfiles[].existe` y `perfiles[].variables`, y muestra también `esperados[]` y `faltan[]`. Si falta un archivo esperado, dilo; no crees perfiles. Si `spring.profiles.active` es variable de entorno o faltan datos, dilo como no determinable/limitación y no lo atribuyas a versiones. Esto no bloquea el cambio de versiones: va a pendientes con remedio cuando corresponda.
   - Al pedir permiso para Gradle indica el perfil activo detectado, los nombres de variables requeridas y que el usuario debe exportarlas o acepte que las pruebas de contexto fallen por entorno.

5. **Aprobación.** Pide aprobación del plan completo antes de escribir. Si el usuario debe editar `stack.yaml` (caso donde no coincidían y eligió otra versión, o librería no fijada por stack), espera esas ediciones del usuario antes de escribir.

6. **Escritura (solo lo aprobado).**
   - `file-writer` cambia únicamente los builds y artefactos aprobados. No cambia versiones ajenas ni resuelve conflictos por su cuenta.
   - Si cambió Java, ejecuta `python3 -I -B .agents/scripts/servicios.py escribir-jdk-ruta <servicio>...` solo para los servicios del plan; usa la ruta aprobada y con `null` no escribe. No abras `gradle.properties` ni reproduzcas sus otras líneas; si el comando rechaza una continuación, informa el motivo y espera su corrección aprobada.
   - Para cada subida de wrapper aprobada, desde la carpeta del servicio ejecuta `./gradlew wrapper --gradle-version <X> --gradle-distribution-sha256-sum <suma publicada>`, con permiso del usuario para Gradle y red y usando el JDK aprobado que admite el wrapper actual. Incluye en la revisión los cuatro archivos del wrapper enumerados en el plan; no sustituyas la suma publicada por una calculada sobre una descarga sin verificar.

7. **Documentación posterior y asociación.**
   - Sigue la regla de ejecución de `.agents/workflows/preparar-documentacion.md`: una orden que escribe por llamada, espera y lee el resultado antes de seguir.
   - Ejecuta la preparación/carga aprobada que falte tras escribir, incluido `resolver-bom` y documentación de las tecnologías con `bom_propiedad` (Lombok; con gateway, Spring Cloud Gateway).
<!-- si devops.infraestructura=jenkins-kubernetes -->
     Incluye Spring Cloud Kubernetes cuando se use.
<!-- fin -->
     Al cambiar el tren de Spring Cloud, repite `resolver-bom` para las tecnologías con `bom_propiedad` de esa BOM. Asocia los servicios a los notebooks nuevos y archiva solo los anteriores sin usuarios, con confirmación. Reutiliza los archivados si se vuelve atrás. Conserva JSON, Markdown y salidas literales del script. Si `documentacion.py` responde `REGISTRO_SOLO_LECTURA` (es suyo, no del preflight ni de `config/codigos.yaml`), detente y pide al usuario que dé a la herramienta permiso de escritura sobre `.agents`; no repitas el comando hasta que lo confirme ni edites el registro a mano.

8. **Verificación propia (solo lo de change-version).**
   - Comprobación estática de Java compartida: `node .agents/scripts/comprobar-versiones.mjs` (Spring Boot y Java, incluyendo `JavaLanguageVersion` = `backend.java` y rutas de `installations.paths` con `bin/javac`).
   - El mismo control debe dar `OK` para el wrapper de cada servicio afectado frente al mínimo de `.agents/config/gradle-java.json`; un aviso de versión no resoluble, no comparable o Java fuera de tabla no acredita esa compatibilidad. Comprueba además que el wrapper nuevo admite tanto el JDK del nodo como el local con los que se ejecutará Gradle; con permiso, verifica su ejecución en los entornos disponibles y deja explícita la comprobación del nodo que deba hacer el usuario si no está accesible desde aquí.
   - `node .agents/scripts/comparar-versiones.mjs`
   - `./gradlew compileJava compileTestJava` en cada servicio afectado, **con permiso del usuario**.
   - `python3 -I -B .agents/scripts/comprobar-documentacion.py` (estricto, sin argumentos). Para el éxito de change-version solo cuentan las líneas propias de las tecnologías/servicios cambiados, incluidas las tecnologías con `bom_propiedad` (Lombok; con gateway, Spring Cloud Gateway) resueltas por BOM.
<!-- si devops.infraestructura=jenkins-kubernetes -->
     Incluye Spring Cloud Kubernetes cuando se use.
<!-- fin -->
     Si cambió el tren de Spring Cloud, exige haber repetido `resolver-bom` de las tecnologías con `bom_propiedad` de esa BOM. El resto se lista en pendientes (una línea que no encaje en el formato se trata como pendiente, nunca como éxito).
   - **Pruebas completas: opcionales.** Si el usuario las pide, ejecútalas con permiso. Si fallan por entorno (BD, perfil, variables), repórtalas aparte; el workflow no falla por ello.

9. **Cierre (sin `preflight.sh`).**
   - No ejecutes `bash .agents/scripts/preflight.sh`.
   - Indica al usuario: «Haz commit de los cambios y ejecuta `bash .agents/scripts/preflight.sh`» como paso suyo.
   - Muestra versiones finales, estado de las comprobaciones propias, y la lista de pendientes con su remedio (preparación si no se hizo, perfiles/puertos/`validar-entornos` ajenos si fallaron, documentación ajena no cubierta, pruebas omitidas o fallidas por entorno, etc.). Nunca muestres credenciales ni valores de variables.

<!-- si devops.infraestructura=jenkins-kubernetes -->
## Entornos del plan aprobado

Antes de pedir aprobación, ejecuta `python3 -I -B .agents/scripts/servicios.py entornos` y `validar-entornos`. Enumera la tabla completa de `devops.entornos` para el pipeline. Solo para entradas con `desplegar: true`, enumera los datos de destino: carpeta, rama, sufijo, credencial_kubeconfig (solo ID), imagen, desplegar, puerto efectivo, nodePort, réplicas, recursos y los perfiles y artefactos que se crearán o modificarán. Los nombres de carpeta son libres y no se obtienen de la rama. El gateway usa gateway_nodo_puerto; sus perfiles llevan sufijo, CORS e issuer públicos de cada entorno y mantienen los valores globales en local.

Si el proyecto solo tiene una carpeta, lista las que faltan para aprobación; no alteres un entorno existente fuera del plan. Para migrar el Jenkinsfile existente, incluye su diff aprobado de lógica y mapa de entornos; no lo reemplaces automáticamente. RBAC y cuentas de Jenkins mantienen nombres fijos y contenido idéntico si comparten clúster; nunca leas los archivos existentes de account/. Las nuevas cuentas y Secrets vacíos requieren sus rutas aprobadas por carpeta y las comprobaciones de ausencia e ignore vigentes.

Con modo generar, DevOps corre después de la escritura exitosa y antes de comparar-plan.py, git add -N, git diff HEAD, pruebas, gate y revisión. Lo activa el plan aunque el diff previo no tocara DevOps. Un fallo de artefactos vuelve a DevOps con feedback.md (máximo dos intentos); solo codigo_diff vuelve a escritura. En la revisión posterior se invoca modo validar. La fase de revisión de todo el diff se asigna a `.agents/skills/code-reviewer/SKILL.md`, cuyo gate es `node .agents/scripts/sonar-diff-gate.mjs` (análisis por MCP, sin subir análisis al servidor); el orquestador acepta `APPROVED` o `APPROVED WITH RECOMMENDATIONS` solo tras `node .agents/scripts/sonar-diff-gate.mjs --comprobar-recibo RUN_DIR/gate-recibo.json` y, si falla, repite la revisión sin consumir iteración. No se ejecuta `./gradlew sonar` en ningún paso: el análisis en el servidor lo hace el pipeline. Con modo validar inicial se conservan la comparación temprana y la condición posterior del diff.
<!-- fin -->

Antes de aprobar cualquier plan, sigue `.agents/workflows/references/decisiones-stack.md`; consulta clases, remedios y códigos que resuelve este workflow en `.agents/config/codigos.yaml`.

Los avisos DevOps del registro solo van a pendientes con su remedio; este workflow no los incorpora al plan.
