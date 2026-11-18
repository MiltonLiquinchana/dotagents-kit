#!/usr/bin/env bash
# lint-touched.sh — corre ESLint solo sobre archivos .ts/.tsx tocados
# y filtra por líneas nuevas/modificadas (git diff -U0).
#
# Uso: .agents/scripts/lint-touched.sh
# Requiere: git, node, npx en el PATH.
# Retorna exit code 1 si hay errores en líneas modificadas, 0 si no.

set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

# Config de ESLint: sale de .agents/stack.yaml (frontend.eslint_config), sin valor por defecto.
ESLINT_CONFIG=$(node .agents/scripts/stack.mjs get frontend.eslint_config)

# Archivos .ts/.tsx añadidos o modificados (staged + unstaged, excluyendo eliminados)
FILES=$(git diff --name-only --diff-filter=AM HEAD -- '*.ts' '*.tsx' 2>/dev/null || true)
# También incluir archivos nuevos no rastreados (untracked) que sean .ts/.tsx
UNTRACKED=$(git ls-files --others --exclude-standard -- '*.ts' '*.tsx' 2>/dev/null || true)
ALL_FILES=$(printf '%s\n%s' "$FILES" "$UNTRACKED" | sort -u | xargs)

if [ -z "$ALL_FILES" ]; then
  echo "lint-touched: no hay archivos .ts/.tsx tocados — nada que analizar."
  exit 0
fi

echo "lint-touched: analizando archivos:"
echo "$ALL_FILES" | tr ' ' '\n' | sed 's/^/  /'

# Correr ESLint con la config del agente y formato JSON para parsear líneas
REPORT=$(npx eslint -c "$ESLINT_CONFIG" --format json $ALL_FILES 2>/dev/null || true)

# Para cada archivo, obtener los rangos de líneas modificadas con git diff -U0
BLOCKED=0
for FILE in $ALL_FILES; do
  [ -f "$FILE" ] || continue

  # Líneas modificadas: extraer rangos del diff (formato @@ -a,b +c,d @@)
  DIFF_RANGES=$(git diff -U0 HEAD -- "$FILE" 2>/dev/null \
    | grep '^@@' \
    | grep -oP '\+\K[0-9]+(,[0-9]+)?' || true)

  # Archivos nuevos no rastreados → todas las líneas cuentan
  IS_NEW=$(git ls-files --others --exclude-standard -- "$FILE" 2>/dev/null || true)

  # Extraer issues de este archivo del reporte JSON
  FILE_ISSUES=$(echo "$REPORT" | node -e "
    const data = require('fs').readFileSync('/dev/stdin','utf8');
    let parsed;
    try { parsed = JSON.parse(data); } catch(e) { process.exit(0); }
    const abs = require('path').resolve('$FILE');
    const entry = parsed.find(f => f.filePath === abs);
    if (!entry) { process.exit(0); }
    entry.messages.forEach(m => {
      if (m.severity === 2) { // error only
        console.log(m.line + ' ' + m.ruleId + ' ' + String(m.message).replace(/\s+/g, ' '));
      }
    });
  " 2>/dev/null || true)

  if [ -z "$FILE_ISSUES" ]; then
    continue
  fi

  # Filtrar por líneas en rangos modificados
  while IFS= read -r ISSUE; do
    LINE=$(echo "$ISSUE" | awk '{print $1}')
    REST=$(echo "$ISSUE" | cut -d' ' -f2-)

    IN_RANGE=0
    if [ -n "$IS_NEW" ]; then
      IN_RANGE=1
    else
      for RANGE in $DIFF_RANGES; do
        START=$(echo "$RANGE" | cut -d',' -f1)
        COUNT=$(echo "$RANGE" | grep -oP ',\K[0-9]+' || echo "1")
        END=$((START + COUNT - 1))
        if [ "$LINE" -ge "$START" ] && [ "$LINE" -le "$END" ]; then
          IN_RANGE=1
          break
        fi
      done
    fi

    if [ "$IN_RANGE" -eq 1 ]; then
      echo "  BLOQUEANTE [$FILE:$LINE] $REST"
      BLOCKED=1
    fi
  done <<< "$FILE_ISSUES"
done

if [ "$BLOCKED" -eq 1 ]; then
  echo ""
  echo "lint-touched: ❌ Hay errores ESLint en líneas modificadas — bloquea el avance."
  exit 1
else
  echo "lint-touched: ✅ Sin errores ESLint en líneas modificadas."
  exit 0
fi

