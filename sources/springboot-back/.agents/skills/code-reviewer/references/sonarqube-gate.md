# SonarQube Compliance (Backend)

- **Instancia**: lee la versión viva de SonarQube de `GET /api/system/status` (no requiere autenticación). Si la instancia cambia de versión o de modo, la caché de análisis base se invalida sola (su clave incluye la versión) y debes repetir la calibración antes de confiar en el gate: ejecuta el canario y revisa la lista de exclusión de este archivo.

<!-- si devops.infraestructura=jenkins-kubernetes -->
- **Dos niveles de gate, no equivalentes**:
  1. **Nivel local (diferencial)**: Compara, fichero a fichero, el análisis de la versión base contra el del working tree (ver "Regla de bloqueo"). Es **necesario pero no suficiente**.
  2. **Nivel CI/CD (autoritativo)**: el archivo indicado por `devops.jenkinsfile` ejecuta `./gradlew compileJava sonar` en las ramas `feature/*` y después `waitForQualityGate`; **si el estado no es `OK`, el build falla**. Si el Quality Gate asignado tiene `new_violations > 0` como condición de error, cualquier issue nuevo, de cualquier severidad, rompe el CI. Este nivel no se duplica ni se reemplaza desde el agente.
<!-- si devops.infraestructura=ninguna -->
- **Único nivel de gate: local (diferencial)**. Compara, fichero a fichero, el análisis de la versión base contra el del working tree (ver "Regla de bloqueo").
<!-- fin -->

<!-- si devops.infraestructura=jenkins-kubernetes -->
- **Alcance del gate local** (declararlo siempre en el informe, sin afirmar la causa ni dar porcentajes): *"El análisis por fichero no garantiza cubrir todas las reglas del servidor. El Quality Gate del CI puede fallar aunque este gate pase."*
<!-- si devops.infraestructura=ninguna -->
- **Alcance del gate local** (declararlo siempre en el informe, sin afirmar la causa ni dar porcentajes): *"El análisis por fichero no garantiza cubrir todas las reglas del servidor."*
<!-- fin -->

<!-- si backend.persistencia=jpa -->
- **Hueco comprobado en SQL dinámico (`java:S2077`)**: sobre seis variantes de SQL construido por concatenación o formato, `analyze_code_snippet` solo detectó la que usa `java.sql.Statement` (tipo del JDK). **No detectó** `EntityManager.createNativeQuery`, `EntityManager.createQuery`, `JdbcTemplate.queryForList` ni `String.format` seguido de `createNativeQuery`. Subraya esta limitación al revisar SQL dinámico en JPA/Spring. Por eso el gate incluye el complemento de abajo.
<!-- si backend.persistencia=jdbc -->
- **Hueco comprobado en SQL dinámico (`java:S2077`)**: sobre seis variantes de SQL construido por concatenación o formato, `analyze_code_snippet` solo detectó la que usa `java.sql.Statement` (tipo del JDK). **No detectó** `EntityManager.createNativeQuery`, `EntityManager.createQuery`, `JdbcTemplate.queryForList` ni `String.format` seguido de `createNativeQuery`. Por eso el gate incluye el complemento de abajo.
<!-- fin -->

- **Precondición de disponibilidad y canario**: La verificación previa del entorno (`preflight.sh`), disponibilidad mediante `node .agents/scripts/sonar-mcp.mjs search_my_sonarqube_projects` y el canario (`CanarySqli.java` esperando `java:S2077`) se ejecutan como precondición antes de iniciar la revisión. Si el MCP falla posteriormente durante la revisión, se refleja con `BLOCKED (infraestructura)`; no se reintenta vía reescritura de código porque reescribir código no arregla un servidor caído. Si el error indica que el servidor MCP de SonarQube no pudo iniciar su análisis, revisa `<SONARQUBE_STORAGE_PATH o la carpeta de almacenamiento del MCP>/logs/mcp.log`; si muestra `90028` o `MVStoreException` en `h2/sq-ide.mv.db`, si defines `SONARQUBE_STORAGE_PATH` compartida, evita usarla a la vez desde varios procesos y vuelve a intentarlo. Sin esa variable, cada ejecución tiene almacenamiento exclusivo que se limpia al terminar.

