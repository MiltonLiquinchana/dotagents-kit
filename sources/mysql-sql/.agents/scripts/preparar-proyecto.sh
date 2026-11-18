#!/usr/bin/env bash
set -euo pipefail

ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || { echo "BLOCKED: no se ejecuta dentro de un repositorio git." >&2; exit 2; }
cd "$ROOT"
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
  for line in '.agent-runs/' 'logs/' 'knowledge-base/.tgrep/' '__pycache__/'; do grep -Fqx -- "$line" .gitignore 2>/dev/null || report "falta línea en .gitignore: $line"; done
  if [ ! -f .cbmignore ]; then
    report "falta .cbmignore"
  fi
  if [ ! -f .agents/config/cbmignore ]; then
    report "falta .agents/config/cbmignore"
  else
    while IFS= read -r line || [ -n "$line" ]; do case "$line" in ''|\#*) continue ;; esac; grep -Fqx -- "$line" .cbmignore 2>/dev/null || report "falta línea en .cbmignore: $line"; done < .agents/config/cbmignore
  fi
  # Migra las exclusiones propias sin borrar el archivo antiguo.
  if [ -f .graphifyignore ]; then
    while IFS= read -r line || [ -n "$line" ]; do
      case "$line" in ''|\#*|'graphify-out/') continue ;; esac
      grep -Fqx -- "$line" .cbmignore 2>/dev/null || report "falta línea en .cbmignore: $line"
    done < .graphifyignore
  fi
  if [ "$MISSING" -eq 0 ]; then echo "OK: preparación completa"; exit 0; else echo "preparación incompleta"; exit 1; fi
fi

if [ ! -d knowledge-base ]; then mkdir -p knowledge-base; : > knowledge-base/.gitkeep; echo "creado knowledge-base/.gitkeep"; CHANGED=1
elif [ -z "$(find knowledge-base -mindepth 1 -maxdepth 1 -print -quit)" ]; then
  if [ ! -f knowledge-base/.gitkeep ]; then : > knowledge-base/.gitkeep; echo "creado knowledge-base/.gitkeep"; CHANGED=1; fi
fi
for line in '.agent-runs/' 'logs/' 'knowledge-base/.tgrep/' '__pycache__/'; do ensure_line .gitignore "$line"; done
IGNORE='.agents/config/cbmignore'
[ -f "$IGNORE" ] || { echo "BLOCKED: falta .agents/config/cbmignore" >&2; exit 2; }
[ -f .cbmignore ] || : > .cbmignore
while IFS= read -r line || [ -n "$line" ]; do case "$line" in ''|\#*) continue ;; esac; ensure_line .cbmignore "$line"; done < "$IGNORE"
if [ -f .graphifyignore ]; then
  while IFS= read -r line || [ -n "$line" ]; do
    case "$line" in ''|\#*|'graphify-out/') continue ;; esac
    ensure_line .cbmignore "$line"
  done < .graphifyignore
fi
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
