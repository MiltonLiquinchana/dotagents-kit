#!/usr/bin/env python3
"""servicios.py — consulta el disco: servicios del repositorio, puertos y variables de entorno.

Uso (desde la raíz del repositorio del proyecto):
    python3 -I -B .agents/scripts/servicios.py escribir-jdk-ruta <servicio>...  # solo la línea JDK aprobada
    python3 -I -B .agents/scripts/servicios.py nombres [servicio] [--entorno CARPETA]  # identidad y nombres, JSON
    python3 -I -B .agents/scripts/servicios.py listar            # servicios con group, puertos, context-path y nodePort
    python3 -I -B .agents/scripts/servicios.py siguiente-puerto  # puerto libre nuevo y su nodePort
    python3 -I -B .agents/scripts/servicios.py variables         # NOMBRES de variables ${...} por servicio y riesgos
    python3 -I -B .agents/scripts/servicios.py perfiles [servicio]  # perfil activo, archivo y NOMBRES de variables por servicio
    python3 -I -B .agents/scripts/servicios.py entradas-jenkins  # bloque Groovy para getServices()
    python3 -I -B .agents/scripts/servicios.py validar-jenkins [ruta]  # comprueba getServices() frente al disco
    python3 -I -B .agents/scripts/servicios.py validar-gateway   # comprueba coherencia de rutas de GatewayConfig.java
# si devops.infraestructura=jenkins-kubernetes
    python3 -B -E .agents/scripts/servicios.py comprobar-secreto <ruta>  # usuario: estado de un Secret, sin mostrar valores
# fin

Solo biblioteca estándar. El subcomando `comprobar-secreto` (solo usuario, nunca la IA) importa PyYAML
dentro de sí mismo si está disponible y no imprime valores. Lee parámetros mediante el parser de actualizar.py (mismo
subconjunto YAML de cuatro niveles que stack.mjs); no ejecuta el generador ni llama a node. Nunca imprime el valor de una variable: solo su NOMBRE, y en los
riesgos la ruta del archivo, la línea y el nombre de la clave.

Códigos de salida: 0 = OK.

Qué lee:
- Servicio: toda carpeta del primer nivel con `build.gradle` y `settings.gradle`.
- `src/main/resources/application*.yaml` (y `application*.properties`), SOLO con las
  claves de las expresiones regulares de abajo (`port`, `context-path`, `active`,
  `${NOMBRE}` y las claves de credencial); nunca muestra una línea entera de configuración.
- `devops/<carpeta>/<servicio>/service*.yaml` para el nodePort; las carpetas `account/`
  no se abren nunca por los subcomandos de la IA. `comprobar-secreto` es la única excepción: lo ejecuta
  el usuario y nunca imprime valores (solo estado por clave y diagnósticos sin contenido).

Salida de `variables` (formato parseable; la usa `actualizar.py` al terminar una generación):
    <servicio>: VAR1 VAR2(respaldo) VAR3(riesgo:respaldo) ...
    riesgo en claro: <ruta>:<línea>:<clave>
Un sufijo `(riesgo:respaldo)` marca una variable con valor de respaldo cuyo nombre parece
de credencial. La línea `riesgo en claro` marca una clave de credencial escrita
con un valor literal (que no empieza por `${...}`), sin mostrar el valor.

Con varios perfiles, el puerto de `application.yaml` (base) vale para todos; el de `application-<perfil>.yaml` lleva su perfil. `siguiente-puerto`
cuenta como ocupados los puertos de TODOS los perfiles de todos los servicios. Con DevOps, el
puerto de cada sufijo declarado en devops.entornos es el que cuenta en sus manifiestos.
Comandos entornos/variables-json conservan la carpeta y el perfil, sin valores de variables.
Identidad de nombres: base = rootProject.name sin un -service final (también gateway);
context-path propuesto = /base para servicios nuevos; paquete = group.base sin guiones;
{AliasPascal} = base en PascalCase. El JAR conserva su nombre de artefacto y versión
literales; con DevOps el nombre debe igualar rootProject.name. Sonar usa systemProp
del servicio, propiedad literal del build, group:nombre o nombre, en ese orden.
"""

import os
import json
import importlib.util
import re
import sys
from pathlib import Path

EXCLUIDAS = {"build", "bin", "gradle", "logs", "knowledge-base", "devops"}

RE_GROUP = re.compile(r"^\s*group\s*=?\s*'([^']*)'|^\s*group\s*=?\s*\"([^\"]*)\"")
RE_PORT = re.compile(r"^(\s+)port:\s*([0-9]+)\s*(?:#.*)?$")
RE_CONTEXT_PATH = re.compile(r"^\s+context-path:\s*(\S+)\s*$")
RE_ACTIVE = re.compile(r"^\s+active:\s*(.*)$")
RE_ITEM = re.compile(r"^(\s+)-\s*(\S+)\s*$")
RE_VAR = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(:)?[^}]*\}")
RE_CRED_YAML = re.compile(
    r"^(\s+)([\w.\-]*(?:password|passwd|username|secret|token|key))\s*:\s*(\S.*)$", re.IGNORECASE)
RE_CRED_PROPS = re.compile(
    r"^([\w.\-]*(?:password|passwd|username|secret|token|key))\s*=\s*(\S.*)$", re.IGNORECASE)
RE_NODEPORT = re.compile(r"^\s*nodePort:\s*([0-9]+)\s*(?:#.*)?$")
RE_ROOT_PROJECT_NAME = re.compile(r"^\s*rootProject\.name\s*=\s*(?:'([^']*)'|\"([^\"]*)\")", re.MULTILINE)
# Captura archiveBaseName = '...' / .set('...') y archivesName = '...' / .set('...')
RE_ARCHIVE_BASE_NAME = re.compile(r"archiveBaseName(?:\.set\(|\s*=\s*)(?:'([^']*)'|\"([^\"]*)\")")
RE_ARCHIVES_NAME = re.compile(r"archivesName(?:\.set\(|\s*=\s*)(?:'([^']*)'|\"([^\"]*)\")")
# Detecta asignaciones no literales (con $ o identificador): nombre de variable/expresión
RE_ARCHIVE_NONLITERAL = re.compile(
    r"(?:archiveBaseName|archivesName)\s*(?:\.set\(|\s*=\s*)"
    r"(?:\"[^\"]*\$[^\"]*\"|'[^']*\$[^']*'|[^\"\'][^,;\n\)]*)")
RE_ARCHIVE_FILE_NAME = re.compile(r"\barchiveFileName\b")


def fail(mensaje):
    print(f"ERROR: {mensaje}", file=sys.stderr)
    sys.exit(1)


def servicios(raiz):
    """Toda carpeta del primer nivel con build.gradle y settings.gradle, ordenada."""
    lista = []
    for nombre in sorted(os.listdir(raiz)):
        ruta = os.path.join(raiz, nombre)
        if not os.path.isdir(ruta) or nombre.startswith(".") or nombre in EXCLUIDAS:
            continue
        if os.path.isfile(os.path.join(ruta, "build.gradle")) and \
                os.path.isfile(os.path.join(ruta, "settings.gradle")):
            lista.append(nombre)
    return lista


def group_de(raiz, nombre):
    ruta = os.path.join(raiz, nombre, "build.gradle")
    try:
        with open(ruta, encoding="utf-8", errors="replace") as fh:
            for linea in fh:
                m = RE_GROUP.match(linea)
                if m:
                    return m.group(1) or m.group(2)
    except OSError:
        pass
    return None


def limpiar_comentarios_gradle(texto):
    texto = re.sub(r"/\*[\s\S]*?\*/", "", texto)
    lineas = [l.split("//")[0] for l in texto.splitlines()]
    return "\n".join(lineas)


class _JenkinsEntradaError(Exception):
    """Error al calcular la entrada Jenkins de un servicio individual (no termina el proceso)."""


def base_desde_nombre(nombre):
    """Regla única de identidad, también para el gateway."""
    return nombre[:-8] if nombre.endswith('-service') else nombre


def _calcular_entrada_jenkins_uno(raiz, s):
    """Resuelve solo el nombre del artefacto; las entradas Jenkins calculan sus demás campos.
    Lanza _JenkinsEntradaError si no es resoluble estáticamente."""
    ruta_settings = os.path.join(raiz, s, "settings.gradle")
    try:
        with open(ruta_settings, encoding="utf-8", errors="replace") as fh:
            cont_settings = limpiar_comentarios_gradle(fh.read())
    except OSError:
        cont_settings = ""
    m_root = RE_ROOT_PROJECT_NAME.search(cont_settings)
    if not m_root:
        raise _JenkinsEntradaError(
            f"{s}/settings.gradle: falta 'rootProject.name = \"...\"' o no es resoluble estáticamente; "
            f"decide el nombre en el plan.")
    root_name = (m_root.group(1) or m_root.group(2) or "").strip()
    if not root_name or "$" in root_name:
        raise _JenkinsEntradaError(
            f"{s}/settings.gradle: 'rootProject.name' no es resoluble estáticamente; "
            f"decide el nombre en el plan.")
    name = root_name

    ruta_build = os.path.join(raiz, s, "build.gradle")
    try:
        with open(ruta_build, encoding="utf-8", errors="replace") as fh:
            cont_build = limpiar_comentarios_gradle(fh.read())
    except OSError:
        cont_build = ""

    if RE_ARCHIVE_FILE_NAME.search(cont_build):
        raise _JenkinsEntradaError(
            f"{s}/build.gradle: usa 'archiveFileName', que es incompatible con el pipeline "
            f"(busca <name>-*.jar); decide el nombre en el plan.")

    for m_nl in RE_ARCHIVE_NONLITERAL.finditer(cont_build):
        frag = m_nl.group(0)
        if "$" in frag or ('"' not in frag and "'" not in frag):
            raise _JenkinsEntradaError(
                f"{s}/build.gradle: nombre del JAR no es resoluble estáticamente "
                f"({frag.strip()!r}); decide el nombre en el plan.")

    m_base = RE_ARCHIVE_BASE_NAME.search(cont_build)
    m_archives = RE_ARCHIVES_NAME.search(cont_build)

    if m_base and m_archives:
        val_base = (m_base.group(1) or m_base.group(2) or "").strip()
        val_arch = (m_archives.group(1) or m_archives.group(2) or "").strip()
        if val_base and val_arch and val_base != val_arch:
            raise _JenkinsEntradaError(
                f"{s}/build.gradle: 'archiveBaseName' ({val_base!r}) y 'archivesName' ({val_arch!r}) "
                f"se contradicen; decide el nombre en el plan.")

    for m_jar in (m_base, m_archives):
        if m_jar:
            val = (m_jar.group(1) or m_jar.group(2) or "").strip()
            if "$" in val:
                raise _JenkinsEntradaError(
                    f"{s}/build.gradle: nombre del JAR contiene '$' y no es resoluble estáticamente; "
                    f"decide el nombre en el plan.")
            if val:
                name = val
            break

    return {'name': name}


