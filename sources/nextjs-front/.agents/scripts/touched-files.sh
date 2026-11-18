#!/usr/bin/env bash
set -uo pipefail

# ==============================================================================
# touched-files.sh - Ficheros .ts/.tsx/.mts/.cts tocados respecto a la base (frontend)
#
# Uso:
#   touched-files.sh [--base <ref>]   Imprime en stdout un array JSON.
#   touched-files.sh --ensure-cache   Crea .agents/.cache/sonar-base/ solo si
#                                     está ignorado por git; imprime su ruta.
#
# Cada entrada del array:
#   ruta, rutaBase (la ruta antigua; null si es nuevo), estado
#   (nuevo|modificado|renombrado), scope (MAIN|TEST), language (ts|tsx),
#   blobBase (sha del contenido base, o null si es nuevo)
#
# Se omiten los ficheros cuyo contenido no cambió respecto a la base: cambios de
# solo modo (chmod) y renombrados puros dentro del mismo scope y lenguaje.
# Analizar A y B idénticos no puede producir issues nuevos y solo gastaría llamadas.
#
# Base: HEAD por defecto. El flujo exige árbol limpio al inicio (preflight.sh) y
# comitea una sola vez al final, así que HEAD es exactamente "el estado previo a
# la feature". Usa --base <ref> para comparar contra otra referencia.
#
# Los cambios se leen de un índice TEMPORAL con 'git add -A', de modo que no
# importa si el usuario hizo 'git add': un 'mv' sin añadir se ve como renombrado
# y los ficheros nuevos sin rastrear se ven como nuevos. El índice real no se toca.
#
# Fuera de alcance (no se emiten): .agents/, knowledge-base/, node_modules/, .next/,
# graphify-out/, y los .d.ts.
#
# Salida stdout: JSON. Logs y errores: stderr.
# Códigos de salida: 0 = OK, 2 = BLOCKED (infraestructura)
# ==============================================================================

CACHE_DIR=".agents/.cache/sonar-base"

die() {
    echo "BLOCKED (infraestructura): $1" >&2
    exit 2
}

BASE_REF="HEAD"
ENSURE_CACHE=0
while [ $# -gt 0 ]; do
    case "$1" in
        --base)         [ $# -ge 2 ] || die "--base requiere un valor."; BASE_REF="$2"; shift 2 ;;
        --ensure-cache) ENSURE_CACHE=1; shift ;;
        *)              die "argumento desconocido: $1" ;;
    esac
done

ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || die "no se ejecuta dentro de un repositorio git."
cd "$ROOT" || die "no se pudo entrar en $ROOT."
command -v jq > /dev/null 2>&1 || die "jq no encontrado en PATH."

if [ "$ENSURE_CACHE" -eq 1 ]; then
    git check-ignore -q "$CACHE_DIR/.probe" \
        || die ".agents/.cache/ no está en .gitignore: no se crea la caché."
    mkdir -p "$CACHE_DIR" || die "no se pudo crear $CACHE_DIR."
    echo "$CACHE_DIR"
    exit 0
fi

BASE_SHA=$(git rev-parse --verify -q "$BASE_REF^{commit}") \
    || die "la referencia base '$BASE_REF' no existe."
echo "BASE=$BASE_SHA ($BASE_REF)" >&2

# Índice temporal: copia del real + 'add -A'. El real queda intacto.
WORK_DIR=$(mktemp -d) || die "no se pudo crear un directorio temporal."
trap 'rm -rf "$WORK_DIR"' EXIT
TMP_INDEX="$WORK_DIR/index"
REAL_INDEX=$(git rev-parse --git-path index)
[ -f "$REAL_INDEX" ] && cp "$REAL_INDEX" "$TMP_INDEX"
GIT_INDEX_FILE="$TMP_INDEX" git add -A > /dev/null 2>&1 || die "'git add -A' falló sobre el índice temporal."

# .ts/.tsx/.mts/.cts de código del proyecto (no .d.ts, no carpetas fuera de alcance)
is_source() {
    local path="$1"
    [[ "$path" =~ \.(ts|tsx|mts|cts)$ ]] || return 1
    [[ "$path" == *.d.ts ]] && return 1
    case "$path" in
        .agents/*|knowledge-base/*|node_modules/*|.next/*|graphify-out/*) return 1 ;;
    esac
    return 0
}

scope_of() {
    case "$1" in
        __tests__/*|*/__tests__/*|*.test.ts|*.test.tsx|*.test.mts|*.spec.ts|*.spec.tsx|*.spec.mts) echo "TEST" ;;
        *)                                                                   echo "MAIN" ;;
    esac
}

language_of() {
    case "$1" in
        *.tsx) echo "tsx" ;;   # .ts, .mts y .cts se analizan como "ts"
        *)     echo "ts" ;;
    esac
}

ENTRIES="$WORK_DIR/entries.jsonl"
: > "$ENTRIES"

emit() { # ruta rutaBase estado scope language blobBase
    jq -cn --arg ruta "$1" --arg rutaBase "$2" --arg estado "$3" --arg scope "$4" \
        --arg language "$5" --arg blobBase "$6" \
        '{ruta: $ruta,
          rutaBase: (if $rutaBase == "" then null else $rutaBase end),
          estado: $estado, scope: $scope, language: $language,
          blobBase: (if $blobBase == "" then null else $blobBase end)}' >> "$ENTRIES"
}

DIFF_FILE="$WORK_DIR/diff.z"
GIT_INDEX_FILE="$TMP_INDEX" git diff --cached -M --name-status -z "$BASE_SHA" > "$DIFF_FILE" \
    || die "'git diff' falló contra la base $BASE_SHA."

while IFS= read -r -d '' status; do
    old=""
    case "$status" in
        R*|C*) IFS= read -r -d '' old; IFS= read -r -d '' new ;;
        *)     IFS= read -r -d '' new ;;
    esac

    case "${status:0:1}" in
        D) continue ;;                                  # borrados: no generan issues
    esac
    is_source "$new" || continue

    scope=$(scope_of "$new")
    lang=$(language_of "$new")

    case "${status:0:1}" in
        A|C)
            emit "$new" "" "nuevo" "$scope" "$lang" ""
            ;;
        M|T)
            blob=$(git rev-parse --verify -q "$BASE_SHA:$new") \
                || die "no se encontró $new en la base $BASE_SHA."
            current=$(GIT_INDEX_FILE="$TMP_INDEX" git rev-parse --verify -q ":$new") \
                || die "no se encontró $new en el índice temporal."
            [ "$current" = "$blob" ] && continue          # solo cambió el modo
            emit "$new" "$new" "modificado" "$scope" "$lang" "$blob"
            ;;
        R)
            if is_source "$old" && blob=$(git rev-parse --verify -q "$BASE_SHA:$old"); then
                current=$(GIT_INDEX_FILE="$TMP_INDEX" git rev-parse --verify -q ":$new") \
                    || die "no se encontró $new en el índice temporal."
                # Renombrado puro dentro del mismo scope y lenguaje: A y B serían idénticos.
                if [ "$current" = "$blob" ] && [ "$(scope_of "$old")" = "$scope" ] \
                    && [ "$(language_of "$old")" = "$lang" ]; then
                    continue
                fi
                emit "$new" "$old" "renombrado" "$scope" "$lang" "$blob"
            else
                emit "$new" "" "nuevo" "$scope" "$lang" ""
            fi
            ;;
        *)
            die "estado de git no contemplado: $status ($new)."
            ;;
    esac
done < "$DIFF_FILE"

jq -s '.' "$ENTRIES"
