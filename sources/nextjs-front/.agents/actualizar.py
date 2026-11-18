#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""actualizar.py — regenera el `.agents` del proyecto desde el repositorio de origen (sources).

Uso normal, desde la raíz del proyecto:
    python3 -I -B .agents/actualizar.py --kit <KIT>
Sin `--kit`, el script pregunta la ruta de la carpeta que contiene `sources/`; elige el proyecto de sources
según `proyecto.stack` del `.agents/stack.yaml` del proyecto (nextjs, springboot o mysql) y
escribe en el `.agents` del proyecto solo lo que corresponde a su configuración: las marcas
`si clave=valor` de sources, resueltas con `stack.yaml`.

Opciones:
  --kit <ruta>                  ruta de la carpeta que contiene `sources/`; no pregunta.
  --proyecto <ruta>             raíz del proyecto (por defecto, el directorio actual).
  --simular                     muestra el diff y no escribe nada.
  --si                          aplica sin pedir confirmación.
  --comprobar-referencias       tras generar, comprueba que no queden referencias rotas.
  --comprobar-cobertura         comprueba que cada línea de sources aparece en alguna
                                combinación de valores de opciones.yaml.
  --comprobar-fuentes <ruta>    solo valida las marcas de `sources/<proyecto>` y termina.

Solo la biblioteca estándar de Python 3, sin dependencias.
Códigos de salida: 0 = OK; 2 = BLOCKED (error de marcas, de configuración o de referencias).
Reglas del generador:
  - nunca escribe ni borra `.agents/stack.yaml`, `.agents/documentacion.json`,
    `.agents/documentacion.md`, `.agents/catalogo-proyecto.json`, `.agent-runs/` ni `knowledge-base/`.
  - crea rules/project.md desde plantilla solo si falta; después nunca lo sobrescribe ni borra.
  - avisa de claves nuevas/obsoletas sin valores y resuelve marcadores nomenclatura.
  - nada fuera de `.agents/` y `AGENTS.md`.
  - cada archivo de texto generado lleva una línea de cabecera con el comentario de su tipo;
    los archivos JSON y los assets de las skills no llevan cabecera.
  - al terminar escribe `.agents/.generado.json` con el origen, la huella de la configuración
    y la lista de archivos generados con su sha256.