- **Qué se analiza**: la lista de `bash .agents/scripts/touched-files.sh` (JSON; un elemento por `.java` tocado bajo `<servicio>/src/{main,test}/java/`). Detecta nuevos, modificados y renombrados aunque el usuario no haya hecho `git add`, y **el propio script** omite los ficheros cuyo contenido no cambió (cambios de solo modo y renombrados puros dentro del mismo scope; un renombrado que cambia de `main` a `test` sí se emite). La base es `git.rama_base` de `.agents/stack.yaml` (o `--base <ref>`): el `merge-base` de HEAD con esa referencia; si es `null`, el propio `HEAD`. Si el script termina con código 2, el veredicto es `BLOCKED (infraestructura)`.

- **Cómo se ejecuta la regla de bloqueo**: `node .agents/scripts/sonar-diff-gate.mjs` (opcional `--explain`, que añade `show_rule` de cada regla nueva). El script implementa el algoritmo de abajo, que es su especificación: arranca por su cuenta el servidor MCP de SonarQube (conexión: jar del kit, Java ≥ 21 del PATH, `SONARQUBE_URL` y `SONARQUBE_TOKEN` obligatorias; `SONARQUBE_MCP_JAR` y `SONARQUBE_STORAGE_PATH` opcionales; no lee configuraciones de agentes; `--resolver-config` imprime solo `{ jar: "SONARQUBE_MCP_JAR"|"kit", url: "SONARQUBE_URL", token: "SONARQUBE_TOKEN", storage: "SONARQUBE_STORAGE_PATH"|"por ejecución", java: <versión mayor> }`, sin valores de conexión), llama a `analyze_code_snippet` y devuelve JSON. Códigos de salida: `0` = PASA, `1` = BLOQUEA (hay issues nuevos), `2` = `BLOCKED (infraestructura)`. Si el script no puede ejecutarse, el veredicto es `BLOCKED (infraestructura)`: la vía manual por MCP sin script no permite aprobar. El script habilita la caché por sí solo (no hace falta ejecutar antes `touched-files.sh --ensure-cache`), usa **su propio** servidor MCP —independiente del MCP conectado a la sesión del agente, que puede estar caído sin afectarle— e imprime además una línea de resumen por stderr; el JSON va por stdout y trae `qualityGate` (informativo) por proyecto. La revisión ejecuta el gate con `--recibo OUT_DIR/gate-recibo.json`; el recibo se comprueba después con `node .agents/scripts/sonar-diff-gate.mjs --comprobar-recibo OUT_DIR/gate-recibo.json` (misma base).

- **Regla de bloqueo (diferencial)**. Para cada elemento de la lista:
  1. Fija el contexto de análisis una vez y úsalo **idéntico** en las dos llamadas: `projectKey` (ver más abajo), `scope` (el de `ruta`, es decir, el de la ruta **nueva**) y `language: "java"`.
  2. **A** = `analyze_code_snippet` sobre el contenido base (`git show <blobBase>`). Si `estado` es `nuevo`, A está vacío.
  3. **B** = `analyze_code_snippet` sobre el contenido actual del working tree.
  4. Descarta de A y B las reglas de la lista de exclusión.
  5. Clave de cada issue = `(ruleKey, primaryMessage normalizado)`, **sin línea**. Normaliza reemplazando cada texto entre comillas dobles por `"_"` (los mensajes incrustan identificadores: renombrar una variable cambiaría la clave sin cambiar el defecto). Cuenta la multiplicidad.
  6. Issues nuevos = multiconjunto `B − A`.
  7. **Si hay cualquier issue nuevo, de cualquier severidad, bloquea.** La severidad solo ordena el informe. Se aplica igual a `MAIN` y a `TEST`: el servidor indexa los tests y sus issues cuentan para `new_violations`. Ojo: el conjunto de reglas de `TEST` es distinto — `java:S106` (`System.out`) no se reporta en `TEST`, así que un `println` en un test **no** bloquea; sí bloquean, por ejemplo, las variables sin usar.
  - Un issue preexistente en A no bloquea aunque el fichero se toque. Limitación aceptada: si un cambio elimina un issue y añade otro con la misma clave normalizada, el neto es cero y pasa.
  - **Caché de A**: clave `(blobBase, scope, projectKey, versionServidorSonar, versionJarMcp)` en `.agents/.cache/sonar-base/`, que solo se crea con `bash .agents/scripts/touched-files.sh --ensure-cache` (se niega si git no ignora ese directorio). En cada vuelta del ciclo de corrección solo se recalcula B. Es seguro ante un rebase porque `blobBase` es el hash del contenido.

