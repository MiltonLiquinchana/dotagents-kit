#!/usr/bin/env python3
"""Valida .agents/stack.yaml y que no queden datos del proyecto fuera de él.

Comprueba, por proyecto de sources/:
  A. Existe .agents/stack.yaml, es YAML válido, sin claves repetidas, y respeta el subconjunto acordado:
     claves de primer nivel cuyo valor es un escalar, una lista de escalares o un mapa de
     (escalar | lista de escalares); hasta cuatro niveles en back, dos en los otros stacks.
     PyYAML/UniqueKeyLoader y parsear_yaml del generador deben producir el mismo resultado.
  B. Tiene las claves obligatorias de su stack y `proyecto.stack` coincide con el .agents.
  C. AGENTS.md ordena leer `.agents/stack.yaml`.
  D. Ningún archivo de .agents/ (ni AGENTS.md) contiene coincidencias con los patrones genéricos
     de versiones escritas a mano, los patrones locales opcionales ni los valores de las claves
     dinámicas de stack.yaml enumeradas en DYNAMIC_FORBIDDEN_KEYS.
     Solo pueden aparecer en .agents/stack.yaml, .agents/rules/project.md y .agents/mcp_config.json.
  E. No existe .agents/mcp_config.json (configuración MCP por workspace no admitida).
  F. config/claves.md explica todas las claves hoja y ninguna inexistente. En mapas de
     nombres libres, sus entradas se documentan con {nombre}, también si el mapa está vacío.
     Cada sección tiene «Dónde se ve en tu proyecto» con contenido después de «En resumen».

Uso (desde dotagents-kit/):
  python3 -I -B checkers/check-stack.py [raiz]   (raiz por defecto: sources)
Sale con código 1 si encuentra algún problema.
"""
import pathlib
import re
import sys
import importlib.util

import yaml

root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "sources")

EXPECTED_STACK = {
    "nextjs-front": "nextjs",
    "springboot-back": "springboot",
    "mysql-sql": "mysql",
}

DOCUMENTACION = ["documentacion." + k for k in ("url_api", "variable_password", "modelo_chat", "modelo_contexto_grande", "modelo_transformacion", "timeout_chat")]
COMMON = DOCUMENTACION + ["version_esquema", "proyecto.nombre", "proyecto.stack", "herramientas.codebase_memory", "git.rama_base"]
REQUIRED = {
    "nextjs": COMMON + [
        "herramientas.agent_browser",
        "frontend.framework", "frontend.version", "frontend.gestor_paquetes", "frontend.eslint_config",
        "sonarqube.url", "sonarqube.project_key", "integraciones.autenticacion", "mcp.sonarqube",
    ],
    "springboot": COMMON + [
        "backend.java", "backend.spring_boot", "backend.build", "backend.gateway",
        "sonarqube.url", "backend.jdk_ruta_desarrollo", "integraciones.autenticacion", "mcp.sonarqube",
    ],
    "mysql": COMMON + [
        "base_de_datos.motor", "base_de_datos.version", "base_de_datos.nombre",
        "base_de_datos.carpeta_notebooks", "notebooks", "conexiones", "mcp.base_de_datos",
    ],
}

# Patrones genéricos de versiones escritas a mano.
# Patrones locales opcionales en plans/prohibidos-*.txt.
FORBIDDEN = [
    r"\bJava ?2[0-9]\b", r"Spring Boot ?[0-9]", r"Next\.js ?1[0-9]",
]
_LOCAL_DIR = pathlib.Path(__file__).resolve().parent.parent / "plans"
for _name in ("prohibidos-proyecto.txt", "prohibidos-proceso.txt"):
    _local = _LOCAL_DIR / _name
    if _local.is_file():
        for _lineno, _line in enumerate(_local.read_text(encoding="utf-8").splitlines(), 1):
            _pattern = _line.strip()
            if not _pattern or _pattern.startswith("#"):
                continue
            try:
                re.compile(_pattern)
            except re.error as _error:
                print(f"{_local}:{_lineno}: patrón regular inválido: {_error}", file=sys.stderr)
                sys.exit(1)
            FORBIDDEN.append(_pattern)