def calcular_entradas_jenkins(raiz, identidades=None):
    identidades = calcular_nombres(raiz) if identidades is None else identidades
    items = []
    for row in identidades:
        name = row['jar_nombre']
        if name is None:
            fail(row['servicio'] + ': nombre del JAR no determinable')
        words = [w for w in row['base'].split('-') if w]
        items.append({'servicio': row['servicio'], 'directory': row['servicio'],
            'name': name, 'displayName': ' '.join(p.capitalize() for p in name.split('-') if p),
            'first_word': name.split('-')[0],
            'camel_case': words[0].lower() + ''.join(w.capitalize() for w in words[1:]) if words else name})

    from collections import Counter
    freq = Counter(it["first_word"] for it in items)
    for it in items:
        it["clave"] = it["camel_case"] if freq[it["first_word"]] > 1 else it["first_word"]

    claves_calc = [it["clave"] for it in items]
    if len(claves_calc) != len(set(claves_calc)):
        fail("colisión en claves calculadas de getServices(); requiere nombres diferenciados.")

    return items


def configuraciones(raiz, nombre):
    """Proyección por lista blanca. Nunca conserva líneas completas ni respaldos."""
    carpeta = os.path.join(raiz, nombre, "src", "main", "resources")
    salida = []
    if not os.path.isdir(carpeta):
        return salida
    for archivo in sorted(os.listdir(carpeta)):
        if not re.fullmatch(r"application(?:-[\w-]+)?\.(?:yaml|yml|properties)", archivo):
            continue
        filas, padres = [], []
        try:
            lineas = open(os.path.join(carpeta, archivo), encoding="utf-8", errors="replace").read().splitlines()
            for numero, linea in enumerate(lineas, 1):
                if linea.strip() == "---":
                    padres = []
                    continue
                if not linea.strip() or linea.lstrip().startswith("#"):
                    continue
                fila = {"linea": numero, "variables": []}
                cred = (RE_CRED_PROPS if archivo.endswith(".properties") else RE_CRED_YAML).match(linea)
                if cred:
                    clave = cred.group(1) if archivo.endswith(".properties") else cred.group(2)
                    valor = cred.group(2) if archivo.endswith(".properties") else cred.group(3)
                    if not valor.strip().strip('"').strip("'").startswith("${"):
                        fila["riesgo_claro"] = clave
                for m in RE_VAR.finditer(linea):
                    variable, respaldo = m.group(1), m.group(2) is not None
                    riesgo = respaldo and (cred is not None or re.search(r"PASSWORD|PASSWD|SECRET|KEY|TOKEN", variable, re.I) is not None)
                    fila["variables"].append((variable, respaldo, riesgo))
                if archivo.endswith(".properties"):
                    for clave, campo, patron in (("server.port", "puerto", r"[0-9]+"),
                            ("server.servlet.context-path", "contexto", r"/[A-Za-z0-9_/-]*"),
                            ("spring.application.name", "nombre", r"[A-Za-z0-9_-]+")):
                        m = re.fullmatch(re.escape(clave) + r"\s*=\s*(" + patron + r")\s*", linea.strip())
                        if m:
                            fila[campo] = int(m.group(1)) if campo == "puerto" else m.group(1)
                    m = re.fullmatch(r"\s*spring\.profiles\.active\s*=\s*(.+?)\s*", linea)
                    if m:
                        val = m.group(1).strip().strip('"').strip("'")
                        fila["activos_presente"] = True
                        if val.startswith("${"):
                            fila["activos_variable"] = True
                        else:
                            fila["activos"] = val
                else:
                    m = re.match(r"^(\s*)([A-Za-z_][\w.-]*):(?:\s*(.*))?$", linea)
                    if m:
                        nivel, clave, resto = len(m.group(1)), m.group(2), (m.group(3) or "")
                        while padres and padres[-1][0] >= nivel:
                            padres.pop()
                        ruta = [k for _, k in padres] + [clave]
                        if clave == "spring.profiles.active":
                            ruta = ["spring", "profiles", "active"]
                        # Solo conserva nombres estructurales de la lista blanca.
                        if clave in {"server", "servlet", "spring", "profiles"}:
                            padres.append((nivel, clave))
                        for esperada, campo, patron in ((["server", "port"], "puerto", r"[0-9]+"),
                                (["server", "servlet", "context-path"], "contexto", r"/[A-Za-z0-9_/-]*"),
                                (["spring", "application", "name"], "nombre", r"[A-Za-z0-9_-]+")):
                            if ruta == esperada:
                                v = re.match(r"^\s*[\w.-]+:\s*(" + patron + r")\s*(?:#.*)?$", linea)
                                if v:
                                    valor_campo = v.group(1).strip().strip('"').strip("'")
                                    if campo == "puerto":
                                        if re.fullmatch(r"[0-9]+", valor_campo):
                                            fila[campo] = int(valor_campo)
                                    else:
                                        if re.fullmatch(patron, valor_campo):
                                            fila[campo] = valor_campo
                        if ruta == ["spring", "profiles", "active"]:
                            fila["activos_presente"] = True
                            resto_limpio = resto.strip()
                            if resto_limpio and not resto_limpio.startswith("#"):
                                valor_campo = resto_limpio.split('#', 1)[0].strip().strip('"').strip("'")
                                if valor_campo.startswith("${"):
                                    fila["activos_variable"] = True
                                elif valor_campo.startswith('['):
                                    inner = valor_campo[1:-1] if valor_campo.endswith(']') else valor_campo[1:]
                                    if '${' in inner:
                                        fila["activos_variable"] = True
                                    elif inner.strip():
                                        fila["activos"] = inner
                                else:
                                    fila["activos"] = valor_campo
                            else:
                                # block list: look ahead for '- item' children (permitir mismo sangrado que la clave)
                                items = []
                                var = False
                                j = numero
                                while j < len(lineas):
                                    nxt = lineas[j]
                                    if not nxt.strip() or nxt.lstrip().startswith('#'):
                                        j += 1
                                        continue
                                    indent_n = len(nxt) - len(nxt.lstrip(' '))
                                    mitem = re.match(r"^\s*-\s*(.+?)\s*$", nxt)
                                    if mitem:
                                        if indent_n < nivel:
                                            break
                                        val = mitem.group(1).split('#',1)[0].strip().strip('"').strip("'")
                                        if val.startswith('${'):
                                            var = True
                                        elif val:
                                            items.append(val)
                                        j += 1
                                        continue
                                    if indent_n <= nivel:
                                        break
                                    j += 1
                                if var:
                                    fila["activos_variable"] = True
                                elif items:
                                    fila["activos"] = ",".join(items)
                        if clave == "application" and [k for _, k in padres] == ["spring"]:
                            padres.append((nivel, clave))
                if len(fila) > 2 or fila["variables"]:
                    filas.append(fila)
        except OSError:
            continue
        salida.append((archivo, filas))
    return salida


def perfil_de_archivo(nombre_archivo):
    """Perfil de `application-<perfil>.yaml`; para el archivo base devuelve None."""
    m = re.match(r"^application-(.+)\.(?:yaml|yml|properties)$", nombre_archivo)
    return m.group(1) if m else None


def puertos(raiz, nombre):
    """El puerto base vale para todos los perfiles; los específicos conservan su nombre."""
    resultado = []
    for archivo, filas in configuraciones(raiz, nombre):
        perfil = perfil_de_archivo(archivo)
        for fila in filas:
            if "puerto" in fila:
                resultado.append((fila["puerto"], perfil))
    return list(dict.fromkeys(resultado))


def context_paths(raiz, nombre):
    return list(dict.fromkeys(fila["contexto"] for _, filas in configuraciones(raiz, nombre)
                             for fila in filas if "contexto" in fila))


def node_ports(raiz, nombre):
    return list(dict.fromkeys(item['nodePort'] for item in node_ports_detalle(raiz, nombre)))


def es_gateway_webflux(raiz, s):
    """Devuelve True si build.gradle declara starter de Spring Cloud Gateway."""
    ruta_build = os.path.join(raiz, s, "build.gradle")
    try:
        with open(ruta_build, encoding="utf-8", errors="replace") as fh:
            return "spring-cloud-starter-gateway" in fh.read()
    except OSError:
        return False


def stack_local(raiz):
    """Mismo parser genérico del generador; no crea un tercer dialecto de YAML."""
    archivo = os.path.join(raiz, '.agents', 'stack.yaml')
    lector = os.path.join(raiz, '.agents', 'actualizar.py')
    if not os.path.isfile(archivo) or not os.path.isfile(lector):
        return {}
    spec = importlib.util.spec_from_file_location('parametros_generador', lector)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.cargar_stack(archivo)


def entornos(raiz):
    data = stack_local(raiz)
    devops = data.get('devops', {})
    return devops.get('entornos', {}) if devops.get('infraestructura') == 'jenkins-kubernetes' else {}


def puertos_resueltos(raiz, servicio, perfil):
    items = puertos(raiz, servicio)
    propios = {p for p, f in items if f == perfil}
    base = {p for p, f in items if f is None}
    return sorted(propios or base)


def puerto_efectivo(raiz, servicio, perfil):
    valores = puertos_resueltos(raiz, servicio, perfil)
    return valores[0] if len(valores) == 1 else None


def node_ports_detalle(raiz, nombre):
    salida = []
    base = os.path.join(raiz, 'devops')
    if not os.path.isdir(base):
        return salida
    for carpeta in sorted(os.listdir(base)):
        if carpeta == 'account' or carpeta.startswith('.') or os.path.islink(os.path.join(base, carpeta)):
            continue
        servicio = os.path.join(base, carpeta, nombre)
        if not os.path.isdir(servicio) or os.path.islink(servicio):
            continue
        for archivo in sorted(os.listdir(servicio)):
            if not re.fullmatch(r'service[^/]*\.yaml', archivo):
                continue
            ruta = os.path.join(servicio, archivo)
            if os.path.islink(ruta):
                continue
            with open(ruta, encoding='utf-8') as stream:
                for numero, linea in enumerate(stream, 1):
                    m = RE_NODEPORT.fullmatch(linea.rstrip())
                    if m:
                        salida.append({'carpeta': carpeta, 'servicio': nombre, 'nodePort': int(m[1]),
                                       'archivo': os.path.relpath(ruta, raiz), 'linea': numero})
    return salida


def cmd_entornos(raiz):
    print(json.dumps(entornos(raiz), ensure_ascii=False, indent=2))
    return 0


def cmd_variables_json(raiz):
    mapa = entornos(raiz)
    grupos, riesgos = [], []
    perfiles = [(carpeta, cfg['sufijo']) for carpeta, cfg in mapa.items()] or [(None, stack_local(raiz).get('backend', {}).get('perfil_local') or 'feature')]
    for servicio in servicios(raiz):
        configuracion = configuraciones(raiz, servicio)
        for carpeta, perfil in perfiles:
            nombres = {}
            for archivo, filas in configuracion:
                if perfil_de_archivo(archivo) not in (None, perfil):
                    continue
                for fila in filas:
                    for nombre, respaldo, riesgo in fila['variables']:
                        item = nombres.setdefault(nombre, {'nombre': nombre, 'respaldo': False, 'riesgo': False})
                        item['respaldo'] |= respaldo; item['riesgo'] |= riesgo
                    if 'riesgo_claro' in fila:
                        riesgos.append({'archivo': servicio + '/src/main/resources/' + archivo,
                                        'linea': fila['linea'], 'clave': fila['riesgo_claro']})
            grupos.append({'servicio': servicio, 'carpeta': carpeta, 'perfil': perfil, 'variables': list(nombres.values())})
    print(json.dumps({'grupos': grupos, 'riesgos': riesgos}, ensure_ascii=False, indent=2))
    return 0


