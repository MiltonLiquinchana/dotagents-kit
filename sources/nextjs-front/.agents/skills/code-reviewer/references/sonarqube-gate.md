# Static Analysis Gate (Frontend)

> [!NOTE]
> El gate pre-commit tiene tres capas deterministas y una informativa. ESLint, SonarQube
> (diferencial) y el escáner de seguridad son bloqueantes; el Quality Gate del servidor es
> informativo mientras no exista un pipeline. Todas las bloqueantes son precondición del
> entorno antes de iniciar cambios.

## Infraestructura

- **Instancia SonarQube**: la versión viva se lee de `GET /api/system/status` (no requiere autenticación). Si la instancia cambia de
  versión o de modo, la caché de análisis base se invalida sola (su clave incluye la versión) y
  debes repetir la calibración antes de confiar en el gate: ejecuta el canario y revisa la lista
  de exclusión de este archivo.
- `projectKey`: el valor `sonarqube.project_key` de `.agents/stack.yaml` (registrado en el
  servidor). La descripción del proyecto reside en `.agents/rules/project.md`.
- **CI/CD**: el Quality Gate del servidor y `search_sonar_issues_in_projects` son informativos
  para este gate local. Si el proyecto dispone de un pipeline con análisis SonarQube, conserva
  también sus controles: el gate local es necesario pero no suficiente. No presupongas que el
  servidor tiene un scan publicado ni un estado concreto del Quality Gate.
- **`analyze_code_snippet`**: comprueba su disponibilidad con el canario y consulta las herramientas
  mediante `node .agents/scripts/sonar-mcp.mjs listar`. No presupongas que existen
  `analyze_file_list` ni `run_advanced_code_analysis`. Si `analyze_code_snippet` desaparece,
  el canario falla con `BLOCKED (infraestructura)` y el flujo se detiene hasta que el usuario
  decida. No actualices el JAR del MCP sin repetir el canario y la calibración.

> [!CAUTION]
> Nunca escribir el token de SonarQube en texto plano en comandos, archivos de configuración ni
> mensajes. Usar siempre `$SONARQUBE_TOKEN`.

---

## Precondición de disponibilidad y canario

La verificación de entorno determinista, la comprobación de existencia del proyecto en SonarQube y el canario (`node .agents/scripts/sonar-diff-gate.mjs --canary`, esperando `typescript:S1523`) se ejecutan como precondición antes de iniciar la revisión. Si el MCP falla posteriormente durante la revisión, se refleja con `BLOCKED (infraestructura)`; no se reintenta vía reescritura de código porque reescribir código no arregla un servidor caído. Si el error indica que el servidor MCP de SonarQube no pudo iniciar su análisis, revisa `<SONARQUBE_STORAGE_PATH o la carpeta de almacenamiento del MCP>/logs/mcp.log`; si muestra `90028` o `MVStoreException` en `h2/sq-ide.mv.db`, cierra las herramientas que usan el MCP, renombra ese archivo y vuelve a intentarlo.

---

## Gate pre-commit (ficheros `.ts`/`.tsx`/`.mts`/`.cts` tocados)

**Qué se analiza**: la lista de `bash .agents/scripts/touched-files.sh` (JSON; un elemento por
`.ts`/`.tsx`/`.mts`/`.cts` tocado (los `.mts`/`.cts` se analizan como `ts`; p. ej. `vitest.config.mts`), excluidos `.d.ts`, `.agents/`, `knowledge-base/`, `node_modules/`, `.next/`
y `graphify-out/`). La base es `HEAD`: el flujo exige árbol limpio al inicio y comitea una sola
vez al final, así que `HEAD` es exactamente el estado previo a la feature. Detecta nuevos,
modificados y renombrados aunque el usuario no haya hecho `git add`, y el propio script omite los
ficheros cuyo contenido no cambió (cambios de solo modo y renombrados puros dentro del mismo
scope y lenguaje). Si el script termina con código 2, el veredicto es `BLOCKED (infraestructura)`.

