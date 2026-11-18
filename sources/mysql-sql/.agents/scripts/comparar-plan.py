#!/usr/bin/env python3
"""Compara los archivos declarados en el plan aprobado con el working tree (git).

Uso:
  python3 -I -B .agents/scripts/comparar-plan.py RUN_DIR/approved-plan.md [--solo-plan] [--ignorar <prefijo>]...

Cómo funciona:
- Del plan extrae las rutas listadas como viñetas (listas con `-`, `*` o `n.`) bajo
  encabezados que mencionen archivos u objetos ("Archivos a crear o modificar",
  "Archivos afectados", "Objetos de BD involucrados", ...). Solo cuentan las rutas
  de la primera pareja de tildes invertidas de cada viñeta: la de último segmento con
  extensión (como antes), o con nombre exacto Dockerfile, Jenkinsfile, Makefile,
  Containerfile o gradlew, o un oculto exacto .gitignore, .dockerignore, .graphifyignore
  o .gitattributes; en estos dos últimos casos la ruta completa no puede contener
  espacios, `|`, `*` ni `?`, ni terminar en `/`. Un pipeline sin extensión con otro nombre
  no se reconoce; nómbralo en el plan con extensión o amplía la lista.
- Las rutas bajo encabezados que mencionen "prueba" son permitidas, no obligatorias.
- --solo-plan valida que haya una sección de archivos con al menos una ruta;
  no consulta git y devuelve 0 si existe o 2 si falta.
- Del working tree obtiene `git status --porcelain=v1 -z --untracked-files=all` (incluye archivos sin seguimiento).
- Solo se cuentan los archivos del proyecto: se excluyen por defecto los prefijos
  `.agent-runs/` (carpeta de ejecución), `.agents/`, `.git/` y `node_modules/`, y los
  prefijos adicionales que se pasen con `--ignorar`.
- Falta alguno declarado: exit 1 con la lista. Sobra alguno no declarado: exit 1 con
  la lista. Si coincide: exit 0. Plan sin ninguna sección de archivos: exit 2.

El workflow lo ejecuta tras la escritura de archivos (front y back) o de notebooks
(base). Un archivo extra puede ser legítimo solo si lo añadió una enmienda del plan
aprobado; en ese caso el orquestador re-ejecuta este script con el plan ya enmendado.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

EXCLUIDOS = (".agent-runs/", ".agents/", ".git/", "node_modules/")
RUTA_BASE = re.compile(r"^[^`|]+?\.[A-Za-z][A-Za-z0-9]{1,9}$")
NOMBRES_SIN_EXTENSION = ("Dockerfile", "Jenkinsfile", "Makefile", "Containerfile", "gradlew")
OCULTOS = (".gitignore", ".dockerignore", ".graphifyignore", ".gitattributes")
ENCABEZADO = re.compile(r"^(#{1,6})\s+(.*)$")
VINETA = re.compile(r"^\s*(?:[-*]|\d+\.)\s")


def es_ruta(ruta):
    """Decide si el texto entre tildes de una viñeta cuenta como ruta declarada."""
    ultimo = ruta.split("/")[-1]
    if RUTA_BASE.match(ultimo):
        return True
    if ultimo in (*NOMBRES_SIN_EXTENSION, *OCULTOS):
        if ruta.endswith("/") or any(c in ruta for c in (" ", "|", "*", "?")):
            return False
        return True
    return False


def rutas_del_plan(texto):
    obligatorias, permitidas = set(), set()
    seccion = None
    nivel = 0
    encabezados = []
    for linea in texto.splitlines():
        m = ENCABEZADO.match(linea)
        if m:
            profundidad, titulo = len(m.group(1)), m.group(2)
            if seccion is not None and profundidad > nivel:
                continue
            enc = titulo.lower()
            seccion = (permitidas if "prueba" in enc else obligatorias
                       if any(p in enc for p in ("archivo", "objeto", "afectados"))
                       else None)
            nivel = profundidad
            if seccion is obligatorias:
                encabezados.append(titulo)
            continue
        if seccion is None or not VINETA.match(linea):
            continue
        primera = re.search(r"`([^`]+)`", linea)
        if primera:
            ruta = primera.group(1).strip()
            if es_ruta(ruta):
                seccion.add(ruta)
    return obligatorias, permitidas, encabezados


def rutas_del_arbol(ignorar):
    rutas = set()
    out = subprocess.run(
        ["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"],
        capture_output=True, text=True, check=True
    ).stdout
    entradas = iter(out.split("\0"))
    for entrada in entradas:
        if len(entrada) < 4:
            continue
        estado, ruta = entrada[:2], entrada[3:]
        # En -z, renombres/copias llevan destino primero y origen después.
        if "R" in estado or "C" in estado:
            next(entradas, None)
        if any(ruta.startswith(p) for p in (*EXCLUIDOS, *ignorar)):
            continue
        rutas.add(ruta)
    return rutas


def main():
    ap = argparse.ArgumentParser(
        description="Compara la lista de archivos del plan aprobado con git status."
    )
    ap.add_argument("plan", help="ruta del plan aprobado (RUN_DIR/approved-plan.md)")
    ap.add_argument(
        "--ignorar",
        action="append",
        default=[],
        help="prefijo de ruta a excluir del working tree (opcional, repetible)",
    )
    ap.add_argument("--solo-plan", action="store_true", help="valida las rutas del plan sin consultar git")
    args = ap.parse_args()

    plan = Path(args.plan)
    if not plan.is_file():
        print(f"FALLO: no existe el plan {args.plan}", file=sys.stderr)
        return 2
    rutas_plan, rutas_pruebas, encabezados = rutas_del_plan(plan.read_text(encoding="utf-8"))
    if not rutas_plan:
        if encabezados:
            for titulo in encabezados:
                print(f"FALLO: la sección `{titulo}` no tiene viñetas con una ruta entre tildes")
        else:
            print("FALLO: no hay sección de archivos u objetos en el plan")
            print("encabezados buscables: los que mencionen 'archivo', 'objeto' o 'afectados'.")
        return 2

    sufijo_ignorados = f"; ignorados: {', '.join(args.ignorar)}" if args.ignorar else ""
    if args.solo_plan:
        print(f"OK: el plan declara {len(rutas_plan)} archivos y {len(rutas_pruebas)} pruebas permitidas{sufijo_ignorados}")
        return 0

    rutas_arbol = rutas_del_arbol(args.ignorar)
    faltan = sorted(rutas_plan - rutas_arbol)
    sobran = sorted(rutas_arbol - rutas_plan - rutas_pruebas)

    if faltan:
        print("FALLO: faltan archivos declarados en el plan:")
        for r in faltan:
            print(f"  - {r}")
    if sobran:
        print("FALLO: hay archivos no declarados en el plan:")
        for r in sobran:
            print(f"  - {r}")
    if not faltan and not sobran:
        print(f"OK: el árbol coincide con el plan ({len(rutas_plan)} archivos){sufijo_ignorados}")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
