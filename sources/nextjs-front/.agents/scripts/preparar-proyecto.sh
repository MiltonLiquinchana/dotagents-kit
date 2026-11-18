#!/usr/bin/env bash
set -euo pipefail

ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || { echo "BLOCKED: no se ejecuta dentro de un repositorio git." >&2; exit 2; }
cd "$ROOT"
SCRIPTS=".agents/scripts"
CHANGED=0
ensure_line() {
  local file="$1" line="$2"
  [ -f "$file" ] || : > "$file"
  if ! grep -Fqx -- "$line" "$file"; then printf '%s\n' "$line" >> "$file"; echo "añadido $line a $file"; CHANGED=1; fi
}
COMPROBAR=0
ARRANCAR_TGREP=0
if [ "${1:-}" = "--comprobar" ]; then
  [ "$#" -eq 1 ] || { echo "BLOCKED: opción desconocida o combinación no admitida" >&2; exit 2; }
  COMPROBAR=1
elif [ "${1:-}" = "--arrancar-tgrep" ]; then
  [ "$#" -eq 1 ] || { echo "BLOCKED: opción desconocida: $*" >&2; exit 2; }
  ARRANCAR_TGREP=1
elif [ "$#" -gt 0 ]; then
  echo "BLOCKED: opción desconocida: $1" >&2; exit 2
fi

if [ "$COMPROBAR" -eq 1 ]; then
  MISSING=0
  report() { echo "$1"; MISSING=1; }
  [ -d knowledge-base ] || report "falta knowledge-base/"
  if [ -d knowledge-base ] && [ -z "$(find knowledge-base -mindepth 1 -maxdepth 1 -print -quit)" ] && [ ! -f knowledge-base/.gitkeep ]; then report "falta knowledge-base/.gitkeep"; fi
  for line in '.agent-runs/' 'graphify-out/' 'logs/' 'knowledge-base/.tgrep/'; do grep -Fqx -- "$line" .gitignore 2>/dev/null || report "falta línea en .gitignore: $line"; done
  if [ -f .agents/config/eslint.agent.config.mjs ]; then
    ESLINT_DEST=$(node "$SCRIPTS/stack.mjs" get frontend.eslint_config 2>/dev/null) || ESLINT_DEST=""
    if [ -z "$ESLINT_DEST" ]; then report "no se pudo leer frontend.eslint_config"; elif [ ! -f "$ESLINT_DEST" ]; then report "falta $ESLINT_DEST"; fi
  fi
  if [ ! -f .graphifyignore ]; then
    report "falta .graphifyignore"
  fi
  if [ ! -f .agents/config/graphifyignore ]; then
    report "falta .agents/config/graphifyignore"
  elif [ -f .graphifyignore ]; then
    while IFS= read -r line || [ -n "$line" ]; do case "$line" in ''|\#*) continue ;; esac; grep -Fqx -- "$line" .graphifyignore 2>/dev/null || report "falta línea en .graphifyignore: $line"; done < .agents/config/graphifyignore
  fi
  if [ "$MISSING" -eq 0 ]; then echo "OK: preparación completa"; exit 0; else echo "preparación incompleta"; exit 1; fi
fi

if [ ! -d knowledge-base ]; then mkdir -p knowledge-base; : > knowledge-base/.gitkeep; echo "creado knowledge-base/.gitkeep"; CHANGED=1
elif [ -z "$(find knowledge-base -mindepth 1 -maxdepth 1 -print -quit)" ]; then
  if [ ! -f knowledge-base/.gitkeep ]; then : > knowledge-base/.gitkeep; echo "creado knowledge-base/.gitkeep"; CHANGED=1; fi
fi
for line in '.agent-runs/' 'graphify-out/' 'logs/' 'knowledge-base/.tgrep/'; do ensure_line .gitignore "$line"; done
# Config de ESLint del agente: copia la plantilla a la ruta de frontend.eslint_config solo si
# el destino todavía no existe (idempotente: si ya existe, no se toca).
ESLINT_SRC='.agents/config/eslint.agent.config.mjs'
if [ -f "$ESLINT_SRC" ]; then
  ESLINT_DEST=$(node "$SCRIPTS/stack.mjs" get frontend.eslint_config) || { echo 'BLOCKED: stack.mjs no pudo leer frontend.eslint_config.' >&2; exit 2; }
  if [ ! -f "$ESLINT_DEST" ]; then cp "$ESLINT_SRC" "$ESLINT_DEST"; echo "creado $ESLINT_DEST desde $ESLINT_SRC"; CHANGED=1; fi
fi
# .env.example: si el .gitignore del proyecto excluye .env*, añade !.env.example justo después,
# para que la plantilla de variables de ejemplo quede versionada (idempotente).
if grep -q '\.env\*' .gitignore 2>/dev/null && ! grep -q '^!\.env\.example' .gitignore; then
  awk '{print} index($0, ".env*") == 1 && !added {print "!.env.example"; added=1}' .gitignore > .gitignore.tmp && mv .gitignore.tmp .gitignore
  echo 'añadido !.env.example a .gitignore (justo tras la línea .env*)'; CHANGED=1
fi
IGNORE='.agents/config/graphifyignore'
[ -f "$IGNORE" ] || { echo "BLOCKED: falta .agents/config/graphifyignore" >&2; exit 2; }
[ -f .graphifyignore ] || : > .graphifyignore
while IFS= read -r line || [ -n "$line" ]; do case "$line" in ''|\#*) continue ;; esac; ensure_line .graphifyignore "$line"; done < "$IGNORE"
if [ "$ARRANCAR_TGREP" -eq 1 ]; then
  command -v tgrep >/dev/null 2>&1 || { echo 'BLOCKED: CLI tgrep no encontrada.' >&2; exit 2; }
  mkdir -p logs
  STATUS=$(tgrep status knowledge-base/ 2>&1 || true)
  if ! printf '%s\n' "$STATUS" | grep -q 'Server status'; then
    setsid nohup tgrep serve knowledge-base/ > logs/tgrep-serve.log 2>&1 < /dev/null &
    echo 'iniciado tgrep serve knowledge-base/ (logs/tgrep-serve.log)'
    CHANGED=1
  else echo 'tgrep ya está activo'; fi
  READY=0
  for _ in 1 2 3 4 5 6 7 8 9 10; do
    STATUS=$(tgrep status knowledge-base/ 2>&1 || true)
    if printf '%s\n' "$STATUS" | grep -q 'Indexing: *complete'; then READY=1; break; fi
    sleep 1
  done
  [ "$READY" -eq 1 ] || { echo 'BLOCKED: tgrep no alcanzó Indexing: complete.' >&2; printf '%s\n' "$STATUS" >&2; exit 2; }
  echo 'tgrep: Indexing: complete'
fi
if [ "$CHANGED" -eq 0 ]; then echo 'sin cambios'; else echo 'preparación completada'; fi