DYNAMIC_FORBIDDEN_KEYS = (
    "backend.jdk_ruta_desarrollo", "devops.registry", "devops.java_home_nodo", "devops.java_home_contenedor",
    "devops.jdk_url", "devops.slack_canal", "sonarqube.url",
    "integraciones.clerk_issuer_uri", "backend.cors_origenes",
    "devops.entornos.{nombre}.cors_origenes", "devops.entornos.{nombre}.clerk_issuer_uri",
)
ALLOWED_FILES = {".agents/stack.yaml", ".agents/rules/project.md", ".agents/mcp_config.json"}
SCAN_SUFFIXES = {
    ".md", ".py", ".sh", ".mjs", ".js", ".json", ".yaml", ".yml",
    ".ts", ".tsx", ".java", ".gradle", ".sql", ".properties", ".template", ".groovy",
}
SCAN_NAMES = {"Jenkinsfile", "Dockerfile"}

# Único registro de mapas cuyas claves las elige el usuario. Admite rutas anidadas;
# sus entradas conservan sus subclaves, sustituyendo solo el nombre libre por {nombre}.
FREE_NAME_MAPS = {"conexiones", "devops.entornos"}


def documentation_keys(data, prefix=""):
    if isinstance(data, dict):
        if prefix in FREE_NAME_MAPS:
            keys = {prefix + ".{nombre}"} if any(isinstance(v, dict) for v in data.values()) else set()
            for value in data.values():
                keys.update(documentation_keys(value, prefix + ".{nombre}"))
            return keys or {prefix + ".{nombre}"}
        if data:
            keys = set()
            for name, value in data.items():
                keys.update(documentation_keys(value, f"{prefix}.{name}" if prefix else name))
            return keys
    return {prefix} if prefix else set()