### Capa 1 — ESLint (determinista, costo 0 tokens)

Ejecuta `.agents/scripts/lint-touched.sh`. Solo bloquean errores en **líneas nuevas o modificadas**
del diff (evita heredar los problemas preexistentes). Reglas activas en
`eslint.agent.config.mjs` (solo core ESLint, sin dependencias nuevas): `no-eval`,
`no-implied-eval`, `no-new-func`, `no-debugger`, `complexity ≤ 10`. `eslint-config-next` ya
aporta `@typescript-eslint/parser`. Cubre `eval("literal estático")`, que SonarQube S1523 no
marca (solo marca flujo dinámico).

### Capa 2 — SonarQube `analyze_code_snippet` (diferencial)

**Cómo se ejecuta**: `node .agents/scripts/sonar-diff-gate.mjs` (opcional `--explain`, que añade `show_rule` de cada regla nueva). El script implementa el algoritmo de abajo, que es su especificación: arranca por su cuenta el servidor MCP de SonarQube (configuración: el nombre del servidor sale de `mcp.sonarqube` de `.agents/stack.yaml`; búsqueda en este orden —variables de entorno `SONARQUBE_MCP_JAR`/`SONARQUBE_URL`/`SONARQUBE_TOKEN`, `SONARQUBE_MCP_CONFIG`, o los archivos de las herramientas `~/.claude.json`, `~/.gemini/config/mcp_config.json`, `~/.gemini/antigravity/mcp_config.json`, `~/.config/opencode/opencode.json`, `~/.config/Code/User/mcp.json` y `~/.codex/config.toml`, buscando el servidor `<mcp.sonarqube>`; `--resolver-config` imprime solo de qué archivo y con qué nombre resolvió; nunca se imprime ni se escribe el token), llama a `analyze_code_snippet` y devuelve JSON. Códigos de salida: `0` = PASA, `1` = BLOQUEA (hay issues nuevos), `2` = `BLOCKED (infraestructura)`. Si el script no puede ejecutarse, el veredicto es `BLOCKED (infraestructura)`: la vía manual por MCP sin script no permite aprobar. El script habilita la caché por sí solo (no hace falta ejecutar antes `touched-files.sh --ensure-cache`), usa **su propio** servidor MCP —independiente del MCP conectado a la sesión del agente, que puede estar caído sin afectarle— e imprime además una línea de resumen por stderr; el JSON va por stdout y trae `qualityGate` (informativo) por proyecto. La revisión ejecuta el gate con `--recibo OUT_DIR/gate-recibo.json`; el recibo se comprueba después con `node .agents/scripts/sonar-diff-gate.mjs --comprobar-recibo OUT_DIR/gate-recibo.json` (misma base).

Algoritmo — para cada elemento de la lista de `touched-files.sh`:

1. Fija el contexto de análisis una vez y úsalo **idéntico** en las dos llamadas: `projectKey`,
   `scope` (el de `ruta`, es decir, el de la ruta **nueva**) y `language` (el de la entrada:
   `ts` o `tsx`).
2. **A** = `analyze_code_snippet` sobre el contenido base (`git cat-file -p <blobBase>`). Si
   `estado` es `nuevo`, A está vacío.
3. **B** = `analyze_code_snippet` sobre el contenido actual del working tree.
4. Descarta de A y B las reglas de la lista de exclusión.
5. Clave de cada issue = `(ruleKey, primaryMessage normalizado)`, **sin línea**. Normaliza
   reemplazando cada texto entre comillas dobles por `"_"` (los mensajes incrustan identificadores:
   renombrar una variable cambiaría la clave sin cambiar el defecto). Cuenta la multiplicidad.
6. Issues nuevos = multiconjunto `B − A`.
7. **Si hay cualquier issue nuevo, de cualquier severidad, bloquea.** La severidad solo ordena el
   informe. Se aplica igual a `MAIN` y a `TEST`.

