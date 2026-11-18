#!/usr/bin/env python3
"""sql-lint.py - Gate diferencial determinista de SQL (MySQL) para el repositorio de base de datos.

Equivale al gate diferencial de SonarQube de los repos de código: SonarQube no analiza MySQL, así que
las reglas viven aquí. Para cada objeto tocado (touched-objects.py) compara los hallazgos de la
versión BASE (A) con los de la versión ACTUAL (B) y bloquea ante CUALQUIER hallazgo nuevo (B - A,
multiconjunto por regla + texto normalizado, sin números de línea). Un hallazgo preexistente en A no
bloquea aunque el objeto se toque.

Uso:
  sql-lint.py [--base <ref>]     Gate diferencial sobre los objetos tocados (JSON por stdout).
  sql-lint.py --canary           Comprueba que el linter detecta el fixture con defectos conocidos.
  sql-lint.py --registro [--completo] --sin-datos-prueba  Comparaciones de las doce nomenclaturas.
  sql-lint.py --calibrate        Lint de TODOS los objetos del árbol de trabajo (sin base), para medir ruido.

Códigos de salida: 0 = PASA, 1 = BLOQUEA (hay hallazgos nuevos), 2 = BLOCKED (infraestructura).

El gate revisa parámetros PROCEDURE/FUNCTION y variables de PROCEDURE/FUNCTION/TRIGGER/EVENT,
incluso con PREPARE/EXECUTE. Ante tipos o formas desconocidos, comprueba el prefijo
si extrae el nombre; sin nombre no emite hallazgo. El registro los cuenta como no evaluados.
CONDITION FOR, HANDLER y CURSOR no son variables de datos. DECLARE se busca solo
fuera de literales; las cadenas de SQL dinámico las cubre dynamic-sql.
Es heurístico (regex sobre texto sin comentarios ni literales). No sustituye la revisión humana ni la
ejecución real en el sandbox (sql-sandbox.py): detecta patrones, no semántica.
"""
import collections
from functools import lru_cache
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sqlnb  # noqa: E402

FIXTURE = ".agents/skills/sql-code-reviewer/fixtures/CanarySql.sql"
CANARY_RULES = {"select-star", "dynamic-sql", "destructive", "exit-handler"}

ROUTINE_KINDS = ("PROCEDURE", "FUNCTION", "TRIGGER", "VIEW")
TYPES = sqlnb.TYPES
NON_COLUMN = {"PRIMARY", "FOREIGN", "INDEX", "UNIQUE", "KEY", "CONSTRAINT", "CHECK", "FULLTEXT", "SPATIAL"}


# ---------------------------------------------------------------- utilidades de texto
def mask_strings(sql):
    """Sustituye el contenido de los literales de cadena por 'x' conservando las comillas."""
    def repl(m):
        q = m.group(0)[0]
        return q + "x" * max(len(m.group(0)) - 2, 0) + q
    return re.sub(r"'(?:[^'\\]|\\.|'')*'|\"(?:[^\"\\]|\\.|\"\")*\"", repl, sql)


def clean(sql):
    return sqlnb.strip_comments(sql)


def statements(text):
    return [s.strip() for s in text.split(";") if s.strip()]


def snippet(text, width=140):
    return re.sub(r"\s+", " ", text).strip()[:width]


SQL_NAME = sqlnb.SQL_NAME
ROUTINE_HEADER = sqlnb.ROUTINE_HEADER

def routine_name(code, kind_pattern=r"PROCEDURE|FUNCTION|TRIGGER|VIEW"):
    m = re.search(rf"CREATE\s+(?:DEFINER\s*=\s*\S+\s+)?(?:{kind_pattern})\s+(?:IF\s+NOT\s+EXISTS\s+)?" + SQL_NAME, code, re.I)
    return m.group(1) if m else ""


# ---------------------------------------------------------------- reglas
# Cada regla recibe (obj_tipo, nombre, sql_original) y devuelve lista de textos de hallazgo.

def r_select_star(tipo, nombre, sql):
    m = mask_strings(clean(sql))
    return [snippet(x.group(0)) for x in re.finditer(r"\bSELECT\s+(?:DISTINCT\s+)?(?:\w+\.)?\*|,\s*\w+\.\*", m, re.I)]


def r_dynamic_sql(tipo, nombre, sql):
    code = clean(sql)
    out = []
    for st in statements(code):
        if re.search(r"\bPREPARE\b", st, re.I) and (re.search(r"CONCAT\s*\(", st, re.I) or re.search(r"\bFROM\s+@", st, re.I)):
            out.append(snippet(st))
    # SET @sql = CONCAT(...) que luego se prepara
    if re.search(r"\bPREPARE\b", code, re.I):
        for m in re.finditer(r"SET\s+@\w+\s*=\s*CONCAT\s*\([^;]*", code, re.I):
            out.append(snippet(m.group(0)))
    return out


