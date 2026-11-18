#!/usr/bin/env python3
"""sql-sandbox.py - Base de datos MySQL DESECHABLE para validar el SQL sin tocar la base real.

Equivale a `compileJava` + la suite de tests de los repos de código: levanta un MySQL en un contenedor
(docker o podman), construye el esquema completo desde los notebooks .dbcnb, ejecuta las pruebas y se
destruye. Nunca se conecta a ninguna base de datos externa: solo habla con su propio contenedor mediante
`docker exec`; la contraseña de root es aleatoria, vive en memoria y se pasa por entorno (no por argumentos).
Si ningún notebook crea la base de datos, el propio sandbox crea el esquema `base_de_datos.nombre` de
`.agents/stack.yaml` (`CREATE DATABASE IF NOT EXISTS`) antes de construir los objetos.

Uso:
  sql-sandbox.py --canary               Arranca el contenedor, ejecuta SELECT 1 y lo destruye (Paso 0).
  sql-sandbox.py run [--base <ref>] [--keep] [--no-tests]
                                        Construye el esquema del árbol de trabajo y ejecuta las pruebas.
                                        Con --base <ref> construye y prueba antes esa versión del repo:
                                        un fallo que ya existía en la base se marca `preexistente` y no bloquea.
  sql-sandbox.py explain <fichero.sql>  Construye el esquema y ejecuta EXPLAIN de cada SELECT del fichero
                                        (planes de ejecución; con los datos de prueba, que son pocos: sirven
                                        para ver si se usa un índice, no para medir tiempos).
  sql-sandbox.py --cleanup              Elimina contenedores de sandbox huérfanos.

Formato de prueba con aserciones (celdas del libro de pruebas):
  -- @test: nombre legible de la prueba
  -- @expect-rows: 1                  (nº exacto de filas del resultado)
  -- @expect-rows-min: 1              (al menos N filas)
  -- @expect-columns: colA,colB       (cabeceras exactas, en orden)
  -- @expect-error: 45000 mensaje     (SQLSTATE y fragmento del mensaje)
  USE <esquema del proyecto>;
  CALL sp_x(...);
Una celda sin directivas se ejecuta en modo humo: pasa si no da error. Las directivas se evalúan sobre el
ÚLTIMO resultado de la celda; un CALL que devuelve varios conjuntos de filas no está soportado.
(El nombre del esquema lo da `base_de_datos.nombre` de .agents/stack.yaml.)

Códigos de salida: 0 = OK, 1 = hay fallos nuevos (de construcción o de pruebas), 2 = BLOCKED (infraestructura).
"""
import json
import os
import re
import secrets
import shutil
import signal
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sqlnb  # noqa: E402
from stack import get as stack_get  # noqa: E402

# La imagen por defecto la fija stack.yaml (base_de_datos.motor + base_de_datos.version);
# SQL_SANDBOX_IMAGE tiene prioridad.
IMAGE = os.environ.get("SQL_SANDBOX_IMAGE", f"{stack_get('base_de_datos.motor')}:{stack_get('base_de_datos.version')}")
LABEL = "agents-sql-sandbox=1"
READY_TIMEOUT_S = 120
CELL_TIMEOUT_S = 60


def aviso_version(version):
    """Aviso, no bloqueo (SQL_SANDBOX_IMAGE es un override deliberado): el SQL se escribe y
    prueba según `base_de_datos.version`; el sandbox avisa si su servidor difiere."""
    esperada = str(stack_get("base_de_datos.version"))
    observada = (version or "").strip()
    if esperada.strip() and not observada.startswith(esperada.strip()):
        return (f"la versión del servidor del sandbox ({observada}) no coincide con base_de_datos.version "
                f"({esperada}); el SQL se está probando contra otra versión: revisa que el desajuste sea "
                "deliberado (por ejemplo, una SQL_SANDBOX_IMAGE elegida a mano).")
    return None


def die(msg):
    sys.stderr.write(f"BLOCKED (infraestructura): {msg}\n")
    sys.exit(2)


def pick_engine():
    for engine in ("docker", "podman"):
        if shutil.which(engine):
            probe = subprocess.run([engine, "info"], capture_output=True, text=True, timeout=30)
            if probe.returncode == 0:
                return engine
    die("no hay un motor de contenedores operativo (docker o podman).")