- **Complemento determinista: SQL construido por concatenación** (cubre el hueco anterior). Ejecuta `node .agents/scripts/sql-concat-scan.mjs` (lee `touched-files.sh`, compara base y actual, imprime JSON). Código de salida `1` = hay líneas **nuevas** con un literal de forma SQL unido por `+` a una expresión no literal, o con `String.format`/`.formatted`: **bloquea** igual que un issue nuevo de SonarQube (`CHANGES REQUIRED`, remedio: parámetros con nombre o Query Methods). Código `2` = `BLOCKED (infraestructura)`. Es heurístico y **no es una cobertura completa de inyección SQL**. Marca una línea nueva si tiene un literal SQL completo (`select…from`, `insert into`, `update…set`, `delete from`, `call x(`, `where col =`) unido por `+` a una expresión no literal en esa línea o en las 2 siguientes, o formateado con `String.format`/`.formatted` (incluye multilínea y *text blocks*); o si tiene un fragmento de cláusula (`" AND col = "`, `" ORDER BY "`, `" LIMIT "`) unido por `+` en esa misma línea. Las constantes `UPPER_SNAKE` no cuentan como operando variable. **No detecta** SQL montado con `StringBuilder.append`/`StringJoiner`, ni un literal SQL completo separado de su concatenación por más de 2 líneas cuando esa línea no lleva un fragmento de cláusula, ni un fragmento que no empiece por una cláusula (`q += col + " = " + v`). Puede marcar por error una constante que no siga `UPPER_SNAKE` de 3 o más caracteres. Un cambio CRLF↔LF no genera hallazgos. Si renombras la variable de una línea vulnerable preexistente se vuelve a marcar (error del lado seguro). Tu revisión de la diff sigue siendo obligatoria.

- **Lista de exclusión**. Ampliarla exige evidencia: aparición en ≥ 3 ficheros reales **sin otros hallazgos**, con el mismo mensaje. Es una decisión deliberada, no un accidente: una regla que apareciera siempre junto a un defecto real no se distinguiría de ese defecto, así que no puede excluirse sin ocultarlo.
  - `java:S1598` ("File path "" should match package name"): artefacto de analizar contenido sin ruta.
  - `java:S1220` ("Move this file to a named package"): solo en el canario, que carece de `package`. En un fichero real sin `package` es un defecto legítimo y **no** se excluye.

- **Resolución de `projectKey` y `scope`** (mapa global, una vez por ejecución):
  - Un `-Dsonar.projectKey` en el Jenkinsfile configurado impide determinar la clave estáticamente: se analiza sin `projectKey` y se informa el motivo.
  - Una propiedad fuera del repositorio puede cambiar la clave efectiva de Sonar; este cálculo no la ve. Nunca se lee ~/.gradle/gradle.properties.
  - `projectKey` se obtiene con una única llamada `python3 -I -B .agents/scripts/servicios.py nombres` por ejecución y un mapa por carpeta: systemProp.sonar.projectKey del servicio tiene prioridad sobre el literal del bloque sonar/sonarqube del build, después group:rootProject.name y, sin group, rootProject.name. Se usa si aparece en search_my_sonarqube_projects. Si falta el proyecto, se analiza sin projectKey y se informa omitido (sin proyecto Sonar); si la clave es no_determinable, también se analiza sin projectKey pero se informa omitido (clave Sonar no determinable: <motivo>) y QG N/A con ese motivo. Un fallo global de nombres es BLOCKED (infraestructura), exit 2.
  - Si un fichero se movió a otro servicio, usa el `servicio` del destino para A y B.

- **Quality Gate del servidor: informativo.** El estado del gate se registra en el informe; para una consulta adicional usa `node .agents/scripts/sonar-mcp.mjs get_project_quality_gate_status --json '{"projectKey":"<projectKey>"}'`, pero no sustituye al diferencial: refleja el último scan publicado del proyecto.
<!-- si devops.infraestructura=jenkins-kubernetes -->
  - **AVISO CI de cobertura**: comprueba el Quality Gate asignado al servicio y la configuración de JaCoCo. Si exige cobertura nueva mínima y no hay JaCoCo configurado, advierte en el informe de que el stage Quality Gate del CI puede fallar si el cambio añade líneas cubribles. Quien cambie el Quality Gate asignado a un proyecto, cree un proyecto en Sonar o añada JaCoCo debe reverificarlo en ese mismo cambio (`GET /api/qualitygates/get_by_project?project=<projectKey del servicio>` y `GET /api/qualitygates/show?name=<gate>`, con el token tomado de `$SONARQUBE_TOKEN`, nunca escrito en un fichero). Comprueba también si `sonar.qualitygate.ignoreSmallChanges` exime los cambios pequeños de las condiciones de cobertura.