def cmd_validar_entornos(raiz):
    mapa, data = entornos(raiz), stack_local(raiz)
    if not mapa:
        print('OK: sin entornos Kubernetes que comparar.')
        return 0
    gateway = data.get('backend', {}).get('gateway')
    intervalos, gateways, usados, esperados, errores = [], [], {}, {}, []
    def reservar(puerto, owner, origen):
        if not 30000 <= puerto <= 32767:
            errores.append('nodePort fuera de rango: ' + owner[0] + '/' + owner[1])
        if puerto in usados and usados[puerto] != owner:
            errores.append('nodePort repetido ' + str(puerto) + ': ' + '/'.join(usados[puerto]) + ' y ' + '/'.join(owner))
        usados[puerto] = owner
    identidades = {item['servicio']: item for item in calcular_nombres(raiz)}
    lista = list(identidades)
    for carpeta, cfg in mapa.items():
        if cfg.get('desplegar') is not True:
            continue
        offsets = []
        for servicio in lista:
            base = identidades[servicio]['base']
            if not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]*[a-z0-9])?', base):
                errores.append(carpeta + '/' + servicio + ': base no válida para Kubernetes (RFC 1123); rootProject.name=' + identidades[servicio]['nombre'])
            if len(base + '-' + cfg['sufijo'] + '-service-container') > 63:
                errores.append(carpeta + '/' + servicio + ': nombre final de recurso excede 63 caracteres')
            valores_puerto = puertos_resueltos(raiz, servicio, cfg['sufijo'])
            if not valores_puerto:
                errores.append(carpeta + '/' + servicio + ': puerto no resoluble del perfil ni del base; declara server.port en el application.yaml del servicio mediante un plan aprobado (.agents/workflows/incorporate-service.md)')
                continue
            if len(valores_puerto) > 1:
                errores.append(carpeta + '/' + servicio + ': varios puertos distintos en la configuración (' + ', '.join(str(p) for p in valores_puerto) + '); deja un único server.port efectivo para el perfil o el base.')
                continue
            puerto = valores_puerto[0]
            if servicio == gateway:
                nodo = cfg.get('gateway_nodo_puerto')
                if nodo is None:
                    errores.append(carpeta + ': falta gateway_nodo_puerto'); continue
                gateways.append((carpeta, nodo))
            else:
                offsets.append(puerto - 8080)
                nodo = cfg['nodo_puerto_base'] + puerto - 8080
            reservar(nodo, (carpeta, servicio), 'stack')
            esperados[(carpeta, servicio)] = nodo
        if gateway and not os.path.isdir(os.path.join(raiz, str(gateway))):
            nodo = cfg.get('gateway_nodo_puerto')
            if nodo is None:
                errores.append(carpeta + ': falta gateway_nodo_puerto')
            else:
                gateways.append((carpeta, nodo))
                reservar(nodo, (carpeta, gateway), 'stack')
                esperados[(carpeta, gateway)] = nodo
        if offsets:
            intervalos.append((carpeta, cfg['nodo_puerto_base'] + min(0, min(offsets)), cfg['nodo_puerto_base'] + max(0, max(offsets))))
    for i, (a, lo, hi) in enumerate(intervalos):
        for b, lo2, hi2 in intervalos[i + 1:]:
            if max(lo, lo2) <= min(hi, hi2):
                errores.append('rangos NodePort solapados: ' + a + ' y ' + b)
        for carpeta, puerto in gateways:
            if lo <= puerto <= hi:
                errores.append('gateway de ' + carpeta + ' ocupa el rango de servicios de ' + a)
    for servicio in lista:
        for item in node_ports_detalle(raiz, servicio):
            if mapa.get(item['carpeta'], {}).get('desplegar') is not True:
                continue
            owner = (item['carpeta'], servicio)
            if owner in esperados and esperados[owner] != item['nodePort']:
                errores.append(item['archivo'] + ': nodePort no coincide con el entorno y perfil declarados')
            reservar(item['nodePort'], owner, item['archivo'])
    if errores:
        for error in sorted(set(errores)):
            print('BLOCKED: ' + error)
        return 1
    print('OK: rangos y nodePorts por entorno sin colisiones; gateway explícito.')
    return 0


def cmd_listar(raiz):
    identidades = calcular_nombres(raiz)
    lista = [item['servicio'] for item in identidades]
    puertos_por = {s: puertos(raiz, s) for s in lista}
    for item in identidades:
        service = item['servicio']
        print('servicio: ' + service)
        print('  nombre: ' + item['nombre'])
        print('  base: ' + item['base'])
        print('  group: ' + str(item['group']))
        print('  context_path: ' + str(item['context_path']))
        print('  puerto: ' + ', '.join(str(p) + ' (' + (f or 'base') + ')' for p,f in puertos_por[service]))
        nodes = node_ports(raiz, service)
        if nodes: print('  nodePort: ' + ', '.join(str(v) for v in nodes))
        for aviso in item['avisos']: print('  aviso ' + aviso['codigo'] + ': ' + aviso['motivo'])
    if stack_local(raiz).get('devops', {}).get('infraestructura') == 'jenkins-kubernetes':
        for e in calcular_entradas_jenkins(raiz, identidades):
            print(f"  jenkins: clave={e['clave']}, name={e['name']}, displayName={e['displayName']}, directory={e['directory']}")
    # avisos de choque: base es global; perfiles específicos coinciden entre sí
    por_puerto = {}
    for s in lista:
        for puerto, perfil in puertos_por[s]:
            por_puerto.setdefault(puerto, []).append((s, perfil))
    for puerto in sorted(por_puerto):
        usos = por_puerto[puerto]
        for i in range(len(usos)):
            for j in range(i + 1, len(usos)):
                s_a, f_a = usos[i]
                s_b, f_b = usos[j]
                if s_a == s_b or (f_a is not None and f_b is not None and f_a != f_b):
                    continue
                fa = f_a if f_a is not None else "sin perfil"
                fb = f_b if f_b is not None else "sin perfil"
                print(f"aviso: puerto {puerto} en {s_a} ({fa}) y {s_b} ({fb})")
    if entornos(raiz):
        for nombre in lista:
            for item in node_ports_detalle(raiz, nombre):
                print('  manifiesto: ' + item['carpeta'] + '/' + nombre + '; nodePort: ' + str(item['nodePort']))
    return 0


def cmd_siguiente_puerto(raiz):
    lista = servicios(raiz)
    if not lista:
        fail("no hay carpetas de servicio (build.gradle + settings.gradle) en el primer nivel")
    ocupados = set()
    for s in lista:
        for puerto, _ in puertos(raiz, s):
            ocupados.add(puerto)
    if not ocupados:
        fail("no hay puertos declarados en application*.yaml")
    nuevo = max(ocupados) + 1
    while nuevo in ocupados:  # garantía; tras max+1 no ocurre
        nuevo += 1
    print(f"puerto: {nuevo}")
    mapa = entornos(raiz)
    if mapa:
        for carpeta, cfg in mapa.items():
            if cfg.get('desplegar') is not True:
                print(f"entorno: {carpeta}; perfil: {cfg['sufijo']}; solo construcción, sin nodePort")
                continue
            print(f"entorno: {carpeta}; perfil: {cfg['sufijo']}; nodePort: {cfg['nodo_puerto_base'] + nuevo - 8080}; gateway-nodePort: {cfg.get('gateway_nodo_puerto', 'no declarado')}")
    else:
        print(f"nodePort: {30800 + (nuevo - 8080)}")
    return 0


def cmd_variables(raiz):
    lista = servicios(raiz)
    if not lista:
        fail("no hay carpetas de servicio (build.gradle + settings.gradle) en el primer nivel")
    for s in lista:
        nombres, orden, en_claro = {}, [], []
        for archivo, filas in configuraciones(raiz, s):
            ruta_archivo = f"{s}/src/main/resources/{archivo}"
            for fila in filas:
                for nombre, respaldo, riesgo in fila["variables"]:
                    if nombre not in nombres:
                        nombres[nombre] = (respaldo, riesgo)
                        orden.append(nombre)
                    else:
                        anterior = nombres[nombre]
                        nombres[nombre] = (anterior[0] or respaldo, anterior[1] or riesgo)
                if "riesgo_claro" in fila:
                    en_claro.append((ruta_archivo, fila["linea"], fila["riesgo_claro"]))
        cuerpo = []
        for nombre in orden:
            respaldo, riesgo = nombres[nombre]
            sufijo = "(riesgo:respaldo)" if riesgo else "(respaldo)" if respaldo else ""
            cuerpo.append(nombre + sufijo)
        if cuerpo:
            print(f"{s}: " + " ".join(cuerpo))
        else:
            print(f"{s}:")
        for ruta, linea, clave in en_claro:
            print(f"riesgo en claro: {ruta}:{linea}:{clave}")
    return 0


def cmd_entradas_jenkins(raiz):
    entradas = calcular_entradas_jenkins(raiz)
    bloques = []
    for e in entradas:
        bloque = (
            f"        {e['clave']}: [\n"
            f"            name: '{e['name']}',\n"
            f"            displayName: '{e['displayName']}',\n"
            f"            directory: '{e['directory']}'\n"
            f"        ]"
        )
        bloques.append(bloque)
    print(",\n".join(bloques))
    return 0


def parsear_get_services(contenido, ruta_rel):
    m_func = re.search(r"def\s+getServices\s*\(\s*\)\s*\{([\s\S]*?)\n\}", contenido)
    if not m_func:
        return None, f"BLOCKED: no se pudo leer getServices() de {ruta_rel}; formato esperado: def getServices() {{ return [ clave: [ name: '...', displayName: '...', directory: '...' ], ... ] }}"
    body = m_func.group(1).strip()
    m_ret = re.search(r"return\s*\[([\s\S]*?)\]\s*$", body)
    if not m_ret:
        return None, f"BLOCKED: no se pudo leer getServices() de {ruta_rel}; formato esperado: def getServices() {{ return [ clave: [ name: '...', displayName: '...', directory: '...' ], ... ] }}"
    map_content = m_ret.group(1)

    # Patrón para detectar entradas clave: [...]
    pattern = re.compile(r"([A-Za-z0-9_-]+)\s*:\s*\[([^\]]*?)\]")
    matches = list(pattern.finditer(map_content))

    residuo = pattern.sub("", map_content)
    lineas_residuo = [l.strip() for l in residuo.splitlines() if l.strip() and not l.strip().startswith("//")]
    if any(l for l in lineas_residuo if l != ","):
        return None, f"BLOCKED: no se pudo leer getServices() de {ruta_rel}; formato esperado: def getServices() {{ return [ clave: [ name: '...', displayName: '...', directory: '...' ], ... ] }}"

    # Regex para extraer propiedades individuales: acepta multilínea e inline.
    re_prop = re.compile(r"""([A-Za-z0-9_-]+)\s*:\s*(?:'([^']*)'|"([^"]*)")""")

    keys = []
    entradas = []
    for m in matches:
        key = m.group(1)
        keys.append(key)
        props_text = m.group(2)
        props = {}
        for pm in re_prop.finditer(props_text):
            props[pm.group(1)] = pm.group(2) if pm.group(2) is not None else pm.group(3)
        # Verificar que no haya contenido irreconocible (excluir comas y espacios)
        residuo_p = re_prop.sub("", props_text)
        residuo_p_clean = re.sub(r"[\s,]", "", residuo_p).lstrip("/")
        if residuo_p_clean.strip():
            return None, f"BLOCKED: no se pudo leer getServices() de {ruta_rel}; formato esperado: name: '...', displayName: '...', directory: '...'"
        for req in ('name', 'displayName', 'directory'):
            if req not in props:
                return None, f"BLOCKED: no se pudo leer getServices() de {ruta_rel}; falta '{req}' en la entrada '{key}'"
        entradas.append({'clave': key, 'name': props['name'], 'displayName': props['displayName'], 'directory': props['directory']})

    vistos = set()
    for k in keys:
        if k in vistos:
            return None, f"BLOCKED: getServices() define la clave '{k}' más de una vez."
        vistos.add(k)

    for e in entradas:
        if e['clave'] == 'example' or e['name'] == 'example-service' or e['directory'] == 'example-service':
            return None, "BLOCKED: getServices() contiene la entrada de ejemplo 'example-service'; debe retirarse."

    return entradas, None