class Sandbox:
    def __init__(self, engine, keep=False):
        self.engine = engine
        self.keep = keep
        self.name = f"agents-sql-sandbox-{os.getpid()}"
        self.password = secrets.token_urlsafe(18)
        self.started = False

    def start(self):
        have = subprocess.run([self.engine, "image", "inspect", IMAGE], capture_output=True)
        if have.returncode != 0:
            die(f"la imagen {IMAGE} no está disponible localmente (docker pull {IMAGE}).")
        run = subprocess.run(
            [self.engine, "run", "-d", "--rm", "--name", self.name, "--label", LABEL,
             "-e", f"MYSQL_ROOT_PASSWORD={self.password}", "--tmpfs", "/var/lib/mysql",
             IMAGE, "--character-set-server=utf8mb4", "--skip-log-bin"],
            capture_output=True, text=True)
        if run.returncode != 0:
            die(f"no se pudo arrancar el contenedor: {run.stderr.strip()[:300]}")
        self.started = True
        deadline, ok_in_a_row = time.time() + READY_TIMEOUT_S, 0
        while time.time() < deadline:
            r = self.sql("SELECT 1", timeout=10)
            ok_in_a_row = ok_in_a_row + 1 if r["rc"] == 0 else 0
            if ok_in_a_row >= 2:  # la imagen reinicia el servidor tras inicializar: hacen falta dos respuestas seguidas
                return
            time.sleep(2)
        self.stop()
        die(f"MySQL no estuvo listo en {READY_TIMEOUT_S}s.")

    def sql(self, text, timeout=CELL_TIMEOUT_S, force=False):
        cmd = [self.engine, "exec", "-i", "-e", f"MYSQL_PWD={self.password}", self.name,
               "mysql", "-uroot", "--batch", "--default-character-set=utf8mb4"]
        if force:
            cmd.append("--force")
        try:
            p = subprocess.run(cmd, input=text, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return {"rc": 124, "out": "", "err": f"tiempo agotado ({timeout}s)"}
        return {"rc": p.returncode, "out": p.stdout, "err": self._clean_err(p.stderr)}

    def _clean_err(self, err):
        err = "\n".join(l for l in err.splitlines() if "Using a password on the command line" not in l)
        return err.replace(self.password, "***")

    def version(self):
        r = self.sql("SELECT VERSION()")
        return r["out"].strip().splitlines()[-1] if r["rc"] == 0 and r["out"].strip() else "desconocida"

    def stop(self):
        if self.started and not self.keep:
            subprocess.run([self.engine, "rm", "-f", self.name], capture_output=True)
        self.started = False


def cell_text(sql, use_db=False):
    """Prepara una celda para el cliente mysql: el cuerpo de rutinas va con delimitador propio.

    Cada celda se ejecuta en una sesión nueva (en DBCode la sesión se comparte entre celdas), así que
    una vez creada la base se antepone `USE` para reproducir ese comportamiento.
    """
    head = f"USE `{sqlnb.DATABASE}`;\n" if use_db else ""
    if sqlnb.has_delimiter(sql):
        # la celda ya trae sus propias sentencias DELIMITER (script plano): se envía tal cual
        return head + sql + "\nDELIMITER ;\n"
    prefix, routine = sqlnb.split_routine(sql)
    if routine is None:
        return head + sql
    if "$$" in routine:
        raise ValueError("la rutina contiene '$$', que se usa como delimitador del sandbox")
    return f"{head}{prefix}\nDELIMITER $$\n{routine}\n$$\nDELIMITER ;\n"


def parse_directives(sql):
    d = {"test": None, "rows": None, "rows_min": None, "columns": None, "error": None}
    for m in re.finditer(r"^\s*--\s*@(test|expect-rows-min|expect-rows|expect-columns|expect-error)\s*:?\s*(.*)$", sql, re.M):
        k, v = m.group(1), m.group(2).strip()
        if k == "test":
            d["test"] = v
        elif k == "expect-rows":
            d["rows"] = int(v)
        elif k == "expect-rows-min":
            d["rows_min"] = int(v)
        elif k == "expect-columns":
            d["columns"] = [c.strip() for c in v.split(",") if c.strip()]
        elif k == "expect-error":
            d["error"] = v
    return d


def has_directives(d):
    return any(d[k] is not None for k in ("rows", "rows_min", "columns", "error"))


def evaluate_test(sb, obj, use_db=False):
    d = parse_directives(obj["sql"])
    label = d["test"] or f"celda {obj['celda']}"
    try:
        r = sb.sql(cell_text(obj["sql"], use_db))
    except ValueError as e:
        return {"nombre": label, "estado": "ERROR", "detalle": str(e)}
    err = r["err"].strip()
    if d["error"] is not None:
        expected = d["error"]
        state = re.match(r"(\d{5})\s*(.*)", expected)
        sqlstate, frag = (state.group(1), state.group(2).strip().strip("\"'")) if state else ("", expected.strip("\"'"))
        if r["rc"] == 0:
            return {"nombre": label, "estado": "FALLA", "detalle": f"se esperaba el error '{expected}' y la celda terminó sin error"}
        if (sqlstate and f"({sqlstate})" not in err) or (frag and frag not in err):
            return {"nombre": label, "estado": "FALLA", "detalle": f"error distinto del esperado ({expected}): {err[:200]}"}
        return {"nombre": label, "estado": "OK", "detalle": f"error esperado: {err[:120]}"}
    if r["rc"] != 0:
        return {"nombre": label, "estado": "ERROR", "detalle": err[:300]}
    lines = [l for l in r["out"].splitlines() if l != ""]
    header = lines[0].split("\t") if lines else []
    rows = max(len(lines) - 1, 0)
    problems = []
    if d["rows"] is not None and rows != d["rows"]:
        problems.append(f"filas {rows} != {d['rows']}")
    if d["rows_min"] is not None and rows < d["rows_min"]:
        problems.append(f"filas {rows} < {d['rows_min']}")
    if d["columns"] is not None and rows == 0:
        return {"nombre": label, "estado": "OK", "detalle": "aviso: @expect-columns omitido porque el resultado tiene 0 filas; use solo @expect-rows 0"}
    if d["columns"] is not None and header != d["columns"]:
        problems.append(f"columnas {header} != {d['columns']}")
    if problems:
        return {"nombre": label, "estado": "FALLA", "detalle": "; ".join(problems)}
    mode = "aserciones" if has_directives(d) else "humo"
    return {"nombre": label, "estado": "OK", "detalle": f"{mode}: {rows} fila(s)"}


def build_and_test(sb, books, with_tests=True):
    """books: {libro: [objetos]}; se recorren en el orden de sqlnb.book_order. Devuelve (construcción, pruebas)."""
    build, tests = [], []
    db_ready = False
    # Si ningún notebook crea la base de datos (flujo de objetos sobre un esquema ya existente),
    # el sandbox crea el esquema del proyecto por su cuenta: es desechable y es idempotente.
    if not any(o["tipo"] == "DATABASE" for objs in books.values() for o in objs):
        r = sb.sql(f"CREATE DATABASE IF NOT EXISTS `{sqlnb.DATABASE}`;")
        if r["rc"] == 0:
            db_ready = True
        else:
            build.append({"libro": "-", "celda": "-", "tipo": "DATABASE", "nombre": sqlnb.DATABASE,
                          "estado": "ERROR", "detalle": r["err"].strip()[:300], "hash": "-"})
    for libro in sqlnb.book_order(books.keys()):
        objs = books.get(libro, [])
        test_book = sqlnb.is_test_book(libro)
        for o in objs:
            if test_book or o["tipo"] == "TEST":
                if with_tests:
                    res = evaluate_test(sb, o, db_ready)
                    tests.append({"libro": libro, "celda": o["celda"], **res, "hash": o["hash"]})
                continue
            try:
                r = sb.sql(cell_text(o["sql"], db_ready))
                if o["tipo"] == "DATABASE" and r["rc"] == 0:
                    db_ready = True
            except ValueError as e:
                build.append({"libro": libro, "celda": o["celda"], "tipo": o["tipo"], "nombre": o["nombre"], "estado": "ERROR", "detalle": str(e), "hash": o["hash"]})
                continue
            build.append({"libro": libro, "celda": o["celda"], "tipo": o["tipo"], "nombre": o["nombre"],
                          "estado": "OK" if r["rc"] == 0 else "ERROR", "detalle": r["err"].strip()[:300], "hash": o["hash"]})
    return build, tests


def failing(results):
    return {(r["libro"], r.get("nombre") or r["celda"], r["hash"]) for r in results if r["estado"] != "OK"}


def run(base_ref, keep, with_tests):
    root = sqlnb.repo_root()
    os.chdir(root)
    sb = Sandbox(pick_engine(), keep=keep)

    def cleanup(*_):
        sb.stop()
        sys.exit(2)

    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    try:
        sb.start()
        version = sb.version()
        base_failures = set()
        if base_ref:
            sys.stderr.write(f"sql-sandbox: construyendo la versión base ({base_ref})...\n")
            b_build, b_tests = build_and_test(sb, sqlnb.load_ref(root, base_ref), with_tests)
            base_failures = failing(b_build) | failing(b_tests)
        sys.stderr.write("sql-sandbox: construyendo la versión actual...\n")
        build, tests = build_and_test(sb, sqlnb.load_working_tree(root), with_tests)
        for r in build + tests:
            r["preexistente"] = r["estado"] != "OK" and (r["libro"], r.get("nombre") or r["celda"], r["hash"]) in base_failures
            r.pop("hash", None)
        new_failures = [r for r in build + tests if r["estado"] != "OK" and not r["preexistente"]]
        out = {
            "motor": f"MySQL {version} ({IMAGE})",
            "base": base_ref,
            "construccion": {"objetos": len(build), "ok": sum(r["estado"] == "OK" for r in build),
                             "errores": [r for r in build if r["estado"] != "OK"]},
            "pruebas": {"total": len(tests), "ok": sum(r["estado"] == "OK" for r in tests),
                        "con_aserciones": sum(1 for r in tests if r["detalle"].startswith("aserciones")),
                        "fallos": [r for r in tests if r["estado"] != "OK"]},
            "fallos_nuevos": len(new_failures),
            "veredicto": "FALLA" if new_failures else "OK",
        }
        if keep:
            out["contenedor"] = sb.name
        aviso = aviso_version(version)
        if aviso:
            out["aviso_version"] = aviso
            sys.stderr.write(f"sql-sandbox: AVISO: {aviso}\n")
        json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        sys.stderr.write(f"sql-sandbox: {out['veredicto']} (construcción {out['construccion']['ok']}/{out['construccion']['objetos']}, "
                         f"pruebas {out['pruebas']['ok']}/{out['pruebas']['total']}, fallos nuevos {len(new_failures)}).\n")
        return 1 if new_failures else 0
    finally:
        sb.stop()


def canary():
    sb = Sandbox(pick_engine())
    try:
        sb.start()
        v = sb.version()
        aviso = aviso_version(v)
        if aviso:
            sys.stderr.write(f"sql-sandbox: AVISO: {aviso}\n")
        r = sb.sql("SELECT 1 AS ok")
        if r["rc"] != 0 or "1" not in r["out"]:
            die(f"el sandbox arrancó pero no responde SELECT 1: {r['err'][:200]}")
        json.dump({"sandbox": "OK", "motor": f"MySQL {v} ({IMAGE})"}, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        sys.stderr.write("sql-sandbox: canario OK.\n")
        return 0
    finally:
        sb.stop()


def explain(path):
    root = sqlnb.repo_root()
    os.chdir(root)
    try:
        with open(path, encoding="utf-8") as fh:
            text = sqlnb.strip_comments(fh.read())
    except OSError as exc:
        die(f"no se pudo leer {path}: {exc}")
    selects = [st.strip() for st in text.split(";") if re.match(r"\s*(?:WITH|SELECT)\b", st, re.I)]
    if not selects:
        die("el fichero no contiene ningún SELECT para analizar (EXPLAIN de un CALL no está soportado: extrae sus SELECT).")
    sb = Sandbox(pick_engine())
    try:
        sb.start()
        aviso = aviso_version(sb.version())
        if aviso:
            sys.stderr.write(f"sql-sandbox: AVISO: {aviso}\n")
        build, _ = build_and_test(sb, sqlnb.load_working_tree(root), with_tests=False)
        errors = [b for b in build if b["estado"] != "OK"]
        plans = []
        for st in selects:
            r = sb.sql(f"USE `{sqlnb.DATABASE}`;\nEXPLAIN FORMAT=TRADITIONAL {st};")
            if r["rc"] != 0:
                plans.append({"consulta": re.sub(r"\s+", " ", st)[:200], "error": r["err"].strip()[:300]})
                continue
            lines = [l for l in r["out"].splitlines() if l != ""]
            header = lines[0].split("\t") if lines else []
            rows = [dict(zip(header, l.split("\t"))) for l in lines[1:]]
            plans.append({"consulta": re.sub(r"\s+", " ", st)[:200], "plan": rows})
        json.dump({"motor": f"MySQL {sb.version()} ({IMAGE})", "errores_de_construccion": len(errors), "planes": plans},
                  sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return 0
    finally:
        sb.stop()


def cleanup_orphans():
    engine = pick_engine()
    ids = subprocess.run([engine, "ps", "-aq", "--filter", f"label={LABEL}"], capture_output=True, text=True).stdout.split()
    for cid in ids:
        subprocess.run([engine, "rm", "-f", cid], capture_output=True)
    sys.stderr.write(f"sql-sandbox: {len(ids)} contenedor(es) huérfano(s) eliminado(s).\n")
    return 0


def main(argv):
    if "--canary" in argv:
        return canary()
    if "--cleanup" in argv:
        return cleanup_orphans()
    if argv and argv[0] == "explain" and len(argv) > 1:
        return explain(argv[1])
    if not argv or argv[0] != "run":
        die("uso: sql-sandbox.py --canary | run [--base <ref>] [--keep] [--no-tests] | explain <fichero.sql> | --cleanup")
    base, keep, with_tests, i = None, False, True, 1
    while i < len(argv):
        if argv[i] == "--base" and i + 1 < len(argv):
            base = argv[i + 1]
            i += 1
        elif argv[i] == "--keep":
            keep = True
        elif argv[i] == "--no-tests":
            with_tests = False
        else:
            die(f"argumento desconocido: {argv[i]}")
        i += 1
    return run(base, keep, with_tests)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
