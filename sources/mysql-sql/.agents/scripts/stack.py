#!/usr/bin/env python3
"""stack.py - Lector de .agents/stack.yaml para el repositorio de base de datos (PyYAML).

Único punto del .agents que lee el archivo de parámetros del proyecto. Ningún otro script lee
.agents/stack.yaml por su cuenta: importan este módulo o lo llaman por terminal.

Uso:
  python3 .agents/scripts/stack.py get <clave>    Imprime el valor (para listas, una por línea)
  python3 .agents/scripts/stack.py validate       Comprueba claves obligatorias y formato
  python3 .agents/scripts/stack.py huella        Huella sha256 de la configuración (ver abajo)
  python3 .agents/scripts/stack.py --help

Códigos de salida: 0 = OK, 2 = BLOCKED (infraestructura).

Uso desde código (Python):

    import stack
    stack.cargar()                # dict completo (valida claves obligatorias)
    stack.obtener("base_de_datos.nombre")
"""
import hashlib
import os
import re
import subprocess
import sys
import json

try:
    import yaml
except ImportError:
    sys.stderr.write("BLOCKED (infraestructura): falta PyYAML (python3 -m pip install pyyaml).\n")
    sys.exit(2)


class ClaveRepetidaError(Exception):
    def __init__(self, clave, linea):
        self.clave = clave
        self.linea = linea


class UniqueKeyLoader(yaml.SafeLoader):
    pass


def construir_mapa_unico(loader, nodo, deep=False):
    mapa = {}
    for nodo_clave, nodo_valor in nodo.value:
        clave = loader.construct_object(nodo_clave, deep=deep)
        if clave in mapa:
            raise ClaveRepetidaError(clave, nodo_clave.start_mark.line + 1)
        mapa[clave] = loader.construct_object(nodo_valor, deep=deep)
    return mapa


UniqueKeyLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, construir_mapa_unico)

# Stack que este .agents soporta: si `proyecto.stack` difiere, el archivo no es de este proyecto.
STACK = "mysql"

REQUIRED = [
    'nomenclatura.tablas', 'nomenclatura.tablas_plural', 'nomenclatura.columnas', 'nomenclatura.clave_primaria', 'nomenclatura.prefijo_procedimiento', 'nomenclatura.prefijo_funcion', 'nomenclatura.prefijo_vista', 'nomenclatura.prefijo_evento', 'nomenclatura.prefijo_trigger', 'nomenclatura.prefijo_indice', 'nomenclatura.prefijo_parametro', 'nomenclatura.prefijo_variable',
    "version_esquema",
    "proyecto.nombre", "proyecto.stack",
    "base_de_datos.motor", "base_de_datos.version", "base_de_datos.nombre",
    "base_de_datos.carpeta_notebooks",
    "notebooks",
    "conexiones",
    "mcp.base_de_datos",
    "herramientas.graphify", "git.rama_base",
]


def ruta_opciones():
    return os.path.join(os.path.dirname(ruta_stack()), "config", "opciones.yaml")


def cargar_opciones():
    """Devuelve el mapa `clave -> [valores]` de config/opciones.yaml; {} si no existe el archivo."""
    ruta = ruta_opciones()
    try:
        with open(ruta, encoding="utf-8") as fh:
            texto = fh.read()
    except OSError:
        return {}
    try:
        opciones = yaml.load(texto, Loader=UniqueKeyLoader) or {}
    except ClaveRepetidaError as e:
        bloqueado(f"config/opciones.yaml: clave repetida {e.clave} (línea {e.linea})")
    except yaml.YAMLError as e:
        bloqueado(f"config/opciones.yaml: YAML inválido: {str(e).splitlines()[0]}")
    if not isinstance(opciones, dict):
        bloqueado("config/opciones.yaml: el documento no es un mapa de claves")
    return opciones


def validar_opciones(data):
    """Comprueba las marcas `si clave=valor`: cada clave de config/opciones.yaml debe existir en
    stack.yaml y su valor estar en su lista. Si el archivo falta o está vacío, no hay nada."""
    opciones = cargar_opciones()
    for clave, valores in opciones.items():
        if not isinstance(valores, list) or not valores or not all(es_escalar(x) for x in valores):
            bloqueado(f"config/opciones.yaml: `{clave}` debe valer una lista de escalares")
        valor = obtener(data, clave)
        if valor is None:
            bloqueado(
                f"falta la clave obligatoria {clave} "
                f"(config/opciones.yaml; valores válidos: {', '.join(formato_escalar(x) for x in valores)})"
            )
        if valor not in valores:
            bloqueado(
                f"valor de {clave} no está en config/opciones.yaml; "
                f"valores válidos: {', '.join(formato_escalar(x) for x in valores)}"
            )

    validar_requisitos(data, opciones)