def r_destructive(tipo, nombre, sql):
    code = mask_strings(clean(sql))
    out = []
    if tipo == 'EVENT':
        header = sqlnb.CREATE_RE.search(code)
        action = re.search(r'\bDO\b', code[header.end():], re.I) if header else None
        if action:
            code = code[header.end() + action.end():]
    for st in statements(code):
        if tipo == 'EVENT':
            st = re.sub(r'^\s*(?:(?:\w+\s*:\s*)?BEGIN\b\s*)+', '', st, flags=re.I)
        s = snippet(st)
        if re.match(r"DROP\s+(?:TABLE|DATABASE|SCHEMA)\b", s, re.I):
            out.append(s)
        elif re.match(r"TRUNCATE\b", s, re.I):
            out.append(s)
        elif re.match(r"DELETE\s+FROM\b", s, re.I) and not re.search(r"\bWHERE\b", s, re.I):
            out.append(s)
        elif re.match(r"UPDATE\b", s, re.I) and re.search(r"\bSET\b", s, re.I) and not re.search(r"\bWHERE\b", s, re.I):
            out.append(s)
    return out


def r_definer(tipo, nombre, sql):
    return [snippet(m.group(0)) for m in re.finditer(r"DEFINER\s*=\s*\S+", clean(sql), re.I)]


def r_credentials(tipo, nombre, sql):
    code = clean(sql)
    out = [snippet(m.group(0)) for m in re.finditer(r"\b(?:GRANT\b[^;]*|CREATE\s+USER\b[^;]*|ALTER\s+USER\b[^;]*|SET\s+PASSWORD\b[^;]*)", code, re.I)]
    out += ["IDENTIFIED BY ..." for _ in re.finditer(r"\bIDENTIFIED\s+BY\b", code, re.I)]
    return out


def r_hardcoded_secret(tipo, nombre, sql):
    code = clean(sql)
    # columna de contraseña/token con literal largo asignado o insertado: se informa sin el valor
    out = [snippet(re.sub(r"'[^']*'", "'***'", m.group(0))) for m in
           re.finditer(r"\b(?:password|passwd|pwd|secret|token)\w*\s*=\s*'[^']{6,}'", code, re.I)]
    if tipo == "DATA":
        for m in re.finditer(r"INSERT\s+INTO\s+`?(\w+)`?\s*\(([^)]*)\)", code, re.I):
            cols = m.group(2)
            if re.search(r"\b\w*(password|passwd|secret|token)\w*\b", cols, re.I):
                out.append(f"INSERT INTO {m.group(1)} con columna de credencial")
    return out


def r_non_idempotent(tipo, nombre, sql):
    code = clean(sql)
    out = []
    for m in re.finditer(r"CREATE\s+(?:OR\s+REPLACE\s+)?(?:DEFINER\s*=\s*\S+\s+)?(PROCEDURE|FUNCTION|TRIGGER|VIEW|TABLE|EVENT)\s+(IF\s+NOT\s+EXISTS\s+)?" + SQL_NAME, code, re.I):
        kind, ine, name = m.group(1).upper(), m.group(2), m.group(3)
        if kind == "TABLE":
            if not ine:
                out.append(f"CREATE TABLE {name} sin IF NOT EXISTS")
        elif kind == "EVENT" and ine:
            continue
        elif "OR REPLACE" in m.group(0).upper():
            continue
        elif not re.search(rf"DROP\s+{kind}\s+IF\s+EXISTS\s+" + SQL_NAME.replace(r"(\w+)", re.escape(name)) + r"(?!\w)", code, re.I):
            out.append(f"CREATE {kind} {name} sin DROP {kind} IF EXISTS previo")
    return out


def r_missing_use(tipo, nombre, sql):
    if tipo not in ROUTINE_KINDS:
        return []
    return [] if re.search(rf"\bUSE\s+`?{sqlnb.DATABASE}`?\s*;", clean(sql), re.I) else [f"{tipo} {nombre} sin USE {sqlnb.DATABASE};"]


@lru_cache(maxsize=None)
def naming_setting(key):
    # Un proceso inspecciona una única instantánea del stack.
    return sqlnb.stack_get(key)


NAME_KEYS = {'PROCEDURE':'prefijo_procedimiento', 'FUNCTION':'prefijo_funcion',
             'VIEW':'prefijo_vista', 'TRIGGER':'prefijo_trigger', 'EVENT':'prefijo_evento'}


def naming_name(tipo, nombre):
    """Única regla de prefijos, compartida por gate y comparaciones por nombre."""
    if not nombre or tipo not in NAME_KEYS:
        return []
    prefijo = naming_setting('nomenclatura.' + NAME_KEYS[tipo])
    valores = prefijo if isinstance(prefijo, list) else [prefijo]
    if tipo in ('PROCEDURE', 'FUNCTION'):
        correcto = any(re.fullmatch(re.escape(p) + r'[a-z][a-z0-9]*(?:_[a-z0-9]+)*', nombre) for p in valores)
    else:
        correcto = any(nombre.startswith(p) for p in valores)
    return [] if correcto else [f"{tipo} '{nombre}' debe usar el prefijo configurado: {' | '.join(valores)}"]