- Un issue preexistente en A no bloquea aunque el fichero se toque. Limitación aceptada: si un
  cambio elimina un issue y añade otro con la misma clave normalizada, el neto es cero y pasa.
- **Caché de A**: clave `(blobBase, scope, language, projectKey, versionServidorSonar,
  versionJarMcp)` en `.agents/.cache/sonar-base/`, que solo se crea con
  `bash .agents/scripts/touched-files.sh --ensure-cache` (se niega si git no ignora ese
  directorio; está en `.gitignore`). En cada vuelta del ciclo de corrección solo se recalcula B.
  Es seguro ante un rebase porque `blobBase` es el hash del contenido.
- **Comprobación del diferencial**: verifica que un cambio inocuo conserve el conteo de issues
  preexistentes y que añadir defectos produzca issues nuevos; en una segunda ejecución, comprueba
  que A se reutilice desde la caché.
- **Alcance del gate local** (declararlo siempre en el informe, sin afirmar la causa ni dar
  porcentajes): *"El análisis por fichero no se ha contrastado contra el conjunto completo de reglas
  del servidor. Un scan de CI puede reportar issues que este gate no ve."*
- **Lista de exclusión**: vacía. Ampliarla exige evidencia: aparición en ≥ 3 ficheros reales **sin
  otros hallazgos**, con el mismo mensaje. Una regla que apareciera siempre junto a un defecto real
  no se distinguiría de ese defecto, así que no puede excluirse sin ocultarlo.
- **Palabra «todo»**: `typescript:S1135` marca la palabra «todo» en comentarios aunque sea prosa
  (por ejemplo, `// NOTE: … en todo el flujo`). Es un issue nuevo y bloquea. Evítala
  en comentarios y JSDoc (ver documentación técnica).

### Capa 3 — Escáner de seguridad (determinista, costo 0 tokens)

Ejecuta `node .agents/scripts/security-scan.mjs` (lee `touched-files.sh`, compara base y actual,
imprime JSON). Código de salida `1` = hay hallazgos **nuevos**: **bloquea** igual que un issue
nuevo de SonarQube (`CHANGES REQUIRED`). Código `2` = `BLOCKED (infraestructura)`. Cubre lo que
ni ESLint ni `analyze_code_snippet` detectan:

| Regla | Detecta |
|---|---|
| `secret-aws-key` | clave de acceso AWS (`AKIA` + 16 caracteres) |
| `secret-private-key` | cabecera PEM de clave privada |
| `secret-token-prefix` | prefijos de token conocidos (`ghp_`, `sk_live_`, `sk-…`, `xox*-`, `AIza…`) |
| `secret-jwt` | JWT literal |
| `secret-assignment` | `password`/`secret`/`apiKey`/`token` = literal de 8+ caracteres sin espacios |
| `public-env-secret` | variable `NEXT_PUBLIC_*` con `SECRET`/`PRIVATE`/`PASSWORD`/`CREDENTIAL` en el nombre |
| `html-injection` | `dangerouslySetInnerHTML`, `.innerHTML =`, `.outerHTML =`, `document.write(` |

Es heurístico y **no es una cobertura completa**. **No detecta**: secretos fuera de `.ts`/`.tsx`
(`.env`, `.json`, `.yaml`), secretos con espacios o construidos por concatenación,
`NEXT_PUBLIC_*_TOKEN`/`_KEY` (pueden ser públicos legítimos, p. ej. la clave publicable de Clerk).
`html-injection` marca todo uso nuevo, también el saneado: pide revisar, no afirma que sea
vulnerable. Tu revisión de la diff sigue siendo obligatoria.

### Capa 4 — Quality Gate e issues persistidos (informativo)

