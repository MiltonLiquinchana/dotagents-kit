#!/usr/bin/env python3
"""db-index.py - Índice determinista de objetos SQL y sus dependencias (sustituto del grafo de código).

Los repos de código consultan el grafo (`codebase-memory-mcp cli search_graph`) antes de abrir ficheros. Aquí el equivalente es
este índice, calculado SOLO a partir de los notebooks .dbcnb (sin conectarse a ninguna base de datos).

Uso:
  db-index.py                      Resumen: nº de objetos por tipo.
  db-index.py --object <nombre>    Ficha de un objeto: parámetros, tablas, llamadas, alias del resultado.
  db-index.py --table <Tabla>      Quién usa la tabla: procedimientos, triggers y tablas que la referencian por FK.
  db-index.py --list <tipo>        Nombres de los objetos de un tipo (TABLE|PROCEDURE|TRIGGER|VIEW|FUNCTION|EVENT).
  db-index.py --contracts          Contrato de cada procedimiento: parámetros y alias de su resultado.

Es heurístico (regex sobre texto sin comentarios): la fuente de verdad sigue siendo el notebook. Un
resultado vacío significa "no aparece en el SQL de los notebooks", no "no existe en la base real"
(la base viva puede tener deriva respecto a los notebooks). Un índice vacío (notebooks sin objetos
todavía) es un estado válido y termina con código 0.

Códigos de salida: 0 = OK, 2 = BLOCKED (infraestructura).
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sqlnb  # noqa: E402

KEYWORDS_AFTER_FROM = {"SELECT", "WHERE", "SET", "VALUES", "DUAL", "LATERAL", "DELETED", "NEW", "OLD"}


def index_objects(root, sin_datos_prueba=False):
    objs = []
    for libro, items in sqlnb.load_working_tree(root, sin_datos_prueba=sin_datos_prueba).items():
        for o in items:
            if o["tipo"] in ("TABLE", "PROCEDURE", "TRIGGER", "VIEW", "FUNCTION", "EVENT"):
                objs.append(o)
    return objs


def refs(code, own_name):
    """Tablas leídas/escritas, procedimientos llamados."""
    masked = sqlnb.strip_comments(code)
    tables = set()
    for m in re.finditer(r"\b(?:FROM|JOIN|INTO|UPDATE|TABLE|ON)\s+`?([A-Za-z_]\w*)`?", masked, re.I):
        name = m.group(1)
        if name.upper() in KEYWORDS_AFTER_FROM or name.upper() in ("IF", "NOT", "EXISTS", "SELECT"):
            continue
        tables.add(name)
    calls = {m.group(1) for m in re.finditer(r"\bCALL\s+`?(\w+)`?", masked, re.I)}
    # solo nombres que parecen tablas del esquema (empiezan en mayúscula); descarta alias y variables
    tables = {t for t in tables if t[0].isupper() and t != own_name}
    return sorted(tables), sorted(calls)


def routine_params(code):
    code = sqlnb.strip_comments(code)
    head = re.search(sqlnb.ROUTINE_HEADER + r"\s*\(", code, re.I)
    if not head:
        return []
    # Separar solo comas de la lista: tamaños y literales ENUM/SET pueden contener otras.
    items, start, depth, quote, i = [], head.end(), 0, None, head.end()
    while i < len(code):
        char = code[i]
        if quote:
            if char == "\\" and quote != "`":
                i += 2
                continue
            if char == quote:
                if i + 1 < len(code) and code[i + 1] == quote:
                    i += 2
                    continue
                quote = None
        elif char in ("'", '"', "`"):
            quote = char
        elif char == '(':
            depth += 1
        elif char == ')':
            if depth == 0:
                items.append(code[start:i].strip())
                break
            depth -= 1
        elif char == ',' and depth == 0:
            items.append(code[start:i].strip())
            start = i + 1
        i += 1
    else:
        return []
    out = []
    for item in items:
        param = re.fullmatch(
            r"(?:(INOUT|IN|OUT)\s+)?`?(\w+)`?\s+(" + sqlnb.TYPES +
            r"\b(?:\s*\([^)]*\))?)"
            r"(?:\s+(?:UNSIGNED|SIGNED|ZEROFILL|BINARY|ASCII|UNICODE|"
            r"(?:CHARACTER\s+SET|CHARSET|COLLATE)\s*(?:=\s*)?\w+))*", item, re.I)
        if param:
            out.append({"modo": (param[1] or "IN").upper(), "nombre": param[2],
                        "tipo": re.sub(r"\s+", "", param[3]).upper()})
    return out


def result_aliases(code):
    """Alias (o nombre de columna) del último SELECT que devuelve filas, en orden."""
    body = sqlnb.strip_comments(code)
    selects = [m for m in re.finditer(r"\bSELECT\b(?!\s+[^;]*\bINTO\b\s+[@\w])", body, re.I)]
    best = None
    for m in selects:
        seg = body[m.end(): body.find(";", m.end()) if body.find(";", m.end()) > 0 else len(body)]
        if re.search(r"\bINTO\b", seg.split("FROM")[0], re.I):
            continue
        best = seg
    if best is None:
        return []
    select_list = re.split(r"\bFROM\b", best, maxsplit=1, flags=re.I)[0]
    cols, depth, cur = [], 0, ""
    for ch in select_list:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            cols.append(cur)
            cur = ""
        else:
            cur += ch
    cols.append(cur)
    names = []
    for c in cols:
        c = c.strip()
        if not c:
            continue
        a = re.search(r"\bAS\s+`?(\w+)`?\s*$", c, re.I)
        if a:
            names.append(a.group(1))
        else:
            t = re.search(r"(\w+)\s*$", c)
            names.append(t.group(1) if t else c[:30])
    return names


def trigger_target(code):
    m = re.search(r"(BEFORE|AFTER)\s+(INSERT|UPDATE|DELETE)\s+ON\s+" + sqlnb.SQL_NAME, sqlnb.strip_comments(code), re.I)
    return {"momento": m.group(1).upper(), "evento": m.group(2).upper(), "tabla": m.group(3)} if m else None


def fk_refs(code):
    return sorted({m.group(1) for m in re.finditer(r"REFERENCES\s+`?(\w+)`?", sqlnb.strip_comments(code), re.I)})


def card(o):
    tables, calls = refs(o["sql"], o["nombre"])
    out = {"libro": o["libro"], "celda": o["celda"], "tipo": o["tipo"], "nombre": o["nombre"]}
    if o["tipo"] == "TABLE":
        out["fk_a"] = fk_refs(o["sql"])
    else:
        out["tablas"] = tables
        out["llama_a"] = calls
    if o["tipo"] in ("PROCEDURE", "FUNCTION"):
        out["parametros"] = routine_params(o["sql"])
        out["alias_resultado"] = result_aliases(o["sql"])
    if o["tipo"] == "TRIGGER":
        out["dispara_en"] = trigger_target(o["sql"])
    return out


def main(argv):
    root = sqlnb.repo_root()
    os.chdir(root)
    sin_datos = '--sin-datos-prueba' in argv
    argv = [a for a in argv if a != '--sin-datos-prueba']
    if sin_datos and not os.path.isdir(os.path.join(root, sqlnb.NOTEBOOK_DIR)):
        raise ValueError('carpeta de notebooks ausente')
    objs = index_objects(root, sin_datos)
    if not objs and not argv:
        # Base sin objetos todavía (proyecto recién inicializado o notebooks vacíos): un índice
        # vacío es un estado válido; no bloquea (el preflight lo reporta como aviso).
        json.dump({"objetos": {}}, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return 0
    if not argv:
        counts = {}
        for o in objs:
            counts[o["tipo"]] = counts.get(o["tipo"], 0) + 1
        result = {"objetos": counts}
    elif argv[0] == "--object" and len(argv) > 1:
        result = [card(o) for o in objs if o["nombre"].lower() == argv[1].lower()] or {"error": f"'{argv[1]}' no aparece en los notebooks"}
    elif argv[0] == "--table" and len(argv) > 1:
        t = argv[1]
        users = [card(o) for o in objs if o["tipo"] != "TABLE" and t in card(o).get("tablas", [])]
        fks = [o["nombre"] for o in objs if o["tipo"] == "TABLE" and t in fk_refs(o["sql"])]
        triggers = [c for c in users if c["tipo"] == "TRIGGER" and (c.get("dispara_en") or {}).get("tabla") == t]
        exists = any(o["tipo"] == "TABLE" and o["nombre"].lower() == t.lower() for o in objs)
        result = {"tabla": t, "existe_en_notebooks": exists,
                  "procedimientos": sorted(c["nombre"] for c in users if c["tipo"] == "PROCEDURE"),
                  "triggers_sobre_la_tabla": sorted(c["nombre"] for c in triggers),
                  "otros_triggers_que_la_usan": sorted(c["nombre"] for c in users if c["tipo"] == "TRIGGER" and c not in triggers),
                  "tablas_con_fk_hacia_ella": sorted(fks)}
    elif argv[0] == "--list" and len(argv) > 1:
        result = sorted(o["nombre"] for o in objs if o["tipo"] == argv[1].upper())
    elif argv[0] == "--contracts":
        result = [{"procedimiento": c["nombre"], "parametros": c["parametros"], "alias_resultado": c["alias_resultado"]}
                  for c in (card(o) for o in objs if o["tipo"] == "PROCEDURE")]
    else:
        sys.stderr.write("BLOCKED (infraestructura): uso: db-index.py [--object N | --table T | --list TIPO | --contracts]\n")
        return 2
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except (OSError, ValueError, TypeError, KeyError):
        sys.stderr.write('no se pudo leer el índice SQL permitido\n')
        sys.exit(2)