def identifier_prefix(name, prefix):
    return bool(re.fullmatch(re.escape(prefix) + r"\w+", name))


def r_naming(tipo, nombre, sql):
    out = naming_name(tipo, nombre)
    params, variables, unknown = declarations(tipo, nombre, sql, for_gate=True)
    for label, key, names in [('parámetro','prefijo_parametro',params), ('variable','prefijo_variable',variables)]:
        prefix = naming_setting('nomenclatura.'+key)
        for name in names:
            if not identifier_prefix(name,prefix):
                out.append(f"{label} '{name}' debe empezar por {prefix}")
    return out


def r_sql_data_access(tipo, nombre, sql):
    """Toda `CREATE PROCEDURE` declara su característica de acceso a datos: `READS SQL DATA` si
    el cuerpo solo lee y `MODIFIES SQL DATA` si escribe. Con `CONTAINS SQL` (el valor por
    defecto de MySQL) Connector/J rechaza las llamadas con conexión de solo lectura."""
    if tipo != "PROCEDURE":
        return []
    code = clean(sql)
    m = re.search(r"\bCREATE\s+(?:DEFINER\s*=\s*\S+\s+)?PROCEDURE\s+(?:IF\s+NOT\s+EXISTS\s+)?" + SQL_NAME + r"\s*\(", code, re.I)
    if not m:
        return []
    desde = code[m.end():]
    # Cabecera: opciones de la definición, hasta el primer BEGIN del cuerpo.
    k = re.search(r"\bBEGIN\b", desde, re.I)
    head = desde[: k.start()] if k else desde[:200]
    declarada = re.search(r"\b(READS|MODIFIES)\s+SQL\s+DATA\b", head, re.I)
    cuerpo = desde
    escribe = bool(re.search(r"\b(INSERT|UPDATE|DELETE|REPLACE|CREATE|DROP|ALTER|TRUNCATE|CALL)\b", mask_strings(cuerpo), re.I))
    requerida = "MODIFIES SQL DATA" if escribe else "READS SQL DATA"
    if not declarada:
        mensaje = (f"{nombre} no declara su característica de acceso a datos ({requerida}; el cuerpo "
                   f"{'escribe datos' if escribe else 'solo lee'})")
        if not escribe:
            mensaje += "; 'CONTAINS SQL' (por defecto) impide las llamadas con conexión readOnly"
        return [mensaje]
    if f"{declarada.group(1).upper()} SQL DATA" != requerida:
        return [f"{nombre} declara {declarada.group(1).upper()} SQL DATA pero el cuerpo "
                f"{'escribe datos' if escribe else 'solo lee'}: usa {requerida}"]
    return []


def r_list_order(tipo, nombre, sql):
    if tipo != "PROCEDURE" or not re.match(r"sp_listar_", nombre or ""):
        return []
    return [] if re.search(r"\bORDER\s+BY\b", clean(sql), re.I) else [f"{nombre} devuelve un listado sin ORDER BY (resultado no determinista)"]


def r_exit_handler(tipo, nombre, sql):
    """architecture-rules § 6: todo procedimiento lleva EXIT HANDLER FOR SQLEXCEPTION.
    Si modifica datos: START TRANSACTION + ROLLBACK + RESIGNAL. Si solo lee: RESIGNAL, sin transacción."""
    if tipo != "PROCEDURE":
        return []
    code = mask_strings(clean(sql))
    writes = [s for s in statements(code) if re.match(r"(?:INSERT|UPDATE|DELETE|REPLACE)\b", s.strip(), re.I)]
    writes = [s for s in writes if not re.search(r"\bTEMPORARY\b|\btmp_\w+", s, re.I)]
    has_handler = re.search(r"\bEXIT\s+HANDLER\s+FOR\s+SQLEXCEPTION\b", code, re.I)
    missing = []
    if not has_handler:
        missing.append("DECLARE EXIT HANDLER FOR SQLEXCEPTION")
    if writes:
        if not re.search(r"\bSTART\s+TRANSACTION\b", code, re.I):
            missing.append("START TRANSACTION")
        if not re.search(r"\bROLLBACK\b", code, re.I):
            missing.append("ROLLBACK")
    if has_handler and not re.search(r"\bRESIGNAL\b", code, re.I):
        missing.append("RESIGNAL")
    if not missing:
        return []
    kind = "escribe datos" if writes else "es de solo lectura"
    return [f"{nombre} {kind} y le falta: {', '.join(missing)}"]


def r_sargable(tipo, nombre, sql):
    if tipo not in ROUTINE_KINDS:
        return []
    code = mask_strings(clean(sql))
    out = []
    func = r"(?:YEAR|MONTH|DAY|DATE|DATE_FORMAT|LOWER|UPPER|TRIM|SUBSTRING|LEFT|RIGHT|CAST|CONVERT|DATEDIFF|ABS)"
    for line in code.split("\n"):
        if re.match(r"\s*(?:IF|ELSEIF|WHILE|SET|RETURN|CASE|WHEN|UNTIL)\b", line, re.I):
            continue  # condiciones de control de flujo: no son filtros de tabla
        if not re.search(r"\b(?:WHERE|AND|OR|ON|HAVING)\b", line, re.I):
            continue
        m = re.search(rf"\b{func}\s*\(\s*(?!p_|v_|@|NOW\b|CURRENT|CURDATE|'|\d)([A-Za-z_][\w.]*)[^)]*\)\s*(?:=|<>|!=|<=|>=|<|>|\bBETWEEN\b|\bLIKE\b|\bIN\b)", line, re.I)
        if m:
            out.append(snippet(line))
    return out