def condiciones_documentacion(project_dir, data):
    """Lectura independiente de metadatos; fuentes: comentarios, generado: archivo."""
    agents = project_dir / '.agents'
    # El generador siempre escribe esta huella; las fuentes no la llevan.
    # No depender de carpetas que pueden quedar vacías y desaparecer al clonar.
    fuente = not (agents / '.generado.json').is_file()
    # Incluir mapas padres además de las hojas.
    def schema(value, prefix=''):
        result = set()
        if isinstance(value, dict):
            for key, child in value.items():
                path = (prefix + '.' if prefix else '') + ('{nombre}' if prefix in FREE_NAME_MAPS else key)
                result.add(path)
                result.update(schema(child,path))
        return result
    conocidas = schema(data)
    reglas = {}
    if fuente:
        padres = []
        for numero, line in enumerate((agents/'stack.yaml').read_text().splitlines(),1):
            m = re.match(r'^( *)([\w.-]+):',line)
            if not m:
                continue
            nivel = len(m[1])
            while padres and padres[-1][0] >= nivel:
                padres.pop()
            prefix = '.'.join(k for _,k in padres)
            key = '{nombre}' if prefix in FREE_NAME_MAPS else m[2]
            path = (prefix + '.' if prefix else '') + key
            padres.append((nivel,key))
            cond = re.search(r'requerida_con:\s*(.*)',line)
            if cond:
                if path in reglas and reglas[path] != cond[1].strip():
                    raise ValueError('condiciones distintas en stack.yaml:' + str(numero))
                reglas[path] = cond[1].strip()
        rama = None
        for line in (agents/'config/claves.md').read_text().splitlines():
            abre = re.fullmatch(r'<!-- si ([\w.]+)=([\w-]+) -->',line)
            if abre:
                rama = abre[1] + '=' + abre[2]
            elif line == '<!-- fin -->':
                rama = None
            heading = re.fullmatch(r'## ([\w.{}-]+)',line)
            if heading and rama and heading[1] in conocidas and heading[1] not in reglas:
                reglas[heading[1]] = rama
    else:
        file = agents/'config/condiciones.yaml'
        if not file.is_file():
            raise ValueError('falta config/condiciones.yaml generado; regenera el .agents')
        meta = yaml.load(file.read_text(),Loader=UniqueKeyLoader)
        if not isinstance(meta,dict) or set(meta) != {'version','claves','reglas'} or type(meta['version']) is not int or meta['version'] != 1 or not isinstance(meta['claves'],list) or not meta['claves'] or any(not isinstance(k,str) for k in meta['claves']) or len(set(meta['claves'])) != len(meta['claves']) or not isinstance(meta['reglas'],list):
            raise ValueError('config/condiciones.yaml inválido; regenera el .agents')
        conocidas = set(meta['claves'])
        for regla in meta['reglas']:
            if not isinstance(regla,str) or regla.count(' :: ') != 1:
                raise ValueError('config/condiciones.yaml: regla inválida')
            key,expr = regla.split(' :: ')
            if key in reglas or key not in conocidas:
                raise ValueError('config/condiciones.yaml: regla repetida o clave desconocida')
            reglas[key] = expr
    opciones = yaml.load((agents/'config/opciones.yaml').read_text(),Loader=UniqueKeyLoader) or {}
    terms = {}
    for key,expr in reglas.items():
        terms[key] = []
        for term in expr.split('&&'):
            m = re.fullmatch(r'\s*([\w.{}-]+)\s*(!=|=)\s*(null|true|false|[\w-]+)\s*',term)
            if not m or m[1] not in conocidas:
                raise ValueError('condición inválida o clave desconocida: ' + term)
            ref,op,raw = m.groups()
            value = {'null': None, 'true': True, 'false': False}.get(raw, int(raw) if re.fullmatch(r'-?\d+', raw) else raw)
            if '{nombre}' in ref and ('{nombre}' not in key or not any(ref.startswith(p+'.{nombre}.') for p in FREE_NAME_MAPS)):
                raise ValueError('comodín fuera de contexto: ' + ref)
            if ref in opciones and not any(type(value) is type(v) and value == v for v in opciones[ref]):
                raise ValueError('valor de condición fuera de opciones: ' + term)
            terms[key].append((ref,op,value))
    def activa(normal):
        # Un encabezado de mapa libre cubre todas las entradas que lo usan.
        paths = ['']
        for part in normal.split('.'):
            siguientes = []
            for path in paths:
                if part == '{nombre}':
                    actual = get(data,path) if has_key(data,path) else {}
                    if isinstance(actual,dict):
                        siguientes.extend(path+'.'+k for k in actual)
                else:
                    siguientes.append((path+'.' if path else '')+part)
            paths = siguientes
        for path in paths:
            name = path.split('.')[normal.split('.').index('{nombre}')] if '{nombre}' in normal else None
            ok = True
            for target,comparaciones in terms.items():
                if normal != target and not normal.startswith(target+'.'):
                    continue
                for ref,op,value in comparaciones:
                    real = ref.replace('{nombre}',name) if name else ref
                    if not has_key(data,real):
                        ok = False
                        continue
                    actual = get(data,real)
                    igual = type(actual) is type(value) and actual == value
                    ok &= igual if op == '=' else not igual
            if ok:
                return True
        return False
    return fuente, conocidas, activa


def check_documentation(project_dir, data):
    file = project_dir / ".agents/config/claves.md"
    if not file.is_file():
        return ["F: falta .agents/config/claves.md"]
    text = file.read_text(encoding="utf-8")
    sections = list(re.finditer(r"^## +([\w.{}-]+)[ \t]*$", text, re.M))
    headings = [match.group(1) for match in sections]
    expected = documentation_keys(data)
    try:
        fuente, schema, activa = condiciones_documentacion(project_dir,data)
        if not fuente:
            expected = {key for key in expected if activa(key)}
            # Una clave activa ausente sigue necesitando ficha.
            padres = {key.rsplit('.',1)[0] for key in schema if '.' in key}
            expected.update(key for key in schema if key not in padres and activa(key))
    except Exception as e:
        return ['F: ' + str(e)]
    actual = set(headings)
    errors = [f"F: falta explicación de {key} en config/claves.md" for key in sorted(expected - actual)]
    errors += [f"F: config/claves.md explica una clave inexistente: {key}" for key in sorted(actual - expected)]
    errors += [f"F: sección repetida en config/claves.md: {key}" for key in sorted(actual) if headings.count(key) > 1]
    label = "**Dónde se ve en tu proyecto:**"
    for index, match in enumerate(sections):
        key = match.group(1)
        end = sections[index + 1].start() if index + 1 < len(sections) else len(text)
        body = text[match.end():end]
        fields = list(re.finditer(r"^" + re.escape(label), body, re.M))
        if not fields:
            errors.append(f"F: falta '{label}' en {key}")
            continue
        if len(fields) != 1:
            errors.append(f"F: campo '{label}' repetido en {key}")
        if not re.match(r"\s*\*\*En resumen:\*\*[^\n]*\n\s*\n" + re.escape(label), body):
            errors.append(f"F: '{label}' debe ir justo después de 'En resumen' en {key}")
        detail = body[fields[0].end():]
        detail = re.split(r"^\*\*[^*\n]+:\*\*", detail, maxsplit=1, flags=re.M)[0]
        if not detail.strip():
            errors.append(f"F: '{label}' está vacío en {key}")
    return errors