def cmd_validar_jenkins(raiz, argv=None):
    ruta_rel = argv[0] if argv else stack_local(raiz)["devops"]["jenkinsfile"]
    if not isinstance(ruta_rel, str) or not ruta_rel.strip() or os.path.isabs(ruta_rel) or '..' in ruta_rel or '\\' in ruta_rel:
        fail('devops.jenkinsfile debe ser una ruta relativa segura dentro del repositorio')
    ruta_archivo = os.path.join(raiz, ruta_rel)
    destino = Path(ruta_archivo).resolve()
    if not destino.is_relative_to(Path(raiz).resolve()) or any(x == 'account' or x.startswith('.env') for x in destino.parts):
        fail('Jenkinsfile fuera del alcance permitido')
    if not os.path.isfile(ruta_archivo):
        if not argv:
            print(f"OK: {ruta_rel} no existe; sin pipeline que validar.")
            return 0
        fail(f"archivo '{ruta_rel}' no existe")

    with open(ruta_archivo, encoding="utf-8", errors="replace") as fh:
        contenido = fh.read()

    entradas_jenkins, err = parsear_get_services(contenido, ruta_rel)
    if err:
        print(err)
        return 1

    esperadas = calcular_entradas_jenkins(raiz)

    esperadas_por_dir = {e['directory']: e for e in esperadas}
    esperadas_por_servicio = {e['servicio']: e for e in esperadas}

    bloqueos = []
    avisos = []
    directorios_en_jenkins = set()

    for e in entradas_jenkins:
        clave = e['clave']
        dir_j = e['directory']
        name_j = e['name']
        disp_j = e['displayName']
        directorios_en_jenkins.add(dir_j)

        if dir_j not in esperadas_por_dir:
            avisos.append(f"aviso: getServices() contiene la entrada '{clave}' con directory '{dir_j}', pero la carpeta no existe.")
        else:
            esp = esperadas_por_dir[dir_j]
            srv = esp['servicio']
            if name_j != esp['name']:
                bloqueos.append(f"BLOCKED: getServices()['{clave}'].name es '{name_j}', esperado '{esp['name']}' para '{srv}'.")
            if dir_j != esp['directory']:
                bloqueos.append(f"BLOCKED: getServices()['{clave}'].directory es '{dir_j}', esperado '{esp['directory']}' para '{srv}'.")
            if disp_j != esp['displayName']:
                avisos.append(f"aviso: getServices()['{clave}'].displayName es '{disp_j}', esperado '{esp['displayName']}'.")
            if clave != esp['clave']:
                avisos.append(f"aviso: getServices() usa la clave '{clave}' para '{srv}', calculada '{esp['clave']}'.")

    for srv, esp in esperadas_por_servicio.items():
        if esp['directory'] not in directorios_en_jenkins:
            avisos.append(f"aviso: servicio '{srv}' en disco no está registrado en getServices().")

    for b in bloqueos:
        print(b)
    for a in avisos:
        print(a)

    if bloqueos:
        return 1
    if not avisos:
        print(f"OK: getServices() de {ruta_rel} coincide con los servicios en disco.")
    return 0


def cmd_validar_gateway(raiz, argv=None):
    data = stack_local(raiz)
    gw = data.get('backend', {}).get('gateway')
    if not gw or str(gw).strip() == "" or str(gw) == "null":
        print("OK: backend.gateway es null; sin gateway que validar.")
        return 0
    gw = str(gw).strip()

    gw_dir = os.path.join(raiz, gw)
    if not os.path.isdir(gw_dir):
        print(f"aviso: la carpeta del gateway '{gw}' no existe en disco.", file=sys.stderr)
        return 2

    if argv and len(argv) > 0:
        ruta_gw_config = argv[0] if os.path.isabs(argv[0]) else os.path.join(raiz, argv[0])
    else:
        ruta_gw_config = None
        for r, _, files in os.walk(os.path.join(gw_dir, "src", "main", "java")):
            if "GatewayConfig.java" in files:
                ruta_gw_config = os.path.join(r, "GatewayConfig.java")
                break

    if not ruta_gw_config or not os.path.isfile(ruta_gw_config):
        rel = os.path.relpath(ruta_gw_config, raiz) if ruta_gw_config else f"{gw}/.../GatewayConfig.java"
        print(f"aviso: no se encontró GatewayConfig.java en '{rel}'.", file=sys.stderr)
        return 2

    ruta_rel = os.path.relpath(ruta_gw_config, raiz)
    try:
        contenido = leer_publico(raiz, ruta_rel)
    except (OSError, NombresError):
        print('aviso: GatewayConfig.java fuera de alcance o ilegible.', file=sys.stderr)
        return 2

    # Parsear bloques .route(...) con balanceo exacto de paréntesis respetando strings y comentarios
    rutas = []
    pos = 0
    while True:
        m_r = re.search(r'\.route\s*\(', contenido[pos:])
        if not m_r:
            break
        start_route = pos + m_r.start()
        start_paren = start_route + len(m_r.group(0)) - 1  # índice del '(' de .route(

        depth = 1
        i = start_paren + 1
        en_comentario_linea = False
        en_comentario_bloque = False
        en_string_doble = False
        en_string_simple = False
        escape = False

        while i < len(contenido) and depth > 0:
            ch = contenido[i]
            if en_comentario_linea:
                if ch == '\n':
                    en_comentario_linea = False
            elif en_comentario_bloque:
                if ch == '*' and i + 1 < len(contenido) and contenido[i+1] == '/':
                    en_comentario_bloque = False
                    i += 1
            elif en_string_doble:
                if escape:
                    escape = False
                elif ch == '\\':
                    escape = True
                elif ch == '"':
                    en_string_doble = False
            elif en_string_simple:
                if escape:
                    escape = False
                elif ch == '\\':
                    escape = True
                elif ch == "'":
                    en_string_simple = False
            else:
                if ch == '/' and i + 1 < len(contenido):
                    if contenido[i+1] == '/':
                        en_comentario_linea = True
                        i += 1
                    elif contenido[i+1] == '*':
                        en_comentario_bloque = True
                        i += 1
                elif ch == '"':
                    en_string_doble = True
                elif ch == "'":
                    en_string_simple = True
                elif ch == '(':
                    depth += 1
                elif ch == ')':
                    depth -= 1
            i += 1

        if depth != 0:
            break

        end_route = i
        raw_full = contenido[start_route:end_route]
        pos = end_route

        # Extraer ID de la ruta: .route("<id>", ...
        m_id = re.search(r'^\.route\s*\(\s*["\']([^"\']+)["\']', raw_full)
        if not m_id:
            continue
        route_id = m_id.group(1).strip()

        # Extraer path
        m_p = re.search(r'\.path\(\s*["\']([^"\']+)["\']\s*\)', raw_full)
        path_val = m_p.group(1).strip() if m_p else None

        # uri con extracción balanceada de paréntesis dentro de raw_full
        uri_raw = ""
        idx_u = raw_full.find(".uri(")
        if idx_u != -1:
            start_u = idx_u + len(".uri(")
            depth_u = 1
            i_u = start_u
            while i_u < len(raw_full) and depth_u > 0:
                if raw_full[i_u] == '(':
                    depth_u += 1
                elif raw_full[i_u] == ')':
                    depth_u -= 1
                i_u += 1
            uri_raw = raw_full[start_u:i_u-1].strip()

        # X-Gateway con extracción balanceada dentro de raw_full
        xgw_raw = ""
        pos_x = 0
        while True:
            idx_x = raw_full.find(".addRequestHeader(", pos_x)
            if idx_x == -1:
                break
            start_x = idx_x + len(".addRequestHeader(")
            depth_x = 1
            i_x = start_x
            while i_x < len(raw_full) and depth_x > 0:
                if raw_full[i_x] == '(':
                    depth_x += 1
                elif raw_full[i_x] == ')':
                    depth_x -= 1
                i_x += 1
            call_args = raw_full[start_x:i_x-1].strip()
            pos_x = i_x
            # Dividir argumentos de primer nivel
            parts = []
            curr = []
            d = 0
            for ch in call_args:
                if ch == '(':
                    d += 1
                elif ch == ')':
                    d -= 1
                elif ch == ',' and d == 0:
                    parts.append("".join(curr).strip())
                    curr = []
                    continue
                curr.append(ch)
            if curr:
                parts.append("".join(curr).strip())
            if len(parts) >= 2 and ("X_GATEWAY" in parts[0] or "X-Gateway" in parts[0]):
                xgw_raw = parts[1].strip()
                break

        base_lb = None
        m_lb = re.search(r'lb://([A-Za-z0-9_-]+)-', uri_raw)
        if m_lb:
            base_lb = m_lb.group(1)

        rutas.append({
            'id': route_id,
            'raw': raw_full,
            'path': path_val,
            'uri_raw': uri_raw,
            'xgw_raw': xgw_raw,
            'base_lb': base_lb,
        })

    if not rutas:
        print(f"aviso: no se pudo leer GatewayConfig.java de {ruta_rel}; "
              f"formato esperado: RouteLocator con builder.routes().route(...)...build().", file=sys.stderr)
        return 2

    infra = data.get('devops', {}).get('infraestructura')

    identidades = calcular_nombres(raiz)
    microservicios = {item['servicio']: item for item in identidades if item['servicio'] != gw}
    por_base = {item['base']: item for item in microservicios.values()}
    incoherencias, avisos, cubiertos = [], [], set()
    for ruta in rutas:
        route_id = ruta['id']
        base_id = route_id[:-len('-service-route')] if route_id.endswith('-service-route') else None
        base_lb = ruta['base_lb']
        if infra == 'jenkins-kubernetes' and 'lb://' in ruta['uri_raw']:
            # Solo una URI con el sufijo dinámico y entornos declarados participa
            # en la comparación de identidades. Una URI sin sufijo no es otro servicio.
            sufijos = {cfg.get('sufijo') for cfg in data.get('devops', {}).get('entornos', {}).values() if isinstance(cfg, dict)}
            patron = r'^["\']lb://([A-Za-z0-9_-]+)-["\']\s*\+\s*properties[.]sufijo\(\)\s*\+\s*["\']-service["\']$'
            dinamica = re.fullmatch(patron, ruta['uri_raw'])
            if not dinamica or not any(isinstance(s, str) and s for s in sufijos):
                incoherencias.append('incoherencia: ruta ' + route_id + ': lb:// sin sufijo de entorno; usa properties.sufijo() y un entorno declarado')
                base_lb = None
            else:
                base_lb = dinamica[1]
        por_id, por_lb = por_base.get(base_id), por_base.get(base_lb)
        if por_id and por_lb and por_id['servicio'] != por_lb['servicio']:
            incoherencias.append('incoherencia: id y lb:// identifican servicios distintos en ruta ' + route_id)
            continue
        item = por_lb or por_id
        if item is None:
            avisos.append('aviso: ruta ' + route_id + ' no casa por id/lb:// con ninguna base de servicio en disco.')
            continue
        service, base, cp = item['servicio'], item['base'], item['context_path']
        if service in cubiertos:
            incoherencias.append('incoherencia: varias rutas para el servicio ' + service)
        cubiertos.add(service)
        motivos = []
        if route_id != base + '-service-route': motivos.append('id esperado ' + base + '-service-route')
        esperado = cp.rstrip('/') + '/**' if cp is not None else None
        if esperado is None: motivos.append('context-path no determinable; debe aprobarse en el plan')
        elif ruta['path'] != esperado: motivos.append('path esperado ' + esperado)
        if infra == 'jenkins-kubernetes':
            uri = '"lb://' + base + '-" + properties.sufijo() + "-service"'
            cabecera = '"api-' + base + '-" + properties.sufijo()'
            if re.sub(r'\s+', '', ruta['uri_raw']) != re.sub(r'\s+', '', uri): motivos.append('uri esperada ' + uri)
        else:
            puerto = puerto_efectivo(raiz, service, data.get('backend', {}).get('perfil_local') or 'feature')
            uri = '"http://localhost:' + str(puerto) + '"'
            cabecera = '"api-' + base + '-' + (data.get('backend', {}).get('perfil_local') or 'feature') + '"'
            if puerto is None or ruta['uri_raw'] != uri: motivos.append('uri local esperada ' + uri)
        if ruta['xgw_raw'] and re.sub(r'\s+', '', ruta['xgw_raw']) != re.sub(r'\s+', '', cabecera): motivos.append('X-Gateway esperado ' + cabecera)
        if motivos:
            incoherencias.append('incoherencia: ruta ' + route_id + ' -> servicio ' + service + ' (base ' + base + '): ' + '; '.join(motivos))
    for service, item in microservicios.items():
        if service not in cubiertos: avisos.append('aviso: servicio ' + service + ' (base ' + item['base'] + ') no tiene ruta en GatewayConfig.java.')

    # Comprobación de GatewayProperties y firma de myRoutes en el gateway
    if infra == 'jenkins-kubernetes':
        tiene_properties_file = False
        for r_dir, _, files in os.walk(os.path.join(gw_dir, "src", "main", "java")):
            if "GatewayProperties.java" in files:
                tiene_properties_file = True
                break
        tiene_sufijo_yaml = False
        res_dir = os.path.join(gw_dir, 'src', 'main', 'resources')
        if os.path.isdir(res_dir):
            for f in sorted(os.listdir(res_dir)):
                if not re.fullmatch(r'application(?:-[\w-]+)?\.(?:yaml|yml)', f): continue
                padres = []
                with open(os.path.join(res_dir, f), encoding='utf-8') as stream:
                    for line in stream:
                        m = re.match(r'^(\s*)([\w.-]+):', line)
                        if not m: continue
                        indent, key = len(m[1]), m[2]
                        while padres and padres[-1][0] >= indent: padres.pop()
                        if [k for _, k in padres] + [key] == ['gateway', 'sufijo']: tiene_sufijo_yaml = True
                        padres.append((indent,key))
        tiene_firma_properties = bool(
            re.search(r'RouteLocator\s+myRoutes\s*\([^)]*GatewayProperties\s+properties[^)]*\)', contenido)
        )
        if not tiene_properties_file or not tiene_sufijo_yaml or not tiene_firma_properties:
            partes = []
            if not tiene_properties_file:
                partes.append("GatewayProperties")
            if not tiene_sufijo_yaml:
                partes.append("gateway.sufijo en sus perfiles")
            detalle = " ni ".join(partes) if partes else ""
            if not tiene_firma_properties:
                if detalle:
                    avisos.append(
                        f"aviso: el gateway no tiene {detalle}; además myRoutes no recibe GatewayProperties. "
                        f"El plan debe incluir GatewayProperties, la propiedad gateway.sufijo por perfil "
                        f"(desde las plantillas de service-creator) y cambiar la firma a "
                        f"myRoutes(RouteLocatorBuilder builder, GatewayProperties properties) en el mismo diff."
                    )
                else:
                    avisos.append(
                        "aviso: myRoutes no recibe GatewayProperties; el plan debe cambiar la firma a "
                        "myRoutes(RouteLocatorBuilder builder, GatewayProperties properties) en el mismo diff, "
                        "además de GatewayProperties y gateway.sufijo por perfil."
                    )
            else:
                avisos.append(
                    f"aviso: el gateway no tiene {detalle}; el plan debe incluir GatewayProperties y la propiedad "
                    f"gateway.sufijo (desde las plantillas de service-creator) en el mismo diff."
                )

    # Imprimir resultados
    for inc in incoherencias:
        print(inc)
    for a in avisos:
        print(a)

    if incoherencias or avisos:
        return 1
    print(f"OK: todas las rutas del gateway ({len(rutas)}) coinciden con base, context-path y destino de los servicios.")
    return 0