def r_comment_syntax(tipo, nombre, sql):
    """`--Texto` (sin espacio tras `--`) NO es un comentario en MySQL: el servidor lo rechaza como error de sintaxis."""
    out = []
    for line in (sql or "").split("\n"):
        if re.match(r"\s*--(?=[^\s-])", line):
            out.append(snippet(line))
    return out


def r_audit_columns(tipo, nombre, sql):
    if tipo != "TABLE":
        return []
    code = clean(sql)
    out = []
    for col, pattern in (("fecha_creacion", r"\bfecha_?creacion\b"), ("fecha_modificacion", r"\bfecha_?modificacion\b")):
        if not re.search(pattern, code, re.I):
            out.append(f"tabla {nombre} sin columna de auditoría {col} (con o sin guion bajo); si el dominio ya tiene una fecha equivalente (p. ej. FechaAlta), documéntala en el plan y ajusta esta regla antes de continuar")
    return out


COMMENT_RULE = ("comment-syntax", r_comment_syntax)

RULES_BY_KIND = {
    "TABLE": [("destructive", r_destructive), ("non-idempotent", r_non_idempotent), ("naming", r_naming),
              ("audit-columns", r_audit_columns), ("definer", r_definer), ("credentials", r_credentials),
              ("hardcoded-secret", r_hardcoded_secret)],
    "ROUTINE": [("select-star", r_select_star), ("dynamic-sql", r_dynamic_sql), ("destructive", r_destructive),
                ("non-idempotent", r_non_idempotent), ("missing-use", r_missing_use), ("naming", r_naming),
                ("sql-data-access", r_sql_data_access),
                ("list-order", r_list_order), ("exit-handler", r_exit_handler), ("sargable", r_sargable),
                ("definer", r_definer), ("credentials", r_credentials), ("hardcoded-secret", r_hardcoded_secret)],
    "EVENT": [("naming", r_naming), ("destructive", r_destructive),
              ("non-idempotent", r_non_idempotent), ("definer", r_definer),
              ("credentials", r_credentials), ("hardcoded-secret", r_hardcoded_secret)],
    "TEST": [("destructive", r_destructive), ("credentials", r_credentials), ("hardcoded-secret", r_hardcoded_secret)],
    "DATA": [("destructive", r_destructive), ("credentials", r_credentials), ("hardcoded-secret", r_hardcoded_secret)],
    "DATABASE": [("credentials", r_credentials), ("hardcoded-secret", r_hardcoded_secret)],
    "OTRO": [("credentials", r_credentials)],
}


def findings(tipo, nombre, sql):
    group = "ROUTINE" if tipo in ROUTINE_KINDS else tipo
    if sql and sqlnb.has_delimiter(sql):
        sql = sqlnb.strip_delimiter_lines(sql)
    out = []
    for rule_id, fn in RULES_BY_KIND.get(group, RULES_BY_KIND["OTRO"]) + [COMMENT_RULE]:
        for text in fn(tipo, nombre, sql or ""):
            out.append((rule_id, text))
    return out


# ---------------------------------------------------------------- modos
def diff_counts(a, b):
    ca, cb = collections.Counter(a), collections.Counter(b)
    return {k: n - ca.get(k, 0) for k, n in cb.items() if n - ca.get(k, 0) > 0}


def run_gate(base_ref):
    root = sqlnb.repo_root()
    os.chdir(root)
    import subprocess
    proc = subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "touched-objects.py"), "--base", base_ref],
                          capture_output=True, text=True)
    if proc.returncode != 0:
        sys.stderr.write(f"BLOCKED (infraestructura): touched-objects.py terminó con código {proc.returncode}: {proc.stderr.strip()}\n")
        return 2
    touched = json.loads(proc.stdout)
    base_line = next((l for l in proc.stderr.splitlines() if l.startswith("BASE=")), "")
    per_object, rules = [], collections.Counter()
    before_after = collections.defaultdict(lambda: [0, 0])
    for o in touched:
        if o["estado"] == "eliminado":
            continue
        a = findings(o["tipo"], o["nombre"], o["sqlBase"]) if o["sqlBase"] else []
        b = findings(o["tipo"], o["nombre"], o["sql"])
        new = diff_counts(a, b)
        for (rule, _), n in new.items():
            rules[rule] += n
        for (rule, _) in b:
            before_after[rule][1] += 1
        for (rule, _) in a:
            before_after[rule][0] += 1
        per_object.append({
            "libro": o["libro"], "celda": o["celda"], "tipo": o["tipo"], "nombre": o["nombre"], "estado": o["estado"],
            "A": len(a), "B": len(b),
            "nuevos": [{"regla": r, "texto": t, "mas": n} for (r, t), n in sorted(new.items())],
        })
    blocked = bool(rules)
    out = {
        "base": base_line.replace("BASE=", ""),
        "objetos": per_object,
        "reglasNuevas": [{"regla": r, "antes": before_after[r][0], "ahora": before_after[r][1], "mas": n} for r, n in sorted(rules.items())],
        "veredicto": "BLOQUEA" if blocked else "PASA",
    }
    json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    sys.stderr.write(f"sql-lint: {out['veredicto']} ({len(per_object)} objeto(s) analizado(s), {sum(rules.values())} hallazgo(s) nuevo(s)).\n")
    return 1 if blocked else 0