El gate informa el Quality Gate del último scan publicado; registra el estado que devuelva el servidor sin presuponer su valor. Para consultar aparte, usa `node .agents/scripts/sonar-mcp.mjs get_project_quality_gate_status --json '{"projectKey":"<projectKey>"}'` y `node .agents/scripts/sonar-mcp.mjs search_sonar_issues_in_projects --json '{"projectKeys":["<projectKey>"]}'`. Registra el resultado en el informe: **no bloquea** ni sustituye al diferencial.

---

## Herramientas, en orden de uso

Detalle de parámetros en `references/sonarqube-tools.md` (cárgalo solo ante
ambigüedad).

1. `node .agents/scripts/sonar-mcp.mjs search_my_sonarqube_projects --json '{"q":"<projectKey>"}'` — verificar el proyecto.
2. El gate ejecuta `analyze_code_snippet` en base y actual. Para diagnóstico aislado, usa `node .agents/scripts/sonar-mcp.mjs analyze_code_snippet --json '{"fileContent":"<contenido>","language":"ts","scope":"MAIN"}'`; nunca sustituye al gate para aprobar.
3. `node .agents/scripts/sonar-mcp.mjs show_rule --json '{"key":"<ruleKey>"}'` para el detalle completo; `--explain` del gate ya resume cada regla nueva.
4. `node .agents/scripts/sonar-mcp.mjs get_project_quality_gate_status --json '{"projectKey":"<projectKey>"}'` — consulta adicional solo informativa; el gate ya informa estado.

`change_sonar_issue_status` y `change_security_hotspot_status`: solo tras aprobación explícita del usuario, mediante `node .agents/scripts/sonar-mcp.mjs <herramienta> --json '<objeto JSON conforme al esquema>' --confirmar`. Consulta el esquema con `node .agents/scripts/sonar-mcp.mjs listar`.

---

## Resultado normalizado obligatorio

| Campo | Contenido |
|-------|-----------|
| `projectKey` | El usado y cómo se resolvió |
| Base | `HEAD` (sha) o la referencia pasada con `--base` |
| Por fichero | `estado`, `scope`, `language`, ruta (y ruta antigua si renombrado) |
| Conteo por regla | `ruleKey: antes N → ahora M → +K` para cada regla con issues nuevos, de modo que un bloqueo por multiplicidad no parezca arbitrario |
| ESLint | `Sin errores en líneas modificadas` o la lista de errores |
| Escáner de seguridad | Salida de `security-scan.mjs`: `Ninguno` o lista (`ruta:línea`, regla, texto) |
| Issues nuevos | Lista con `ruleKey`, `impacts`, línea (si hay `textRange`), mensaje y explicación de `show_rule` |
| Quality Gate (informativo) | `OK` / `ERROR` / `WARN` / `NONE` |
| Alcance | La línea fija de "Alcance del gate local" |
| Veredicto gate | `PASA` / `BLOQUEA` / `BLOCKED (infraestructura)` |


### Regla S1135 y comentarios en español

La regla `S1135` puede detectar la palabra española `todo` en comentarios como un TODO. Reformula ese comentario con una descripción concreta; no excluyas ni desactives la regla.


### Reglas React y TypeScript que se comprueban antes de generar código

| Regla | Prohibido | Correcto |
|---|---|---|
| S6551 | `String(formData.get("x") ?? "")` convierte objetos a texto inútil | `const v = formData.get("x"); const x = typeof v === "string" ? v : "";` |
| S3358 | `cargando ? "Cargando" : error ? "Error" : "Listo"` | Inicializa `let estado = "Listo";` y usa `if (cargando) estado = "Cargando"; else if (error) estado = "Error";` |
| S6772 | `<span>Hola<strong>mundo</strong></span>` deja ambiguo el espacio | `<span>Hola{" "}<strong>mundo</strong></span>` |
| S6819 | `<div role="status">Guardado</div>` | `<output>Guardado</output>` |
| S7727 | `model.map(X.formatModelToResponse)` pasa un método sin envolverlo | `model.map((m) => X.formatModelToResponse(m))` |
