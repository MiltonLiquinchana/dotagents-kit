#!/usr/bin/env bash
set -uo pipefail

# ==============================================================================
# touched-files.sh - Ficheros .java tocados respecto a la base de la feature
#
# Uso:
#   touched-files.sh [--base <ref>]   Imprime en stdout un array JSON.
#   touched-files.sh --ensure-cache   Crea .agents/.cache/sonar-base/ solo si
#                                     está ignorado por git; imprime su ruta.
#
# Cada entrada del array:
#   servicio (el del fichero ACTUAL), servicioBase (el de la ruta antigua; difiere
#   en un movimiento entre servicios), ruta, rutaBase, estado
#   (nuevo|modificado|renombrado), scope (MAIN|TEST), blobBase (sha del contenido
#   base, o null si es nuevo)
#
# Se omiten los ficheros cuyo contenido no cambió respecto a la base: cambios de
# solo modo (chmod) y renombrados puros dentro del mismo scope. Analizar A y B
# idénticos no puede producir issues nuevos y solo gastaría llamadas.
#
# Base: .agents/stack.yaml git.rama_base; null usa HEAD. Se recalcula en cada ejecución, así que un rebase no deja estado
# obsoleto; blobBase es un hash de contenido y no cambia con el rebase.
#
# Los cambios se leen de un índice TEMPORAL con 'git add -A', de modo que no
# importa si el usuario hizo 'git add': un 'mv' sin añadir se ve como renombrado
# y los ficheros nuevos sin rastrear se ven como nuevos. El índice real no se toca.
#
# Salida stdout: JSON. Logs y errores: stderr.
# Códigos de salida: 0 = OK, 2 = BLOCKED (infraestructura)
# ==============================================================================

CACHE_DIR=".agents/.cache/sonar-base"

die() {
    echo "BLOCKED (infraestructura): $1" >&2
    exit 2
}

BASE_REF="$(node .agents/scripts/stack.mjs get git.rama_base 2>/dev/null || true)"
BASE_REF="${BASE_REF:-HEAD}"
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

# HEAD es la instantánea previa a la feature cuando rama_base es null.
git rev-parse --verify -q "$BASE_REF^{commit}" >/dev/null \
    || die "la referencia base '$BASE_REF' de git.rama_base no existe."
if [ "$BASE_REF" = "HEAD" ]; then BASE_SHA=$(git rev-parse HEAD); else
    BASE_SHA=$(git merge-base HEAD "$BASE_REF" 2>/dev/null) \
        || die "no hay ancestro común entre HEAD y la referencia base '$BASE_REF'."
fi
echo "BASE=$BASE_SHA ($BASE_REF)" >&2

# Índice temporal: copia del real + 'add -A'. El real queda intacto.
WORK_DIR=$(mktemp -d) || die "no se pudo crear un directorio temporal."
trap 'rm -rf "$WORK_DIR"' EXIT
TMP_INDEX="$WORK_DIR/index"
REAL_INDEX=$(git rev-parse --git-path index)
[ -f "$REAL_INDEX" ] && cp "$REAL_INDEX" "$TMP_INDEX"
GIT_INDEX_FILE="$TMP_INDEX" git add -A > /dev/null 2>&1 || die "'git add -A' falló sobre el índice temporal."

# <servicio>/src/{main,test}/java/**/*.java, y solo si <servicio> es un build Gradle
is_service_source() {
    local path="$1" service
    [[ "$path" =~ ^[^/]+/src/(main|test)/java/.+\.java$ ]] || return 1
    service="${path%%/*}"
    [ -f "$service/build.gradle" ]
}

scope_of() {
    case "$1" in
        */src/test/*) echo "TEST" ;;
        *)            echo "MAIN" ;;
    esac
}

ENTRIES="$WORK_DIR/entries.jsonl"
: > "$ENTRIES"

emit() { # servicio ruta rutaBase estado scope blobBase
    local servicio_base=""
    [ -n "$3" ] && servicio_base="${3%%/*}"
    jq -cn --arg servicio "$1" --arg servicioBase "$servicio_base" --arg ruta "$2" \
        --arg rutaBase "$3" --arg estado "$4" --arg scope "$5" --arg blobBase "$6" \
        '{servicio: $servicio,
          servicioBase: (if $servicioBase == "" then null else $servicioBase end),
          ruta: $ruta,
          rutaBase: (if $rutaBase == "" then null else $rutaBase end),
          estado: $estado, scope: $scope,
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
    is_service_source "$new" || continue

    service="${new%%/*}"
    scope=$(scope_of "$new")

    case "${status:0:1}" in
        A|C)
            emit "$service" "$new" "" "nuevo" "$scope" ""
            ;;
        M|T)
            blob=$(git rev-parse --verify -q "$BASE_SHA:$new") \
                || die "no se encontró $new en la base $BASE_SHA."
            current=$(GIT_INDEX_FILE="$TMP_INDEX" git rev-parse --verify -q ":$new") \
                || die "no se encontró $new en el índice temporal."
            [ "$current" = "$blob" ] && continue          # solo cambió el modo
            emit "$service" "$new" "$new" "modificado" "$scope" "$blob"
            ;;
        R)
            if is_service_source "$old" && blob=$(git rev-parse --verify -q "$BASE_SHA:$old"); then
                current=$(GIT_INDEX_FILE="$TMP_INDEX" git rev-parse --verify -q ":$new") \
                    || die "no se encontró $new en el índice temporal."
                # Renombrado puro dentro del mismo scope: A y B serían idénticos.
                if [ "$current" = "$blob" ] && [ "$(scope_of "$old")" = "$scope" ]; then
                    continue
                fi
                emit "$service" "$new" "$old" "renombrado" "$scope" "$blob"
            else
                emit "$service" "$new" "" "nuevo" "$scope" ""
            fi
            ;;
        *)
            die "estado de git no contemplado: $status ($new)."
            ;;
    esac
done < "$DIFF_FILE"

jq -s '.' "$ENTRIES"