def is_scalar(v):
    return v is None or isinstance(v, (str, int, float, bool))


class UniqueKeyLoader(yaml.SafeLoader):
    """Cargador que falla con claves repetidas (YAML las acepta en silencio y se queda con la última)."""


def _no_duplicates(loader, node, deep=False):
    seen = set()
    for key_node, _ in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in seen:
            raise yaml.YAMLError(f"clave repetida `{key}` (línea {key_node.start_mark.line + 1})")
        seen.add(key)
    return loader.construct_mapping(node, deep=deep)


UniqueKeyLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _no_duplicates)


def check_shape(data, limit=4):
    errs = []
    def walk(value, depth=0, key=''):
        if is_scalar(value):
            return
        if isinstance(value, list):
            if not all(is_scalar(x) for x in value):
                errs.append(f"A: `{key}` contiene lista no escalar")
        elif isinstance(value, dict):
            if value and depth >= limit:
                errs.append(f"A: `{key}` supera {limit} niveles")
            else:
                for k, v in value.items():
                    walk(v, depth + 1, (key + '.' if key else '') + str(k))
        else:
            errs.append(f"A: `{key}` tiene tipo no admitido")
    if not isinstance(data, dict):
        return ['A: el documento no es un mapa de claves']
    walk(data)
    return errs


def mismo_resultado_yaml(antes, despues):
    # Distingue también tipos: True no equivale al entero 1.
    if type(antes) is not type(despues):
        return False
    if isinstance(antes, dict):
        return (antes.keys() == despues.keys()
                and all(mismo_resultado_yaml(antes[k], despues[k]) for k in antes))
    if isinstance(antes, list):
        return (len(antes) == len(despues)
                and all(mismo_resultado_yaml(a, b) for a, b in zip(antes, despues)))
    return antes == despues


def leer_subconjunto(project_dir, archivo):
    # Carga independiente: sintaxis YAML y claves repetidas no dependen del generador.
    texto = archivo.read_text(encoding='utf-8')
    independiente = yaml.load(texto, Loader=UniqueKeyLoader)
    # Importar funciones no ejecuta main; evita bytecode en sources al correr sin -B.
    spec = importlib.util.spec_from_file_location('lector_generador', project_dir / '.agents/actualizar.py')
    module = importlib.util.module_from_spec(spec)
    previo = sys.dont_write_bytecode
    try:
        sys.dont_write_bytecode = True
        spec.loader.exec_module(module)
        generado = module.parsear_yaml(texto, str(archivo))
        if not mismo_resultado_yaml(independiente, generado):
            raise ValueError(f'{archivo}: PyYAML y parsear_yaml del generador producen resultados distintos')
        return independiente
    finally:
        sys.dont_write_bytecode = previo


def valores_dinamicos(data, partes):
    if not partes:
        return data if isinstance(data, list) else [data]
    if not isinstance(data, dict):
        return []
    if partes[0] == '{nombre}':
        return [v for child in data.values() for v in valores_dinamicos(child, partes[1:])]
    return valores_dinamicos(data[partes[0]], partes[1:]) if partes[0] in data else []


def has_key(data, dotted):
    cur = data
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return False
        cur = cur[part]
    return True