def validar_requisitos(data, opciones):
    ruta = os.path.join(os.path.dirname(ruta_stack()), "config", "requisitos.yaml")
    if not os.path.isfile(ruta):
        return
    try:
        with open(ruta, encoding="utf-8") as fh:
            reglas = yaml.load(fh, Loader=UniqueKeyLoader) or {}
    except (yaml.YAMLError, ClaveRepetidaError):
        bloqueado("config/requisitos.yaml: mapa plano de condiciones no válido")
    if not isinstance(reglas, dict):
        bloqueado("config/requisitos.yaml: el documento debe ser un mapa")

    def condicion(texto):
        if not isinstance(texto, str) or "=" not in texto:
            bloqueado("config/requisitos.yaml: se esperaba clave=valor")
        clave, literal = texto.split("=", 1)
        valores = [v for v in opciones.get(clave, []) if formato_escalar(v) == literal]
        if len(valores) != 1:
            bloqueado(f"config/requisitos.yaml: {texto} no está en config/opciones.yaml")
        return clave, valores[0]

    pares = []
    for izquierda, lista in reglas.items():
        if not isinstance(lista, list) or not lista:
            bloqueado("config/requisitos.yaml: lista de requisitos no válida")
        pares.append((condicion(izquierda), [condicion(x) for x in lista]))
    for (clave, valor), requisitos in pares:
        if obtener(data, clave) == valor:
            for requerida, esperado in requisitos:
                if obtener(data, requerida) != esperado:
                    bloqueado(f"{clave}={formato_escalar(valor)} exige {requerida}={formato_escalar(esperado)}")


def bloqueado(msg):
    sys.stderr.write(f"BLOCKED (infraestructura): .agents/stack.yaml: {msg}\n")
    sys.exit(2)


def raiz_repo():
    out = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    return out.stdout.strip() if out.returncode == 0 else os.getcwd()


def ruta_stack():
    return os.path.join(raiz_repo(), ".agents", "stack.yaml")


def es_escalar(v):
    return v is None or isinstance(v, (str, int, float, bool))


def parsear(texto):
    if texto.strip() == "":
        bloqueado("el archivo está vacío")
    try:
        data = yaml.load(texto, Loader=UniqueKeyLoader)
    except ClaveRepetidaError as e:
        bloqueado(f"clave repetida {e.clave} (línea {e.linea})")
    except yaml.YAMLError as e:
        bloqueado(f"YAML inválido: {str(e).splitlines()[0]}")
    if not isinstance(data, dict):
        bloqueado("el documento no es un mapa de claves")
    if 'conexiones' in data and data['conexiones'] is None:
        data['conexiones'] = {}
    for k, v in data.items():
        if es_escalar(v):
            continue
        if isinstance(v, list):
            if not all(es_escalar(x) for x in v):
                bloqueado(f"`{k}` es una lista con elementos no escalares")
            continue
        if isinstance(v, dict):
            for k2, v2 in v.items():
                if es_escalar(v2):
                    continue
                if isinstance(v2, list) and all(es_escalar(x) for x in v2):
                    continue
                bloqueado(f"`{k}.{k2}` anida más de dos niveles o mezcla tipos")
            continue
        bloqueado(f"`{k}` tiene un tipo no admitido")
    return data


def cargar():
    ruta = ruta_stack()
    try:
        with open(ruta, encoding="utf-8") as fh:
            texto = fh.read()
    except OSError:
        bloqueado("no se encontró .agents/stack.yaml en la raíz del repositorio.")
    data = parsear(texto)
    import importlib.util
    spec = importlib.util.spec_from_file_location('condiciones_generadas', os.path.join(os.path.dirname(ruta_stack()), 'actualizar.py'))
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    try:
        meta = modulo.cargar_condiciones(os.path.dirname(ruta_stack()))
        modulo.validar_claves_condicionales(data, meta)
    except ValueError as e:
        bloqueado(str(e))
    return validar_datos(data)


