# dotagents-kit

Instrucciones para que una IA de programación trabaje en tu proyecto siguiendo un proceso fijo:
diseñar, pedir tu aprobación, implementar, probar, pasar el quality gate, revisar y documentar.

`dotagents-kit` genera, dentro de tu proyecto, una carpeta `.agents/` con workflows, skills, reglas y
scripts adaptados a tu `stack.yaml`. Puede usarse con herramientas que lean `AGENTS.md`, como
opencode o codex. Claude Code carga `CLAUDE.md`: crea en tu proyecto ese archivo con la línea
`@AGENTS.md` para que incluya las instrucciones que genera el kit.

## Stacks

| Carpeta | Stack | Incluye |
|---|---|---|
| `sources/springboot-back` | Microservicios Spring Boot con Gradle | Persistencia JPA/JDBC, Lombok, gateway, autenticación con Clerk (opcional), Jenkins + Kubernetes (opcional), gestión de usuarios (Clerk, opcional) |
| `sources/nextjs-front` | Next.js (App Router) con TypeScript | Capas de API, notificaciones opcionales, llamadas a la API desde navegador o servidor, autenticación con Clerk (opcional), gestión de usuarios (Clerk, opcional) |
| `sources/mysql-sql` | MySQL con notebooks `.dbcnb` | Sandbox desechable, linter SQL, pruebas por objeto, gestión de usuarios (opcional) |

## Empezar

Requisitos: Git, Python 3, `jq`, `tgrep`, Open Notebook con un proveedor de modelos y una IA que pueda
ejecutar comandos y escribir archivos; según el stack, Node.js, `curl`, SonarQube y su servidor MCP
(back y front), JDK (back) y Java para el servidor MCP de SonarQube (back y front), PyYAML y
Docker/Podman (SQL), y `db-mcp-server` para los pasos con la base real (SQL).
Consulta la [tabla de requisitos](manual-usuario.md#requisitos).

1. Clona este repositorio con `git clone <url>`; en la documentación esa ruta se llama `<KIT>`.
2. Abre tu IA en el workspace de **tu** proyecto y pídele que siga
   `<KIT>/guia-ia-preparar-proyecto.md`. La guía propone lo que detecta, pide confirmar cada decisión
   y prepara `.agents/stack.yaml`; con tu confirmación, la IA ejecuta el generador.
3. Sigue el orden de [Qué haces después de generar](manual-usuario.md#qué-haces-después-de-generar):
   prepara el proyecto, revisa y haz el commit indicado, ajusta las versiones y, si `herramientas.graphify`
   es `true`, pide `graphify` antes de `preparar-documentacion`: sin grafo, el cierre de
   `preparar-documentacion` bloquea. Después pide `preparar-documentacion`.
4. Elige una tarea del [catálogo de tu stack](manual-usuario.md#2-trabajar-con-los-workflows) y pídesela a la IA.

El [manual de usuario](manual-usuario.md) explica cada paso, el prompt exacto, los requisitos,
los catálogos de workflows y qué hacer cuando el preflight se detiene.

## Estructura

- `sources/<carpeta del stack>/`: las plantillas de cada stack. No son instrucciones para la IA de este repositorio.
- `guia-ia-preparar-proyecto.md`: la guía que sigue la IA en tu proyecto.
- `manual-usuario.md`: el manual para personas.
- `ejemplos/<carpeta del stack>/project.md`: un `project.md` completado para un proyecto ficticio.
- `checkers/`: validan las plantillas.

## Para contribuir

Ejecuta los cinco `checkers/check-*.py` desde la raíz con
`python3 -I -B checkers/<checker>.py` (sustituye `<checker>` por el nombre sin `.py`).
`check-stack.py` necesita PyYAML en el Python del sistema, por ejemplo mediante el paquete
`python3-yaml`: con `-I` no se carga el site-packages del usuario.

## Licencia

[MIT](LICENSE).
