#!/usr/bin/env python3
"""sqlnb.py - Lectura de los notebooks .dbcnb (YAML de DBCode) y extracción de objetos SQL.

Librería compartida por touched-objects.py, sql-lint.py y sql-sandbox.py. No tiene CLI.

Un .dbcnb es un YAML con `cells:`; cada celda tiene `kind` (1 = markdown, 2 = sql), `languageId`
y `value`. Una celda SQL suele crear un objeto (`DROP ... IF EXISTS` + `CREATE ...`), pero puede
contener varios. La unidad que el flujo versiona y revisa es el OBJETO (tipo + nombre) y el texto de
su celda.

NOTEBOOK_DIR, DATABASE, los nombres de notebooks y su orden de carga se leen de .agents/stack.yaml
(vía stack.py del mismo directorio): si falta el archivo o sus claves, el import termina
con `BLOCKED (infraestructura)`.
"""
import hashlib
import os
import re
import subprocess
import sys

try:
    import yaml
except ImportError:  # se comprueba también en preflight.sh
    sys.stderr.write("BLOCKED (infraestructura): falta PyYAML (python3 -m pip install pyyaml).\n")
    sys.exit(2)

# Parámetros del proyecto: única fuente .agents/stack.yaml (vía el lector stack.py del mismo .agents).
from stack import get as stack_get

NOTEBOOK_DIR = stack_get("base_de_datos.carpeta_notebooks")
DATABASE = stack_get("base_de_datos.nombre")
NOTEBOOKS = stack_get("notebooks") or {}

# Orden de carga en el sandbox: primero el esquema y los objetos de los que dependen otros (funciones antes que
# procedimientos, vistas y triggers), después los datos de prueba y por último los libros de pruebas.
# Los nombres concretos de los notebooks son los del mapa `notebooks` de stack.yaml.
_ORDER_KEYS = [
    "tablas", "funciones", "vistas", "procedimientos", "triggers", "eventos",
    "migraciones", "datos_prueba",
]
LOAD_ORDER = [NOTEBOOKS[k] for k in _ORDER_KEYS if k in NOTEBOOKS and NOTEBOOKS[k]]


def is_test_book(name):
    """True si el notebook es uno de los libros de pruebas (`pruebas_*` de stack.yaml) o sigue su prefijo canónico."""
    if any(k.startswith("pruebas_") and v == name for k, v in NOTEBOOKS.items()):
        return True
    return name.startswith("Book de pruebas")


def book_order(names):
    """Orden de carga de los notebooks presentes: los conocidos, luego los desconocidos, y los libros de pruebas al final."""
    names = list(names)
    known = [n for n in LOAD_ORDER if n in names]
    others = sorted(n for n in names if n not in LOAD_ORDER and not is_test_book(n))
    tests = sorted(n for n in names if is_test_book(n))
    return known + others + tests


def has_delimiter(sql):
    """True si la celda ya trae sus propias sentencias `DELIMITER` (celdas pensadas para ejecutarse como script plano)."""
    return re.search(r"(?im)^\s*DELIMITER\s+\S+", sql) is not None


def strip_delimiter_lines(sql):
    """Quita las líneas `DELIMITER x` y deja un único `;` como terminador, para analizar el texto con las reglas del linter."""
    out = []
    delim = ";"
    for line in sql.split("\n"):
        m = re.match(r"\s*DELIMITER\s+(\S+)\s*$", line, re.I)
        if m:
            delim = m.group(1)
            continue
        if delim != ";" and line.rstrip().endswith(delim):
            line = line.rstrip()[: -len(delim)] + ";"
        out.append(line)
    return "\n".join(out)


TYPES = r"(?:TINYINT|SMALLINT|MEDIUMINT|MIDDLEINT|BIGINT|INTEGER|INT1|INT2|INT3|INT4|INT8|INT|SERIAL|BIT|DECIMAL|DEC|NUMERIC|FIXED|FLOAT|DOUBLE(?:\s+PRECISION)?|REAL|NATIONAL\s+(?:VARCHAR|CHARACTER(?:\s+VARYING)?|CHAR(?:\s+VARYING)?)|NVARCHAR|NCHAR|VARCHAR|CHARACTER(?:\s+VARYING)?|CHAR|TINYTEXT|MEDIUMTEXT|LONGTEXT|TEXT|DATETIME|TIMESTAMP|DATE|TIME|YEAR|BOOLEAN|BOOL|ENUM|SET|JSON|TINYBLOB|MEDIUMBLOB|LONGBLOB|BLOB|BINARY|VARBINARY|GEOMETRYCOLLECTION|GEOMETRY|POINT|LINESTRING|POLYGON|MULTIPOINT|MULTILINESTRING|MULTIPOLYGON)"