<!-- fin -->

- **Herramientas, en orden de uso** (detalle de parámetros en `references/sonarqube-tools.md`, cárgalo solo ante ambigüedad):
  1. `node .agents/scripts/sonar-mcp.mjs search_my_sonarqube_projects --json '{"q":"<projectKey>"}'` — resolver `projectKey`.
  2. El gate ejecuta `analyze_code_snippet` en base y actual. Para diagnóstico aislado, usa `node .agents/scripts/sonar-mcp.mjs analyze_code_snippet --json '{"fileContent":"<contenido>","language":"java","scope":"MAIN"}'`; nunca sustituye al gate para aprobar.
  3. `node .agents/scripts/sonar-mcp.mjs show_rule --json '{"key":"<ruleKey>"}'` para el detalle completo; `--explain` del gate ya resume cada regla nueva.
  4. `node .agents/scripts/sonar-mcp.mjs get_project_quality_gate_status --json '{"projectKey":"<projectKey>"}'` — consulta adicional solo informativa; el gate ya informa estado.
  - Comprueba las herramientas disponibles mediante `node .agents/scripts/sonar-mcp.mjs listar`; no presupongas que existen `analyze_file_list` ni `run_advanced_code_analysis`. No uses herramientas de ramas o PR si la edición del servidor no ofrece esos análisis.
  - `change_sonar_issue_status` y `change_security_hotspot_status`: solo tras aprobación explícita del usuario, mediante `node .agents/scripts/sonar-mcp.mjs <herramienta> --json '<objeto JSON conforme al esquema>' --confirmar`. Consulta el esquema con `node .agents/scripts/sonar-mcp.mjs listar`.

- **Contingencia — disponibilidad de `analyze_code_snippet`.** Si el servidor MCP anuncia su deprecación, no sustituyas el gate por otra herramienta sin validar su comportamiento. Si la herramienta desaparece, el canario falla con `BLOCKED (infraestructura): MCP SonarQube no responde / herramienta inexistente` y el flujo se detiene hasta que el usuario decida. No actualices el JAR del MCP (`sonarqube-mcp-server`) sin repetir el canario y la calibración.

- **Resultado normalizado obligatorio**:

  | Campo | Contenido |
  |-------|-----------|
  | `projectKey` por servicio | El key usado, `omitido (sin proyecto Sonar)` o `omitido (clave Sonar no determinable: <motivo>)`; y cómo se resolvió |
  | Base | `merge-base` (sha) y la referencia usada |
  | Por fichero | `estado`, `scope`, ruta (y ruta antigua si renombrado) |
  | Conteo por regla | `ruleKey: antes N → ahora M → +K` para cada regla con issues nuevos, de modo que un bloqueo por multiplicidad no parezca arbitrario |
  | SQL por concatenación | Salida de `sql-concat-scan.mjs`: `Ninguno` o lista (`ruta:línea`, texto) |
  | Issues nuevos | Lista con `ruleKey`, `impacts`, línea (si hay `textRange`), mensaje y explicación de `show_rule` |
  | Quality Gate (informativo) | `OK` / `ERROR` / `WARN` / `NONE` / `N/A (sin proyecto Sonar)` / `N/A (clave Sonar no determinable: <motivo>)` |
  | Alcance | La línea fija de "Alcance del gate local" |
<!-- si devops.infraestructura=jenkins-kubernetes -->
  | AVISO CI | Solo si aplica (cobertura) |
<!-- fin -->
  | Veredicto SonarQube | `PASA` / `BLOQUEA` / `BLOCKED (infraestructura)` |


### Regla S1135 y comentarios en español

La regla `S1135` puede detectar la palabra española `todo` en comentarios como un TODO. Reformula ese comentario con una descripción concreta; no excluyas ni desactives la regla.
