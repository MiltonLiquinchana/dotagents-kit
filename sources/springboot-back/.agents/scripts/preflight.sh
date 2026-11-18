#!/usr/bin/env bash
set -uo pipefail
# El motor acumula hallazgos y consulta un único catálogo; no omite por workflow.
SCRIPTS="$(cd -- "$(dirname -- "$0")" && pwd)" || {
    echo 'BLOCKED [PLANTILLA] no se pudo localizar scripts; avisa al mantenedor.'
    echo 'Remedio: Avisa al mantenedor de .agents.'
    echo 'RESULTADO codigo=PLANTILLA clase=bloqueo servicio=* remedio="Avisa al mantenedor de .agents"'
    echo 'RESUMEN workflow=estricto fase=entrada bloqueos=1 plan=0 avisos=0 omitidos=0 primero=PLANTILLA exit=1'
    exit 1
}
command -v python3 >/dev/null 2>&1 || {
    echo 'BLOCKED [HERRAMIENTA] python3 no encontrado en PATH.'
    echo 'Remedio: Usuario: instala python3 y repite el workflow.'
    echo 'RESULTADO codigo=HERRAMIENTA clase=bloqueo servicio=* remedio="Usuario: instala python3"'
    echo 'RESUMEN workflow=estricto fase=entrada bloqueos=1 plan=0 avisos=0 omitidos=0 primero=HERRAMIENTA exit=1'
    exit 1
}
python3 -I -B "$SCRIPTS/preflight.py" "$@"
