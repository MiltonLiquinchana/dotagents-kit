# Ejecución de fases

## Qué es una fase

Cada paso que asigna una skill se ejecuta en un **subagente nuevo**, sin el historial de la conversación. El orquestador (la sesión principal) solo prepara las entradas, lanza el subagente, valida la salida y decide el paso siguiente. Los pasos que son del propio workflow (preflight, aprobación del plan, `git`, grafo) los hace el orquestador.

## Cómo se lanza

Usa la herramienta de la herramienta de IA que permita delegar una tarea en un agente nuevo:

- En Claude Code, la herramienta `Agent`.
- En OpenCode, la herramienta `subagent`.
- En Codex, la herramienta `spawn_agent` con `fork_turns: "none"`.

En otras herramientas (VS Code, Antigravity…) usa la equivalente si existe. No inventes nombres de herramientas: estos son los tres ejemplos verificados.

En Codex, `fork_turns: "none"` arranca el subagente sin heredar el historial del orquestador, que es justo lo que esta referencia exige. El valor por defecto (`fork_turns: all`) hereda la conversación entera, **incluidas las credenciales que el usuario haya escrito en ella**: no lo uses.

## Mensaje fijo para el subagente

El orquestador rellena los marcadores antes de lanzar la fase:

```text
Eres la fase <paso> de un workflow. Trabaja solo con lo que se indica aquí.
1. Lee completo .agents/skills/<skill>/SKILL.md y las reglas que cite.
2. Lee solo estos archivos de entrada: <lista de rutas en RUN_DIR> (y modo: <modo>, si aplica).
3. Escribe tu salida en <OUT_DIR>/<artefacto>, con la cabecera que pide la skill.
4. No leas otros archivos de RUN_DIR ni escribas archivos del proyecto, salvo que tu skill lo pida.
5. No lances subagentes ni delegues en otra IA: haz tú todo el trabajo de la fase.
Al terminar responde solo: "salida: <ruta> · estado: <ok|fallo|bloqueado>".
Relee tu salida antes de responder: el `estado` que anuncias es el del frontmatter del artefacto escrito.
```

## Validación del resultado

Al volver, el orquestador comprueba que el archivo existe y valida su cabecera (`estado`, `entradas_leidas`). El subagente declara qué ficheros de entrada leyó completos; si no leyó alguno, lo indica y la fase no acepta una salida que afirme lo contrario. En un reintento comprueba además que se usó `feedback.md`. Solo para la fase de revisión, un `review.md` sin la `SKILL.md` de su fase en `entradas_leidas` no cuenta.
El estado lo da el **frontmatter del artefacto escrito**, no el mensaje final del subagente. Si el mensaje final y el frontmatter no coinciden, el orquestador relee el artefacto: si está completo y es válido, sigue con el estado del frontmatter y lo anota en el manifest; si no, para e informa al usuario.
Al validar una fase, el orquestador **cierra su subagente** para que no quede activo consumiendo contexto: en Codex, `close_agent` (o `interrupt_agent` si sigue ejecutando). Antes del `git commit`, comprueba que no queda ningún subagente activo: en Codex, `list_agents`.
En `manifest.md` anota `ejecución: subagente` para cada fase.

## Sin subagentes (último recurso)

Si la herramienta no tiene ninguna forma de lanzar subagentes, la fase se ejecuta en la misma sesión con las mismas reglas: leer solo sus entradas, escribir solo su salida y anotar `ejecución: misma sesión` en el manifest. Nunca se elige este modo por comodidad.

## Comandos que pueden pedir permiso

En entornos con sandbox, estos comandos pueden pedir aprobación al usuario. Si la piden, se aprueba **comando a comando** y sin rodeos: no se envuelven en `sh -c`, no se sustituyen por alternativas ni se silencian.

- Escrituras en `.git/`: `git add`, `git commit` y `bash .agents/scripts/touched-files.sh`.
- La red: SonarQube (canario, gate, registro del proyecto y `node .agents/scripts/sonar-mcp.mjs`), la API en pruebas y tgrep cuando habla con su servidor.

## Contrato de escritura

| Qué se escribe | Quién escribe |
|---|---|
| Código de producción | Solo `file-writer`, a partir de los `code-changes*.md`. |
| Pruebas | La fase de pruebas, en `__tests__/`. |
| Documentación (JSDoc, `// WHY:` / `// NOTE:`, README) | Las skills de desarrollo, dentro de su `code-changes*.md`; `file-writer` lo aplica al working tree. |
| Notas de `knowledge-base/` | La fase de conocimiento. |

Esto vale en los dos modos de ejecución.