def _perfil_activo_info(raiz, servicio):
    configs = configuraciones(raiz, servicio)
    activos_literal = None
    activos_variable = False
    activos_presente = False
    for archivo, filas in configs:
        if perfil_de_archivo(archivo) is not None:
            continue
        for fila in filas:
            if fila.get("activos_presente"):
                activos_presente = True
            if fila.get("activos_variable"):
                activos_variable = True
                activos_presente = True
            if "activos" in fila and not fila.get("activos_variable"):
                activos_literal = str(fila["activos"])
                activos_presente = True
    if activos_variable:
        return None, True, True, []
    if not activos_presente or activos_literal is None:
        return None, False, activos_presente, []
    # soporta 'a,b' y '[a,b]'
    bruto = activos_literal.strip()
    if bruto.startswith('[') and bruto.endswith(']'):
        bruto = bruto[1:-1]
    nombres = [x.strip() for x in bruto.split(',') if x.strip()]
    return activos_literal, False, True, nombres


def _variables_para_perfil(raiz, servicio, perfil):
    nombres = {}
    for archivo, filas in configuraciones(raiz, servicio):
        pf = perfil_de_archivo(archivo)
        if pf not in (None, perfil):
            continue
        for fila in filas:
            for nombre, _, _ in fila.get('variables', []):
                nombres[nombre] = True
    return sorted(nombres.keys())



# Rutas públicas exactas: ningún llamador puede ampliar esta proyección.
RUTAS_YAML = frozenset({
    'spring.security.oauth2.resourceserver.jwt.issuer-uri',
    'gateway.cors-origenes',
    'spring.jpa.hibernate.naming.physical-strategy',
})


def _yaml_entradas(lines):
    """Solo estructura y posiciones; no conserva valores de hojas ajenas."""
    parents = []
    for n, line in enumerate(lines):
        m = re.match(r'^( *)([A-Za-z0-9_.-]+):(?:\s+(.*))?$', line)
        if not m:
            continue
        indent, key = len(m[1]), m[2]
        while parents and parents[-1][0] >= indent:
            parents.pop()
        path = '.'.join([k for _, k in parents] + [key])
        yield path, n, indent
        parents.append((indent, key))


def _yaml_valor(lines, n, indent):
    def scalar(raw):
        # Nunca exportar respaldos de variables, tampoco en rutas permitidas.
        raw = re.sub(r'\$\{([A-Za-z_][A-Za-z0-9_]*)(?::[^}]*)?\}', r'${\1}', raw)
        quote = None
        end = len(raw)
        for i, char in enumerate(raw):
            if char in ('"', "'"):
                quote = None if quote == char else char if quote is None else quote
            elif char == '#' and quote is None and (i == 0 or raw[i-1].isspace()):
                end = i; break
        return raw[:end].strip().strip('"').strip("'")
    raw = lines[n].split(':', 1)[1].strip()
    if not raw or raw.startswith('#'):
        items = []
        for line in lines[n+1:]:
            if not line.strip() or line.lstrip().startswith('#'):
                continue
            mi = re.match(r'^( *)-\s+(.*)$', line)
            if mi and len(mi[1]) >= indent:
                items.append(scalar(mi[2]))
            else:
                break
        return items or None
    if raw.startswith('[') and raw.endswith(']'):
        return [scalar(x) for x in re.split(r',\s*(?=(?:[^\"\']*[\"\'][^\"\']*[\"\'])*[^\"\']*$)', raw[1:-1]) if x.strip()]
    return scalar(raw)


def rutas_yaml_servicio(raiz, servicio, rutas):
    # Validar ANTES de resolver el servicio, listar o abrir un archivo.
    if not rutas or any(r not in RUTAS_YAML for r in rutas):
        raise ValueError('ruta YAML no permitida; solo se admiten las tres rutas públicas de RUTAS_YAML')
    if servicio not in servicios(raiz):
        raise ValueError('servicio inexistente')
    res = os.path.join(raiz, servicio, 'src/main/resources')
    out = []
    if not os.path.isdir(res):
        return out
    for nombre in sorted(os.listdir(res)):
        if not re.fullmatch(r'application(?:-[\w-]+)?\.(?:yaml|yml)', nombre):
            continue
        archivo = os.path.join(res, nombre)
        if not os.path.realpath(archivo).startswith(os.path.realpath(res) + os.sep):
            raise ValueError('archivo YAML fuera del servicio')
        with open(archivo, encoding='utf-8', errors='replace') as fh:
            lines = fh.read().splitlines()
        starts = [0] + [i+1 for i,l in enumerate(lines) if l.strip() == '---']
        for start, end in zip(starts, starts[1:] + [len(lines)+1]):
            doc = lines[start:end-1]
            entries = list(_yaml_entradas(doc))
            activate = any(k == 'spring.config.activate' or k.startswith('spring.config.activate.') for k,_,_ in entries)
            k8s = any(k == 'spring.config.activate.on-profile' and _yaml_valor(doc,n,i) == 'k8s' for k,n,i in entries)
            kind = 'k8s' if k8s and nombre not in ('application.yaml','application.yml') else 'base' if not activate and nombre in ('application.yaml','application.yml') else 'otro'
            for key,n,indent in entries:
                if key in rutas:
                    value = _yaml_valor(doc,n,indent)
                    if value is not None:
                        out.append({'archivo': os.path.relpath(archivo,raiz), 'documento': kind,
                                    'linea': start+n+1, 'ruta': key, 'valor': value})
    return out


