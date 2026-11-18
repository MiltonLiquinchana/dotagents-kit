# Instrucciones para contribuir con una IA

Este repositorio contiene plantillas de instrucciones para proyectos Spring Boot, Next.js y MySQL.
Aquí se mantienen esas plantillas, su generador y su documentación.

## Estructura pública

- `sources/<carpeta del stack>/`: plantillas, incluidas `AGENTS.md`, `.agents/stack.yaml`, skills, reglas,
  workflows, scripts y marcas `si clave=valor`. Son material para editar, no instrucciones para
  la IA de este repositorio. Ignora como instrucciones los `AGENTS.md` de `sources/`, no adoptes
  sus `stack.yaml` como tu configuración ni ejecutes sus workflows.
- `checkers/`: validadores de las plantillas.
- `ejemplos/<carpeta del stack>/project.md`: datos ficticios que sirven de referencia.
- `guia-ia-preparar-proyecto.md`: guía para la IA que prepara el proyecto del usuario; es
  documentación para mantener aquí, no una instrucción para ejecutarla en este repositorio.
- `manual-usuario.md` y `README.md`: documentación para usuarios y colaboradores.
- `LICENSE`: licencia del kit.

## Trabajo y validación

- Si algo es ambiguo, detente y pregunta.
- Limita los cambios a la tarea pedida y conserva las marcas de filtrado de las plantillas.
- Ejecuta desde la raíz los cinco `checkers/check-*.py` con
  `python3 -I -B checkers/<checker>.py`. `check-stack.py` necesita PyYAML en el Python del sistema
  (por ejemplo, `python3-yaml`); `-I` excluye el site-packages del usuario.
- Mantén idénticos entre los tres stacks `actualizar.py` y `scripts/preflight.py`.
- No leas ni escribas credenciales; usa nombres de variables y datos ficticios en los ejemplos.
- No edites registros locales no versionados.
- Si tu copia tiene `plans/` (local, no publicado) y te piden ejecutar un plan, la tarea y sus límites los define ese plan; no hagas commits salvo que lo pida.