def run_canary():
    root = sqlnb.repo_root()
    path = os.path.join(root, FIXTURE)
    if not os.path.isfile(path):
        sys.stderr.write(f"BLOCKED (infraestructura): falta el fixture {FIXTURE}.\n")
        return 2
    sql = open(path, encoding="utf-8").read()
    kind, name = sqlnb.classify_cell(sql)[0]
    seen = {rule for rule, _ in findings(kind, name, sql)}
    missing = CANARY_RULES - seen
    if missing:
        sys.stderr.write(f"BLOCKED (infraestructura): el canario no detectó las reglas {sorted(missing)} (detectadas: {sorted(seen)}).\n")
        return 2
    json.dump({"canario": "OK", "reglas": sorted(seen)}, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    sys.stderr.write("sql-lint: canario OK.\n")
    return 0


def run_calibrate():
    root = sqlnb.repo_root()
    os.chdir(root)
    total, objects = collections.Counter(), 0
    per_rule = collections.defaultdict(list)
    for libro, objs in sqlnb.load_working_tree(root).items():
        for o in objs:
            objects += 1
            for rule, text in findings(o["tipo"], o["nombre"], o["sql"]):
                total[rule] += 1
                if len(per_rule[rule]) < 3:
                    per_rule[rule].append(f"{o['tipo']} {o['nombre'] or o['celda']}: {text}")
    clean_objects = objects - len({(o["libro"], o["celda"]) for libro, objs in sqlnb.load_working_tree(root).items() for o in objs
                                   if findings(o["tipo"], o["nombre"], o["sql"])})
    json.dump({"objetos": objects, "hallazgos_por_regla": dict(total), "ejemplos": per_rule}, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    sys.stderr.write(f"sql-lint: calibración sobre {objects} objeto(s); ~{clean_objects} sin hallazgos.\n")
    return 0


def word_parts(name):
    return re.findall(r'[A-Z]+(?=[A-Z][a-z]|$)|[A-Z]?[a-z]+|[0-9]+', name.replace('_',' '))


def spelling(name, style):
    words=word_parts(name)
    if not words:raise ValueError('identificador no clasificable')
    if style=='snake_case':return '_'.join(w.lower() for w in words)
    pascal=''.join(w[0].upper()+w[1:] for w in words)
    return pascal[0].lower()+pascal[1:] if style=='camelCase' else pascal


def style_ok(name, style):
    return bool(re.fullmatch({'PascalCase':r'[A-Z][A-Za-z0-9]*','camelCase':r'[a-z][A-Za-z0-9]*','snake_case':r'[a-z][a-z0-9]*(?:_[a-z0-9]+)*'}[style],name))


def balanced(text, start):
    depth=0
    for i in range(start,len(text)):
        if text[i]=='(':depth+=1
        elif text[i]==')':
            depth-=1
            if not depth:return text[start+1:i],i+1
    raise ValueError('paréntesis incompletos')


def split_items(text):
    depth=0;start=0;items=[]
    for i,c in enumerate(text):
        if c=='(':depth+=1
        elif c==')':depth-=1
        elif c==',' and depth==0:items.append(text[start:i].strip());start=i+1
    return items+[text[start:].strip()]


PASCAL_ENTITY = r'[A-Z][a-z0-9]+(?:[A-Z][a-z0-9]+)*'

CONTENT_KEYS=['prefijo_indice','columnas','clave_primaria','prefijo_parametro','prefijo_variable']


DATA_TYPE = (TYPES + r'(?:\s*\([^)]*\))?'
             r'(?:\s+(?:UNSIGNED|SIGNED|ZEROFILL|BINARY|ASCII|UNICODE|(?:CHARACTER\s+SET|CHARSET|COLLATE)\s*(?:=\s*)?\w+))*')


def declarations(tipo,nombre,sql, for_gate=False):
    """Extractor compartido: el gate comprueba nombres aun con tipo desconocido o SQL dinámico."""
    code=mask_strings(clean(sql))
    params=[];variables=[];unknown={'prefijo_parametro':[],'prefijo_variable':[]}
    if tipo in ('PROCEDURE','FUNCTION'):
        head=re.search(ROUTINE_HEADER + r'\s*\(',code,re.I)
        try:
            if not head:raise ValueError()
            body,_=balanced(code,head.end()-1)
            for i,item in enumerate(split_items(body)):
                if not item:continue
                pm=re.fullmatch(r'(?:INOUT\s+|IN\s+|OUT\s+)?`?(\w+)`?\s+'+DATA_TYPE,item,re.I)
                if pm:params.append(pm[1])
                else:
                    token=re.match(r'`?(\w+)',re.sub(r'^(?:INOUT|IN|OUT)\s+', '', item, flags=re.I))
                    if for_gate and token:params.append(token[1])
                    elif not for_gate:unknown['prefijo_parametro'].append(nombre+'.'+(token[1] if token else 'parametro_'+str(i)))
        except ValueError:
            if not for_gate:unknown['prefijo_parametro'].append(nombre+'.parametros')
    if tipo in ('PROCEDURE','FUNCTION','TRIGGER','EVENT'):
        if not for_gate and re.search(r'\b(?:PREPARE|EXECUTE)\b',code,re.I):
            unknown['prefijo_variable'].append(nombre+'.variables_dinamicas')
        else:
            variable_code = code
            for i,m in enumerate(re.finditer(r'\bDECLARE\s+([^;]+)',variable_code,re.I)):
                if re.search(r'\b(?:HANDLER|CURSOR)\b|\bCONDITION\s+FOR\b',mask_strings(m[1]),re.I):continue
                vm=re.fullmatch(r'((?:`?\w+`?\s*,\s*)*`?\w+`?)\s+'+DATA_TYPE+r'(?:\s+DEFAULT\b[\s\S]+)?',m[1].strip(),re.I)
                if vm:variables.extend(x.strip().strip('`') for x in vm[1].split(','))
                else:
                    token=re.match(r'((?:`?\w+`?\s*,\s*)*`?\w+`?)',m[1])
                    if for_gate and token:variables.extend(x.strip().strip('`') for x in token[1].split(','))
                    elif not for_gate:
                        if token:
                            unknown['prefijo_variable'].extend(nombre+'.'+x.strip().strip('`') for x in token[1].split(','))
                        else:
                            unknown['prefijo_variable'].append(nombre+'.declare_'+str(i))
    return params,variables,unknown


def empty_analysis():
    return {'bad':{k:[] for k in CONTENT_KEYS},'unknown':{k:[] for k in CONTENT_KEYS},'evaluated':{k:0 for k in CONTENT_KEYS},'evaluated_names':{k:{} for k in CONTENT_KEYS}}


def naming_content(obj):
    out=empty_analysis();code=mask_strings(clean(obj['sql']));owner=obj['nombre']
    if not owner:
        target=re.search(r'\bALTER\s+TABLE\s+`?(\w+)`?',code,re.I)
        owner=target[1] if target else ''
    def evaluate(key,name,good,table=None):
        stable=(table if table is not None else owner)+'.'+name
        out['evaluated'][key]+=1
        counts=out['evaluated_names'][key]
        counts[stable]=counts.get(stable,0)+1
        if not good:out['bad'][key].append(stable)
    def prefix(key,name,table=None):evaluate(key,name,identifier_prefix(name,naming_setting('nomenclatura.'+key)),table)
    for m in re.finditer(r'\b(?:INDEX|KEY)\s+`?([A-Za-z_]\w*)`?\s*\(',code,re.I):
        if m[1].upper() not in ('PRIMARY','FOREIGN'):prefix('prefijo_indice',m[1],owner or 'indice')
    for m in re.finditer(r'\bCREATE\s+(?:UNIQUE\s+)?INDEX\s+`?(\w+)`?\s+ON\s+`?(\w+)`?',code,re.I):prefix('prefijo_indice',m[1],m[2])
    tables=0
    for m in re.finditer(r'\bCREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?'+SQL_NAME+r'\s*\(',code,re.I):
        tables+=1;table=m[1]
        try:body,_=balanced(code,m.end()-1)
        except ValueError:
            out['unknown']['columnas'].append(table);out['unknown']['clave_primaria'].append(table);continue
        pk=[]
        for item in split_items(body):
            if re.match(r'(?:CONSTRAINT|PRIMARY|FOREIGN|INDEX|UNIQUE|KEY|CHECK|FULLTEXT|SPATIAL)\b',item,re.I):
                pm=re.search(r'\bPRIMARY\s+KEY\s*\(([^)]+)\)',item,re.I)
                if pm:pk.extend(x.strip().strip('`') for x in pm[1].split(','))
                continue
            cm=re.match(r'`?(\w+)`?\s+'+TYPES+r'\b',item,re.I)
            if cm:
                evaluate('columnas',cm[1],style_ok(cm[1],naming_setting('nomenclatura.columnas')),table)
                if re.search(r'\bPRIMARY\s+KEY\b',item,re.I):pk.append(cm[1])
            else:
                token=re.match(r'`?(\w+)',item);out['unknown']['columnas'].append(table+'.'+(token[1] if token else 'columna'))
        pk=list(dict.fromkeys(pk))
        if len(pk)==1:
            candidates={table}
            if table.endswith('es'):candidates.add(table[:-2])
            if table.endswith('s'):candidates.add(table[:-1])
            expected={spelling(naming_setting('nomenclatura.clave_primaria').replace('{Entidad}',spelling(n,'PascalCase')),naming_setting('nomenclatura.columnas')) for n in candidates if n and re.fullmatch(PASCAL_ENTITY,spelling(n,'PascalCase'))}
            evaluate('clave_primaria',pk[0],pk[0] in expected,table)
        else:out['unknown']['clave_primaria'].append(table+'.PRIMARY')
    if obj['tipo']=='TABLE' and not tables:
        out['unknown']['columnas'].append(owner);out['unknown']['clave_primaria'].append(owner+'.PRIMARY')
    # ALTER/CREATE INDEX pueden estar en celdas OTRO, sin inventar objetos en el índice.
    for m in re.finditer(r'\bALTER\s+TABLE\s+`?(\w+)`?\s+([^;]+)',code,re.I):
        for item in split_items(m[2]):
            cm=re.match(r'(?:ADD|MODIFY)\s+(?:COLUMN\s+)?`?(\w+)`?\s+'+TYPES+r'\b',item,re.I)
            if cm:evaluate('columnas',cm[1],style_ok(cm[1],naming_setting('nomenclatura.columnas')),m[1])
            elif re.match(r'(?:ADD|MODIFY)\s+(?:COLUMN\s+)?(?!(?:INDEX|KEY|UNIQUE|CONSTRAINT|PRIMARY|FOREIGN)\b)',item,re.I):
                token=re.search(r'(?:ADD|MODIFY)\s+(?:COLUMN\s+)?`?(\w+)',item,re.I);out['unknown']['columnas'].append(m[1]+'.'+(token[1] if token else 'columna'))
    params,variables,unknown=declarations(obj['tipo'],owner,code)
    for key,items in [('prefijo_parametro',params),('prefijo_variable',variables)]:
        for name in items:prefix(key,name)
        out['unknown'][key].extend(unknown[key])
    return out


def name_results(kind,names):
    checks={NAME_KEYS[kind]:[]} if kind!='TABLE' else {'tablas':[],'tablas_plural':[]}
    unknown={k:[] for k in checks};evaluated={k:0 for k in checks}
    for name in sorted(names):
        if kind in NAME_KEYS:
            key=NAME_KEYS[kind];evaluated[key]+=1
            if naming_name(kind,name):checks[key].append(name)
        else:
            evaluated['tablas']+=1
            if not style_ok(name,naming_setting('nomenclatura.tablas')):checks['tablas'].append(name)
            words=word_parts(name)
            if not words:
                unknown['tablas_plural'].append(name)
                continue
            evaluated['tablas_plural']+=1
            if words[-1].lower().endswith('s') != naming_setting('nomenclatura.tablas_plural'):checks['tablas_plural'].append(name)
    out={}
    for key,bad in checks.items():
        pending=sorted(set(unknown[key]));unread=bool(pending and not evaluated[key])
        flagged=sorted(set(bad or (pending if unread else [])))
        mapping={n:[n] for n in flagged}
        out[key]={'resultado':'difiere' if bad else 'no_determinable' if unread else 'coincide',
                  'motivo':'nombres contrarios' if bad else 'sin elementos evaluables' if unread else 'nombres coherentes' if names else 'sin objetos aplicables',
                  'nombres':flagged,'evidencia':[n for n in sorted(set(bad))]+([f'No evaluados: {len(pending)}']+['no evaluado: '+n for n in pending] if pending else []),
                  'evidencia_por_nombre':mapping,'archivos':[], 'evaluados':evaluated[key],
                  'no_evaluados':{'cantidad':len(pending),'nombres':pending},
                  'evaluados_por_nombre':{n:names.count(n) for n in set(names) if n not in pending}}
    return out


def registro_mode(argv):
    if '--sin-datos-prueba' not in argv:raise ValueError('se exige exclusión de datos de prueba')
    if '--nombres' in argv:
        if len(argv)!=3 or argv[0]!='--nombres':raise ValueError('uso nombres')
        kind=argv[1].upper();names=json.load(sys.stdin)
        if kind not in set(NAME_KEYS)|{'TABLE'} or not isinstance(names,list) or any(not isinstance(n,str) or not re.fullmatch(r'[A-Za-z_]\w*',n) for n in names):raise ValueError('lista inválida')
        output=name_results(kind,names)
    else:
        if set(argv)-{'--registro','--registro-nomenclatura','--completo','--sin-datos-prueba'}:raise ValueError('uso registro')
        root=sqlnb.repo_root()
        books=sqlnb.load_working_tree(root,sin_datos_prueba=True)
        all_objects=[o for items in books.values() for o in items]
        objects=[o for o in all_objects if o['tipo'] in set(NAME_KEYS)|{'TABLE'}]
        checks={}
        for kind in sorted(set(NAME_KEYS)|{'TABLE'}):
            group=[o for o in objects if o['tipo']==kind]
            entries=name_results(kind,[o['nombre'] for o in group])
            for entry in entries.values():
                entry['archivos_por_nombre']={n:sorted({o['libro'] for o in group if o['nombre']==n}) for n in {o['nombre'] for o in group}}
                visible=entry['nombres']+entry['no_evaluados']['nombres']
                entry['archivos']=sorted({p for n in visible for p in entry['archivos_por_nombre'].get(n,[])})
            checks.update(entries)
        extra=[o for o in all_objects if o['tipo']=='OTRO' and re.search(r'\b(?:CREATE\s+(?:UNIQUE\s+)?INDEX|ALTER\s+TABLE)\b',mask_strings(clean(o['sql'])),re.I)]
        chosen=[]
        for kind in sorted(set(NAME_KEYS)|{'TABLE','OTRO'}):
            group=sorted((o for o in objects+extra if o['tipo']==kind),key=lambda o:(o['nombre'],o['libro'],o['celda']))
            chosen.extend(group if '--completo' in argv else group[:5])
        bad={k:{} for k in CONTENT_KEYS};unknown={k:[] for k in CONTENT_KEYS};evaluated={k:0 for k in CONTENT_KEYS}
        counts={k:{} for k in CONTENT_KEYS};files={k:{} for k in CONTENT_KEYS}
        for obj in chosen:
            try:analysis=naming_content(obj)
            except (ValueError,IndexError):
                analysis=empty_analysis()
                for k in CONTENT_KEYS:analysis['unknown'][k].append(obj['nombre'] or f"{obj['libro']}:celda={obj['celda']}")
            location=f"{obj['libro']}:celda={obj['celda']}"
            for k in CONTENT_KEYS:
                evaluated[k]+=analysis['evaluated'][k]
                for n,c in analysis['evaluated_names'][k].items():counts[k][n]=counts[k].get(n,0)+c
                for n in list(analysis['evaluated_names'][k])+analysis['unknown'][k]:files[k].setdefault(n,set()).add(obj['libro'])
                unknown[k].extend(analysis['unknown'][k])
                for n in analysis['bad'][k]:bad[k].setdefault(n,[]).append(location+': '+n)
        for k in CONTENT_KEYS:
            pending=sorted(set(unknown[k]));unread=bool(pending and not evaluated[k])
            flagged=sorted(bad[k] or (dict.fromkeys(pending) if unread else {}))
            mapping=bad[k] if bad[k] else {n:['no evaluado: '+n] for n in pending}
            checks[k]={'resultado':'difiere' if bad[k] else 'no_determinable' if unread else 'coincide',
                       'motivo':'identificadores contrarios' if bad[k] else 'sin elementos evaluables' if unread else 'sin diferencias en el alcance',
                       'nombres':flagged,'evidencia_por_nombre':mapping,
                       'evidencia':[e for n in sorted(bad[k]) for e in bad[k][n]]+([f'No evaluados: {len(pending)}']+['no evaluado: '+n for n in pending] if pending else []),
                       'no_evaluados':{'cantidad':len(pending),'nombres':pending},'evaluados':evaluated[k],
                       'archivos':sorted({p for n in flagged+pending for p in files[k].get(n, [])}),
                       'archivos_por_nombre':{n:sorted(v) for n,v in files[k].items()},
                       'evaluados_por_nombre':counts[k],
                       'muestra':[{'tipo':o['tipo'],'nombre':o['nombre'],'libro':o['libro'],'celda':o['celda']} for o in chosen]}
        if not (objects or extra):
            for entry in checks.values():entry['motivo']='sin objetos aplicables'
        output={'comprobaciones':{'nomenclatura.'+k:v for k,v in checks.items()},'procedimientos':sorted({o['nombre'] for o in objects if o['tipo']=='PROCEDURE'}),'sin_objetos_aplicables':not (objects or extra)} if '--registro' in argv else {k:checks[k] for k in CONTENT_KEYS}
    json.dump(output,sys.stdout,ensure_ascii=False,sort_keys=True)
    sys.stdout.write('\n')
    return 0


def main(argv):
    if any(a in argv for a in ("--nombres", "--registro", "--registro-nomenclatura")):
        try:
            return registro_mode(argv)
        except (OSError, ValueError, TypeError, KeyError, IndexError):
            sys.stderr.write("no se pudo analizar nomenclatura SQL permitida\n")
            return 2
    mode, base = "gate", "HEAD"
    i = 0
    while i < len(argv):
        if argv[i] == "--canary":
            mode = "canary"
        elif argv[i] == "--calibrate":
            mode = "calibrate"
        elif argv[i] == "--base" and i + 1 < len(argv):
            base = argv[i + 1]
            i += 1
        else:
            sys.stderr.write(f"BLOCKED (infraestructura): argumento desconocido: {argv[i]}\n")
            return 2
        i += 1
    return {"gate": lambda: run_gate(base), "canary": run_canary, "calibrate": run_calibrate}[mode]()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