def cmd_rutas_yaml(raiz, argv_rest=None):
    if not argv_rest or len(argv_rest) != 2:
        print('Uso: servicios.py rutas-yaml <servicio> <ruta[,ruta]> ', file=sys.stderr)
        return 2
    try:
        result = rutas_yaml_servicio(raiz, argv_rest[0], argv_rest[1].split(','))
    except (ValueError, OSError) as error:
        print('ERROR: ' + str(error), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def cmd_perfiles(raiz, argv_rest=None):
    lista = servicios(raiz)
    if not lista:
        fail("no hay carpetas de servicio (build.gradle + settings.gradle) en el primer nivel")
    objetivo = lista
    if argv_rest:
        if len(argv_rest) != 1:
            print(__doc__)
            return 2
        sname = argv_rest[0]
        if sname not in lista:
            print(f"ERROR: el servicio '{sname}' no existe en {raiz}", file=sys.stderr)
            return 1
        objetivo = [sname]
    salida = []
    data = stack_local(raiz)
    backend = data.get('backend', {}) if isinstance(data.get('backend'), dict) else {}
    perfil_local = backend.get('perfil_local') or 'feature'
    devops = data.get('devops', {}) if isinstance(data.get('devops'), dict) else {}
    esperados_base = [perfil_local]
    if devops.get('infraestructura') == 'jenkins-kubernetes':
        for cfg in (devops.get('entornos') or {}).values():
            if isinstance(cfg, dict) and cfg.get('sufijo'):
                if cfg['sufijo'] not in esperados_base:
                    esperados_base.append(cfg['sufijo'])
    for sname in objetivo:
        activo_literal, activo_variable, activo_presente, perfiles_nombres = _perfil_activo_info(raiz, sname)
        perfiles = []
        avisos = []
        esperados = list(esperados_base)
        faltan = []
        res_dir = os.path.join(raiz, sname, 'src', 'main', 'resources')
        if not os.path.isdir(res_dir):
            avisos.append('sin src/main/resources/')
        # perfil local entry
        def existe_perfil(nombre):
            for ext in ('yaml', 'yml', 'properties'):
                p = os.path.join(res_dir, f'application-{nombre}.{ext}')
                if os.path.isfile(p):
                    return os.path.relpath(p, raiz), True
            return os.path.join(sname, 'src', 'main', 'resources', f'application-{nombre}.yaml'), False
        if activo_variable:
            avisos.append('perfil activo por variable de entorno: no determinable')
        # build perfiles list for esperados
        for nombre in esperados:
            esperado, existe = existe_perfil(nombre)
            perfiles.append({
                'nombre': nombre,
                'archivo_esperado': esperado,
                'existe': existe,
                'variables': _variables_para_perfil(raiz, sname, nombre),
            })
            if not existe:
                faltan.append(nombre)
        if not activo_variable and perfiles_nombres and perfil_local not in perfiles_nombres:
            avisos.append(f'perfil activo {perfiles_nombres} difiere de backend.perfil_local {perfil_local}')
        # if no active profile declared, still check files but avisar
        if not activo_presente and not activo_variable:
            avisos.append('application.yaml sin spring.profiles.active declarado')
        aviso_test = []
        test_res = os.path.join(raiz, sname, 'src', 'test', 'resources')
        if os.path.isdir(test_res):
            for archivo in sorted(os.listdir(test_res)):
                if re.fullmatch(r'application(?:-[\w-]+)?\.(?:yaml|yml|properties)', archivo):
                    aviso_test.append(archivo)
        item = {
            'servicio': sname,
            'perfil_local': perfil_local,
            'perfil_activo': [] if activo_variable else perfiles_nombres,
            'activos_variable': activo_variable,
            'esperados': esperados,
            'faltan': faltan,
            'perfiles': perfiles,
            'aviso_test_resources': aviso_test,
            'avisos': avisos,
        }
        salida.append(item)
    print(json.dumps(salida, ensure_ascii=False, indent=2))
    return 0

# Identidad pública: base = rootProject.name sin un -service final; context-path
# propuesto para servicios nuevos = /base; paquete = group.base sin guiones;
# {AliasPascal} = base en PascalCase. Nunca se deriva identidad desde la carpeta.
class NombresError(ValueError):
    """Diagnóstico público, sin contenido de archivos de propiedades."""


def leer_publico(raiz, relativa):
    root = Path(raiz).resolve()
    ruta = root / relativa
    if not ruta.resolve().is_relative_to(root) or any(x == 'account' or x.startswith('.env') for x in ruta.resolve().parts):
        raise NombresError('ruta pública fuera del alcance permitido')
    return ruta.read_text(encoding='utf-8')


def ruta_propiedades(raiz, servicio):
    root = Path(raiz).resolve()
    ruta = root / servicio / 'gradle.properties'
    if not ruta.resolve().is_relative_to(root) or any(x == 'account' or x.startswith('.env') for x in ruta.resolve().parts):
        raise NombresError('gradle.properties fuera del repositorio o del alcance permitido')
    return ruta


def propiedades_permitidas(raiz, servicio):
    """Solo proyecta dos claves; recorre continuaciones opacas sin guardar su contenido."""
    ruta = ruta_propiedades(raiz, servicio)
    if not ruta.exists():
        return {}
    permitidas = re.compile(rb'^\s*(org[.]gradle[.]java[.]installations[.]paths|systemProp[.]sonar[.]projectKey)(?:[ \t\f]*[=:][ \t\f]*|[ \t\f]+)(.*)$')
    claves = (b'org.gradle.java.installations.paths', b'systemProp.sonar.projectKey')
    result, continuada = {}, False
    with ruta.open('rb') as stream:
        for numero, linea in enumerate(stream, 1):
            raw = linea.rstrip(b'\r\n')
            sigue = (len(raw) - len(raw.rstrip(b'\\'))) % 2 == 1
            if continuada:
                continuada = sigue
                continue
            if not raw.strip() or raw.lstrip().startswith((b'#', b'!')):
                continue
            continuada = sigue
            m = permitidas.fullmatch(raw)
            if m:
                key = m[1].decode('ascii')
                result.setdefault(key, []).append({'valor': m[2].decode('utf-8').strip(),
                    'linea': numero, 'continuada': sigue, 'malformada': False})
            else:
                for clave in claves:
                    if raw.lstrip().startswith(clave):
                        result.setdefault(clave.decode('ascii'), []).append({'valor': None,
                            'linea': numero, 'continuada': sigue, 'malformada': True})
    return result


def codigo_gradle(texto):
    """Elimina comentarios preservando cadenas y números de línea."""
    tokens = r'''"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|/\*[\s\S]*?\*/|//[^\n]*'''
    return re.sub(tokens, lambda m: re.sub(r'[^\n]', ' ', m[0])
                  if m[0].startswith(('/*', '//')) else m[0], texto)


def enmascarar_cadenas(texto):
    strings = r'''"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*' '''.strip()
    return re.sub(strings, lambda m: ' ' * len(m[0]), texto)


def gradle_primer_nivel(texto):
    texto = codigo_gradle(texto)
    masked = enmascarar_cadenas(texto)
    depth = 0
    salida = []
    for char, visible in zip(texto, masked):
        salida.append(char if depth == 0 or char == "\n" else " ")
        if visible == "{": depth += 1
        elif visible == "}": depth -= 1
        if depth < 0: raise NombresError("llaves de build.gradle no balanceadas")
    if depth: raise NombresError("llaves de build.gradle no balanceadas")
    return "".join(salida)


def bloques_publicos(texto, patron):
    """Cuerpos con llaves balanceadas; ignora llaves dentro de cadenas y comentarios."""
    texto = codigo_gradle(texto)
    masked = enmascarar_cadenas(texto)
    salida = []
    for m in re.finditer(patron, masked):
        start = m.end()
        depth, end = 1, start
        while end < len(masked) and depth:
            if masked[end] == '{': depth += 1
            elif masked[end] == '}': depth -= 1
            end += 1
        if depth:
            raise NombresError('bloque público sin cierre determinable')
        salida.append((start, texto[start:end-1]))
    return salida


def _literal_expresion(expresion):
    m = re.fullmatch(r'''\s*(['"])([^'"\n\\]*)\1\s*;?\s*''', expresion)
    if not m or '$' in m[2] or not m[2].strip():
        return None
    return m[2]


def _sonar(raiz, servicio, build, nombre, group, data):
# si devops.infraestructura=jenkins-kubernetes
    jf = data.get('devops', {}).get('jenkinsfile')
    if jf and data.get('devops', {}).get('infraestructura') == 'jenkins-kubernetes':
        path = Path(raiz) / jf
        if path.is_file() and re.search(r'-Dsonar[.]projectKey(?:=|\s|$)', codigo_gradle(leer_publico(raiz, jf))):
            return None, 'no_determinable', '-Dsonar.projectKey en el Jenkinsfile'
# fin
    props = propiedades_permitidas(raiz, servicio).get('systemProp.sonar.projectKey', [])
    if props:
        if len(props) != 1 or props[0]['continuada'] or props[0]['malformada']:
            return None, 'no_determinable', 'systemProp.sonar.projectKey duplicada, continuada o con formato no soportado'
        val = props[0]['valor']
        if not re.fullmatch(r'[A-Za-z0-9_.:-]+', val):
            return None, 'no_determinable', 'systemProp.sonar.projectKey no literal o no soportada'
        return val, 'gradle.properties', None
    vals = []
    for _, body in bloques_publicos(build, r'\b(?:sonar|sonarqube)\s*\{'):
        reconocidos = []
        for m in re.finditer(r'''\bproperty\s*(\(\s*)?(['"])sonar[.]projectKey\2\s*,\s*([^\n}]*)''', body):
            reconocidos.append(m.span())
            exp = m[3].strip()
            if m[1]:
                if not exp.endswith(')') and not exp.endswith(');'):
                    return None, 'no_determinable', 'sonar.projectKey no literal en build.gradle'
                exp = re.sub(r'\)\s*;?$', '', exp)
            val = _literal_expresion(exp)
            if val is None:
                return None, 'no_determinable', 'sonar.projectKey no literal en build.gradle'
            vals.append(val)
        resto = body
        for start, end in reversed(reconocidos): resto = resto[:start] + ' ' * (end-start) + resto[end:]
        if 'sonar.projectKey' in resto:
            return None, 'no_determinable', 'sonar.projectKey en una forma no soportada en build.gradle'
    if vals:
        if len(vals) != 1:
            return None, 'no_determinable', 'sonar.projectKey con varias asignaciones en build.gradle'
        return vals[0], 'build.gradle', None
    if re.search(r'^\s*group\s*(?:=|\s)', gradle_primer_nivel(build), re.M) and group is None:
        return None, 'no_determinable', 'group no literal en build.gradle'
    return (group + ':' + nombre, 'group:nombre', None) if group else (nombre, 'nombre', None)


# si devops.infraestructura=jenkins-kubernetes
def _nombres_entorno(servicio, nombre, base, cp, data, env, cfg, gateway, con_base, puerto):
    sufijo = cfg['sufijo']; pref = base + '-' + sufijo
    despliega = cfg.get('desplegar') is True
    carpeta = 'devops/' + env
    dest = carpeta + '/' + servicio
    files = {'jenkinsfile': data['devops']['jenkinsfile'], 'dockerfile': servicio + '/Dockerfile',
        'deployment': dest + '/deployment-' + base + '.yaml', 'service': dest + '/service-' + base + '.yaml',
        'pv': dest + '/persistence-volume.yaml' if con_base else None,
        'pvc': dest + '/persistence-volume-claim.yaml' if con_base else None,
        'secret_base': carpeta + '/account/secrets-' + pref + '.yaml' if con_base else None,
        'cuenta_jenkins': carpeta + '/account/jenkins-account.yaml',
        'secret_jenkins': carpeta + '/account/secrets-jenkins-account.yaml',
        'rbac': carpeta + '/account/rbac.yaml' if gateway else None}
    rec = {'deployment': pref + '-deployment', 'service': pref + '-service',
        'pv': pref + '-volume' if con_base else None, 'pvc': pref + '-claim' if con_base else None,
        'contenedor': pref + '-service-container', 'secret_base': pref + '-service-db-secret' if con_base else None,
        'volumen_pod': base + '-volume' if con_base else None,
        'host_path': '/mnt/data/' + pref if con_base else None, 'mount_path': '/app/logs' if con_base else None,
        'app': pref, 'environment': env, 'namespace': 'default',
        'usage_purpose': pref + '-log-storage' if con_base else None, 'puerto_nombre': pref + '-port',
        'imagen': data['devops']['registry'] + '/' + nombre,
        'spring_application_name': nombre + '-' + sufijo, 'spring_profiles_active': 'docker,k8s,' + sufijo,
        'variables_base': [key + '_' + sufijo.upper() for key in ('DB_HOST','DB_PORT','DB_NAME','USER_NAME_DB','PASSWORD_DB')] if con_base else [],
        'jenkins_cuenta': 'jenkins', 'jenkins_role': 'jenkins', 'jenkins_role_binding': 'jenkins',
        'jenkins_cluster_role': 'jenkinsclusterrole', 'jenkins_cluster_role_binding': 'jenkins-crb',
        'jenkins_secret': 'jenkins-token',
        'discovery_cuenta': 'discovery-service-account' if gateway else None,
        'discovery_cluster_role': 'discovery-cluster-role' if gateway else None,
        'discovery_cluster_role_binding': 'discovery-cluster-role-binding' if gateway else None}
    node = cfg.get('gateway_nodo_puerto') if gateway else (cfg.get('nodo_puerto_base', 0) + puerto - 8080 if puerto is not None and cfg.get('nodo_puerto_base') is not None else None)
    red = {'puerto': puerto, 'node_port': node, 'health_path': '/actuator/health' if gateway else (cp.rstrip('/') + '/actuator/health' if cp is not None else None)}
    ruta = None if gateway else {'id': base + '-service-route', 'uri': 'lb://' + pref + '-service',
        'path': cp.rstrip('/') + '/**' if cp is not None else None, 'x_gateway': 'api-' + pref}
    if not despliega:
        files = {k: v if k in ('jenkinsfile','dockerfile') else None for k,v in files.items()}
        rec = {k: v if k == 'imagen' else None for k,v in rec.items()}
        red = ruta = None
    return {'sufijo': sufijo, 'desplegar': despliega, 'archivos': files, 'recursos': rec, 'red': red, 'ruta_gateway': ruta}


# fin

def calcular_nombres(raiz, servicio=None, entorno=None):
    lista = servicios(raiz)
    if not lista:
        raise NombresError('no hay carpetas de servicio (build.gradle + settings.gradle) en el primer nivel')
    if servicio is not None and servicio not in lista:
        raise NombresError('servicio solicitado inexistente')
    data = stack_local(raiz)
    devops = data.get('devops', {}).get('infraestructura') == 'jenkins-kubernetes'
    mapa = data.get('devops', {}).get('entornos', {}) if devops else {}
    if entorno is not None and entorno not in mapa:
        raise NombresError('entorno solicitado inexistente o sin Jenkins y Kubernetes')
    result, bases = [], {}
    for s in lista:
        settings = codigo_gradle(leer_publico(raiz, s + '/settings.gradle'))
        roots = re.findall(r'^\s*rootProject[.]name\s*=\s*(.*)$', settings, re.M)
        nombre = _literal_expresion(roots[0]) if len(roots) == 1 else None
        if nombre is None or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', nombre):
            raise NombresError(s + '/settings.gradle: rootProject.name no determinable')
        base = base_desde_nombre(nombre)
        if not base: raise NombresError(s + ': base vacía')
        if base in bases:
            raise NombresError('base duplicada ' + base + ': ' + bases[base] + ' y ' + s)
        bases[base] = s
        build = codigo_gradle(leer_publico(raiz, s + '/build.gradle'))
        nivel_cero = gradle_primer_nivel(build)
        groups = re.findall(r'^\s*group\s*=?\s+(.+)$|^\s*group\s*=\s*(.+)$', nivel_cero, re.M)
        group = _literal_expresion(next(x for x in groups[0] if x)) if len(groups) == 1 else None
        jar_aviso = None
        try:
            entry = _calcular_entrada_jenkins_uno(raiz, s)
        except _JenkinsEntradaError as error:
            if devops: raise NombresError(str(error)) from None
            entry = {'name': None}
            jar_aviso = {'codigo': 'NOMBRE_SERVICIO', 'motivo': 'JAR no determinable estáticamente; sin DevOps no impide calcular nombres'}
        versions = re.findall(r'^\s*version\s*=?\s+(.+)$|^\s*version\s*=\s*(.+)$', nivel_cero, re.M)
        version = _literal_expresion(next(x for x in versions[0] if x)) if len(versions) == 1 else None
        jar = entry['name'] + '-' + version + '.jar' if version and entry['name'] else None
        cps = context_paths(raiz, s)
        gateway = s == data.get('backend', {}).get('gateway')
        cp = cps[0] if len(cps) == 1 else ('' if gateway and not cps else None)
        avisos = [jar_aviso] if jar_aviso else []
        if not nombre.endswith('-service'):
            avisos.append({'codigo':'NOMBRE_SERVICIO','motivo':'rootProject.name no termina en -service'})
        if cp is not None and cp and base != cp.lstrip('/'):
            avisos.append({'codigo':'NOMBRE_SERVICIO','motivo':'la base ' + base + ' difiere del context-path ' + cp})
        if devops and entry['name'] != nombre:
            avisos.append({'codigo':'NOMBRE_JAR','motivo':'nombre de artefacto ' + entry['name'] + ' distinto de rootProject.name ' + nombre})
        sonar, origen, motivo = _sonar(raiz, s, build, nombre, group, data)
        item = {'servicio':s,'nombre':nombre,'base':base,'group':group,'sonar_clave':sonar,
            'sonar_origen':origen,'sonar_motivo':motivo,'jar':jar,'jar_nombre':entry['name'],
            'context_path':cp,'avisos':avisos}
# si devops.infraestructura=jenkins-kubernetes
        if devops:
            con_base = not gateway and ('spring-boot-starter-data-jpa' in build or 'spring-boot-starter-jdbc' in build)
            item['devops'] = {env: _nombres_entorno(s,nombre,base,cp,data,env,cfg,gateway,con_base,
                puerto_efectivo(raiz,s,cfg['sufijo'])) for env,cfg in sorted(mapa.items()) if entorno is None or env == entorno}
# fin
        result.append(item)
    return [item for item in result if servicio is None or item['servicio'] == servicio]


# si devops.infraestructura=jenkins-kubernetes
def cmd_comprobar_secreto(raiz, args):
    """Comprueba un Secret de devops/<carpeta>/account/ sin mostrar valores. Solo lo ejecuta el usuario."""
    import argparse
    import base64

    print('comprobador del usuario: no lo ejecuta la IA')
    parser = argparse.ArgumentParser(
        prog='servicios.py comprobar-secreto',
        description='Comprobador de Secret para el usuario (no lo ejecuta la IA). Comprueba estado de claves sin mostrar valores.')
    parser.add_argument('ruta', help='Ruta relativa bajo devops/<carpeta>/account/')
    try:
        ns = parser.parse_args(args)
    except SystemExit as exc:
        return 1 if exc.code else 0

    try:
        import yaml
    except ModuleNotFoundError:
        print('falta PyYAML; instálalo tú (`python3 -m pip install --user pyyaml`) y repite con `python3 -B -E`')
        return 1

    class _Loader(yaml.SafeLoader):
        pass

    def _dup_constructor(loader, node, deep=False):
        mapping = {}
        for key_node, value_node in node.value:
            key = loader.construct_object(key_node, deep=deep)
            if key in mapping:
                mark = key_node.start_mark
                raise yaml.constructor.ConstructorError(
                    'while constructing a mapping', node.start_mark,
                    'found duplicate key', mark)
            mapping[key] = loader.construct_object(value_node, deep=deep)
        return mapping

    _Loader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _dup_constructor)

    def yaml_err(exc):
        mark = getattr(exc, 'problem_mark', None)
        if mark is not None:
            line = getattr(mark, 'line', None)
            col = getattr(mark, 'column', None)
            if line is not None and col is not None:
                if 'duplicate key' in str(getattr(exc, 'problem', '') or ''):
                    print(f'ERROR: YAML inválido (clave duplicada) en línea {line + 1}, columna {col + 1}')
                    return 1
                print(f'ERROR: YAML inválido en línea {line + 1}, columna {col + 1}')
                return 1
        print('ERROR: YAML inválido (ubicación no disponible)')
        return 1

    ruta = ns.ruta.replace('\\', '/')
    if os.path.isabs(ns.ruta) or ruta.startswith('/'):
        print('ERROR: ruta no permitida; usa una ruta relativa bajo devops/<carpeta>/account/')
        return 1
    norm = os.path.normpath(ruta)
    if norm != ruta and not (norm == ruta.rstrip('/')):
        norm = os.path.normpath(ruta)
    # rechazar escapes y rutas fuera del patrón
    if norm.startswith('..') or '/..' in ('/' + norm) or '\\' in ns.ruta:
        print('ERROR: ruta no permitida; usa una ruta relativa bajo devops/<carpeta>/account/')
        return 1
    parts = norm.split('/')
    if len(parts) != 4 or parts[0] != 'devops' or parts[2] != 'account' or not parts[1] or not parts[3]:
        print('ERROR: ruta no permitida; usa una ruta relativa bajo devops/<carpeta>/account/')
        return 1
    carpeta = parts[1]
    nombre_archivo = parts[3]
    if nombre_archivo in ('jenkins-account.yaml', 'secrets-jenkins-account.yaml', 'rbac.yaml'):
        print('ERROR: el archivo no corresponde a un secret_base de servicio en ' + carpeta)
        return 1

    data_stack = stack_local(raiz)
    devops = data_stack.get('devops', {}) if isinstance(data_stack, dict) else {}
    if devops.get('infraestructura') != 'jenkins-kubernetes':
        print('ERROR: el proyecto no tiene infraestructura jenkins-kubernetes')
        return 1
    mapa_entornos = devops.get('entornos', {}) if isinstance(devops.get('entornos'), dict) else {}
    if carpeta not in mapa_entornos:
        print('ERROR: entorno/carpeta desconocido: ' + carpeta)
        return 1

    try:
        filas = calcular_nombres(raiz, None, carpeta)
    except Exception:
        print('ERROR: no se pudo resolver la configuración pública del entorno')
        return 1

    candidatos = []
    for item in filas:
        d = item.get('devops') or {}
        env = d.get(carpeta) or {}
        archivos = env.get('archivos') or {}
        recursos = env.get('recursos') or {}
        if env.get('desplegar') is not True:
            continue
        sb = archivos.get('secret_base')
        if sb and sb.replace('\\', '/') == norm:
            candidatos.append((item, env, archivos, recursos))
    if not candidatos:
        # distinguir sin despliegue/gateway de no correspondencia
        hay_env = False
        for item in filas:
            d = item.get('devops') or {}
            env = d.get(carpeta)
            if env is not None:
                hay_env = True
                if env.get('desplegar') is False:
                    continue
        print('ERROR: el archivo no corresponde a un secret_base de servicio desplegable en ' + carpeta)
        return 1
    if len(candidatos) != 1:
        print('ERROR: el archivo no corresponde a un secret_base de servicio desplegable en ' + carpeta)
        return 1

    item, env, archivos, recursos = candidatos[0]
    secret_esperado = recursos.get('secret_base')
    deployment_rel = archivos.get('deployment')
    ruta_abs = os.path.join(raiz, norm)
    if not os.path.exists(ruta_abs) and not os.path.islink(ruta_abs):
        print('ERROR: archivo inexistente: ' + norm)
        return 1

    # claves esperadas desde deployment (público)
    esperadas = set()
    if deployment_rel:
        dep_abs = os.path.join(raiz, deployment_rel)
        try:
            with open(dep_abs, encoding='utf-8') as fh:
                dep_doc = yaml.load(fh, Loader=_Loader) or {}
        except Exception as exc:
            if isinstance(exc, yaml.YAMLError):
                print('ERROR: no se pudo leer el deployment público del servicio')
                return 1
            print('ERROR: no se pudo leer el deployment público del servicio')
            return 1
        def walk(obj):
            if isinstance(obj, dict):
                ref = obj.get('secretKeyRef')
                if isinstance(ref, dict) and ref.get('name') == secret_esperado and 'key' in ref:
                    esperadas.add(str(ref['key']))
                for v in obj.values():
                    walk(v)
            elif isinstance(obj, list):
                for v in obj:
                    walk(v)
        walk(dep_doc)
    if not esperadas:
        print('ERROR: no se pudieron determinar las claves esperadas del deployment')
        return 1

    try:
        with open(ruta_abs, encoding='utf-8') as fh:
            doc = yaml.load(fh, Loader=_Loader)
    except yaml.YAMLError as exc:
        return yaml_err(exc)
    except Exception:
        print('ERROR: no se pudo leer el archivo')
        return 1

    errores = 0
    avisos = 0
    if not isinstance(doc, dict):
        print('ERROR: el Secret no es un objeto YAML válido')
        return 1
    md = doc.get('metadata') or {}
    if not isinstance(md, dict) or md.get('name') != secret_esperado:
        print('ERROR: metadata.name distinto del esperado')
        errores += 1
    tiene_data = 'data' in doc and doc.get('data') is not None
    tiene_string = 'stringData' in doc and doc.get('stringData') is not None
    if tiene_data and tiene_string:
        print('ERROR: no deben coexistir data y stringData; usa solo uno')
        errores += 1
    bloque_nombre = 'stringData' if tiene_string else 'data' if tiene_data else None
    bloque = doc.get(bloque_nombre) if bloque_nombre else {}
    if bloque is None:
        bloque = {}
    if not isinstance(bloque, dict):
        print('ERROR: el bloque de datos no es un mapa')
        errores += 1
        bloque = {}

    def es_utf8_imprimible(b):
        try:
            t = b.decode('utf-8')
        except Exception:
            return False
        return all(ch.isprintable() or ch in '\t\n\r' for ch in t)

    def clasificar(s, es_data):
        if not (len(s) % 4 == 0 and re.fullmatch(r'[A-Za-z0-9+/]+={0,2}', s)):
            return 'no'
        try:
            b = base64.b64decode(s, validate=True)
        except Exception:
            return 'no'
        imprimible = es_utf8_imprimible(b)
        if es_data:
            return 'ok' if imprimible else 'no_imprimible'
        # stringData
        if imprimible and len(s) >= 8:
            return 'fuerte'
        if imprimible and 4 <= len(s) <= 7:
            return 'ambiguo'
        if not imprimible:
            return 'noimp_string'  # texto plano legítimo
        return 'no'

    presentes = set(str(k) for k in bloque.keys())
    for clave in sorted(esperadas):
        if clave not in presentes:
            print('ERROR: falta la clave ' + clave)
            errores += 1
            continue
        val = bloque.get(clave)
        if val is None or (isinstance(val, str) and val.strip() == ''):
            print(clave + ': ERROR vacío; completa el valor')
            errores += 1
            continue
        if not isinstance(val, str):
            print(clave + ': ERROR no es texto; usa texto entre comillas en stringData')
            errores += 1
            continue
        if bloque_nombre == 'stringData':
            c = clasificar(val, False)
            if c == 'fuerte':
                print(clave + ': ERROR parece Base64 bajo stringData; cambia stringData: por data: o pega el texto plano')
                errores += 1
            elif c == 'ambiguo':
                print(clave + ': AVISO valor ambiguo (podría ser texto corto o Base64); revísalo')
                avisos += 1
            else:
                print(clave + ': ok')
        elif bloque_nombre == 'data':
            c = clasificar(val, True)
            if c == 'ok':
                print(clave + ': ok')
            elif c == 'no_imprimible':
                print(clave + ': ERROR no es Base64 imprimible bajo data; cambia a stringData: o codifica en Base64')
                errores += 1
            else:
                print(clave + ': ERROR parece texto plano bajo data; cambia a stringData: o codifica en Base64')
                errores += 1
        else:
            print(clave + ': ERROR falta bloque data o stringData')
            errores += 1
    for clave in sorted(presentes - esperadas):
        print('ERROR: sobra la clave ' + clave)
        errores += 1

    return 1 if errores else 0
