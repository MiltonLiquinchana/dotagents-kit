---
trigger: model_decision
description: Verify the running app in a browser with the agent-browser CLI.
---

# Verificación en el navegador

- Con `herramientas.agent_browser` distinto de `true`, no abras ningún navegador.
- Comprueba solo la app local en `http://localhost` o `http://127.0.0.1`, con el puerto con que arranca. Nunca abras URLs externas ni uses cuentas reales o credenciales en comandos o archivos. Usa datos de prueba ficticios.
- Exporta `AGENT_BROWSER_NO_VERSION_CHECK=1`. Toda orden lleva `--session <nombre>`, con un nombre único por ejecución compuesto de letras, números, `-` y `_`. La primera orden, `open <url>`, lleva además `--allowed-domains localhost,127.0.0.1`. Nunca uses `--profile`, `--restore`, `--state`, `--cdp` ni `--auto-connect`.
- Pon un límite de tiempo a cada orden, por ejemplo `timeout 60 agent-browser --session <nombre> ...`, también al cerrar. Si una orden no responde, ejecuta `close` de esa sesión y reintenta una vez. Si vuelve a fallar, registra un bloqueo de herramienta.
- Obtén referencias con `snapshot -i`: por ejemplo, `- textbox "Nombre" [ref=e2]` corresponde a `@e2`. Interactúa mediante `fill`, `click`, `select` y `press` sobre esas referencias. Espera el resultado con `wait --text "<texto>"`, `wait --url "<url>"` o `wait --load networkidle`. Obtén una nueva `snapshot -i` tras cada navegación o cambio del DOM; las referencias anteriores pueden no valer. Para la sintaxis completa consulta `agent-browser skills get core` o `agent-browser <orden> --help`, conservando la sesión y el límite de tiempo.
- El navegador queda limitado a la app local. Una dependencia de otro dominio (una API en otro host, el script o el inicio de sesión de Clerk) no constituye por sí misma un fallo de la app. Si impide completar el flujo, el resultado es `bloqueado`, con los hosts afectados. Con `integraciones.autenticacion` distinto de `ninguna`, recorre solo rutas públicas; una ruta que exige sesión es `bloqueado` con el motivo «requiere sesión real; verificación manual». Nunca inicies sesión ni añadas dominios por cuenta propia.
- Comprueba y conserva la salida literal de `console`, `errors`, `network requests --status 400-499` y `network requests --status 500-599`.
- Decide en este orden:
  1. `bloqueado`: agent-browser no responde tras el reintento; el navegador no arranca; una petición a otro host queda sin respuesta o da 5xx; el flujo necesita un dominio externo o una sesión. Registra la causa literal y los hosts afectados.
  2. `fallo` de la app: cualquier línea `[error]` de `console` o entrada de `errors` que no se deba a un dominio bloqueado; cualquier petición 4xx o 5xx al propio origen de la app, salvo `favicon.ico`; una petición 4xx a la API (la app la llamó mal); o que no aparezca el estado esperado. El navegador puede pedir `favicon.ico` por su cuenta; su 404 se ignora.
  3. `ok`: no hay ninguna de las situaciones anteriores.
- Guarda evidencia con `screenshot --full <ruta>` dentro de la carpeta de ejecución, además de las salidas literales anteriores. Si la herramienta impide obtener una evidencia, registra ese impedimento y conserva la evidencia disponible.
- Al terminar, ejecuta siempre `close` de la sesión, también si hubo fallo o una orden falló a mitad.
- Esta verificación no sustituye las pruebas unitarias, ESLint, SonarQube ni la prueba de humo por HTTP.