"""

import argparse
import difflib
import hashlib
import fnmatch
import itertools
import json
import os
import re
import shutil
import subprocess
import sys

# Stacks que este generador soporta. La carpeta de `sources/` correspondiente no se
# declara aquí: se encuentra en tiempo de ejecución buscando en
# `<ruta>/sources/*/.agents/stack.yaml` el proyecto con `proyecto.stack` igual a este valor.
STACKS = ("mysql", "nextjs", "springboot")

PREGUNTA_RUTA = "Ruta de la carpeta que contiene `sources/`: "
PREGUNTA_STACK = "nextjs | springboot | mysql: "
CABECERA = (
    "generado automáticamente; no editar aquí: los cambios se hacen "
    "en el repositorio de origen (sources)"
)

ARCHIVO_ESTADO = ".generado.json"
# Rutas relativas a `.agents` que el generador nunca escribe ni borra (viven solo en el proyecto):
PROTEGIDAS = {"stack.yaml", "rules/project.md", "documentacion.json", "documentacion.md", "catalogo-proyecto.json", ".harness-local"}


#______________________________________________________________________________
# Errores

class MarcaError(Exception):
    def __init__(self, archivo, linea, mensaje):
        super().__init__(f"{archivo}:{linea}: {mensaje}")
        self.archivo = archivo
        self.linea = linea
        self.mensaje = mensaje


def abortar(errores):
    for e in errores:
        sys.stderr.write(f"BLOCKED: {e}\n")
    sys.exit(2)


def bloqueado(mensaje):
    sys.stderr.write(f"BLOCKED: {mensaje}\n")
    sys.exit(2)


#______________________________________________________________________________
# Subconjunto YAML (el mismo formato que aceptan `.agents/scripts/stack.mjs` y `stack.py`:
# mapas de hasta cuatro niveles (back), listas de escalares en línea o en bloque, comentarios con `#`).
# Aquí va copiado como funciones (sin importar de otro sitio) porque el generador corre en
# `-I` con la biblioteca estándar de Python 3.

RE_CLAVE = re.compile(r"^([\w.\-]+):\s*(.*)$")
RE_LISTA = re.compile(r"^\[(.*)\]$")


def texto_sin_comentario(linea):
    en_comillas = None
    i = 0
    while i < len(linea):
        c = linea[i]
        if en_comillas:
            if c == "\\" and en_comillas != "'":
                i += 1
            elif c == en_comillas:
                en_comillas = None
        elif c in ('"', "'"):
            en_comillas = c
        elif c == "#":
            return linea[:i]
        i += 1
    return linea


def escalar(s):
    s = s.strip()
    if s in ("null", "~"):
        return None
    if s == "true":
        return True
    if s == "false":
        return False
    if re.fullmatch(r"-?\d+(?:\.\d+)?", s):
        return float(s) if "." in s else int(s)
    if len(s) >= 2 and s[0] in ('"', "'") and s[-1] == s[0]:
        cuerpo = s[1:-1]
        if s[0] == '"':
            cuerpo = cuerpo.replace('\\"', '"').replace("\\\\", "\\")
        return cuerpo
    return s


def lista_en_linea(texto):
    m = RE_LISTA.match(texto.strip())
    if not m:
        return None
    interior = m.group(1).strip()
    if interior == "":
        return []
    en_comillas = None
    actual = ""
    items = []
    for c in interior:
        if en_comillas:
            if c == en_comillas:
                en_comillas = None
            actual += c
        elif c in ('"', "'"):
            en_comillas = c
            actual += c
        elif c == ",":
            items.append(actual)
            actual = ""
        else:
            actual += c
    items.append(actual)
    return [escalar(x) for x in items]


def parsear_yaml(texto, nombre):
    """Mapas de hasta cuatro niveles; sangría de dos espacios y listas escalares."""
    filas = []
    for numero, cruda in enumerate(texto.splitlines(), 1):
        linea = texto_sin_comentario(cruda)
        if not linea.strip():
            continue
        prefijo = linea[:len(linea) - len(linea.lstrip())]
        if '\t' in prefijo or len(prefijo) % 2:
            raise MarcaError(nombre, numero, 'sangría incoherente; usa dos espacios por nivel, sin tabuladores')
        filas.append((len(prefijo), linea.strip(), numero))

    def error(fila, mensaje):
        raise MarcaError(nombre, fila[2], mensaje)

    def valor(bruto, fila, lista=True):
        if bruto.startswith('['):
            if not lista or not bruto.endswith(']'):
                error(fila, 'lista inválida o no escalar')
            cuerpo = bruto[1:-1].strip()
            if not cuerpo:
                return []
            partes, actual, comilla, escape = [], '', '', False
            for c in cuerpo:
                if comilla:
                    actual += c
                    if escape:
                        escape = False
                    elif c == '\\' and comilla == '"':
                        escape = True
                    elif c == comilla:
                        comilla = ''
                elif c in ('"', "'"):
                    comilla = c
                    actual += c
                elif c == ',':
                    partes.append(actual.strip()); actual = ''
                else:
                    actual += c
            partes.append(actual.strip())
            if comilla or any(not p for p in partes):
                error(fila, 'lista inválida o comillas sin cerrar')
            return [valor(p, fila, False) for p in partes]
        if bruto[:1] in ('"', "'"):
            if len(bruto) < 2 or bruto[-1] != bruto[0]:
                error(fila, 'comillas sin cerrar')
        elif bruto[:1] in ('{', '}', '&', '*', '!', '|', '>') or bruto in ('---', '...'):
            error(fila, 'formato no admitido: sin mapas en línea, anclas, tags ni multilínea')
        elif re.match(r'^[\w.-]+:\s', bruto):
            error(fila, 'solo se admiten elementos escalares')
        return escalar(bruto)

    def leer(indice, sangria, profundidad):
        es_lista = filas[indice][1].startswith('- ')
        resultado = [] if es_lista else {}
        while indice < len(filas):
            fila = filas[indice]; nivel, texto_fila, _ = fila
            if nivel < sangria:
                break
            if nivel != sangria:
                error(fila, 'sangría incoherente o hijos de un escalar')
            if es_lista:
                if not texto_fila.startswith('- '):
                    error(fila, 'no se pueden mezclar listas y mapas')
                resultado.append(valor(texto_fila[2:].strip(), fila, False))
                indice += 1
                continue
            if profundidad >= 4:
                error(fila, 'máximo cuatro niveles de claves')
            match = RE_CLAVE.fullmatch(texto_fila)
            if not match:
                error(fila, 'se esperaba clave: valor; sin listas de objetos ni documentos múltiples')
            clave, bruto = match.group(1), match.group(2).strip()
            if clave in resultado:
                error(fila, 'clave repetida ' + clave)
            indice += 1
            if bruto == '{}' and clave == 'conexiones' and profundidad == 0:
                resultado[clave] = {}
            elif bruto:
                resultado[clave] = valor(bruto, fila)
            elif indice < len(filas) and filas[indice][0] > sangria:
                if filas[indice][0] != sangria + 2:
                    error(filas[indice], 'cada nivel añade exactamente dos espacios')
                resultado[clave], indice = leer(indice, sangria + 2, profundidad + 1)
            else:
                resultado[clave] = {}
        return resultado, indice

    if not filas:
        return {}
    if filas[0][0] != 0 or filas[0][1].startswith('- '):
        error(filas[0], 'el documento debe empezar con un mapa sin sangría')
    raiz, fin = leer(0, 0, 0)
    if fin != len(filas):
        error(filas[fin], 'sangría incoherente')
    return raiz


def obtener(data, clave):
    cur = data
    for parte in clave.split("."):
        if not isinstance(cur, dict) or parte not in cur:
            return None
        cur = cur[parte]
    return cur


def es_escalar(v):
    return v is None or isinstance(v, (str, int, float, bool))


def formato_escalar(valor):
    if valor is None:
        return ""
    if isinstance(valor, bool):
        return "true" if valor else "false"
    if isinstance(valor, float) and valor.is_integer():
        return str(int(valor))
    return str(valor)


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


def cargar_opciones(raiz_agents):
    """Devuelve {clave: [valores permitidos]} desde .agents/config/opciones.yaml."""
    ruta = os.path.join(raiz_agents, "config", "opciones.yaml")
    if not os.path.isfile(ruta):
        return {}
    with open(ruta, encoding="utf-8", newline="") as fh:
        texto = fh.read()
    try:
        data = parsear_yaml(texto, "config/opciones.yaml")
    except MarcaError as e:
        abortar([str(e)])
    opciones = {}
    for clave, valores in data.items():
        if (not isinstance(valores, list) or not valores
                or not all(es_escalar(x) for x in valores)):
            abortar([f"config/opciones.yaml:-1: `{clave}` debe valer una lista de escalares"])
        opciones[clave] = valores
    return opciones


def cargar_requisitos(raiz_agents, opciones):
    """Lista de implicaciones entre opciones, validada incluso para condiciones inactivas."""
    ruta = os.path.join(raiz_agents, "config", "requisitos.yaml")
    if not os.path.isfile(ruta):
        return []
    reglas, vistas = [], set()

    def condicion(texto):
        if not isinstance(texto, str) or "=" not in texto:
            bloqueado("config/requisitos.yaml: se esperaba clave=valor")
        clave, literal = texto.split("=", 1)
        permitidos = opciones.get(clave, [])
        valores = [v for v in permitidos if formato_escalar(v) == literal]
        if len(valores) != 1:
            bloqueado(f"config/requisitos.yaml: {texto} no está en config/opciones.yaml")
        return clave, valores[0]

    with open(ruta, encoding="utf-8") as fh:
        for numero, cruda in enumerate(fh, 1):
            linea = texto_sin_comentario(cruda.rstrip("\r\n"))
            if not linea.strip():
                continue
            match = re.fullmatch(r"([^\s:]+):\s*(\[.*\])\s*", linea)
            if not match or match[1] in vistas:
                bloqueado(f"config/requisitos.yaml:{numero}: mapa plano de condiciones no válido")
            vistas.add(match[1])
            izquierda = condicion(match[1])
            lista = lista_en_linea(match[2])
            if not lista:
                bloqueado(f"config/requisitos.yaml:{numero}: lista de requisitos vacía")
            reglas.append((izquierda, [condicion(x) for x in lista]))
    return reglas


def validar_requisitos(data, opciones, raiz_agents):
    for (clave, valor), requisitos in cargar_requisitos(raiz_agents, opciones):
        if obtener(data, clave) == valor:
            for requerida, esperado in requisitos:
                if obtener(data, requerida) != esperado:
                    bloqueado(f"{clave}={formato_escalar(valor)} exige {requerida}={formato_escalar(esperado)}")


def cargar_stack(ruta):
    if not os.path.isfile(ruta):
        bloqueado(f"no existe {ruta}")
    with open(ruta, encoding="utf-8", newline="") as fh:
        texto = fh.read()
    try:
        data = parsear_yaml(texto, ruta)
    except MarcaError as e:
        abortar([str(e)])
    if not isinstance(data, dict) or not isinstance(obtener(data, "proyecto"), dict):
        bloqueado(f"{ruta} no es un mapa de claves con la clave 'proyecto'")
    return data


def linea_de_clave(ruta, hoja):
    """1-based primera línea de `hoja:` en stack.yaml, para los mensajes de validación."""
    try:
        with open(ruta, encoding="utf-8") as fh:
            for i, l in enumerate(fh, start=1):
                sin = texto_sin_comentario(l.rstrip("\r\n"))
                if re.match(rf"^\s*{re.escape(hoja)}\s*:", sin):
                    return i
    except OSError:
        pass
    return -1


def validar_opciones(data, opciones, ruta_stack=None):
    """Cada clave de opciones.yaml debe existir en stack.yaml y su valor estar en la lista."""
    for clave, valores in opciones.items():
        valor = obtener(data, clave)
        permitidos = ", ".join(formato_escalar(v) for v in valores)
        linea = linea_de_clave(ruta_stack, clave.split(".")[-1]) if ruta_stack else -1
        if not es_escalar(valor):
            abortar([
                f"{ruta_stack}:{linea}: la clave {clave} falta o no es un escalar "
                f"(valores válidos: {permitidos})"
            ])
        if valor not in valores:
            abortar([
                f"{ruta_stack}:{linea}: el valor de {clave} no está permitido "
                f"(valores válidos: {permitidos})"
            ])
    return True


def huella_configuracion(data, opciones):
    """sha256 (hex) de las líneas `<clave>=<valor>\\n`, en orden alfabético: la misma fórmula
    de `stack.mjs` / `stack.py` (subcomando `huella`)."""
    pares = []
    for clave in sorted(opciones):
        pares.append(f"{clave}={formato_escalar(obtener(data, clave))}\n")
    return hashlib.sha256("".join(pares).encode("utf-8")).hexdigest()


#______________________________________________________________________________
# Tipos de archivo y marcas

EXT_BINARIO = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".woff", ".woff2", ".ttf"}

APELLIDOS = re.compile(r"^\{/\*\s*(si|fin|si-archivo)\b")


def estilo_ruta(nombre_archivo):
    base = os.path.basename(nombre_archivo)
    ext = os.path.splitext(base)[1].lower()
    if ext in (".json", ".dbcnb"):
        return {"prefijos": [], "cabecera": False}
    if base == "Dockerfile" or ext in (".sh", ".py", ".yaml", ".yml", ".properties"):
        prefijo = "#"
    elif base == "Jenkinsfile" or ext in (".ts", ".tsx", ".js", ".mjs", ".java", ".gradle"):
        prefijo = "//"
    elif ext == ".sql":
        prefijo = "--"
    elif ext == ".md":
        prefijo = "<!--"
    else:
        prefijo = "#"  # texto sin tipo conocido
    prefijos = [prefijo]
    if ext == ".tsx":
        prefijos.append("{/*")  # comentarios JSX
    return {"prefijos": prefijos, "cabecera": True}


RE_SI = {
    "#":  re.compile(r"^#\s*si\s+([\w.\-]+)=([\w.\-|]*)\s*$"),
    "//": re.compile(r"^//\s*si\s+([\w.\-]+)=([\w.\-|]*)\s*$"),
    "--": re.compile(r"^--\s*si\s+([\w.\-]+)=([\w.\-|]*)\s*$"),
    "<!--": re.compile(r"^<!--\s*si\s+([\w.\-]+)=([\w.\-|]*)\s*-->\s*$"),
    "{/*": re.compile(r"^\{/\*\s*si\s+([\w.\-]+)=([\w.\-|]*)\s*\*/}\s*$"),
}
RE_FIN = {
    "#":  re.compile(r"^#\s*fin\s*$"),
    "//": re.compile(r"^//\s*fin\s*$"),
    "--": re.compile(r"^--\s*fin\s*$"),
    "<!--": re.compile(r"^<!--\s*fin\s*-->\s*$"),
    "{/*": re.compile(r"^\{/\*\s*fin\s*\*/}\s*$"),
}
RE_SI_ARCHIVO = {
    "#":  re.compile(r"^#\s*si-archivo\s+([\w.\-]+)=([\w.\-|]*)\s*$"),
    "//": re.compile(r"^//\s*si-archivo\s+([\w.\-]+)=([\w.\-|]*)\s*$"),
    "--": re.compile(r"^--\s*si-archivo\s+([\w.\-]+)=([\w.\-|]*)\s*$"),
    "<!--": re.compile(r"^<!--\s*si-archivo\s+([\w.\-]+)=([\w.\-|]*)\s*-->\s*$"),
}


def comment_de_cabecera(prefijos):
    prefijo = prefijos[0] if prefijos else "#"
    if prefijo == "<!--":
        return f"<!-- {CABECERA} -->"
    return f"{prefijo} {CABECERA}" if prefijo else f"# {CABECERA}"


def corte_shebang_frontmatter(lineas):
    """Líneas que van antes del cuerpo: el shebang (si lo hay) y el frontmatter (si lo hay)."""
    inicio = 0
    if lineas and lineas[0].startswith("#!"):
        inicio = 1
    if inicio < len(lineas) and lineas[inicio].rstrip("\r") == "---":
        for i in range(inicio + 1, len(lineas)):
            if lineas[i].rstrip("\r") == "---":
                return i + 1
        return inicio  # frontmatter sin cerrar: se trata el resto como cuerpo
    return inicio


def frontmatter_fin(lineas):
    """Índice (excluido) en que termina el frontmatter; None si no hay."""
    if lineas and lineas[0].rstrip("\r") == "---":
        for i in range(1, len(lineas)):
            if lineas[i].rstrip("\r") == "---":
                return i + 1
    return None


def buscar_si_archivo(lineas, prefijos, corte_cab):
    """Busca la marca de archivo completo: en la primera línea, o justo tras el shebang o el
    frontmatter. Devuelve (índice absoluta, (clave, valores)) o None."""
    for prefijo in prefijos:
        if prefijo not in RE_SI_ARCHIVO:
            continue
        for idx in (corte_cab, corte_cab + 1):
            if idx >= len(lineas):
                continue
            linea = lineas[idx].rstrip("\r")
            if linea.strip() == "":
                continue
            m = RE_SI_ARCHIVO[prefijo].match(linea)
            if m:
                return idx, (m.group(1), m.group(2))
            break  # la primera línea no vacía tras la cabecera no es de marca: para de buscar
    return None


def condicion_cumple(clave, valores_brutos, resueltos):
    texto = formato_escalar(resueltos.get(clave))
    for valor in valores_brutos.split("|"):
        if valor == texto:
            return True
    return False


def procesar_marcas(lineas, nombre, offset_linea, prefijos, opciones, resueltos, errores,
                    valores_conocidos=None):
    """Procesa los bloques `si` a partir de `lineas` (una lista de líneas, sin saltos).
    `valores_conocidos`, si se da, es la lista de valores admitidos por combinación de
    cobertura (para no exigir que cada valor del bloque esté en la lista)."""
    salida = []
    grupo = None  # {clave, match, actual}

    def cerrar_grupo():
        nonlocal grupo
        if grupo is not None:
            if grupo["match"]:
                salida.extend(grupo["actual"])
            grupo = None

    for i, cruda in enumerate(lineas, start=1):
        linea = cruda.rstrip("\r")
        abre, fin = None, None
        for prefijo in prefijos:
            if prefijo in RE_SI:
                abre = RE_SI[prefijo].match(linea) or abre
                fin = RE_FIN[prefijo].match(linea) or fin
        if abre:
            clave, valores = abre.group(1), abre.group(2)
            permitidos = opciones.get(clave)
            if permitidos is None:
                errores.append(MarcaError(
                    nombre, offset_linea + i,
                    f"la marca usa la clave `{clave}`, que no está en config/opciones.yaml"))
                continue
            valores_lista = valores.split("|")
            if valores_conocidos is None:
                permitidas_texto = {formato_escalar(v) for v in permitidos}
                for v in valores_lista:
                    if v not in permitidas_texto:
                        errores.append(MarcaError(
                            nombre, offset_linea + i,
                            f"la marca usa el valor `{v}` fuera de la lista de `{clave}` "
                            "de config/opciones.yaml"))
                        break
            match = condicion_cumple(clave, valores, resueltos)
            if grupo is None:
                grupo = {"clave": clave, "match": match, "actual": []}
            elif grupo["clave"] == clave:
                # nueva rama alternativa de la misma clave: queda solo la que coincide
                if grupo["match"]:
                    salida.extend(grupo["actual"])
                grupo["actual"], grupo["match"] = [], match
            else:
                errores.append(MarcaError(
                    nombre, offset_linea + i,
                    f"bloque anidado: `{clave}` dentro de un bloque de `{grupo['clave']}`"))
        elif fin:
            if grupo is None:
                errores.append(MarcaError(nombre, offset_linea + i,
                                          "`fin` sin bloque `si` abierto"))
                continue
            cerrar_grupo()
        elif grupo is not None:
            grupo["actual"].append(cruda)
        else:
            salida.append(cruda)
    if grupo is not None:
        errores.append(MarcaError(nombre, offset_linea + len(lineas) + 1,
                                  f"`si {grupo['clave']}=...` sin `fin`"))
    return salida


def generar_archivo(texto, nombre, opciones, resueltos, errores):
    """Pipeline de un archivo de texto: si-archivo + bloques de `si` + cabecera.
    Devuelve el texto generado, o None si el archivo se excluye (`si-archivo`)."""
    estilo = estilo_ruta(nombre)
    prefijos = estilo["prefijos"]
    acabar_con_salto = texto.endswith("\n")
    lineas = texto.split("\n")
    if lineas and lineas[-1] == "":
        lineas = lineas[:-1]
    corte_cab = corte_shebang_frontmatter(lineas)
    # una marca no puede estar dentro del frontmatter
    fin_fmx = frontmatter_fin(lineas)
    if fin_fmx is not None:
        for i in range(0, fin_fmx):
            for prefijo in prefijos:
                if (RE_SI[prefijo].match(lineas[i].rstrip("\r"))
                        or RE_FIN[prefijo].match(lineas[i].rstrip("\r"))):
                    errores.append(MarcaError(nombre, i + 1,
                                              "hay una marca dentro del frontmatter"))
                    break
    # archivo completo (`si-archivo`)
    cuerpo = lineas[corte_cab:]
    si_arch = buscar_si_archivo(lineas, prefijos, corte_cab)
    if si_arch:
        idx, (clave, valores) = si_arch
        permitidos = opciones.get(clave)
        if permitidos is None:
            errores.append(MarcaError(
                nombre, idx + 1,
                f"la marca usa la clave `{clave}`, que no está en config/opciones.yaml"))
            return None
        permitidas_texto = {formato_escalar(v) for v in permitidos}
        for v in valores.split("|"):
            if v not in permitidas_texto:
                errores.append(MarcaError(
                    nombre, idx + 1,
                    f"la marca usa el valor `{v}` fuera de la lista de `{clave}` "
                    "de config/opciones.yaml"))
                return None
        if not condicion_cumple(clave, valores, resueltos):
            return None  # el archivo no se copia con esta configuración
        cuerpo = lineas[idx + 1:]
    limpio = procesar_marcas(cuerpo, nombre, 0, prefijos, opciones, resueltos, errores)
    final = list(lineas[:corte_cab])
    # nombre es el destino resuelto, también al recopilar una carpeta de opción.
    es_asset = re.match(r"^skills/[^/]+/assets/", nombre.replace(os.sep, "/")) is not None
    if estilo["cabecera"] and not es_asset and nombre.replace(os.sep, "/") != "rules/project.md":
        final.append(comment_de_cabecera(prefijos))
    final.extend(limpio)
    salida = "\n".join(final)
    if acabar_con_salto:
        salida += "\n"
    return salida


#______________________________________________________________________________
# Entrada/salida

def es_texto(contenido_bytes):
    if b"\x00" in contenido_bytes:
        return False
    try:
        contenido_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return True


def leer_binario(ruta):
    with open(ruta, "rb") as fh:
        return fh.read()


def sha256_bin(contenido_bytes):
    return hashlib.sha256(contenido_bytes).hexdigest()


def iterar_archivos(raiz, saltar_top=None):
    for diractual, dirnames, filenames in os.walk(raiz):
        rel_dir = "" if os.path.relpath(diractual, raiz) == "." else os.path.relpath(diractual, raiz)
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        if rel_dir == "" and saltar_top:
            dirnames[:] = [d for d in dirnames if d not in saltar_top]
            filenames = [n for n in filenames if n not in saltar_top]
        for n in sorted(filenames):
            ruta = os.path.join(diractual, n)
            rel = os.path.normpath(os.path.join(rel_dir, n)) if rel_dir else n
            yield ruta, rel


#______________________________________________________________________________
# Generación del árbol

def recopilar(ruta_agents_sources, opciones, resueltos, errores):
    """Recorre `sources/<proyecto>/.agents/` y construye {rel: contenido} aplicando marcas.
    Los archivos protegidos no se copian; `.generado.json` tampoco."""
    archivos = {}
    for ruta_abs, ruta_rel in iterar_archivos(ruta_agents_sources,
                                              saltar_top={"opciones"}):
        if ruta_rel in PROTEGIDAS or os.path.basename(ruta_rel) in {ARCHIVO_ESTADO, '.harness-local'}:
            continue
        contenido = leer_binario(ruta_abs)
        if not es_texto(contenido):
            archivos[ruta_rel] = ("binaria", contenido)
            continue
        generado = generar_archivo(contenido.decode("utf-8"), ruta_rel, opciones,
                                   resueltos, errores)
        if generado is None:
            continue
        archivos[ruta_rel] = ("texto", generado)
    raiz_opciones = os.path.join(ruta_agents_sources, "opciones")
    if os.path.isdir(raiz_opciones):
        for ruta_abs, ruta_rel in iterar_archivos(raiz_opciones):
            partes = ruta_rel.split(os.sep)
            if len(partes) < 3:
                continue
            clave, valor = partes[0], partes[1]
            destino = os.path.sep.join(partes[2:])
            if condicion_cumple(clave, valor, resueltos):
                contenido = leer_binario(ruta_abs)
                if not es_texto(contenido):
                    archivos[destino] = ("binaria", contenido)
                    continue
                generado = generar_archivo(contenido.decode("utf-8"), destino, opciones,
                                           resueltos, errores)
                if generado is not None:
                    archivos[destino] = ("texto", generado)
    return archivos


#______________________________________________________________________________
# Comprobaciones sobre el árbol generado

RE_REF_RUTA = re.compile(r"\.agents/[\w./\-]+")
RE_REF_SKILL = re.compile(r"(?<![\w./\-])skills/[\w\-]+")
RE_REF_ROL = re.compile(r"\brol `([a-z][a-z0-9\-]+)`")
RE_REF_MOVILIZABLE = re.compile(r"`([^\`\s]+\.template\.[A-Za-z0-9]+)`")
RE_REF_COPIA = re.compile(r"`([^\`\s]*(?:assets|references)/[\w.\-\[\]/]+)`")


def ref_si_existe(token, rutas, nombres_base, rel, i, errores):
    """Un nombre de archivo citado entre comillas invertidas debe existir en la combinación
    generada: como ruta (o como final de una ruta generada), como carpeta que contenga
    archivos generados, por su nombre final, o, con comodines, porque alguna ruta generada
    case con el patrón."""
    t = token[8:] if token.startswith(".agents/") else token
    if "<" in t:
        return  # marcador tipo <skill-de-integracion>: no es un nombre de archivo
    if "*" in t:
        for ruta in rutas:
            if (fnmatch.fnmatch(f"/{ruta}", f"*/{t}")
                    or fnmatch.fnmatch(f"/{ruta}", f"*/{t}/")):
                return
    else:
        pref_dir = f"/{t}/"
        for ruta in rutas:
            cand = f"/{ruta}/"
            if f"/{t}" in cand[:-1] or pref_dir in cand:
                return
    if t.rsplit("/", 1)[-1] in nombres_base:
        return
    errores.append(MarcaError(
        rel, i,
        f"referencia rota: `{token}` no existe en el .agents generado"))


def comprobar_referencias(archivos, errores):
    """Toda `.agents/...` o `skills/<nombre>` citada en un .md generado debe existir en el
    árbol generado (o estar en PROTEGIDAS: archivos que el generador no escribe); todo `rol <nombre>` de un workflow debe tener
    `.agents/skills/<nombre>/SKILL.md`; y todo nombre de archivo entre comillas invertidas que
    termine en `.template.<ext>` o que tenga la forma de un archivo de `assets/`/`references/`
    debe existir en la combinación generada (como ruta, como carpeta o por nombre final)."""
    rutas = set(k.replace(os.sep, "/") for k in archivos) | {"AGENTS.md"} | PROTEGIDAS
    nombres_base = set(x.rsplit("/", 1)[-1] if "/" in x else x for x in rutas)
    # carpetas que existen en runtime y no se generan (las crean los scripts del .agents):
    CARPETAS_RUNTIME = (".cache/", ".agent-runs/")
    for rel, (tipo, contenido) in sorted(archivos.items()):
        if tipo != "texto" or os.path.splitext(rel)[1].lower() != ".md":
            continue
        en_workflow = rel.startswith("workflows/")
        for i, linea in enumerate(contenido.split("\n"), start=1):
            for m in RE_REF_RUTA.finditer(linea):
                ruta = m.group(0).rstrip(".,;:`")
                interna = ruta[len(".agents/"):]
                if not interna or interna == ARCHIVO_ESTADO:
                    continue
                if interna in rutas:
                    continue
                if interna.startswith(CARPETAS_RUNTIME):
                    continue
                if interna.endswith("/"):
                    # referencia a una carpeta: basta con que genere algo debajo
                    if any(x.startswith(interna) for x in rutas):
                        continue
                    errores.append(MarcaError(
                        rel, i,
                        f"referencia rota: `{ruta}` no existe en el .agents generado"))
                    continue
                errores.append(MarcaError(
                    rel, i,
                    f"referencia rota: `{ruta}` no existe en el .agents generado"))
            for m in RE_REF_SKILL.finditer(linea):
                texto = m.group(0).rstrip(".,;:`")
                ruta_skills = texto[len("skills/"):]
                if ruta_skills not in rutas and ruta_skills != "":
                    if f"skills/{ruta_skills}/SKILL.md" not in rutas:
                        errores.append(MarcaError(
                            rel, i,
                            f"referencia rota: `.agents/{texto}` no existe en el .agents generado"))
            for m in RE_REF_ROL.finditer(linea):
                if not en_workflow:
                    continue
                nombre = m.group(1)
                if f"skills/{nombre}/SKILL.md" not in rutas:
                    errores.append(MarcaError(
                        rel, i,
                        f"referencia rota: el rol `{nombre}` no tiene "
                        f"`.agents/skills/{nombre}/SKILL.md` en el .agents generado"))
            vistos = set()
            for patron in (RE_REF_MOVILIZABLE, RE_REF_COPIA):
                for m in patron.finditer(linea):
                    token = m.group(1).rstrip(".,;:")
                    if token not in vistos:
                        vistos.add(token)
                        ref_si_existe(token, rutas, nombres_base, rel, i, errores)


def comprobar_residuales(archivos, errores):
    """En la salida no queda ninguna marca."""
    for rel, (tipo, contenido) in sorted(archivos.items()):
        if tipo != "texto":
            continue
        prefijos = estilo_ruta(rel)["prefijos"]
        for i, linea in enumerate(contenido.split("\n"), start=1):
            limpio = linea.rstrip("\r")
            for prefijo in prefijos:
                if (RE_SI[prefijo].match(limpio) or RE_FIN[prefijo].match(limpio)
                        or (prefijo in RE_SI_ARCHIVO and RE_SI_ARCHIVO[prefijo].match(limpio))):
                    errores.append(MarcaError(rel, i, "quedó una marca en la salida"))


#______________________________________________________________________________
# Cobertura

def combinaciones(opciones):
    claves = sorted(opciones)
    if not claves:
        yield {}
        return
    for tupla in itertools.product(*(opciones[c] for c in claves)):
        yield dict(zip(claves, tupla))


def lineas_objetivo(texto, prefijos):
    """Líneas de un archivo de sources que no son marcas (las que la cobertura debe cubrir)."""
    lineas = texto.split("\n")
    if lineas and lineas[-1] == "":
        lineas = lineas[:-1]
    objetivos = []
    for i, cruda in enumerate(lineas, start=1):
        linea = cruda.rstrip("\r")
        for prefijo in prefijos:
            if (RE_SI[prefijo].match(linea) or RE_FIN[prefijo].match(linea)
                    or (prefijo in RE_SI_ARCHIVO and RE_SI_ARCHIVO[prefijo].match(linea))):
                break
        else:
            objetivos.append((i, linea))
    return objetivos


def comprobar_cobertura(ruta_agents_sources, opciones, ruta_agmds=None):
    """Cada línea de sources que no es una marca aparece en al menos una combinación.
    Excepción declarada: los archivos protegidos (`stack.yaml`, `rules/project.md`,
    `documentacion.json`, `documentacion.md`, `catalogo-proyecto.json`) no se
    generan, así que ninguna de sus líneas participa en la cobertura."""
    huérfanas = []
    proceder = []
    for ruta_abs, rel in iterar_archivos(ruta_agents_sources, saltar_top={"opciones"}):
        if rel in PROTEGIDAS or os.path.basename(rel) == ARCHIVO_ESTADO:
            continue
        proceder.append((ruta_abs, rel, None, None))
    raiz_opciones = os.path.join(ruta_agents_sources, "opciones")
    if os.path.isdir(raiz_opciones):
        for ruta_abs, rel in iterar_archivos(raiz_opciones):
            partes = rel.split(os.sep)
            if len(partes) < 3:
                continue
            proceder.append((ruta_abs, os.path.sep.join(partes[2:]), partes[0], partes[1]))
    if ruta_agmds and os.path.isfile(ruta_agmds):
        proceder.append((ruta_agmds, "AGENTS.md", None, None))
    for ruta_abs, destino, clave_opc, valor_opc in proceder:
        contenido = leer_binario(ruta_abs)
        if not es_texto(contenido):
            continue
        texto = contenido.decode("utf-8")
        prefijos = estilo_ruta(destino)["prefijos"]
        objetivos = lineas_objetivo(texto, prefijos)
        cabecera = comment_de_cabecera(prefijos)
        apariciones = set()
        for resueltos in combinaciones(opciones):
            if clave_opc is not None and not condicion_cumple(clave_opc, valor_opc, resueltos):
                continue
            generado = generar_archivo(texto, destino, opciones, resueltos, [])
            if generado is None:
                continue
            for linea in generado.split("\n"):
                limpio = linea.rstrip("\r")
                if limpio != cabecera:
                    apariciones.add(limpio)
        for i, linea in objetivos:
            if linea not in apariciones:
                huérfanas.append((destino, i, linea))
    return huérfanas


#______________________________________________________________________________
# git de sources

def estado_git(ruta, proyecto):
    """Origen por carpeta; nunca consulta status del repositorio de plantillas."""
    try:
        r = subprocess.run(['git', '-C', ruta, 'log', '-1', '--format=%H', '--',
                            'sources/' + proyecto], capture_output=True, text=True)
        return r.stdout.strip() if r.returncode == 0 else ''
    except OSError:
        return ''


#______________________________________________________________________________
# Interacción

def mostrar_diff(archivo, antes, despues):
    a = antes.split("\n") if isinstance(antes, str) else antes
    b = despues.split("\n") if isinstance(despues, str) else despues
    for l in difflib.unified_diff(a, b, fromfile=f"a/{archivo}", tofile=f"b/{archivo}",
                                  lineterm="", n=1):
        print(l)


def pedir_si(pregunta):
    try:
        return input(f"{pregunta} [s/N]: ").strip().lower() in ("s", "si", "sí", "y", "yes")
    except EOFError:
        return False


def pedir_ruta_sources():
    while True:
        try:
            ruta = input(PREGUNTA_RUTA).strip()
        except EOFError:
            bloqueado("entrada interrumpida: ejecuta de nuevo y responde la ruta, "
                      "o usa la opción `--kit <ruta>`.")
        if ruta:
            ruta = os.path.abspath(os.path.expanduser(ruta))
            if os.path.isdir(os.path.join(ruta, "sources")):
                return ruta
            print(f"En `{ruta}` no hay una carpeta `sources/`. Revisa la ruta.")


def buscar_sources(ruta_raiz, stack):
    """Carpeta de `sources/` cuyo `.agents/stack.yaml` declara `proyecto.stack: <stack>`."""
    base = os.path.join(ruta_raiz, "sources")
    if not os.path.isdir(base):
        return None
    for nombre in sorted(os.listdir(base)):
        ruta_stack = os.path.join(base, nombre, ".agents", "stack.yaml")
        if not os.path.isfile(ruta_stack):
            continue
        try:
            stack_vecino = obtener(cargar_stack(ruta_stack), "proyecto.stack")
        except Exception:
            continue
        if stack_vecino == stack:
            return nombre
    return None


def resolver_stack(ruta_proyecto):
    """(stack, ruta stack.yaml | None) del proyecto."""
    ruta_stack = os.path.join(ruta_proyecto, ".agents", "stack.yaml")
    if os.path.isfile(ruta_stack):
        data = cargar_stack(ruta_stack)
        stack = obtener(data, "proyecto.stack")
        if isinstance(stack, str) and stack in STACKS:
            return stack, ruta_stack
        abortar([f"{ruta_stack}:-1: `proyecto.stack` es {stack!r}; este generador solo "
                 f"soporta: {', '.join(sorted(STACKS))}"])
    return None, None


#______________________________________________________________________________
# Ejecución

def claves_hoja(data, prefijo=""):
    claves = set()
    for key, value in data.items():
        ruta = prefijo + key
        if isinstance(value, dict) and value:
            claves.update(claves_hoja(value, ruta + "."))
        else:
            claves.add(ruta)
    return claves


FREE_NAME_MAPS = {"conexiones", "devops.entornos"}


# Metadatos de uso: no son parámetros del proyecto ni opciones de generación.
def normalizar_condicion(path):
    partes, actual, salida = path.split('.'), '', []
    for parte in partes:
        salida.append('{nombre}' if actual in FREE_NAME_MAPS else parte)
        actual = (actual + '.' if actual else '') + parte
    return '.'.join(salida)


def esquema_condiciones(data, prefix=''):
    result = {}
    for key, value in data.items():
        path = prefix + '.' + key if prefix else key
        result[normalizar_condicion(path)] = value
        if isinstance(value, dict):
            result.update(esquema_condiciones(value, path))
    return result


def terminos_condicion(expr, meta, opciones):
    if not isinstance(expr, str) or not expr.strip():
        raise ValueError('condición vacía')
    result = []
    for term in expr.split('&&'):
        m = re.fullmatch(r'\s*([\w.{}-]+)\s*(!=|=)\s*(null|true|false|[\w-]+)\s*', term)
        if not m:
            raise ValueError('condición inválida: ' + expr)
        key, op, raw = m.groups()
        if key not in meta['claves']:
            raise ValueError('condición con clave desconocida: ' + key)
        if '{nombre}' in key and not any(key.startswith(p + '.{nombre}.') for p in FREE_NAME_MAPS):
            raise ValueError('comodín fuera de un mapa libre: ' + key)
        value = escalar(raw)
        if key in opciones and not any(type(value) is type(v) and value == v for v in opciones[key]):
            raise ValueError('valor fuera de config/opciones.yaml: ' + term.strip())
        result.append((key, op, value))
    return result


def validar_metadata(meta, opciones):
    if not isinstance(meta, dict) or set(meta) != {'version', 'claves', 'reglas'} or type(meta['version']) is not int or meta['version'] != 1:
        raise ValueError('config/condiciones.yaml inválido: se esperan version: 1, claves y reglas')
    if not isinstance(meta['claves'], list) or not meta['claves'] or any(not isinstance(k, str) or not re.fullmatch(r'[\w.{}-]+', k) for k in meta['claves']) or len(set(meta['claves'])) != len(meta['claves']):
        raise ValueError('config/condiciones.yaml: claves inválidas o repetidas')
    if not isinstance(meta['reglas'], list):
        raise ValueError('config/condiciones.yaml: reglas debe ser una lista')
    seen = set()
    for regla in meta['reglas']:
        if not isinstance(regla, str) or regla.count(' :: ') != 1:
            raise ValueError('config/condiciones.yaml: regla inválida')
        key, expr = regla.split(' :: ')
        if key not in meta['claves'] or key in seen:
            raise ValueError('config/condiciones.yaml: clave de regla desconocida o repetida: ' + key)
        seen.add(key)
        for ref, _, _ in terminos_condicion(expr, meta, opciones):
            if '{nombre}' in ref and '{nombre}' not in key:
                raise ValueError('config/condiciones.yaml: comodín sin entrada de contexto')
    return meta


def extraer_condiciones(fuentes):
    ruta = os.path.join(fuentes, 'stack.yaml')
    modelo = cargar_stack(ruta)
    meta = {'version': 1, 'claves': sorted(esquema_condiciones(modelo)), 'reglas': []}
    padres, reglas = [], {}
    with open(ruta, encoding='utf-8') as fh:
        for numero, linea in enumerate(fh, 1):
            limpio = texto_sin_comentario(linea)
            m = re.match(r'^( *)([\w.-]+):', limpio)
            if not m:
                continue
            nivel = len(m[1])
            while padres and padres[-1][0] >= nivel:
                padres.pop()
            path = normalizar_condicion('.'.join([k for _, k in padres] + [m[2]]))
            padres.append((nivel, m[2]))
            cond = re.search(r'requerida_con:\s*(.*)', linea[len(limpio):])
            if cond:
                expr = cond[1].strip()
                try:
                    for ref, _, literal in terminos_condicion(expr, meta, cargar_opciones(fuentes)):
                        muestra = esquema_condiciones(modelo)[ref]
                        if literal is not None and muestra is not None and type(literal) is not type(muestra):
                            raise ValueError('literal incompatible con el tipo de ' + ref)
                    if path in reglas and reglas[path] != expr:
                        raise ValueError('condiciones distintas para la misma clave normalizada')
                    reglas[path] = expr
                except ValueError as e:
                    raise MarcaError(ruta, numero, str(e))
    # Las marcas de fichas ya existentes expresan condiciones simples de uso.
    # Conserva esas condiciones en el contrato, sin cambiar la política de opciones.
    ruta_fichas = os.path.join(fuentes, 'config', 'claves.md')
    rama = None
    with open(ruta_fichas, encoding='utf-8') as fh:
        for linea in fh:
            abre = re.fullmatch(r'<!-- si ([\w.]+)=([\w-]+) -->\s*', linea)
            if abre:
                rama = abre[1] + '=' + abre[2]
            elif re.fullmatch(r'<!-- fin -->\s*', linea):
                rama = None
            heading = re.fullmatch(r'## ([\w.{}-]+)\s*', linea)
            if heading and rama and heading[1] in meta['claves'] and heading[1] not in reglas:
                reglas[heading[1]] = rama
    meta['reglas'] = [k + ' :: ' + v for k, v in sorted(reglas.items())]
    return validar_metadata(meta, cargar_opciones(fuentes))


def cargar_condiciones(agents):
    ruta = os.path.join(agents, 'config', 'condiciones.yaml')
    if not os.path.isfile(ruta):
        raise ValueError('falta config/condiciones.yaml generado; regenera el .agents con actualizar.py')
    try:
        with open(ruta, encoding='utf-8') as fh:
            meta = parsear_yaml(fh.read(), ruta)
        return validar_metadata(meta, cargar_opciones(agents))
    except Exception as e:
        raise ValueError('config/condiciones.yaml inválido; regenera el .agents: ' + str(e))


def reglas_de_clave(meta, path):
    normal = normalizar_condicion(path)
    return [regla.split(' :: ', 1)[1] for regla in meta['reglas']
            if normal == regla.split(' :: ', 1)[0] or normal.startswith(regla.split(' :: ', 1)[0] + '.')]


def condicion_activa(meta, path, datos):
    # Resolver {nombre} con la entrada de esta ruta, nunca con un entorno vecino.
    partes = path.split('.')
    normal = normalizar_condicion(path).split('.')
    nombre = next((partes[i] for i, p in enumerate(normal) if p == '{nombre}'), None)
    for expr in reglas_de_clave(meta, path):
        for key, op, valor in terminos_condicion(expr, meta, {}):
            if '{nombre}' in key:
                if nombre is None:
                    return False
                key = key.replace('{nombre}', nombre)
            actual = datos
            for parte in key.split('.'):
                if not isinstance(actual, dict) or parte not in actual:
                    return False
                actual = actual[parte]
            igual = type(actual) is type(valor) and actual == valor
            if (op == '=' and not igual) or (op == '!=' and igual):
                return False
    return True


def explicar_condicion(meta, path):
    frases = []
    for expr in reglas_de_clave(meta, path):
        for key, op, valor in terminos_condicion(expr, meta, {}):
            literal = "null" if valor is None else formato_escalar(valor)
            frase = key.split('.')[-1] + (': ' if op == '=' else ' distinto de ') + literal
            if frase not in frases:
                frases.append(frase)
    return ' (solo con ' + ' y '.join(frases) + ')' if frases else ''


def rutas_concretas(datos, normal):
    paths = ['']
    for part in normal.split('.'):
        siguientes = []
        for path in paths:
            if part == '{nombre}':
                value = obtener(datos, path)
                if isinstance(value, dict):
                    siguientes.extend(path + '.' + key for key in value)
            else:
                siguientes.append((path + '.' if path else '') + part)
        paths = siguientes
    return paths


def validar_claves_condicionales(datos, meta):
    for regla in meta['reglas']:
        normal = regla.split(' :: ', 1)[0]
        for path in rutas_concretas(datos, normal):
            if condicion_activa(meta, path, datos) and path not in esquema_rutas(datos):
                raise ValueError('falta en tu stack.yaml: ' + path + explicar_condicion(meta, path))


def esquema_rutas(datos, prefix=''):
    result = set()
    for key, value in datos.items():
        path = (prefix + '.' if prefix else '') + key
        result.add(path)
        if isinstance(value, dict):
            result.update(esquema_rutas(value, path))
    return result


def filtrar_fichas(texto, datos, meta):
    trozos = re.split(r'(?=^## [\w.{}-]+\s*$)', texto, flags=re.M)
    salida = []
    for trozo in trozos:
        m = re.match(r'## ([\w.{}-]+)', trozo)
        if m and reglas_de_clave(meta, m[1]):
            paths = rutas_concretas(datos, m[1])
            if not any(condicion_activa(meta, path, datos) for path in paths):
                continue
        salida.append(trozo)
    return re.sub(r'\n{3,}', '\n\n', ''.join(salida))


def avisar_claves_stack(datos, fuentes):
    """Compara esquemas; los nombres de mapas libres nunca son claves obligatorias."""
    ruta = os.path.join(fuentes, 'stack.yaml')
    plantilla = cargar_stack(ruta)
    meta = extraer_condiciones(fuentes)
    comentarios, padres = {}, []

    def normalizar(path):
        partes, actual, salida = path.split('.'), '', []
        for parte in partes:
            salida.append('{nombre}' if actual in FREE_NAME_MAPS else parte)
            actual = (actual + '.' if actual else '') + parte
        return '.'.join(salida)

    with open(ruta, encoding='utf-8') as fh:
        for numero, linea in enumerate(fh, 1):
            limpio = texto_sin_comentario(linea)
            m = re.match(r'^( *)([\w.-]+):', limpio)
            if not m:
                continue
            nivel = len(m.group(1))
            while padres and padres[-1][0] >= nivel:
                padres.pop()
            path = '.'.join([k for _, k in padres] + [m.group(2)])
            padres.append((nivel, m.group(2)))
            key = normalizar(path)
            comentario = linea[len(limpio) + 1:].strip() if len(limpio) < len(linea) else 'sin comentario en la plantilla'
            comentarios[key] = re.sub(r'\s*#?\s*requerida_con:.*$', '', comentario).strip() or 'clave requerida por su condición de uso'

    def activa(path, real):
        return condicion_activa(meta, real, datos)

    falta = object()
    def ausente(real, normal):
        if activa(normal, real):
            print(f'falta en tu stack.yaml: {real}{explicar_condicion(meta, real)} — {comentarios.get(normal, "sin comentario en la plantilla")}')

    def sobran(value, real):
        if isinstance(value, dict) and value:
            for k, v in value.items():
                sobran(v, real + '.' + k)
        else:
            print('ya no se usa: ' + real)

    def comparar(real, modelo, path='', normal=''):
        if not activa(normal, path):
            if real is not falta:
                print('ya no se usa: ' + path + explicar_condicion(meta, path))
            return
        if normal in FREE_NAME_MAPS:
            if real is falta or not isinstance(real, dict) or not real:
                if modelo and (real is falta or not isinstance(real, dict) or any(regla.split(' :: ', 1)[0] == normal for regla in meta['reglas'])):
                    ausente(path, normal)
                return
            esquemas = list(modelo.values())
            if any(isinstance(v, dict) for v in esquemas):
                esquema = {}
                for v in esquemas:
                    if isinstance(v, dict):
                        esquema.update(v)
                for nombre, valor in real.items():
                    comparar(valor, esquema, path + '.' + nombre, normal + '.{nombre}')
            return
        if isinstance(modelo, dict) and modelo:
            if real is falta:
                for k, v in modelo.items():
                    comparar(falta, v, path + '.' + k if path else k, normal + '.' + k if normal else k)
                return
            if not isinstance(real, dict):
                ausente(path, normal)
                return
            for k, v in modelo.items():
                comparar(real.get(k, falta), v, path + '.' + k if path else k, normal + '.' + k if normal else k)
            for k in sorted(set(real) - set(modelo)):
                sobran(real[k], path + '.' + k if path else k)
        elif real is falta:
            ausente(path, normal)

    comparar(datos, plantilla)


def resolver_nomenclatura(texto, datos, rel):
    def sustituir(m):
        valor = obtener(datos, m.group(1))
        if valor is None:
            return m.group(0)  # stack antiguo: se avisa, nunca se rellena.
        if isinstance(valor, list):
            return " | ".join(str(v) for v in valor)
        salida = str(valor).lower() if isinstance(valor, bool) else str(valor)
        if rel.startswith("skills/") and "/assets/" in rel:
            salida = salida.replace("{Entidad}", "[Entity]").replace("{nombre}", "[nombre]")
        return salida
    return re.sub(r"<(nomenclatura\.[a-z_]+)>", sustituir, texto)


def cargar_migraciones(fuentes):
    ruta = os.path.join(fuentes, 'config', 'migraciones.yaml')
    if not os.path.isfile(ruta):
        return {}
    with open(ruta, encoding='utf-8') as fh:
        reglas = parsear_yaml(fh.read(), ruta)
    if not isinstance(reglas, dict):
        raise ValueError('config/migraciones.yaml debe ser un mapa de rutas y pares [valor retirado, mensaje]')
    for clave, par in reglas.items():
        if not re.fullmatch(r'[a-z_][\w-]*(?:\.[a-z_][\w-]*)*', clave) or not isinstance(par, list) or len(par) != 2 or isinstance(par[0], (dict, list)) or not isinstance(par[1], str) or not par[1].strip():
            raise ValueError('config/migraciones.yaml: regla inválida; usa ruta: [valor retirado, mensaje]')
    return reglas


def validar_migraciones(datos, fuentes):
    try:
        reglas = cargar_migraciones(fuentes)
    except (OSError, ValueError, MarcaError) as error:
        bloqueado(str(error))
    for clave, (retirado, mensaje) in reglas.items():
        if clave in esquema_rutas(datos):
            actual = obtener(datos, clave)
            if type(actual) is type(retirado) and actual == retirado:
                bloqueado(mensaje)


def ejecutar(args):
    ruta_proyecto = os.path.abspath(args.proyecto)
    ruta_agents_proyecto = os.path.join(ruta_proyecto, ".agents")
    if not os.path.isdir(ruta_agents_proyecto):
        bloqueado(f"{ruta_proyecto} no tiene `.agents/`")

    stack, ruta_stack = resolver_stack(ruta_proyecto)
    primera_instalacion = False
    if stack is None:
        mjs = os.path.join(ruta_agents_proyecto, "scripts", "stack.mjs")
        py = os.path.join(ruta_agents_proyecto, "scripts", "stack.py")
        for ruta, patron in ((mjs, r"^const STACK = '(\w+)'"),
                             (py, r'^STACK = "(\w+)"')):
            if os.path.isfile(ruta):
                with open(ruta, encoding="utf-8") as fh:
                    m = re.search(patron, fh.read(), re.M)
                if m and m.group(1) in STACKS:
                    stack = m.group(1)
                    break
        if stack is None:
            if not sys.stdin.isatty():
                abortar(["falta `.agents/stack.yaml` en el proyecto y no se puede preguntar "
                         "el stack si la salida no es un terminal; crea `.agents/stack.yaml` "
                         f"a partir del de sources ({', '.join(sorted(STACKS))})"])
            print("Este proyecto aún no declara `proyecto.stack` (falta `.agents/stack.yaml`).")
            print("¿Qué carpeta de `sources/` copias?")
            try:
                eleccion = input(PREGUNTA_STACK).strip()
            except EOFError:
                abortar(["entrada interrumpida: vuelve a ejecutar o crea `.agents/stack.yaml` a mano"])
            if eleccion not in STACKS:
                abortar([f"`{eleccion}` no es un stack válido "
                         f"({', '.join(sorted(STACKS))})"])
            stack = eleccion
        primera_instalacion = True

    ruta_raiz = args.kit
    nombre_sources = None
    while True:
        if ruta_raiz is None:
            ruta_raiz = pedir_ruta_sources()
        ruta_raiz = os.path.realpath(os.path.expanduser(ruta_raiz))
        nombre_sources = buscar_sources(ruta_raiz, stack)
        if nombre_sources is not None:
            break
        if args.kit is not None:
            abortar([f"`--kit {args.kit}` no contiene `sources/<proyecto>/.agents` "
                     f"con `proyecto.stack: {stack}`"])
        print(f"En `{ruta_raiz}/sources/` no hay ningún proyecto con `proyecto.stack: {stack}`.")
        ruta_raiz = None
    ruta_fuentes_agents = os.path.join(ruta_raiz, "sources", nombre_sources, ".agents")
    ruta_fuentes_proyecto = os.path.join(ruta_raiz, "sources", nombre_sources)

    # El stack pertenece al usuario incluso durante la primera instalación.
    if primera_instalacion:
        bloqueado("falta .agents/stack.yaml: crea tu archivo desde la plantilla de sources y vuelve a ejecutar")

    datos_stack = cargar_stack(ruta_stack)
    validar_migraciones(datos_stack, ruta_fuentes_agents)
    opciones = cargar_opciones(ruta_fuentes_agents)
    avisar_claves_stack(datos_stack, ruta_fuentes_agents)
    validar_opciones(datos_stack, opciones, ruta_stack)
    validar_requisitos(datos_stack, opciones, ruta_fuentes_agents)
    meta = extraer_condiciones(ruta_fuentes_agents)
    try:
        validar_claves_condicionales(datos_stack, meta)
    except ValueError as e:
        bloqueado(str(e))
    lector = os.path.join(ruta_fuentes_agents, 'scripts', 'stack.mjs')
    comando_lector = ['node', lector] if os.path.isfile(lector) else [sys.executable, '-B', '-E', os.path.join(ruta_fuentes_agents, 'scripts', 'stack.py')]
    if os.path.isfile(comando_lector[-1]):
        proceso = subprocess.run(comando_lector + ['--validar-generacion'],
            input=json.dumps({'data': datos_stack, 'meta': meta, 'opciones': opciones}),
            capture_output=True, text=True)
        if proceso.returncode:
            abortar([proceso.stderr.strip() or 'no se pudo validar la configuración antes de generar'])
    resueltos = {k: obtener(datos_stack, k) for k in opciones}

    # generación en memoria (nada se escribe hasta que todo pase)
    errores = []
    archivos = recopilar(ruta_fuentes_agents, opciones, resueltos, errores)
    metadata_texto = '# generado automáticamente; metadatos de uso, no parámetros del proyecto\n'
    metadata_texto += 'version: 1\nclaves: ' + json.dumps(meta['claves'], ensure_ascii=False) + '\nreglas: ' + json.dumps(meta['reglas'], ensure_ascii=False) + '\n'
    archivos['config/condiciones.yaml'] = ('texto', metadata_texto)
    if 'config/claves.md' in archivos:
        archivos['config/claves.md'] = ('texto', filtrar_fichas(archivos['config/claves.md'][1], datos_stack, meta))
    project_nuevo = not os.path.lexists(os.path.join(ruta_agents_proyecto, "rules", "project.md"))
    if project_nuevo:
        ruta_project = os.path.join(ruta_fuentes_agents, "rules", "project.md")
        if os.path.isfile(ruta_project):
            texto_project = generar_archivo(leer_binario(ruta_project).decode("utf-8"),
                "rules/project.md", opciones, resueltos, errores)
            if texto_project is not None:
                archivos["rules/project.md"] = ("texto", texto_project)
    for rel, (tipo, contenido) in list(archivos.items()):
        if tipo == "texto":
            archivos[rel] = (tipo, resolver_nomenclatura(contenido, datos_stack, rel))
    ruta_agmds = os.path.join(ruta_fuentes_proyecto, "AGENTS.md")
    if os.path.isfile(ruta_agmds):
        generado = generar_archivo(
            leer_binario(ruta_agmds).decode("utf-8"), "AGENTS.md", opciones,
            resueltos, errores)
        if generado is not None:
            archivos["AGENTS.md"] = ("texto", generado)
    if errores:
        abortar(errores)
    residuales = []
    comprobar_residuales(archivos, residuales)
    if residuales:
        abortar([str(e) for e in residuales])

    if args.comprobar_referencias:
        refs = []
        comprobar_referencias(archivos, refs)
        if refs:
            abortar([str(e) for e in refs])
        print("referencias: OK")
    if args.comprobar_cobertura:
        huérfanas = comprobar_cobertura(ruta_fuentes_agents, opciones, ruta_agmds)
        if huérfanas:
            abortar([f"{rel}:{n}: línea huérfana (ninguna combinación la incluye): {texto}"
                     for rel, n, texto in huérfanas])
        print("cobertura: OK")

    # alineación con el proyecto: comparar, pedir confirmaciones, preparar acciones
    ruta_estado = os.path.join(ruta_agents_proyecto, ARCHIVO_ESTADO)
    registros_previos = {}
    estado_anterior = {}
    if os.path.isfile(ruta_estado):
        try:
            with open(ruta_estado, encoding="utf-8") as fh:
                estado_anterior = json.load(fh)
                registros_previos = estado_anterior.get("archivos", {})
        except (OSError, ValueError) as e:
            bloqueado(f"`.agents/{ARCHIVO_ESTADO}` no es un JSON legible: {e}")

    def ruta_destino(rel):
        return os.path.join(ruta_proyecto, "AGENTS.md") if rel == "AGENTS.md" \
            else os.path.join(ruta_agents_proyecto, rel)

    acciones, creados, modificados, borrados, omitidos = [], [], [], [], []
    for rel in sorted(archivos):
        destino = ruta_destino(rel)
        tipo, contenido = archivos[rel]
        nuevo_bytes = contenido.encode("utf-8") if tipo == "texto" else contenido
        if os.path.isfile(destino):
            viejo_bytes = leer_binario(destino)
            if viejo_bytes == nuevo_bytes:
                continue
            diff = ""
            if es_texto(viejo_bytes) and tipo == "texto":
                diff = "\n".join(difflib.unified_diff(
                    viejo_bytes.decode("utf-8", errors="replace").split("\n"),
                    contenido.split("\n"), fromfile=f"a/{rel}", tofile=f"b/{rel}",
                    lineterm="", n=1))
            if rel in registros_previos and sha256_bin(viejo_bytes) != registros_previos[rel]:
                print(f"\n⚠️  `{rel}` lo editaste a mano (su sha256 no coincide con "
                      "`.generado.json`):")
                if diff:
                    print(diff)
                if not args.si and not pedir_si(f"¿Sobrescribir `{rel}`?"):
                    print(f"omitido: {rel}")
                    omitidos.append(rel)
                    continue
            elif rel not in registros_previos:
                print(f"\n⚠️  `{rel}` existe y no lo generó este generador "
                      "(no está en `.generado.json`):")
                if diff:
                    print(diff)
                if not args.si and not pedir_si(f"¿Sobrescribir `{rel}`?"):
                    print(f"omitido: {rel}")
                    omitidos.append(rel)
                    continue
            modificados.append(rel)
            acciones.append((rel, destino, nuevo_bytes, "modificar"))
        else:
            creados.append(rel)
            acciones.append((rel, destino, nuevo_bytes, "crear"))
    for rel in sorted(registros_previos):
        if rel in PROTEGIDAS:
            continue
        if rel in archivos:
            continue
        destino = ruta_destino(rel)
        if os.path.isfile(destino):
            viejo_bytes = leer_binario(destino)
            if es_texto(viejo_bytes):
                print(f"\n--- el archivo `/{rel}` ya no se genera con esta configuración; "
                      "diff de lo que se borrará:")
                mostrar_diff(rel, viejo_bytes.decode("utf-8", errors="replace"), "")
            borrados.append(rel)
            acciones.append((rel, destino, None, "borrar"))

    if args.simular:
        print("\n=== SIMULACIÓN: no se escribe nada ===")
        if project_nuevo and "rules/project.md" in archivos:
            print("crearía `rules/project.md` desde la plantilla: rellena las secciones `(por completar)`")
        for rel, destino, nuevo, clase in acciones:
            print(f"\n{clase}: `{rel}`")
            if clase == "borrar":
                with open(destino, "rb") as fh:
                    viejo = fh.read()
                if es_texto(viejo):
                    mostrar_diff(rel, viejo.decode("utf-8", errors="replace"), "")
            elif clase == "crear":
                mostrar_diff(rel, "", nuevo.decode("utf-8"))
        imprimir_resumen(archivos, resueltos, ruta_raiz, stack, nombre_sources)
        return 0

    if acciones and not args.si:
        print(f"\nSe van a aplicar {len(acciones)} cambio(s): "
              f"{len(creados)} a crear, {len(modificados)} a modificar, {len(borrados)} a borrar.")
        if not pedir_si("¿Continuar?"):
            print("cancelado; no se escribió nada")
            return 0

    for rel, destino, nuevo, clase in acciones:
        if clase == "borrar":
            os.remove(destino)
        else:
            os.makedirs(os.path.dirname(destino), exist_ok=True)
            with open(destino, "xb" if rel == "rules/project.md" else "wb") as fh:
                fh.write(nuevo)
        print(f"{clase}: `{rel}`" if False else f"{clase}: {rel}")
        if rel == "rules/project.md":
            print("creado `rules/project.md` desde la plantilla: rellena las secciones `(por completar)`")

    # `.generado.json`
    registros = {}
    omitido_set = set(omitidos)
    for rel in sorted(archivos):
        if rel in PROTEGIDAS:
            continue
        if rel in omitido_set and rel in registros_previos:
            registros[rel] = registros_previos[rel]
            continue
        tipo, contenido = archivos[rel]
        bytes_ = contenido if tipo == "binaria" else contenido.encode("utf-8")
        registros[rel] = sha256_bin(bytes_)
    estado = {
        "formato": 1,
        "sources_commit": estado_git(ruta_raiz, nombre_sources),
        "regenerar": mapa_regenerar(datos_stack, opciones),
        "huella_config": huella_configuracion(datos_stack, opciones),
        "archivos": registros,
        "protegidos": {"rules/project.md": "creado desde plantilla" if project_nuevo else estado_anterior.get("protegidos", {}).get("rules/project.md", "existente, sin tocar")},
    }
    with open(ruta_estado, "w", encoding="utf-8", newline="") as fh:
        fh.write(json.dumps(estado, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    print(f"escrito: `.agents/{ARCHIVO_ESTADO}`")

    local = {"ruta": ruta_raiz, "proyecto": nombre_sources,
             "commit": estado["sources_commit"]}
    # Metadatos locales fuera del árbol versionable, también en worktrees.
    try:
        git_dir = subprocess.run(['git', '-C', ruta_proyecto, 'rev-parse', '--git-common-dir'],
                                 capture_output=True, text=True, errors='replace')
        if git_dir.returncode == 0 and git_dir.stdout.strip():
            directorio = os.path.realpath(os.path.join(ruta_proyecto, git_dir.stdout.strip()))
            with open(os.path.join(directorio, 'agents-kit-local.json'), 'w', encoding='utf-8') as fh:
                fh.write(json.dumps(local, ensure_ascii=False, sort_keys=True) + '\n')
            # Nombre anterior del archivo de metadatos locales.
            anterior = os.path.join(directorio, 'agents-harness-local.json')
            if os.path.isfile(anterior):
                os.remove(anterior)
            legado = os.path.join(ruta_agents_proyecto, '.harness-local')
            if os.path.isfile(legado):
                try:
                    with open(legado, encoding='utf-8') as fh:
                        previo_local = json.load(fh)
                    if isinstance(previo_local, dict) and set(previo_local) == {'ruta', 'proyecto', 'commit'}:
                        os.remove(legado)
                except (OSError, ValueError, UnicodeError):
                    print('AVISO: metadata local antigua no reconocida; el usuario puede revisarla.')
    except OSError:
        print('AVISO: no se pudo guardar agents-kit-local.json; la metadata local es opcional y la generación continúa.')
    imprimir_resumen(archivos, resueltos, ruta_raiz, stack, nombre_sources)
    if not (args.comprobar_referencias or args.comprobar_cobertura):
        imprimir_variables_entorno(datos_stack, resueltos, ruta_proyecto)
    return 0


def imprimir_resumen(archivos, resueltos, ruta_raiz, stack, nombre_sources):
    pares = ", ".join(f"{k}={formato_escalar(v)}" for k, v in sorted(resueltos.items()))
    print(f"stack={stack} opciones={pares} sources={estado_git(ruta_raiz, nombre_sources)}")


#______________________________________________________________________________
# Variables de entorno que necesita el proyecto (fin de una generación real;
# nunca en --simular): solo NOMBRES y su estado en el entorno. Nunca pide, escribe
# ni imprime valores.

def variables_api_url(datos_stack):
    """Variable con la URL de la API del front, según `frontend.llamadas_api`."""
    llamadas = obtener(datos_stack, "frontend.llamadas_api")
    if llamadas == "navegador":
        return "NEXT_PUBLIC_API_BASE_URL"
    if llamadas == "servidor":
        return "API_BASE_URL"
    return None


def variables_servicios(ruta_raiz):
    """Lo que devuelve `servicios.py variables`, en NOMBRES:
    ([grupos, avisos_en_claro]) donde grupos = [(servicio, [(nombre, riesgo)])],
    con `riesgo` para las variables con respaldo de credencial; los avisos en
    claro (ruta:línea:clave) se reimprimen tal cual, sin valor. Devuelve None si el
    script no está disponible o falla."""
    script = os.path.join(ruta_raiz, ".agents", "scripts", "servicios.py")
    if not os.path.isfile(script):
        return None
    try:
        proceso = subprocess.run(
            [sys.executable, "-I", "-B", script, "variables"], cwd=ruta_raiz,
            capture_output=True, text=True, check=True)
    except (OSError, subprocess.SubprocessError):
        return None
    grupos, avisos, actual = [], [], None
    for linea in proceso.stdout.splitlines():
        if linea.startswith("riesgo en claro: "):
            if re.fullmatch(r"riesgo en claro: [A-Za-z0-9_./-]+:[0-9]+:[A-Za-z0-9_.-]+", linea):
                avisos.append(linea)
            else:
                return None
            continue
        m = re.fullmatch(r"([A-Za-z0-9_-]+):(?: (.*))?", linea)
        if not m:
            continue
        servicio, resto = m.group(1), (m.group(2) or "").strip()
        actual = (servicio, [])
        grupos.append(actual)
        for token in resto.split():
            match = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_]*)(?:\((riesgo:respaldo|respaldo)\))?", token)
            if not match:
                return None
            nombre, marca = match.groups()
            actual[1].append((nombre, marca == "riesgo:respaldo"))
    return grupos, avisos


def imprimir_variables_por_entorno(datos_stack, ruta_raiz):
    """Ayuda pública: solo nombres; jamás lee Secret, kubeconfig ni sus valores."""
    if obtener(datos_stack, 'proyecto.stack') != 'springboot':
        return
    script = os.path.join(ruta_raiz, '.agents', 'scripts', 'servicios.py')
    try:
        identidad = subprocess.run([sys.executable, '-I', '-B', script, 'nombres'], cwd=ruta_raiz,
                                  capture_output=True, text=True, check=True)
        filas = json.loads(identidad.stdout)
        nombres_servicios = {item['servicio']: item for item in filas}
        proceso = subprocess.run([sys.executable, '-I', '-B', script, 'variables-json'], cwd=ruta_raiz,
                                 capture_output=True, text=True, check=True)
        resultado = json.loads(proceso.stdout)
        grupos, riesgos = resultado['grupos'], resultado['riesgos']
        for grupo in grupos:
            if not re.fullmatch(r'[a-z][a-z0-9-]*', grupo['carpeta'] or '') or not re.fullmatch(r'[A-Za-z0-9_-]+', grupo['servicio']):
                raise ValueError()
            if any(not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', v['nombre']) for v in grupo['variables']):
                raise ValueError()
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, TypeError):
        print('aviso: no se pudo preparar la ayuda de variables por entorno; revisa servicios.py nombres y variables-json, sin leer secretos.')
        return
    print('\n=== Variables de entorno que necesita este proyecto ===')
    print('los valores los exporta el usuario; este script nunca los muestra ni los pide')
    vistos = set()
    for grupo in grupos:
        servicio, carpeta, perfil = grupo['servicio'], grupo['carpeta'], grupo['perfil']
        print(f'\nEntorno {carpeta} (perfil {perfil}), servicio {servicio}:')
        nombres = []
        for variable in grupo['variables']:
            nombre = variable['nombre']; vistos.add(nombre)
            marca = ' (riesgo: tiene valor de respaldo; no se muestra)' if variable['riesgo'] else ''
            print(f'  {nombre}: {"definida" if nombre in os.environ else "no definida"}{marca}')
            print(f'  local: export {nombre}=')
            if nombre.startswith(('DB_HOST_', 'DB_PORT_', 'DB_NAME_', 'USER_NAME_DB_', 'PASSWORD_DB_')) or nombre.startswith('CLERK_'):
                nombres.append(nombre)
        # Solo servicios que realmente usan base; no inventar Secret para gateway u otros servicios.
        cfg = (obtener(datos_stack, 'devops.entornos') or {}).get(carpeta, {})
        if cfg.get('desplegar') is True and any(n.startswith('DB_HOST_') for n in nombres):
            try:
                info = nombres_servicios[servicio]['devops'][carpeta]
                secret, archivo = info['recursos']['secret_base'], info['archivos']['secret_base']
                if not isinstance(secret, str) or not re.fullmatch(r'[a-z0-9][a-z0-9.-]*', secret): raise ValueError()
                if not isinstance(archivo, str) or not re.fullmatch(r'devops/[a-z][a-z0-9-]*/account/secrets-[a-z0-9.-]+[.]yaml', archivo): raise ValueError()
            except (KeyError, TypeError, ValueError):
                print('  aviso: no hay nombre público de secret determinable; revisa servicios.py nombres.')
                continue
            print('  destino: ' + archivo)
            print('  usuario: kubectl create secret generic ' + secret + ''.join(' --from-literal=' + n + '=' for n in nombres))
    meta_variables = cargar_condiciones(os.path.join(ruta_raiz, ".agents"))
    autenticacion = (obtener(datos_stack, 'integraciones.variables_autenticacion') or []) if condicion_activa(meta_variables, 'integraciones.variables_autenticacion', datos_stack) and obtener(datos_stack, 'integraciones.autenticacion') == 'clerk' else []
    for nombre in autenticacion:
        if not isinstance(nombre, str) or not re.fullmatch(r'[A-Z][A-Z0-9_]{0,63}', nombre):
            bloqueado('variables_autenticacion debe contener solo NOMBRES')
        if nombre not in vistos:
            print(f'  {nombre}: {"definida" if nombre in os.environ else "no definida"}')
            print('  local: export ' + nombre + '=')
    for riesgo in riesgos:
        if isinstance(riesgo.get('archivo'), str) and re.fullmatch(r'[A-Za-z0-9_./-]+', riesgo['archivo']) and isinstance(riesgo.get('linea'), int) and re.fullmatch(r'[A-Za-z0-9_.-]+', riesgo.get('clave', '')):
            print(f"riesgo en claro: {riesgo['archivo']}:{riesgo['linea']}:{riesgo['clave']}")
    print('El usuario elige su clúster, completa y aplica los secrets; no se ejecuta ningún comando ni se lee su configuración.')


def imprimir_variables_entorno(datos_stack, resueltos, ruta_raiz):
    """Sección final "Variables de entorno que necesita este proyecto": nombres y estado
    en el entorno actual (sí/no, sin valor); cómo configurarlos en local (`export
    NOMBRE=`, valor vacío) y, con DevOps Jenkins-Kubernetes, el comando `kubectl create
    secret generic <base>-<entorno>-service-db-secret --from-literal=NOMBRE=` por
    variable de servicio, con el valor vacío para que lo complete el usuario. Las
    variables con respaldo de credencial salen marcadas como riesgo, sin el respaldo."""
    def estado(nombre):
        return "definida" if nombre in os.environ else "no definida"

    con_kubernetes = obtener(datos_stack, "devops.infraestructura") == "jenkins-kubernetes"
    entorno = obtener(datos_stack, "backend.perfil_local") or "feature"
    if con_kubernetes:
        imprimir_variables_por_entorno(datos_stack, ruta_raiz)
        return
    es_back = obtener(datos_stack, "backend") is not None
    resultado = variables_servicios(ruta_raiz) if es_back else ([], [])
    grupos, avisos = resultado if resultado else ([], [])

    lineas = []
    nombres_en_servicios = {n for _, variables in grupos for n, _ in variables}
    meta_variables = cargar_condiciones(os.path.join(ruta_raiz, ".agents"))
    autenticacion = (obtener(datos_stack, "integraciones.variables_autenticacion") or []) if condicion_activa(meta_variables, "integraciones.variables_autenticacion", datos_stack) and obtener(datos_stack, "integraciones.autenticacion") == "clerk" else []
    if not isinstance(autenticacion, list) or any(
        not isinstance(n, str) or not re.fullmatch(r"[A-Z][A-Z0-9_]{0,63}", n)
        for n in autenticacion
    ):
        bloqueado("integraciones.variables_autenticacion debe contener solo NOMBRES, no valores")
    integr = [n for n in autenticacion if n not in nombres_en_servicios]
    if integr:
        lineas += ["", "Autenticación:"]
        for nombre in integr:
            lineas += [f"  {nombre}: {estado(nombre)}",
                       f"  local: export {nombre}="]
    if grupos:
        lineas += ["", f"Servicios (perfil que cuenta en DevOps: {entorno}):"]
        for servicio, variables in grupos:
            lineas.append(f"  {servicio}:")
            for nombre, riesgo in variables:
                marca = " (riesgo: tiene valor de respaldo; no se muestra)" if riesgo else ""
                lineas.append(f"    {nombre}: {estado(nombre)}{marca}")
                lineas.append(f"    local: export {nombre}=")
    url_api = variables_api_url(datos_stack)
    if url_api:
        lineas += ["", "Frontend:",
                   f"  {url_api}: {estado(url_api)}",
                   f"  local: export {url_api}=",
                   f"  .env.local: {url_api}="]
    if not resultado and es_back:
        lineas.append("  aviso: `servicios.py variables` no devolvió servicios;"
                      " no se listan variables de servicios.")
    lineas += [f"  {aviso}" for aviso in avisos]
    if not lineas:
        return
    print("\n=== Variables de entorno que necesita este proyecto ===")
    print("los valores los exporta el usuario; este script nunca los muestra ni los pide")
    for linea in lineas:
        print(linea)
    return


#______________________________________________________________________________
# --comprobar-fuentes: solo valida las marcas de un árbol sources/<proyecto>

def comprobar_fuentes(ruta):
    ruta = os.path.abspath(ruta)
    raiz_agents = os.path.join(ruta, ".agents")
    if not os.path.isdir(raiz_agents):
        bloqueado(f"`{ruta}` no contiene `.agents/`; pasa la ruta de `sources/<proyecto>`")
    opciones = cargar_opciones(raiz_agents)
    cargar_requisitos(raiz_agents, opciones)
    errores = []
    examinar = []
    for ruta_abs, rel in iterar_archivos(raiz_agents, saltar_top={"opciones"}):
        if rel not in PROTEGIDAS:  # protegidas no se generan, no se les exigen marcas
            examinar.append((ruta_abs, rel))
    raiz_opciones = os.path.join(raiz_agents, "opciones")
    if os.path.isdir(raiz_opciones):
        for ruta_abs, rel in iterar_archivos(raiz_opciones):
            partes = rel.split(os.sep)
            if len(partes) >= 3:
                examinar.append((ruta_abs, os.path.sep.join(partes[2:])))
    ruta_agmds = os.path.join(ruta, "AGENTS.md")
    if os.path.isfile(ruta_agmds):
        examinar.append((ruta_agmds, "AGENTS.md"))
    for ruta_abs, destino in examinar:
        contenido = leer_binario(ruta_abs)
        if not es_texto(contenido):
            continue
        prefijos = estilo_ruta(destino)["prefijos"]
        texto = contenido.decode("utf-8")
        lineas = texto.split("\n")
        if lineas and lineas[-1] == "":
            lineas = lineas[:-1]
        fin_fmx = frontmatter_fin(lineas)
        if fin_fmx is not None:
            for i in range(0, fin_fmx):
                for prefijo in prefijos:
                    if (RE_SI[prefijo].match(lineas[i].rstrip("\r"))
                            or RE_FIN[prefijo].match(lineas[i].rstrip("\r"))):
                        errores.append(MarcaError(destino, i + 1,
                                                  "hay una marca dentro del frontmatter"))
                        break
        corte_cab = corte_shebang_frontmatter(lineas)
        cuerpo = lineas[corte_cab:]
        si_arch = buscar_si_archivo(lineas, prefijos, corte_cab)
        if si_arch:
            idx, (clave, valores) = si_arch
            if clave not in opciones:
                errores.append(MarcaError(
                    destino, idx + 1,
                    f"la marca usa la clave `{clave}`, que no está en config/opciones.yaml"))
            else:
                for v in valores.split("|"):
                    if v not in opciones[clave]:
                        errores.append(MarcaError(
                            destino, idx + 1,
                            f"la marca usa el valor `{v}` fuera de la lista de `{clave}` "
                            "de config/opciones.yaml"))
                        break
            cuerpo = lineas[idx + 1:]
        else:
            cuerpo = lineas[corte_cab:]
        validar_de_lineas(cuerpo, destino, corte_cab, prefijos, opciones, errores)
    if errores:
        abortar([str(e) for e in errores])
    print(f"marcas OK: {ruta}")
    return 0


def validar_de_lineas(lineas, nombre, offset_linea, prefijos, opciones, errores):
    """Valida (sin resolver configuración): `si` alternativos de una misma clave, bloques
    anidados, `fin` sin `si`, `si` sin `fin` y claves o valores fuera de opciones.yaml."""
    abiertas = []  # [(clave, línea)]
    for i, cruda in enumerate(lineas, start=1):
        linea = cruda.rstrip("\r")
        abre, fin = None, None
        for prefijo in prefijos:
            if prefijo in RE_SI:
                abre = RE_SI[prefijo].match(linea) or abre
                fin = RE_FIN[prefijo].match(linea) or fin
        if abre:
            clave, valores = abre.group(1), abre.group(2)
            if clave not in opciones:
                errores.append(MarcaError(
                    nombre, offset_linea + i,
                    f"la marca usa la clave `{clave}`, que no está en config/opciones.yaml"))
            else:
                permitidas_texto = {formato_escalar(v) for v in opciones[clave]}
                for v in valores.split("|"):
                    if v not in permitidas_texto:
                        errores.append(MarcaError(
                            nombre, offset_linea + i,
                            f"la marca usa el valor `{v}` fuera de la lista de `{clave}` "
                            "de config/opciones.yaml"))
                        break
            if abiertas:
                if abiertas[-1][0] == clave:
                    abiertas[-1] = (clave, i)  # nueva rama alternativa de la misma clave
                else:
                    errores.append(MarcaError(
                        nombre, offset_linea + i,
                        f"bloque anidado: `{clave}` dentro de un bloque de `{abiertas[-1][0]}`"))
                    continue
            else:
                abiertas.append((clave, i))
        elif fin:
            if not abiertas:
                errores.append(MarcaError(nombre, offset_linea + i, "`fin` sin bloque `si` abierto"))
                continue
            abiertas.pop()
    if abiertas:
        errores.append(MarcaError(nombre, offset_linea + len(lineas) + 1,
                                  f"`si {abiertas[-1][0]}=...` sin `fin`"))


#______________________________________________________________________________
# CLI

def parse_argumentos(argv):
    p = argparse.ArgumentParser(add_help=False, prog=".agents/actualizar.py", description=None)
    p.add_argument("--kit", metavar="RUTA", default=None,
                   help="ruta de la carpeta que contiene sources/; no pregunta")
    # Nombre anterior del parámetro; se acepta para no romper comandos ya guardados.
    p.add_argument("--harness", dest="kit", metavar="RUTA", default=None, help=argparse.SUPPRESS)
    p.add_argument("--proyecto", metavar="RUTA", default=None,
                   help="raíz del proyecto (por defecto, el directorio actual)")
    p.add_argument("--simular", action="store_true", help="muestra el diff y no escribe nada")
    p.add_argument("--si", action="store_true", help="aplica sin pedir confirmación")
    p.add_argument("--comprobar-referencias", action="store_true",
                   help="tras generar, comprueba referencias rotas")
    p.add_argument("--comprobar-cobertura", action="store_true",
                   help="comprueba que cada línea de sources aparece en alguna combinación")
    p.add_argument("--comprobar-fuentes", metavar="RUTA", default=None,
                   help="solo valida las marcas de sources/<proyecto> y termina")
    args = p.parse_args(argv)
    if "-h" in argv or "--help" in argv:
        print(__doc__)
        sys.exit(0)
    return args


def main(argv):
    args = parse_argumentos(argv)
    if args.comprobar_fuentes is not None:
        return comprobar_fuentes(args.comprobar_fuentes)
    if args.proyecto is None:
        args.proyecto = os.getcwd()
    return ejecutar(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