def validar_datos(data):
    if "proyecto" not in data or not isinstance(data["proyecto"], dict) or "stack" not in data["proyecto"]:
        bloqueado("falta la clave 'proyecto.stack'")
    if data["proyecto"]["stack"] != STACK:
        bloqueado(f"proyecto.stack es {data['proyecto']['stack']!r}, este .agents corresponde al stack {STACK!r}")
    if "version_esquema" not in data:
        bloqueado("falta la clave obligatoria version_esquema")
    for clave in REQUIRED:
        valor = obtener(data, clave)
        if valor is None and clave not in ("git.rama_base",):
            bloqueado(f"falta la clave obligatoria {clave}")
        if clave == "git.rama_base" and (not isinstance(data.get("git"), dict) or "rama_base" not in data["git"]):
            bloqueado("falta la clave obligatoria git.rama_base")
    from urllib.parse import urlsplit
    config = data.get("documentacion")
    if not isinstance(config, dict):
        bloqueado("falta documentacion")
    for clave in ("url_api", "variable_password", "modelo_chat", "modelo_contexto_grande", "modelo_transformacion", "timeout_chat"):
        if clave not in config:
            bloqueado(f"falta documentacion.{clave}; declara esta clave según la plantilla y regenera.")
        if clave not in ("url_api", "timeout_chat") and config[clave] is not None and (not isinstance(config[clave], str) or not config[clave].strip()):
            bloqueado(f"documentacion.{clave} debe ser texto o null")
    if type(config["timeout_chat"]) is not int or not 1 <= config["timeout_chat"] <= 3600:
        bloqueado("documentacion.timeout_chat debe ser un entero entre 1 y 3600 segundos")
    if not isinstance(config["url_api"], str):
        bloqueado("documentacion.url_api debe ser HTTP(S)")
    try:
        url = urlsplit(config["url_api"])
        valido = url.scheme in ("http", "https") and url.hostname and not any((url.username, url.password, url.query, url.fragment))
    except ValueError:
        valido = False
    if not valido:
        bloqueado("documentacion.url_api debe ser HTTP(S), sin credenciales ni parámetros")
    if config["variable_password"] is not None and not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", config["variable_password"]):
        bloqueado("documentacion.variable_password solo admite el nombre de una variable")
    for clave in ("tablas", "columnas"):
        if obtener(data, "nomenclatura." + clave) not in ("PascalCase", "snake_case", "camelCase"):
            bloqueado("nomenclatura." + clave + " debe ser PascalCase, snake_case o camelCase")
    patron = obtener(data, "nomenclatura.clave_primaria")
    if not isinstance(patron, str) or "{Entidad}" not in patron:
        bloqueado("nomenclatura.clave_primaria debe contener {Entidad}")
    for clave in ("procedimiento", "funcion", "vista", "evento", "trigger", "indice", "parametro", "variable"):
        valor = obtener(data, "nomenclatura.prefijo_" + clave)
        valores = valor if isinstance(valor, list) and clave == "trigger" else [valor]
        if not valores or any(not isinstance(v, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", v) for v in valores):
            bloqueado("nomenclatura.prefijo_" + clave + " debe ser texto de identificador no vacío")
    if not isinstance(obtener(data, "nomenclatura.tablas_plural"), bool):
        bloqueado("nomenclatura.tablas_plural debe ser true o false")
    return data


def obtener(data, clave_punteada):
    cur = data
    for part in clave_punteada.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def get(clave):
    data = cargar()
    if clave == 'base_de_datos.version':
        return version_texto()
    valor = obtener(data, clave)
    permitido_none = (
        (clave == "git.rama_base" and isinstance(data.get("git"), dict) and "rama_base" in data["git"])
    )
    if clave in ("documentacion.variable_password", "documentacion.modelo_chat", "documentacion.modelo_contexto_grande", "documentacion.modelo_transformacion") and isinstance(data.get("documentacion"), dict) and clave.split(".")[1] in data["documentacion"]:
        permitido_none = True
    if valor is None and not permitido_none:
        bloqueado(f"falta la clave {clave}")
    return valor


def validar():
    data = cargar()
    validar_opciones(data)
    return True


def huella_configuracion(data):
    """sha256 (hex) de las líneas `<clave>=<valor>\n`, para cada clave de config/opciones.yaml
    resuelta en .agents/stack.yaml, en orden alfabético. Es la misma fórmula que aplica
    actualizar.py al escribir .generado.json y stack.mjs en su subcomando `huella`."""
    pares = []
    for clave in sorted(cargar_opciones()):
        valor = obtener(data, clave)
        if not es_escalar(valor):
            bloqueado(
                f"falta la clave {clave} "
                "(huella de la configuración; lista de valores en config/opciones.yaml)"
            )
        pares.append(f"{clave}={formato_escalar(valor)}\n")
    return hashlib.sha256("".join(pares).encode("utf-8")).hexdigest()


def valor_canonico(valor):
    """Contrato compartido con los lectores: escalares históricos; compuestos JSON."""
    def normalizar(v):
        if isinstance(v, float) and v.is_integer():
            return int(v)
        if isinstance(v, list):
            return [normalizar(x) for x in v]
        if isinstance(v, dict):
            return {k: normalizar(x) for k, x in v.items()}
        return v
    if isinstance(valor, (list, dict)):
        return json.dumps(normalizar(valor), ensure_ascii=False, sort_keys=True,
                          separators=(',', ':'), allow_nan=False)
    return formato_escalar(valor)


def mapa_regenerar(data, opciones):
    valores = {k: valor_canonico(obtener(data, k)) for k in opciones}
    def hojas(obj, prefijo):
        if isinstance(obj, dict) and obj:
            for k, v in sorted(obj.items()):
                hojas(v, prefijo + '.' + k)
        else:
            valores[prefijo] = valor_canonico(obj)
    hojas(data.get('nomenclatura', {}), 'nomenclatura')
    return dict(sorted(valores.items()))


def huella():
    data = cargar()
    validar_opciones(data)
    return huella_configuracion(data)


def version_texto():
    """El escalar fuente conserva la precisión de 8.10 sin convertirlo a float."""
    try:
        with open(ruta_stack(), encoding='utf-8') as fh:
            tree = yaml.compose(fh.read(), Loader=UniqueKeyLoader)
        database = next(v for k,v in tree.value if k.value == 'base_de_datos')
        version = next(v for k,v in database.value if k.value == 'version')
        if not isinstance(version, yaml.nodes.ScalarNode):
            raise ValueError()
        return version.value
    except (OSError, ValueError, StopIteration, TypeError, AttributeError, yaml.YAMLError):
        bloqueado('base_de_datos.version debe ser un escalar textual válido')


def main(argv):
    if argv and argv[0] == '--validar-generacion':
        payload = json.load(sys.stdin)
        validar_datos(payload['data'])
        return 0

    if not argv or argv[0] in ("--help", "-h"):
        sys.stdout.write(
            "Uso: python3 .agents/scripts/stack.py get <clave> | validate | huella | regenerar | registro-datos | --help\n"
            "  get <clave>   imprime el valor de la clave punteada (p. ej. base_de_datos.nombre);\n"
            "                salida: booleanos true/false; null línea vacía; números sin decimales añadidos;\n"
            "                textos tal cual; listas, un elemento por línea\n"
            "  validate      comprueba que .agents/stack.yaml existe, respeta el subconjunto\n"
            f"                y tiene las claves obligatorias del stack '{STACK}'\n"
            "  huella        imprime el sha256 de la configuración (claves de config/opciones.yaml\n"
            "                resueltas en stack.yaml): misma fórmula que usa actualizar.py en .generado.json\n"
            "Códigos de salida: 0 = OK, 2 = BLOCKED (infraestructura).\n")
        return 0
    if argv[0] == "validate":
        validar()
        sys.stdout.write(f"OK: .agents/stack.yaml es válido para el stack '{STACK}'.\n")
        return 0
    if argv[0] in ('regenerar', 'registro-datos') and len(argv) == 1:
        validar()
        data = cargar()
        result = mapa_regenerar(data, cargar_opciones()) if argv[0] == 'regenerar' else {
            'stack': STACK, 'servicios': ['.'], 'gateway': None,
            'valores': {key: obtener(data,key) for key in ['integraciones.gestion_usuarios', 'nomenclatura.tablas', 'nomenclatura.tablas_plural', 'nomenclatura.columnas', 'nomenclatura.clave_primaria', 'nomenclatura.prefijo_procedimiento', 'nomenclatura.prefijo_funcion', 'nomenclatura.prefijo_vista', 'nomenclatura.prefijo_evento', 'nomenclatura.prefijo_trigger', 'nomenclatura.prefijo_indice', 'nomenclatura.prefijo_parametro', 'nomenclatura.prefijo_variable', 'base_de_datos.version']}}
        if argv[0] == 'registro-datos':
            result['valores']['base_de_datos.version'] = version_texto()
        sys.stdout.write(json.dumps(result, ensure_ascii=False, sort_keys=True) + '\n')
        return 0
    if argv[0] == "huella":
        sys.stdout.write(huella() + "\n")
        return 0
    if argv[0] == "get":
        if len(argv) != 2:
            sys.stderr.write("uso: python3 stack.py get <clave>\n")
            return 2
        imprimir(get(argv[1]))
        return 0
    sys.stderr.write(f"uso: python3 stack.py get <clave> | validate | huella | regenerar | registro-datos | --help\n   argumento desconocido: {argv[0]}\n")
    return 2


def formato_escalar(valor):
    if valor is None:
        return ""
    if isinstance(valor, bool):
        return "true" if valor else "false"
    if isinstance(valor, float) and valor.is_integer():
        return str(int(valor))
    return str(valor)


def imprimir(valor):
    if isinstance(valor, list):
        for x in valor:
            sys.stdout.write(formato_escalar(x) + "\n")
        return
    if isinstance(valor, dict):
        bloqueado("la clave solicitada es un mapa; pide una clave concreta dentro de él")
    sys.stdout.write(formato_escalar(valor) + "\n")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
