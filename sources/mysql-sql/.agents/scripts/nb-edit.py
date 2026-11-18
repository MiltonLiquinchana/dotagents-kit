#!/usr/bin/env python3
"""nb-edit.py - Escribe UNA celda SQL en un notebook .dbcnb sin tocar el resto del fichero.

Es la herramienta de persistencia del flujo (equivale a file-writer en los repos de código): regenerar un
notebook entero con un dumper de YAML reescribiría todas sus celdas; aquí solo cambia el bloque de la celda
indicada y el resto del fichero queda byte a byte igual. Después de escribir, el script re-lee el notebook y
comprueba que (1) es YAML válido, (2) el objeto quedó con el contenido pedido y (3) el resto de celdas no cambió.

Uso:
  nb-edit.py upsert --sql-file <ruta.sql> [--book "<libro>.dbcnb"] [--after <celda>] [--markdown "<título>"]
      Reemplaza la celda que define el mismo objeto (tipo + nombre) o, si no existe, la añade al final
      (o tras la celda <celda>). --markdown añade antes una celda de texto con ese título. Si no se da
      --book, el notebook canónico del tipo de objeto se resuelve con el mapa `notebooks` de
      .agents/stack.yaml (TABLE→tablas, PROCEDURE→procedimientos, FUNCTION→funciones, VIEW→vistas,
      TRIGGER→triggers, EVENT→eventos, DATABASE→tablas). Si el notebook aún no existe, se crea vacío con el formato
      mínimo (`cells:` vacío + `metadata: {}`).
  nb-edit.py append --book "<libro>.dbcnb" --sql-file <ruta.sql> [--markdown "<título>"]
      Añade al final una celda SQL que no define un objeto (una prueba o datos de prueba), sin reemplazar nada.
      Si el mismo texto exacto (comentarios incluidos) ya existe en el notebook, no la duplica; si el
      notebook no existe, se crea vacío con el formato mínimo.
  nb-edit.py delete --book "<libro>.dbcnb" --object <nombre>
      Elimina la celda SQL que define ese objeto.
  nb-edit.py show --book "<libro>.dbcnb" --object <nombre>
      Imprime el SQL de la celda de ese objeto.
  nb-edit.py upsert-test --book "<libro>.dbcnb" --id <id> --sql-file <ruta.sql>
      Reemplaza o añade una celda de prueba identificada por `-- @test: <id>` en su primera línea.
  nb-edit.py upsert-doc --book "<libro>.dbcnb" --object <nombre> --markdown-file <ruta.md>
      Reemplaza o inserta una celda markdown justo después de la celda SQL del objeto.

Códigos de salida: 0 = OK, 1 = la verificación posterior falló (el fichero se restaura), 2 = BLOCKED (infraestructura).
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sqlnb  # noqa: E402
import yaml  # noqa: E402

CELL_START = re.compile(r"^  - kind:", re.M)

# Clave del mapa `notebooks` de stack.yaml que corresponde a cada tipo de objeto canónico
CANONICAL_BOOK = {
    "TABLE": "tablas", "DATABASE": "tablas", "PROCEDURE": "procedimientos",
    "FUNCTION": "funciones", "VIEW": "vistas", "TRIGGER": "triggers", "EVENT": "eventos",
}


def die(msg, code=2):
    sys.stderr.write(f"BLOCKED (infraestructura): {msg}\n" if code == 2 else f"{msg}\n")
    sys.exit(code)


def split_blocks(text):
    """(cabecera, [bloques de celda], cierre del fichero) conservando el texto exacto."""
    starts = [m.start() for m in CELL_START.finditer(text)]
    if not starts:
        # notebook vacío recién creado (`cells: []` + cierre): la cabecera es la línea `cells:`;
        # un notebook con celdas pero sin el formato esperado sigue siendo un bloqueo.
        m = re.search(r"^cells:\s*(\[.*\]\s*)?$", text, re.M)
        if not m:
            die("el notebook no tiene celdas ('  - kind:').")
        head = text[: m.end()] + "\n"
        return head, [], text[len(head):]
    head = text[:starts[0]]
    blocks = [text[s:e] for s, e in zip(starts, starts[1:] + [len(text)])]
    # el último bloque puede arrastrar claves de primer nivel (p. ej. `metadata: {}`): no son parte de la celda
    tail = ""
    m = re.search(r"^\S", blocks[-1], re.M)
    if m:
        tail = blocks[-1][m.start():]
        blocks[-1] = blocks[-1][:m.start()]
    return head, blocks, tail


def block_cell(block):
    data = yaml.safe_load("cells:\n" + block)
    return data["cells"][0]


def render_cell(kind_sql, value):
    if kind_sql:
        header = "  - kind: 2\n    languageId: sql\n"
    else:
        header = "  - kind: 1\n    languageId: markdown\n"
    body = "\n".join(("      " + line) if line.strip() else "" for line in value.rstrip("\n").split("\n"))
    # `|-` conserva el texto tal cual, sin salto final; las líneas en blanco quedan vacías
    return f"{header}    value: |-\n{body}\n    metadata: {{}}\n"


def object_of(cell):
    if cell.get("languageId") != "sql":
        return None
    kinds = [k for k in sqlnb.classify_cell(cell.get("value", "")) if k[0] not in ("TEST", "DATA", "OTRO")]
    return kinds[0] if kinds else None


def load(path):
    if not os.path.isfile(path):
        die(f"no existe el notebook {path}")
    with open(path, encoding="utf-8", newline="") as fh:
        return fh.read()


def verify(path, original_cells, expected_value, wanted):
    """Comprueba el notebook resultante. Devuelve un texto de problema o None."""
    new_text = load(path)
    try:
        cells = yaml.safe_load(new_text)["cells"]
    except Exception as exc:  # noqa: BLE001
        return f"el notebook resultante no es YAML válido: {exc}"
    before = [c for c in original_cells if not wanted(c)]
    after = [c for c in cells if not wanted(c)]
    # `after` debe ser `before` con, como mucho, una celda de texto añadida, y en el mismo orden
    if len(after) - len(before) not in (0, 1):
        return "cambió el número de celdas ajenas a la edición"
    it = iter(after)
    if not all(any(c == x for x in it) for c in before):
        return "alguna celda ajena a la edición cambió o se reordenó"
    if len(after) - len(before) == 1:
        extra = [c for c in after if c not in before]
        if len(extra) != 1 or extra[0].get("languageId") != "markdown":
            return "se añadió una celda que no es el texto pedido"
    matches = [c for c in cells if wanted(c)]
    if expected_value is None:
        return None if not matches else "la celda no se eliminó"
    if len(matches) != 1 or matches[0]["value"].strip() != expected_value.strip():
        return "la celda escrita no coincide con el contenido pedido"
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["upsert", "append", "delete", "show", "upsert-test", "upsert-doc"])
    ap.add_argument("--book")
    ap.add_argument("--sql-file")
    ap.add_argument("--object")
    ap.add_argument("--after", type=int)
    ap.add_argument("--markdown")
    ap.add_argument("--id")
    ap.add_argument("--markdown-file")
    a = ap.parse_args()

    root = sqlnb.repo_root()

    # upsert admite omitir --book: se resuelve con el notebook canónico del tipo de objeto
    # (mapa `notebooks` de .agents/stack.yaml).
    if a.action == "upsert" and a.book is None:
        if not a.sql_file:
            die("upsert requiere --sql-file")
        with open(a.sql_file, encoding="utf-8") as fh:
            upsert_sql = fh.read()
        kinds = [k for k in sqlnb.classify_cell(upsert_sql) if k[0] not in ("TEST", "DATA", "OTRO")]
        if len(kinds) != 1:
            die("la celda debe definir exactamente un objeto (tabla, procedimiento, trigger, vista, función o evento); "
                f"encontrados: {kinds}")
        canonical = CANONICAL_BOOK.get(kinds[0][0])
        a.book = sqlnb.NOTEBOOKS.get(canonical) if canonical else None
        if not a.book:
            die(f"no hay notebook canónico declarado en .agents/stack.yaml (mapa notebooks.*) "
                f"para objetos de tipo {kinds[0][0]}")
        sys.stderr.write(f"nb-edit: notebook canónico para {kinds[0][0]}: '{a.book}' (de .agents/stack.yaml).\n")
    if not a.book:
        die(f"--book es obligatorio para {a.action} (solo upsert lo omite y lo resuelve con stack.yaml)")

    book_dir = os.path.join(root, sqlnb.NOTEBOOK_DIR)
    path = os.path.join(book_dir, a.book)
    os.makedirs(book_dir, exist_ok=True)
    if a.action in ("upsert", "append", "upsert-test", "upsert-doc") and not os.path.isfile(path):
        # Notebook canónico nuevo: formato mínimo que preserva el formato DBCode
        # (`cells:` vacío; el guard `.get("cells") or []` lo pasa por lista vacía).
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write("cells:\nmetadata: {}\n")
        sys.stderr.write(f"nb-edit: notebook nuevo creado: {a.book}.\n")
    text = load(path)
    head, blocks, tail = split_blocks(text)
    original_cells = (yaml.safe_load(text) or {}).get("cells") or []

    if a.action in ("upsert-test", "upsert-doc"):
        if a.action == "upsert-test":
            if not a.id or not a.sql_file:
                die("upsert-test requiere --id y --sql-file")
            with open(a.sql_file, encoding="utf-8") as fh:
                value = fh.read()
            marker = f"-- @test: {a.id}"
            if not value.splitlines() or value.splitlines()[0].strip() != marker:
                die(f"la primera línea de la prueba debe ser `{marker}`")
            matches = [i for i, c in enumerate(original_cells)
                       if c.get("languageId") == "sql" and c.get("value", "").splitlines()
                       and c["value"].splitlines()[0].strip() == marker]
            if len(matches) > 1:
                die(f"el id de prueba '{a.id}' aparece más de una vez")
            idx = matches[0] if matches else None
            wanted = lambda c, m=marker: c.get("languageId") == "sql" and c.get("value", "").splitlines() and c["value"].splitlines()[0].strip() == m
            block = render_cell(True, value)
        else:
            if not a.object or not a.markdown_file:
                die("upsert-doc requiere --object y --markdown-file")
            with open(a.markdown_file, encoding="utf-8") as fh:
                value = fh.read()
            obj = next((i for i,c in enumerate(original_cells) if (object_of(c) or ("", ""))[1].lower() == a.object.lower()), None)
            if obj is None:
                die(f"no se encontró el objeto SQL '{a.object}' en {a.book}", 1)
            doc_marker = f"<!-- @doc: {a.object.lower()} -->"
            idx = obj + 1 if obj + 1 < len(original_cells) and original_cells[obj+1].get("languageId") == "markdown" and original_cells[obj+1].get("value", "").startswith(doc_marker) else None
            wanted = lambda c, ob=a.object.lower(): c.get("languageId") == "markdown" and c.get("value", "").startswith(f"<!-- @doc: {ob} -->")
            value = f"{doc_marker}\n{value.rstrip()}"
            block = render_cell(False, value)
        if blocks and not blocks[-1].endswith("\n"):
            blocks[-1] += "\n"
        if idx is None:
            if a.action == "upsert-doc":
                blocks.insert(obj + 1, block)
            else:
                blocks.append(block)
        else:
            blocks[idx] = block
        new_text = head + "".join(blocks) + tail
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write(new_text)
        try:
            cells = (yaml.safe_load(load(path)) or {}).get("cells") or []
        except Exception as exc:  # noqa: BLE001
            cells = []
        hits = [c for c in cells if wanted(c)]
        if len(hits) != 1 or hits[0].get("value", "").strip() != value.strip():
            with open(path, "w", encoding="utf-8", newline="") as fh:
                fh.write(text)
            die("la celda de prueba/documentación no quedó única y con el contenido pedido; el notebook se restauró.", 1)
        sys.stderr.write(f"nb-edit: {a.action} OK en {a.book}.\n")
        return 0

    if a.action == "show":
        if not a.object:
            die("show requiere --object")
        for cell in original_cells:
            o = object_of(cell)
            if o and o[1].lower() == a.object.lower():
                print(cell["value"])
                return 0
        die(f"'{a.object}' no está en {a.book}", 1)

    if a.action == "delete":
        if not a.object:
            die("delete requiere --object")
        idx = next((i for i, b in enumerate(blocks) if (object_of(block_cell(b)) or ("", ""))[1].lower() == a.object.lower()), None)
        if idx is None:
            die(f"'{a.object}' no está en {a.book}", 1)
        wanted = lambda c: (object_of(c) or ("", ""))[1].lower() == a.object.lower()  # noqa: E731
        new_blocks = blocks[:idx] + blocks[idx + 1:]
        new_text = head + "".join(new_blocks) + tail
        expected = None
    elif a.action == "append":
        if not a.sql_file:
            die("append requiere --sql-file")
        with open(a.sql_file, encoding="utf-8") as fh:
            sql = fh.read()
        if any(k[0] not in ("TEST", "DATA", "OTRO") for k in sqlnb.classify_cell(sql)):
            die("append es para pruebas y datos de prueba; para un objeto usa upsert.")
        # Se compara el texto EXACTO (sin recortar comentarios): las directivas `-- @expect-*` son la prueba, así que
        # dos celdas con el mismo CALL y distintas directivas son pruebas distintas.
        exact = sql.strip()
        if any(c.get("languageId") == "sql" and c.get("value", "").strip() == exact for c in original_cells):
            sys.stderr.write("nb-edit: la celda ya existe; no se duplica.\n")
            return 0
        if blocks and not blocks[-1].endswith("\n"):
            blocks[-1] += "\n"
        md = render_cell(False, a.markdown) if a.markdown else ""
        blocks.append(md + render_cell(True, sql))
        new_text = head + "".join(blocks) + tail
        expected = sql
        wanted = lambda c, e=exact: c.get("languageId") == "sql" and c.get("value", "").strip() == e  # noqa: E731
    else:
        if not a.sql_file:
            die("upsert requiere --sql-file")
        with open(a.sql_file, encoding="utf-8") as fh:
            sql = fh.read()
        kinds = [k for k in sqlnb.classify_cell(sql) if k[0] not in ("TEST", "DATA", "OTRO")]
        if len(kinds) != 1:
            die("la celda debe definir exactamente un objeto (tabla, procedimiento, trigger, vista, función o evento); "
                f"encontrados: {kinds}")
        kind, name = kinds[0]
        # comparación sin distinguir mayúsculas del nombre, como hace sqlnb.key
        wanted = lambda c, kind=kind, name=name: (object_of(c) or ("", ""))[0] == kind and (object_of(c) or ("", ""))[1].lower() == name.lower()  # noqa: E731
        new_block = render_cell(True, sql)
        if blocks and not blocks[-1].endswith("\n"):
            blocks[-1] += "\n"  # el último bloque original puede no terminar en salto de línea
        idx = next((i for i, b in enumerate(blocks) if wanted(block_cell(b))), None)
        if idx is not None:
            blocks[idx] = new_block
        else:
            md = render_cell(False, a.markdown) if a.markdown else ""
            insert_at = (a.after + 1) if a.after is not None and 0 <= a.after < len(blocks) else len(blocks)
            blocks[insert_at:insert_at] = [md + new_block] if md else [new_block]
        new_text = head + "".join(blocks) + tail
        expected = sql

    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(new_text)
    problem = verify(path, original_cells, expected, wanted)
    if problem:
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
        die(f"{problem}; el notebook se restauró.", 1)
    sys.stderr.write(f"nb-edit: {a.action} OK en {a.book}.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