# fin


def cmd_nombres(raiz, args):
    import argparse
    parser = argparse.ArgumentParser(prog='servicios.py nombres')
    parser.add_argument('servicio', nargs='?')
    parser.add_argument('--entorno')
    ns = parser.parse_args(args)
    try:
        resultado = calcular_nombres(raiz, ns.servicio, ns.entorno)
    except (NombresError, _JenkinsEntradaError) as error:
        # Los diagnósticos de identidad solo proceden de archivos públicos del build.
        print('ERROR: ' + str(error), file=sys.stderr)
        return 1
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
    return 0


def cmd_escribir_jdk_ruta(raiz, args):
    """Actualiza solo la propiedad aprobada; copia el resto como bytes opacos, sin proyectarlo."""
    import argparse
    import tempfile
    import stat
    parser = argparse.ArgumentParser(prog='servicios.py escribir-jdk-ruta')
    parser.add_argument('servicios', nargs='+')
    ns = parser.parse_args(args)
    if any(s not in servicios(raiz) for s in ns.servicios):
        raise NombresError('servicio solicitado inexistente')
    valor = stack_local(raiz).get('backend', {}).get('jdk_ruta_desarrollo')
    if valor is None:
        print('OK: backend.jdk_ruta_desarrollo es null; no se modifica gradle.properties.')
        return 0
    if not isinstance(valor, str) or not valor.startswith('/') or any(c in valor for c in ',\r\n\0'):
        raise NombresError('backend.jdk_ruta_desarrollo debe ser una sola ruta POSIX absoluta sin comas')
    key = 'org.gradle.java.installations.paths'
    pendientes = []
    for servicio in dict.fromkeys(ns.servicios):
        ruta = ruta_propiedades(raiz, servicio)
        if ruta.is_symlink():
            raise NombresError('no se escribe gradle.properties a través de un enlace simbólico')
        filas = propiedades_permitidas(raiz, servicio).get(key, [])
        if any(f['continuada'] for f in filas):
            raise NombresError(servicio + ': ' + key + ' usa continuación; no se escribe ni se interpreta su contenido')
        if any(f['malformada'] for f in filas):
            raise NombresError(servicio + ': ' + key + ' tiene formato no soportado; no se escribe')
        pendientes.append((servicio, ruta, {f['linea'] for f in filas}))
    # Revisar todos los destinos antes de empezar a escribir. Nunca se guardan líneas
    # ajenas como datos: se copian secuencialmente a la sustitución atómica del archivo.
    for servicio, ruta, numeros in pendientes:
        temporal = None
        try:
            with tempfile.NamedTemporaryFile(mode='wb', dir=ruta.parent, prefix='.jdk-ruta-', delete=False) as dst:
                temporal = Path(dst.name)
                ultimo = b''
                if ruta.exists():
                    with ruta.open('rb') as src:
                        for numero, raw in enumerate(src, 1):
                            if numero in numeros:
                                final = b'\r\n' if raw.endswith(b'\r\n') else b'\n' if raw.endswith(b'\n') else b''
                                dst.write((key + '=' + valor).encode('utf-8') + final)
                            else:
                                dst.write(raw)
                            ultimo = raw[-1:]
                if not numeros:
                    if ultimo and ultimo != b'\n': dst.write(b'\n')
                    dst.write((key + '=' + valor).encode('utf-8') + b'\n')
            if ruta.exists():
                temporal.chmod(stat.S_IMODE(ruta.stat().st_mode))
            os.replace(temporal, ruta)
            print('OK: ' + servicio + '/gradle.properties: ' + key + ' actualizada desde backend.jdk_ruta_desarrollo.')
        finally:
            if temporal is not None and temporal.exists(): temporal.unlink()
    return 0


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    cmd = argv[0]
    if cmd in ('nombres', 'escribir-jdk-ruta'):
        try:
            return (cmd_nombres if cmd == 'nombres' else cmd_escribir_jdk_ruta)(os.getcwd(), argv[1:])
        except NombresError as error:
            print('ERROR: ' + str(error), file=sys.stderr)
            return 1
        except (OSError, ValueError, KeyError, TypeError):
            print('ERROR: nombres no determinables; revisa los archivos públicos del servicio.', file=sys.stderr)
            return 1
    rest = argv[1:]
    commands = {
        'listar': lambda r, _: cmd_listar(r),
        'siguiente-puerto': lambda r, _: cmd_siguiente_puerto(r),
        'variables': lambda r, _: cmd_variables(r),
        'variables-json': lambda r, _: cmd_variables_json(r),
        'entornos': lambda r, _: cmd_entornos(r),
        'validar-entornos': lambda r, _: cmd_validar_entornos(r),
        'entradas-jenkins': lambda r, _: cmd_entradas_jenkins(r),
        'validar-jenkins': lambda r, a: cmd_validar_jenkins(r, a),
        'validar-gateway': lambda r, a: cmd_validar_gateway(r, a),
        'perfiles': lambda r, a: cmd_perfiles(r, a),
        'rutas-yaml': lambda r, a: cmd_rutas_yaml(r, a),
    }
# si devops.infraestructura=jenkins-kubernetes
    commands['comprobar-secreto'] = lambda r, a: cmd_comprobar_secreto(r, a)
# fin
    if cmd not in commands:
        print(__doc__)
        return 2
    con_args = ('validar-jenkins', 'validar-gateway', 'perfiles', 'rutas-yaml')
# si devops.infraestructura=jenkins-kubernetes
    con_args = con_args + ('comprobar-secreto',)
# fin
    if cmd not in con_args and len(rest) > 0:
        print(__doc__)
        return 2
    if cmd in ('validar-jenkins', 'validar-gateway', 'perfiles') and len(rest) > 2:
        print(__doc__)
        return 2
# si devops.infraestructura=jenkins-kubernetes
    if cmd == 'comprobar-secreto' and len(rest) != 1:
        print(__doc__)
        return 2
# fin
    try:
        return commands[cmd](os.getcwd(), rest)
    except NombresError as error:
        print('ERROR: ' + str(error), file=sys.stderr)
        return 1
    except (KeyError, TypeError, ValueError, OSError) as error:
        print('BLOCKED: revisa los parámetros o la configuración pública de perfiles; no se muestran valores.', file=sys.stderr)
        return 1



if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