# El esquema cualificador no forma parte del identificador estable del objeto.
SQL_NAME = r"(?:`?\w+`?\s*\.\s*)?`?(\w+)`?"
ROUTINE_HEADER = (r"\bCREATE\s+(?:DEFINER\s*=\s*\S+\s+)?"
                  r"(?:PROCEDURE|FUNCTION)\s+(?:IF\s+NOT\s+EXISTS\s+)?" + SQL_NAME)
CREATE_RE = re.compile(
    r"CREATE\s+(?:OR\s+REPLACE\s+)?(?:DEFINER\s*=\s*\S+\s+)?"
    r"(TABLE|PROCEDURE|TRIGGER|VIEW|FUNCTION|EVENT|DATABASE|SCHEMA)\s+(?:IF\s+NOT\s+EXISTS\s+)?" + SQL_NAME,
    re.I,
)


def repo_root():
    out = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if out.returncode != 0:
        sys.stderr.write("BLOCKED (infraestructura): no se ejecuta dentro de un repositorio git.\n")
        sys.exit(2)
    return out.stdout.strip()


def strip_comments(sql):
    """Quita comentarios `-- ...`, `# ...` y `/* ... */` respetando literales de cadena."""
    out, i, n = [], 0, len(sql)
    while i < n:
        c = sql[i]
        if c in ("'", '"', "`"):
            j = i + 1
            while j < n:
                if sql[j] == "\\" and c != "`":
                    j += 2
                    continue
                if sql[j] == c:
                    if j + 1 < n and sql[j + 1] == c:
                        j += 2
                        continue
                    break
                j += 1
            out.append(sql[i:j + 1])
            i = j + 1
        elif sql.startswith("--", i) and (i + 2 >= n or sql[i + 2] in " \t\r\n"):
            while i < n and sql[i] != "\n":
                i += 1
        elif c == "#":
            while i < n and sql[i] != "\n":
                i += 1
        elif sql.startswith("/*", i):
            j = sql.find("*/", i + 2)
            i = n if j < 0 else j + 2
        else:
            out.append(c)
            i += 1
    return "".join(out)


def normalize(sql):
    """Texto comparable: sin comentarios, espacios colapsados."""
    return re.sub(r"\s+", " ", strip_comments(sql)).strip()


def digest(sql):
    return hashlib.sha256(normalize(sql).encode("utf-8")).hexdigest()[:16]


def classify_cell(sql):
    """Devuelve lista de (tipo, nombre) creados por la celda, o [('TEST', '')]/[('DATA', '')].

    Clasifica cada sentencia por su primera palabra y mira INSERT, UPDATE y DELETE antes que
    SELECT: una celda que inserta (o actualiza o borra) datos es DATA, aunque después verifique
    el resultado con un SELECT.
    """
    body = strip_comments(sql)
    masked = re.sub(r"'(?:[^'\\]|\\.|'')*'|\"(?:[^\"\\]|\\.|\"\")*\"", lambda m: ' ' * len(m[0]), body)
    matches = list(CREATE_RE.finditer(masked))
    event_ranges = []
    for match in matches:
        if match[1].upper() != 'EVENT':
            continue
        action = re.search(r'\bDO\b', masked[match.end():], re.I)
        if not action:
            continue
        start = match.end() + action.end()
        block = re.match(r'\s*BEGIN\b', masked[start:], re.I)
        end = masked.find(';', start)
        if block:
            depth = 0
            for token in re.finditer(r'\bBEGIN\b|\bEND\b(?!\s+(?:IF|CASE|LOOP|WHILE|REPEAT)\b)', masked[start:], re.I):
                depth += 1 if token[0].upper() == 'BEGIN' else -1
                if depth == 0:
                    end = start + token.end()
                    break
        event_ranges.append((start, end if end >= 0 else len(masked)))
    found = [(m[1].upper().replace('SCHEMA','DATABASE'),m[2]) for m in matches if not any(start <= m.start() < end for start,end in event_ranges)]
    if found:
        return found
    primeras = []
    for sentencia in body.split(";"):
        sentencia = sentencia.strip()
        if not sentencia:
            continue
        primera = re.match(r"([A-Za-z_]+)", sentencia)
        primeras.append(primera.group(1).upper() if primera else "")
    if any(primera in ("INSERT", "UPDATE", "DELETE") for primera in primeras):
        return [("DATA", "")]
    if primeras and all(primera in ("CALL", "SELECT") for primera in primeras):
        return [("TEST", "")]
    return [("OTRO", "")]