def get(data, dotted):
    cur = data
    for part in dotted.split("."):
        cur = cur[part]
    return cur


def check_project(project_dir):
    errs = []
    expected = EXPECTED_STACK.get(project_dir.name)
    stack_file = project_dir / ".agents" / "stack.yaml"

    # A y B
    data = None
    if not stack_file.exists():
        errs.append("A: falta .agents/stack.yaml")
    else:
        try:
            data = leer_subconjunto(project_dir, stack_file)
        except Exception as e:
            data = None
            errs.append(f"A: YAML inválido: {str(e).splitlines()[0]}")
        if data is not None:
            errs += check_shape(data, 4 if expected == "springboot" else 2)
            if isinstance(data, dict):
                errs += check_documentation(project_dir, data)
                for key in REQUIRED.get(expected, COMMON):
                    if not has_key(data, key):
                        errs.append(f"B: falta la clave `{key}`")
                if has_key(data, "proyecto.stack") and get(data, "proyecto.stack") != expected:
                    errs.append(f"B: proyecto.stack es {get(data, 'proyecto.stack')!r}, se esperaba {expected!r}")

    # Los metadatos de migración no declaran claves vigentes de stack.yaml.
    migraciones = project_dir / '.agents/config/migraciones.yaml'
    if migraciones.exists():
        try:
            rules = yaml.load(migraciones.read_text(), Loader=UniqueKeyLoader)
            if not isinstance(rules, dict) or any(not isinstance(key, str) or not re.fullmatch(r'[a-z_][\w-]*(?:\.[a-z_][\w-]*)*', key) or not isinstance(pair, list) or len(pair) != 2 or not is_scalar(pair[0]) or not isinstance(pair[1], str) or not pair[1].strip() for key, pair in rules.items()):
                raise ValueError('usa ruta: [valor retirado, mensaje]')
        except (yaml.YAMLError, ValueError, OSError) as error:
            errs.append('A: config/migraciones.yaml inválido: ' + str(error).splitlines()[0])

    # E. La configuración MCP por workspace .agents/mcp_config.json no debe existir.
    if (project_dir / ".agents" / "mcp_config.json").exists():
        errs.append("E: existe .agents/mcp_config.json; ya no se usa y debe eliminarse")

    # C
    agents_md = project_dir / "AGENTS.md"
    if not agents_md.exists() or ".agents/stack.yaml" not in agents_md.read_text(encoding="utf-8"):
        errs.append("C: AGENTS.md no ordena leer `.agents/stack.yaml`")

    # D
    # La lista D admite valores dinámicos: escalares o listas de escalares (se aplanan, un
    # patrón por elemento). El documento fuente es el mismo stack.yaml.
    dynamic_values = []
    if data is not None:
        for key in DYNAMIC_FORBIDDEN_KEYS:
            dynamic_values += [re.escape(str(v)) for v in valores_dinamicos(data, key.split('.'))
                               if v is not None and str(v).strip()]

    pat = re.compile("|".join(FORBIDDEN + dynamic_values))
    files = [agents_md] if agents_md.exists() else []
    files += [p for p in (project_dir / ".agents").rglob("*")
              if p.is_file() and (p.suffix in SCAN_SUFFIXES or p.name in SCAN_NAMES)
              and p.name != ".generado.json" and p.suffix != ".dbcnb"
              and "__pycache__" not in str(p) and "/.cache/" not in str(p)]
    for f in sorted(files):
        rel = str(f.relative_to(project_dir))
        if rel in ALLOWED_FILES:
            continue
        content = f.read_bytes()
        if b"\x00" in content:
            continue
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            m = pat.search(line)
            if m:
                errs.append(f"D: {rel} L{i} [{m.group(0)}] {line.strip()[:120]}")
    return errs


def main():
    total = 0
    for project_dir in sorted(p for p in root.iterdir() if (p / ".agents").is_dir()):
        errs = check_project(project_dir)
        total += len(errs)
        print(f"##### {project_dir.name}")
        for e in errs:
            print("  " + e)
        print()
    print(f"Total de problemas: {total}")
    sys.exit(1 if total else 0)


if __name__ == "__main__":
    main()
