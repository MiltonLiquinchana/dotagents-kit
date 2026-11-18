#!/usr/bin/env python3
"""touched-objects.py - Objetos SQL tocados respecto a la base (repositorio de base de datos).

Equivale a touched-files.sh de los otros repos, pero la unidad no es el fichero sino el OBJETO
(tabla, procedimiento, trigger...) que vive dentro de una celda de un notebook .dbcnb.

Uso:
  touched-objects.py [--base <ref>] [--compact]

Salida (stdout): array JSON. Cada entrada:
  libro, celda, tipo (TABLE|PROCEDURE|TRIGGER|VIEW|FUNCTION|DATABASE|TEST|DATA|OTRO), nombre,
  estado (nuevo|modificado|eliminado), sql (contenido actual, null si eliminado),
  sqlBase (contenido base, null si nuevo), hash, hashBase

Base: HEAD por defecto. El flujo exige árbol limpio al inicio (preflight.sh) y comitea una sola vez
al final, así que HEAD es exactamente "el estado previo a la feature".
Se omiten los objetos cuyo contenido normalizado (sin comentarios ni espacios) no cambió.

Códigos de salida: 0 = OK, 2 = BLOCKED (infraestructura).
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sqlnb  # noqa: E402


def touched(root, base_ref):
    base = sqlnb.load_ref(root, base_ref)
    now = sqlnb.load_working_tree(root)
    base_idx = {sqlnb.key(o): o for objs in base.values() for o in objs}
    now_idx = {sqlnb.key(o): o for objs in now.values() for o in objs}
    out = []
    for k, o in now_idx.items():
        b = base_idx.get(k)
        if b is None:
            out.append({**_meta(o), "estado": "nuevo", "sql": o["sql"], "sqlBase": None,
                        "hash": o["hash"], "hashBase": None})
        elif b["hash"] != o["hash"]:
            out.append({**_meta(o), "estado": "modificado", "sql": o["sql"], "sqlBase": b["sql"],
                        "hash": o["hash"], "hashBase": b["hash"]})
    for k, b in base_idx.items():
        if k not in now_idx:
            out.append({**_meta(b), "estado": "eliminado", "sql": None, "sqlBase": b["sql"],
                        "hash": None, "hashBase": b["hash"]})
    out.sort(key=lambda e: (e["libro"], e["celda"], e["nombre"]))
    return out


def _meta(o):
    return {"libro": o["libro"], "celda": o["celda"], "tipo": o["tipo"], "nombre": o["nombre"]}


def main(argv):
    base_ref, compact = "HEAD", False
    i = 0
    while i < len(argv):
        if argv[i] == "--base" and i + 1 < len(argv):
            base_ref = argv[i + 1]
            i += 2
        elif argv[i] == "--compact":
            compact = True
            i += 1
        else:
            sys.stderr.write(f"BLOCKED (infraestructura): argumento desconocido: {argv[i]}\n")
            return 2
    root = sqlnb.repo_root()
    os.chdir(root)
    sys.stderr.write(f"BASE={base_ref}\n")
    result = touched(root, base_ref)
    if compact:
        result = [{k: v for k, v in e.items() if k not in ("sql", "sqlBase")} for e in result]
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