def parse_notebook(text, book):
    """Lista de celdas SQL: {libro, celda, tipo, nombre, sql, hash}. Una entrada por objeto."""
    data = yaml.safe_load(text) or {}
    objects = []
    for idx, cell in enumerate(data.get("cells", [])):
        if cell.get("languageId") != "sql":
            continue
        sql = cell.get("value", "")
        for kind, name in classify_cell(sql):
            objects.append({
                "libro": book, "celda": idx, "tipo": kind, "nombre": name,
                "sql": sql, "hash": digest(sql),
            })
    return objects


def load_working_tree(root, sin_datos_prueba=False):
    objects = {}
    base = os.path.join(root, NOTEBOOK_DIR)
    if sin_datos_prueba and (os.path.islink(base) or os.path.commonpath([os.path.realpath(root), os.path.realpath(base)]) != os.path.realpath(root)):
        raise ValueError('carpeta de notebooks fuera del alcance permitido')
    if not os.path.isdir(base):
        return objects
    excluded = {NOTEBOOKS.get('datos_prueba'), 'Datos de prueba para las tablas principales.dbcnb'}
    excluded_paths = {os.path.realpath(os.path.join(base,n)) for n in excluded if n}
    for name in sorted(os.listdir(base)):
        path = os.path.join(base, name)
        if sin_datos_prueba and (name in excluded or os.path.islink(path) or os.path.realpath(path) in excluded_paths):
            continue
        if name.endswith(".dbcnb"):
            with open(os.path.join(base, name), encoding="utf-8") as fh:
                objects[name] = parse_notebook(fh.read(), name)
    return objects


def load_ref(root, ref):
    """Objetos de los notebooks tal como están en `ref` (un commit); {} si el libro no existía."""
    ls = subprocess.run(["git", "ls-tree", "-r", "--name-only", ref, "--", NOTEBOOK_DIR],
                        cwd=root, capture_output=True, text=True)
    if ls.returncode != 0:
        sys.stderr.write(f"BLOCKED (infraestructura): la referencia base '{ref}' no existe.\n")
        sys.exit(2)
    objects = {}
    for path in ls.stdout.splitlines():
        if path.endswith(".dbcnb"):
            blob = subprocess.run(["git", "show", f"{ref}:{path}"], cwd=root, capture_output=True)
            objects[os.path.basename(path)] = parse_notebook(blob.stdout.decode("utf-8"), os.path.basename(path))
    return objects


def key(obj):
    """Identidad estable de un objeto: libro + tipo + nombre. Las celdas de prueba/datos usan su hash."""
    if obj["tipo"] in ("TEST", "DATA", "OTRO"):
        return (obj["libro"], obj["tipo"], obj["hash"])
    return (obj["libro"], obj["tipo"], obj["nombre"].lower())


def split_routine(sql):
    """Separa una celda en (prefijo ejecutable normal, cuerpo de rutina | None).

    Los CREATE PROCEDURE/TRIGGER/FUNCTION contienen `;` internos y el cliente `mysql` los cortaría:
    el cuerpo se ejecuta con un delimitador propio.
    """
    m = re.search(r"CREATE\s+(?:DEFINER\s*=\s*\S+\s+)?(PROCEDURE|TRIGGER|FUNCTION)\b", sql, re.I)
    if not m:
        return sql, None
    start = m.start()
    # el comentario previo al CREATE queda en el prefijo, que es inocuo
    return sql[:start], sql[start:].rstrip().rstrip(";").rstrip()
