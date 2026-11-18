# Referencia: cliente de SonarQube

Consulta el esquema vigente con `node .agents/scripts/sonar-mcp.mjs listar`: pagina `tools/list` y muestra solo las herramientas permitidas por este stack. Los esquemas proceden del servidor, no de esta referencia. La conexión usa solo `SONARQUBE_URL` y `SONARQUBE_TOKEN`, obligatorias en el entorno de la herramienta. El kit instala su servidor MCP con `node .agents/scripts/instalar-sonar-mcp.mjs`, previa autorización del usuario para descargarlo en `~/.dotagentskit`; necesita Java ≥ 21 del PATH. `SONARQUBE_MCP_JAR` permite un jar propio y `SONARQUBE_STORAGE_PATH` una carpeta compartida opcional; sin ella cada ejecución tiene almacenamiento exclusivo que se limpia al terminar. No se consulta la configuración de ningún agente. No leas credenciales ni sus valores.

La interfaz es `node .agents/scripts/sonar-mcp.mjs <herramienta> --json '<objeto JSON>'`. Las llamadas usan el cliente propio; no uses el MCP conectado directamente. Salida: una línea JSON, código 0 éxito, 1 error de herramienta sin reintento, 2 bloqueo/infraestructura. Los códigos SONAR_* son del cliente, no del preflight. Si la salida está truncada, usa pageIndex/pageSize cuando el esquema los admita.

## Lecturas permitidas

- `node .agents/scripts/sonar-mcp.mjs search_my_sonarqube_projects --json '{"q":"<projectKey>"}'`: Verificar el proyecto y disponibilidad. Admite pageIndex/pageSize según esquema.
- `node .agents/scripts/sonar-mcp.mjs show_rule --json '{"key":"<ruleKey>"}'`: Detalle completo de una regla bloqueante; --explain del gate ofrece un resumen de 400 caracteres.
- `node .agents/scripts/sonar-mcp.mjs get_project_quality_gate_status --json '{"projectKey":"<projectKey>"}'`: Consulta informativa adicional del último scan; el gate ya informa estado.
- `node .agents/scripts/sonar-mcp.mjs search_sonar_issues_in_projects --json '{"projectKeys":["<projectKey>"]}'`: Issues del último scan, no del diff local; informativo. Usa filtros y paginación según esquema.
- `node .agents/scripts/sonar-mcp.mjs list_quality_gates --json '{}'`: Diagnóstico de disponibilidad.

## Análisis de contenido

`node .agents/scripts/sonar-mcp.mjs analyze_code_snippet --json '{"fileContent":"<contenido>","language":"ts","scope":"MAIN"}'` permite diagnóstico aislado. `fileContent` es obligatorio; `filePath` no existe. `projectKey` es opcional en el esquema; respeta la configuración del proyecto. `scope` distingue MAIN y TEST; no uses codeSnippet en el gate. La aprobación del diff exige `node .agents/scripts/sonar-diff-gate.mjs --explain --recibo OUT_DIR/gate-recibo.json`, que analiza base y actual. La consulta aislada nunca permite aprobar. `analyze_code_snippet` está deprecada: si desaparece, informa bloqueo y detente hasta decisión del usuario.

## Escrituras

`change_sonar_issue_status` y `change_security_hotspot_status`: **solo tras aprobación explícita del usuario**. Primero consulta su esquema con `node .agents/scripts/sonar-mcp.mjs listar`; después ejecuta `node .agents/scripts/sonar-mcp.mjs <herramienta> --json '<objeto JSON conforme al esquema>' --confirmar`. Para issues, el texto de referencia documenta key y status (accept, falsepositive, reopen); comprueba el esquema vigente. No inventes parámetros de hotspots. --confirmar lo escribe el propio agente y no equivale a obtener aprobación: no añadas estas órdenes a una lista de aprobaciones automáticas. Ninguna escritura reintenta; tras timeout pudo aplicarse y se debe comprobar antes de repetir.

## Disponibilidad y almacenamiento

El preflight consulta GET /api/system/status y el canario comprueba análisis; una consulta de proyectos usa el cliente anterior. Si defines `SONARQUBE_STORAGE_PATH` compartida y aparece 90028 o MVStoreException, evita usar esa carpeta a la vez desde varios procesos. Sin esa variable se usa almacenamiento exclusivo por ejecución. No necesitas conservar una entrada MCP en tu agente; no leas configuraciones privadas ni valores de credenciales.

## Herramientas excluidas

No uses analyze_file_list, run_advanced_code_analysis, search_dependency_risks, get_system_status ni ping_system: los textos de esta versión no las exponen. list_branches y list_pull_requests no se usan en Community Build. La lista histórica completa del servidor no es una lista de herramientas autorizadas. El cliente solo permite las documentadas arriba y las dos escrituras con aprobación.
