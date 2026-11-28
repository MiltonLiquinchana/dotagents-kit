#!/usr/bin/env python3
"""Consultas genéricas de documentación pública, por REST y con citas comprobadas."""
import argparse
from contextlib import contextmanager
import copy
import html
import http.client
import ipaddress
import socket
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from datetime import datetime, timezone
import difflib
import errno
import tempfile
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

try:
    import fcntl
except ImportError:
    fcntl = None

NAME = 'Capacidades de la versión'
OWNER = 'documentacion-versiones-v1'
KEYS = ('url_api', 'variable_password', 'modelo_chat', 'modelo_contexto_grande', 'modelo_transformacion', 'timeout_chat')
TIMEOUT = 30
CONNECTION_TIMEOUT = 5
JOB_TIMEOUT = 180
EMBEDDING_WAIT_TIMEOUT = 600
EMBEDDING_POLL_INTERVAL = 5
# Sonda local con EmbeddingGemma: relacionadas 0.76–0.79; sin relación 0.56.
MINIMUM_VECTOR_SCORE = 0.65


class Blocked(Exception):
    def __init__(self, code, message, http_status=None):
        self.code, self.message, self.http_status = code, message, http_status


def block(code, message, http_status=None):
    raise Blocked(code, message, http_status)


def causa_os(message, error):
    if (isinstance(error, OSError) and error.errno is not None
            and error.strerror is not None):
        return message + f' ({errno.errorcode.get(error.errno, str(error.errno))}: {error.strerror})'
    return message


def comprobar_escritura_registro(root):
    temporary = None
    try:
        try:
            with tempfile.NamedTemporaryFile(dir=root, prefix='.documentacion-',
                                             delete=False) as stream:
                temporary = Path(stream.name)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
    except OSError as error:
        message = causa_os('No se puede escribir en .agents', error)
        block('REGISTRO_SOLO_LECTURA', message +
              '; da a la herramienta permiso de escritura sobre .agents y repite. No se ha cambiado nada.')


def sanear_motivo(value):
    clean = ' '.join(re.sub(r'[\x00-\x1f\x7f-\x9f\u2028\u2029]', ' ', value).split())
    return clean if len(clean) <= 80 else clean[:79] + '…'


@contextmanager
def bloqueo_agents(root):
    if fcntl is None:
        yield
        return
    fd = os.open(root, os.O_RDONLY)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)


def leer_bytes_opcionales(path):
    try:
        return path.read_bytes()
    except FileNotFoundError:
        return None


def huella_bytes(raw):
    return None if raw is None else hashlib.sha256(raw).hexdigest()


def comprobar_huella(path, esperada, code, nombre):
    if huella_bytes(leer_bytes_opcionales(path)) != esperada:
        block(code, f'Otro proceso cambió {nombre}; repite la orden.')


def digest(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def version(value, major=False):
    if not re.fullmatch(r'\d+(?:\.\d+){0,3}(?:[-+][\w.-]+)?', str(value)):
        block('VERSION', 'Indica una versión concreta, sin rangos.')
    parts = str(value).split('-')[0].split('+')[0].split('.')
    if not major and len(parts) < 2:
        block('VERSION', 'Esta tecnología necesita major.minor como mínimo.')
    return '.'.join(parts[:1 if major else 2])


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        block('REDIRECCION', 'La API redirige; revisa su dirección sin reenviar credenciales.')


class Parser(argparse.ArgumentParser):
    def error(self, message):
        block('ARGUMENTOS', 'Revisa los argumentos del subcomando; no se muestran sus valores.')


SOURCE_TYPES = ('referencia', 'migracion', 'notas', 'requisitos')
BOOT_BOM = 'org.springframework.boot:spring-boot-dependencies'
CLOUD_BOM = 'org.springframework.cloud:spring-cloud-dependencies'
BOMS_ADMITIDAS = {bom: tuple(bom.split(':')) for bom in (BOOT_BOM, CLOUD_BOM)}
MAX_SOURCE_BYTES = 10 * 1024 * 1024


def url_pom_bom(bom, bom_version):
    group, artifact = BOMS_ADMITIDAS[bom]
    version(bom_version)
    return f'https://repo1.maven.org/maven2/{group.replace(".", "/")}/{artifact}/{bom_version}/{artifact}-{bom_version}.pom'


def normalizar_cita(text, *, fuente=True):
    text = re.sub(r'https?://[^\s\[<>]+\[([^\]]*)\]', r'\1', text)
    text = re.sub(r'\[([^\]]+)\]\([^\s)]+(?:\s+"[^"]*")?\)', r'\1', text)
    if fuente:
        text = re.sub(r'\{[^{}]+\}', '', text)
        text = html.unescape(re.sub(r'<[^>]*>', ' ', text))
    text = text.translate(str.maketrans('', '', '*_`'))
    return ' '.join(text.split())


def cita_presente(quote, text):
    normalized = normalizar_cita(quote, fuente=False)
    return not any(c in normalized for c in '{}<>') and bool(normalized) and normalized in normalizar_cita(text)


def url_publica(url):
    decoded = url
    if isinstance(decoded, str):
        while True:
            current = urllib.parse.unquote(decoded)
            if current == decoded:
                break
            decoded = current
    if not isinstance(decoded, str) or any(c in decoded for c in '{}'):
        block('URL_MARCADOR', 'La URL contiene un marcador sin rellenar; completa todos los valores antes de proponerla o cargarla.')
    parsed = urllib.parse.urlsplit(url)
    try:
        port = parsed.port
    except ValueError:
        block('URL_HOST', 'La fuente debe estar en un host público HTTPS permitido; no se admiten destinos locales o privados.')
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or any(c.isspace() for c in url):
        block('URL', 'La fuente debe ser HTTPS, con host público y sin credenciales, parámetros ni fragmento.')
    path = parsed.path
    while True:
        current = urllib.parse.unquote(path)
        if current == path:
            break
        path = current
    if any(segment in ('.', '..') for segment in path.replace('\\', '/').split('/')):
        block('URL', 'La fuente no admite segmentos punto en la ruta, incluidos los codificados.')
    host = parsed.hostname.lower().rstrip('.')
    if port not in (None, 443) or host == 'localhost' or host.endswith(('.localhost', '.local')):
        block('URL_HOST', 'La fuente debe estar en un host público HTTPS permitido; no se admiten destinos locales o privados.')
    try:
        if not ipaddress.ip_address(host).is_global:
            block('URL_HOST', 'La fuente debe estar en un host público HTTPS permitido; no se admiten destinos locales o privados.')
    except ValueError:
        pass
    return parsed


class PublicNoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        block('URL_REDIRECCION', 'La URL redirige a otro destino; no se cargó. Propón y verifica la URL definitiva y pide aprobación.')


class PublicConnection(http.client.HTTPSConnection):
    def connect(self):
        # Conectar a la IP ya verificada conserva TLS/SNI del host original y evita una segunda resolución.
        def connect_public(address, timeout, source_address=None, **kwargs):
            addresses = socket.getaddrinfo(address[0], address[1], type=socket.SOCK_STREAM)
            if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
                block('URL_HOST', 'La fuente debe estar en un host público HTTPS permitido; no se admiten destinos locales o privados.')
            return socket.create_connection((addresses[0][4][0], address[1]), timeout, source_address)
        self._create_connection = connect_public
        super().connect()


class PublicHTTPSHandler(urllib.request.HTTPSHandler):
    def https_open(self, req):
        return self.do_open(PublicConnection, req, context=self._context)


class PublicHTTP:
    def __init__(self, opener=None):
        self.opener = opener or urllib.request.build_opener(urllib.request.ProxyHandler({}), PublicHTTPSHandler(), PublicNoRedirect())

    def fetch(self, url, method='GET', limit=MAX_SOURCE_BYTES, probe=False):
        url_publica(url)
        request = urllib.request.Request(url, method=method, headers={'Accept': '*/*', **({'Range': 'bytes=0-65535'} if probe else {})})
        try:
            with self.opener.open(request, timeout=10) as response:
                if response.geturl() != url:
                    block('URL_REDIRECCION', 'La URL redirige a otro destino; no se cargó. Propón y verifica la URL definitiva y pide aprobación.')
                status = response.getcode()
                if status < 200 or status >= 300:
                    block('URL_HTTP', 'La fuente no respondió con éxito; no se cargó. Revisa su disponibilidad.')
                content = response.read(limit + 1) if method == 'GET' else b''
                if len(content) > limit and not probe:
                    block('ARCHIVO_TAMANO', 'La fuente supera el límite de lectura; no se cargó.')
                return content[:limit], response.headers.get_content_type()
        except urllib.error.HTTPError as error:
            if 300 <= error.code < 400:
                block('URL_REDIRECCION', 'La URL redirige a otro destino; no se cargó. Propón y verifica la URL definitiva y pide aprobación.')
            if method == 'HEAD' and error.code in (405, 501):
                return self.fetch(url, 'GET', 65536, probe=True)
            block('URL_HTTP', 'La fuente no respondió con éxito; no se cargó. Revisa su disponibilidad.')
        except (urllib.error.URLError, TimeoutError, OSError):
            block('URL_COMPROBACION', 'No se pudo comprobar la URL dentro del plazo; no se cargó. Revisa el acceso y repite la comprobación.')


def boot_del_servicio(service, inventory):
    boms = [b for b in service.get('boms', []) if b.get('coordenada') == BOOT_BOM]
    plugins = [b for b in service.get('plugins', []) if b.get('id') == 'org.springframework.boot']
    declarations = boms + plugins
    if any(b.get('estado') != 'literal' or not b.get('version') for b in declarations) or len({b['version'] for b in declarations}) > 1:
        block('BOM_CONFLICTO', 'La BOM explícita y el plugin del servicio difieren o una declaración local no es resoluble; no hay respaldo silencioso.')
    selected = (boms or plugins or [{'version': inventory.get('base', {}).get('spring-boot')}])[0]['version']
    if not selected:
        block('BOM_VERSION', 'Falta la versión de Spring Boot en el servicio y en .agents/stack.yaml; indícala antes de resolver su BOM.')
    version(selected)
    return selected, 'bom' if boms else 'plugin' if plugins else 'stack'


def aviso_bom(service, selected, inventory):
    base = inventory.get('base', {}).get('spring-boot')
    if base and base != selected:
        return f"AVISO BOM_STACK: {service['nombre']} declara Spring Boot {selected} y .agents/stack.yaml {base}; se documenta con {selected}. Ejecuta node .agents/scripts/comprobar-versiones.mjs para revisarlo."
    return None


def version_bom_del_servicio(service, inventory, bom):
    if bom == BOOT_BOM:
        return boot_del_servicio(service, inventory)
    if bom != CLOUD_BOM:
        block('BOM', 'Indica un servicio y una tecnología con propiedad de una BOM admitida (Spring Boot o Spring Cloud).')
    boms = [b for b in service.get('boms', []) if b.get('coordenada') == bom]
    if not boms:
        block('BOM_VERSION', f"{service['nombre']} no declara la BOM de Spring Cloud; declárala con versión literal antes de resolver TECNOLOGIA.")
    if any(b.get('estado') != 'literal' or not b.get('version') for b in boms) or len({b['version'] for b in boms}) != 1:
        block('BOM_CONFLICTO', f"{service['nombre']} declara la BOM de Spring Cloud sin una versión literal única; no se resuelve TECNOLOGIA.")
    selected = boms[0]['version']
    version(selected)
    return selected, 'bom'


def resolucion_vigente(saved, detector, bom_version, identity):
    return (isinstance(saved, dict) and saved.get('bom') == detector['bom']
            and saved.get('propiedad') == detector['bom_propiedad'] and saved.get('version_bom') == bom_version
            and detector.get('identificador') == identity)


def resolver_bom(root, catalog, service_name, tech, confirmed=False, public=None):
    registro = Registro(root, catalog)
    data = registro.read()
    inventory = inventario_local(root)
    service = next((s for s in inventory['servicios'] if s['nombre'] == service_name), None)
    if service is None:
        block('BOM', 'Indica un servicio y una tecnología con propiedad de una BOM admitida (Spring Boot o Spring Cloud).')
    candidates = [d for d in catalog.get('detectores', []) if d['tecnologia'] == tech and d['tipo'] in ('dependencia', 'bom_gestionado')]
    present = {}
    matches = []
    for item in service.get('dependencias', []):
        identity = item.get('coordenada')
        detectors = [d for d in candidates if d.get('identificador') == identity or
                     (d.get('prefijo') and identity and identity.startswith(d['prefijo']))]
        if detectors:
            matches.append(item)
            present.setdefault(identity, []).extend(detectors)
    detectors = [d for identity in sorted(present) for d in present[identity]]
    if not detectors or any(d.get('bom') not in BOMS_ADMITIDAS or not d.get('bom_propiedad') or
                            d.get('identificador') not in present for d in detectors):
        block('BOM', 'Indica un servicio y una tecnología con propiedad de una BOM admitida (Spring Boot o Spring Cloud).')
    detector = detectors[0]
    if any((d['bom'], d['bom_propiedad']) != (detector['bom'], detector['bom_propiedad']) for d in detectors):
        block('BOM', 'Las coordenadas presentes de la tecnología no comparten BOM y propiedad; unifica sus detectores antes de resolver.')
    if not matches or any(d.get('estado') not in ('literal', 'del_bom') for d in matches):
        block('BOM', 'La dependencia no existe o su declaración local no es resoluble.')
    if all(d['estado'] == 'literal' for d in matches):
        if len({d['version'] for d in matches}) != 1:
            block('BOM', 'Las declaraciones literales de la dependencia son contradictorias; no se elige una por su cuenta.')
        return {'version': matches[0]['version'], 'origen': 'build', 'confirmado': False, 'avisos': []}
    if any(d['estado'] == 'literal' for d in matches):
        block('BOM', f'{service_name} mezcla declaraciones literales y gestionadas de {tech}; unifícalas antes de resolver.')
    try:
        bom_version, origin = version_bom_del_servicio(service, inventory, detector['bom'])
    except Blocked as error:
        block(error.code, error.message.replace('TECNOLOGIA', tech))
    url = url_pom_bom(detector['bom'], bom_version)
    warning = aviso_bom(service, bom_version, inventory) if detector['bom'] == BOOT_BOM else None
    saved = data.get('resoluciones_bom', {}).get(service_name, {}).get(tech)
    try:
        raw, _ = (public or PublicHTTP()).fetch(url, limit=2 * 1024 * 1024)
    except Blocked as error:
        if error.code == 'URL_COMPROBACION':
            if resolucion_vigente(saved, detector, bom_version, detector['identificador']):
                return {'version': saved['version'], 'origen': 'registro', 'confirmado': False, 'avisos': [w for w in (warning, 'BOM_RED: se reutiliza una resolución vigente sin red.') if w]}
            block('BOM_RED', 'No se pudo leer el POM público de la BOM y no hay una resolución vigente; repite resolver-bom cuando haya acceso.')
        raise
    try:
        if b'\x00' in raw or b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():
            raise ValueError()
        pom = ET.fromstring(raw)
        ns = {'m': 'http://maven.apache.org/POM/4.0.0'}
        group, artifact = BOMS_ADMITIDAS[detector['bom']]
        if pom.findtext('m:groupId', namespaces=ns) != group or pom.findtext('m:artifactId', namespaces=ns) != artifact or pom.findtext('m:version', namespaces=ns) != bom_version:
            raise ValueError()
        properties = pom.findall('m:properties/m:' + detector['bom_propiedad'], ns)
        if len(properties) != 1 or not properties[0].text:
            raise ValueError()
        resolved = properties[0].text.strip()
        version(resolved)
    except (ET.ParseError, ValueError, Blocked):
        block('BOM_PROPIEDAD', 'El POM no publica una versión literal inequívoca para la propiedad solicitada; no se deduce ni se cambia el build.')
    record = {'dependencia': detector['identificador'], 'bom': detector['bom'], 'version_bom': bom_version,
              'version': resolved, 'propiedad': detector['bom_propiedad'], 'url_pom': url,
              'sha256_pom': hashlib.sha256(raw).hexdigest(), 'resuelto_en': datetime.now(timezone.utc).isoformat(), 'origen_version_bom': origin}
    with bloqueo_agents(root):
        data = registro.read()
        proposed = copy.deepcopy(data)
        proposed.setdefault('resoluciones_bom', {}).setdefault(service_name, {})[tech] = record
        try:
            original = registro.path.read_text() if registro.path.exists() else ''
            md_path = root / 'documentacion.md'
            original_md = md_path.read_text() if md_path.exists() else ''
            payload, markdown = registro.preparar_archivos(proposed)
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
            block('REGISTRO', causa_os('No se pudo preparar documentacion.json y su Markdown; revisa el registro sin sobrescribirlo a mano.', error))
        diff_json = ''.join(difflib.unified_diff(original.splitlines(True), payload.splitlines(True), fromfile='documentacion.json', tofile='documentacion.json'))
        diff_md = ''.join(difflib.unified_diff(original_md.splitlines(True), markdown.splitlines(True), fromfile='documentacion.md', tofile='documentacion.md'))
        diff = diff_json + diff_md
        if confirmed:
            registro.save(proposed, actualizado_en=proposed['actualizado_en'])
    return {'version': resolved, 'origen': 'pom', 'confirmado': confirmed, 'resolucion': record, 'diff': diff, 'avisos': [warning] if warning else []}


SCAN_LINE_LIMIT = 4096
SCAN_OVERLAP = 256
_CREDENTIAL_NAMES = ('password', 'passwd', 'secret', 'token', 'api_key', 'apikey', 'client_secret', 'private_key', 'access_key')
_CREDENTIAL_QUERY = frozenset(('token', 'key', 'password', 'secret', 'auth', 'api_key', 'apikey'))
_COMMON_VALUES = frozenset(('string', 'integer', 'boolean', 'null', 'none', 'true', 'false', 'example', 'changeme', 'password', 'secret', 'token', 'your-token', 'your_password'))
_PEM_SIGNATURE = re.compile(r'-----BEGIN [A-Z ]{0,40}PRIVATE KEY-----')
_AWS_SIGNATURE = re.compile(r'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b')
_AWS_PREFIX = re.compile(r'\b(?:AKIA|ASIA)')
_GITHUB_PREFIX = re.compile(r'\b(?:gh[pousr]_|github_pat_)')
_GITHUB_SIGNATURE = re.compile(r'\b(?:gh[pousr]_[A-Za-z0-9]{20,255}|github_pat_[A-Za-z0-9_]{20,255})\b')
_AUTH_SIGNATURE = re.compile(r'(?i:Authorization:\s{0,5}(?:Bearer|Basic)\s{1,5})')
_URL_SIGNATURE = re.compile(r'[A-Za-z][A-Za-z0-9+.-]{0,20}://[^\s"\x27`]{1,4096}')
_BASE64_RUN = re.compile(r'[A-Za-z0-9_-]{1,4096}')
_ASSIGN_SEPARATOR = re.compile(r':=|=>|==|[:=]')
_HTML_TAG = re.compile(r'(?i:</?(?:html|head|body|script|style|p|div|span|a|img|pre|code|table|section|article|link|meta)(?=[\s/>])[^<>\r\n]{0,4096}>)')
MAX_ASSIGNMENTS_PER_LINE = 64
_SHELL_VARIABLE = re.compile(r'\$[A-Z_][A-Z0-9_]{0,4094}')
_PERCENT_VARIABLE = re.compile(r'%[A-Za-z_][A-Za-z0-9_]{0,4093}%')
_VALUE_PUNCTUATION = frozenset(',;)}]."\'`')


def _brace_pairs(text):
    pairs, braces, parens = {}, [], []
    angle = None
    for index, char in enumerate(text):
        if char == '{':
            braces.append(index)
        elif char == '}' and braces:
            pairs[braces.pop()] = index
        elif char == '(':
            parens.append(index)
        elif char == ')' and parens:
            pairs[('paren', parens.pop())] = index
        elif char == '<':
            angle = index
        elif char == '>' and angle is not None:
            pairs[('angle', angle)] = index
            angle = None
    return pairs


def _marker_end(text, start, pairs):
    if text.startswith('${', start):
        return pairs.get(start + 1)
    if text.startswith('{{', start):
        return pairs.get(start)
    if text.startswith('$(', start):
        return pairs.get(('paren', start + 1))
    if text.startswith('<', start):
        return pairs.get(('angle', start))
    return None


def marcador_ejemplo(value):
    # El marcador completo, incluidas sustituciones de comandos, nunca es una credencial.
    if not value:
        return False
    if value.startswith(('${', '{{', '<', '$(')):
        return _marker_end(value, 0, _brace_pairs(value)) == len(value) - 1
    if len(value) >= 2 and value[0] == value[-1] == '`':
        return True
    if value.startswith(('your-', 'my-', 'example-')):
        return True
    if '_' in value and 'A' <= value[0] <= 'Z' and all('A' <= c <= 'Z' or '0' <= c <= '9' or c == '_' for c in value):
        return True
    return _SHELL_VARIABLE.fullmatch(value) is not None or _PERCENT_VARIABLE.fullmatch(value) is not None


def _limpiar_valor(value):
    value = value.strip()
    if value and value[0] in ('"', "'"):
        close = value.find(value[0], 1)
        if close != -1 and all(c.isspace() or c in _VALUE_PUNCTUATION for c in value[close + 1:]):
            value = value[1:close].strip()
    if value.startswith(('${', '{{', '<', '$(')):
        end = _marker_end(value, 0, _brace_pairs(value))
        if end is not None and all(c.isspace() or c in _VALUE_PUNCTUATION for c in value[end + 1:]):
            return value[:end + 1]
    if value.startswith('`'):
        end = value.find('`', 1)
        if end != -1 and all(c.isspace() or c in _VALUE_PUNCTUATION for c in value[end + 1:]):
            return value[:end + 1]
    return value.rstrip(''.join(_VALUE_PUNCTUATION)).strip()


def parece_secreto(value):
    value = _limpiar_valor(value)
    if len(value) < 8 or marcador_ejemplo(value) or any(c.isspace() for c in value):
        return False
    # Una URL o expresión de código no es secreta por sí misma: sus URL se revisan por firmas.
    if '(' in value or _URL_SIGNATURE.match(value):
        return False
    lower = value.casefold()
    if lower in _COMMON_VALUES or set(lower) == {'x'} or set(value) == {'*'} or len(set(value)) == 1:
        return False
    return any(c.isalpha() for c in value) and any(c.isdigit() or not c.isalnum() for c in value)


def _valor_en_linea(line, start, pairs):
    end = len(line)
    while start < end and line[start].isspace():
        start += 1
    if start == end:
        return '', start
    cursor = start
    if line[start] in ('"', "'", '`'):
        cursor += 1
        while cursor < end and line[cursor] != line[start]:
            cursor += 1
        if cursor < end:
            cursor += 1
        if cursor < end and not line[cursor].isspace() and line[cursor] not in _VALUE_PUNCTUATION:
            while cursor < end and not line[cursor].isspace() and line[cursor] not in ('"', "'", '`'):
                cursor += 1
        return line[start:cursor], cursor
    close = _marker_end(line, start, pairs)
    if close is not None:
        cursor = close + 1
    # Sin comillas el valor llega al próximo espacio; solo se quita puntuación FINAL.
    # Una comilla exterior de una orden shell delimita también el valor de la cabecera.
    while cursor < end and not line[cursor].isspace() and line[cursor] not in ('"', "'", '`'):
        cursor += 1
    return line[start:cursor], cursor


def _contenido_protegido(category, line_number):
    block('CONTENIDO_PROTEGIDO', f'Se detectó posible contenido protegido; no se cargó ni se muestran sus valores. Categoría: {category}; línea: {line_number}.')


def _firma_jwt(line, line_number):
    # Equivalente a la firma JWT acotada, sin reintentar un sufijo por cada prefijo eyJ.
    if 'eyJ' not in line or '.' not in line:
        return
    history = []
    current = None
    def word(char):
        return bool(char) and (char.isalnum() or char == '_')
    def finish(run):
        start, end, head, tail = run
        length = end - start
        tail_start = end - len(tail)
        candidate = tail.find('eyJ')
        prefix = False
        while candidate != -1:
            position = tail_start + candidate
            if 13 <= end - position <= 4099 and (position == 0 or not word(line[position - 1])):
                prefix = True
                break
            candidate = tail.find('eyJ', candidate + 3)
        if len(history) == 2:
            first, second = history
            if first[3] and 10 <= second[2] <= 4096 and first[1] + 1 == second[0] and second[1] + 1 == start and line[first[1]] == '.' and line[second[1]] == '.':
                for size in range(10, min(length, 4096) + 1):
                    following = line[start + size] if start + size < len(line) else ''
                    if word(head[size - 1]) != word(following):
                        _contenido_protegido('JWT', line_number)
        history.append((start, end, length, prefix))
        if len(history) > 2:
            history.pop(0)
    # El estado conserva solo dos segmentos y los extremos acotados del segmento actual.
    seen = 0
    for offset in range(0, len(line), SCAN_LINE_LIMIT - SCAN_OVERLAP):
        stop = min(offset + SCAN_LINE_LIMIT, len(line))
        piece = line[seen:stop]
        for match in _BASE64_RUN.finditer(piece):
            start, end = seen + match.start(), seen + match.end()
            token = match.group()
            if current is not None and start == current[1]:
                current = (current[0], end, (current[2] + token)[:4097], (current[3] + token)[-4100:])
            else:
                if current is not None:
                    finish(current)
                current = (start, end, token[:4097], token[-4100:])
        seen = stop
        if stop == len(line):
            break
    if current is not None:
        finish(current)


def _firmas_en_trozo(piece, line_number, original=None, offset=0):
    original = piece if original is None else original
    if 'PRIVATE KEY-----' in piece and _PEM_SIGNATURE.search(piece):
        _contenido_protegido('PEM', line_number)
    if 'AKIA' in piece or 'ASIA' in piece:
        for prefix in _AWS_PREFIX.finditer(piece):
            if _AWS_SIGNATURE.match(original, offset + prefix.start()):
                _contenido_protegido('AWS', line_number)
    if 'gh' in piece or 'github_pat_' in piece:
        for prefix in _GITHUB_PREFIX.finditer(piece):
            # Mirada acotada (máximo 266 caracteres) conserva firma y límites entre trozos.
            if _GITHUB_SIGNATURE.match(original, offset + prefix.start()):
                _contenido_protegido('GitHub', line_number)
    if 'authorization:' in piece.casefold():
        pairs = _brace_pairs(piece)
        for match in _AUTH_SIGNATURE.finditer(piece):
            value, _ = _valor_en_linea(piece, match.end(), pairs)
            if parece_secreto(value):
                _contenido_protegido('Authorization', line_number)
    if '://' in piece:
        for match in _URL_SIGNATURE.finditer(piece):
            try:
                parsed = urllib.parse.urlsplit(match.group())
                if parsed.password:
                    _contenido_protegido('URL_USERINFO', line_number)
                for key, value in urllib.parse.parse_qsl(parsed.query, keep_blank_values=True, max_num_fields=4096):
                    if key.casefold() in _CREDENTIAL_QUERY and parece_secreto(value):
                        _contenido_protegido('URL_PARAMETRO', line_number)
            except ValueError:
                continue  # Una URL mal formada no acredita por sí sola una credencial.


def _asignaciones_en_linea(line, line_number):
    lower = line.casefold().replace('-', '_').replace('.', '_')
    if not any(name in lower for name in _CREDENTIAL_NAMES):
        return
    pairs = _brace_pairs(line) if any(c in line for c in ('{', '<', '$(')) else {}
    spans = []
    index = 0 if '${' in line or '{{' in line else len(line)
    while index < len(line):
        if line.startswith(('${', '{{'), index):
            end = _marker_end(line, index, pairs)
            if end is not None:
                spans.append((index, end + 1))
                index = end + 1
                continue
        index += 1
    cursor = span_index = evaluated = 0
    while evaluated < MAX_ASSIGNMENTS_PER_LINE and (match := _ASSIGN_SEPARATOR.search(line, cursor)):
        cursor = match.end()
        while span_index < len(spans) and spans[span_index][1] <= match.start():
            span_index += 1
        if span_index < len(spans) and spans[span_index][0] <= match.start() < spans[span_index][1]:
            cursor = spans[span_index][1]
            continue
        left = match.start() - 1
        while left >= 0 and (line[left].isspace() or line[left] in ('"', "'", '`')):
            left -= 1
        end = left + 1
        while left >= 0 and (line[left].isalnum() or line[left] in '_.-'):
            left -= 1
        name = line[left + 1:end].casefold().replace('-', '_').replace('.', '_')
        if any(part in name for part in _CREDENTIAL_NAMES):
            evaluated += 1
            value, cursor = _valor_en_linea(line, cursor, pairs)
            if parece_secreto(value):
                _contenido_protegido('ASIGNACION', line_number)


def escanear_contenido(text, html=False):
    if html or ('>' in text and _HTML_TAG.search(text)):
        parser = TextoDetectorHTML()
        parser.feed(text)
        parser.close()
        text = ''.join(parser.parts)
    for line_number, line in enumerate(text.splitlines(), 1):
        if not line:
            continue
        _firma_jwt(line, line_number)
        if len(line) <= SCAN_LINE_LIMIT:
            _firmas_en_trozo(line, line_number)
            _asignaciones_en_linea(line, line_number)
        else:
            for offset in range(0, len(line), SCAN_LINE_LIMIT - SCAN_OVERLAP):
                _firmas_en_trozo(line[offset:offset + SCAN_LINE_LIMIT], line_number, line, offset)


class TextoDetectorHTML(HTMLParser):
    """Solo texto visible y href/src; conserva los saltos para el diagnóstico."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.hidden = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.hidden += 1
        if not self.hidden:
            for name, value in attrs:
                if name in ('href', 'src') and value:
                    self.parts.extend((' ', value, ' '))
        self.parts.append(' ' + '\n' * self.get_starttag_text().count('\n'))

    def handle_endtag(self, tag):
        if tag in ('script', 'style') and self.hidden:
            self.hidden -= 1
        self.parts.append(' ')

    def handle_data(self, data):
        self.parts.append('\n' * data.count('\n') if self.hidden else data)


class TextoHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.hidden = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.hidden += 1
        self.parts.append(' ')

    def handle_endtag(self, tag):
        if tag in ('script', 'style') and self.hidden:
            self.hidden -= 1
        self.parts.append(' ')

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def extraer_documento(raw, name, mime=None):
    if len(raw) > MAX_SOURCE_BYTES:
        block('ARCHIVO_TAMANO', 'La fuente supera el límite de 10 MiB; no se cargó.')
    ext = Path(name).suffix.lower()
    allowed = {'.md', '.markdown', '.txt', '.adoc', '.html', '.htm', '.pdf'}
    if raw.startswith(b'%PDF-') and ext == '.pdf' and mime in (None, 'application/pdf'):
        try:
            result = subprocess.run(['pdftotext', '-', '-'], input=raw, capture_output=True, timeout=20)
            text = result.stdout.decode('utf-8')
            if result.returncode or not text.strip():
                raise ValueError()
        except (OSError, ValueError, UnicodeError, subprocess.SubprocessError):
            block('ARCHIVO_TIPO', 'El PDF no puede inspeccionarse localmente; aporta documentación pública textual.')
        escanear_contenido(text)
        return text, 'application/pdf'
    if ext not in allowed - {'.pdf'} or (mime and mime not in ('text/plain', 'text/markdown', 'text/html', 'text/x-asciidoc', 'application/octet-stream')):
        block('ARCHIVO_TIPO', 'El formato no está admitido o no puede inspeccionarse localmente; aporta documentación pública en un formato admitido.')
    try:
        text = raw.decode('utf-8-sig')
        if '\x00' in text or not text.strip():
            raise ValueError()
    except (UnicodeError, ValueError):
        block('ARCHIVO_TIPO', 'El formato no está admitido o no puede inspeccionarse localmente; aporta documentación pública en un formato admitido.')
    is_html = ext in ('.html', '.htm') or mime == 'text/html'
    escanear_contenido(text, html=is_html)
    if is_html:
        parser = TextoHTML()
        parser.feed(text)
        return ''.join(parser.parts), 'text/html'
    return text, 'text/markdown' if ext in ('.md', '.markdown') else 'text/plain'


def leer_archivo_publico(path, project, declared):
    original = Path(path).absolute()
    resolved = original.resolve()
    prohibited = lambda p: any(x.lower().startswith('.env') or x.lower() in ('account', 'kubeconfig', '.kube', '.aws', '.ssh', '.config', '.codex', '.agents', '.docker') or re.search(r'(?i)(?:secret|credential|password)', x) for x in p.parts)
    if prohibited(original) or prohibited(resolved):
        block('CONTENIDO_PROTEGIDO', 'La ruta identifica contenido protegido; no se abrió ni se cargó.')
    if resolved.is_relative_to(project.resolve()) or original.is_relative_to(project.resolve()):
        block('ARCHIVO_PROYECTO', 'El archivo está dentro del repositorio del proyecto; no se cargó. Aporta una fuente pública externa.')
    if not declared:
        block('APROBACION_PUBLICA', 'Confirma que el archivo es documentación pública sin datos del proyecto; añade --documentacion-publica.')
    if any(ord(c) < 32 for c in resolved.name):
        block('ARCHIVO_TIPO', 'El nombre del archivo contiene caracteres de control.')
    if not resolved.is_file():
        block('ARCHIVO_TIPO', 'Indica un archivo regular de documentación pública.')
    with resolved.open('rb') as stream:
        raw = stream.read(MAX_SOURCE_BYTES + 1)
    text, mime = extraer_documento(raw, resolved.name)
    return raw, text, mime, resolved.name


def es_oficial(catalog, tech, url):
    if not url:
        return False
    parsed = url_publica(url)
    for rule in catalog.get('dominios_oficiales', {}).get(tech, []):
        path = urllib.parse.unquote(parsed.path)
        prefix = rule.get('ruta', '/').rstrip('/')
        if parsed.hostname == rule['host'] and (path == prefix or path.startswith(prefix + '/')):
            return True
    return False


ALIAS_TECNOLOGIA = {
    'jdk': ['Java', 'Java SE', 'OpenJDK', 'Java Platform, Standard Edition', 'Oracle JDK'],
    'lombok': ['Project Lombok'],
    'spring-cloud-kubernetes': ['DiscoveryClient for Kubernetes'],
    'spring-cloud-gateway': [
        'Spring Cloud Gateway Server WebFlux',
        'Spring Cloud Gateway Server Web MVC',
        'Spring Cloud Gateway Server WebMVC',
        'Spring Cloud Gateway Server MVC',
    ],
}


def _quitar_sufijo_version(nombre):
    return re.sub(r'\s*(?:v(?:ersion)?\s*)?\d+(?:\.\d+)*\s*$', '', nombre, flags=re.I)


def nombres_tecnologia(meta, catalog):
    tech = meta['tecnologia']
    nombres = [tech, catalog['tecnologias'][tech], *ALIAS_TECNOLOGIA.get(tech, [])]
    vistos, out = set(), []
    for nombre in nombres:
        clave = nombre.casefold()
        if clave not in vistos:
            vistos.add(clave)
            out.append(nombre)
    return out


def tecnologia_compatible(name, meta, catalog):
    if not isinstance(name, str):
        return False
    normalize = lambda value: re.sub(r'[^a-z0-9]', '', value.casefold())
    base = _quitar_sufijo_version(name).strip() or name
    allowed = {normalize(nombre) for nombre in nombres_tecnologia(meta, catalog)}
    return normalize(base) in allowed


def nombre_de_otra_tecnologia(name, meta, catalog):
    base = _quitar_sufijo_version(name).strip()
    normalize = lambda value: re.sub(r'[^a-z0-9]', '', value.casefold())
    words = re.findall(r'[a-z0-9]+', base.casefold())
    for tech in catalog['tecnologias']:
        if tech == meta['tecnologia']:
            continue
        for label in nombres_tecnologia({'tecnologia': tech}, catalog):
            if normalize(base) == normalize(label):
                return True
            parts = re.findall(r'[a-z0-9]+', _quitar_sufijo_version(label).casefold())
            if parts and any(words[i:i + len(parts)] == parts for i in range(len(words) - len(parts) + 1)):
                return True
    return False


def entradas_registradas(data):
    """Incluye el historial, cuya versión se conserva explícitamente."""
    for tech, group in data['tecnologias'].items():
        for expected, entry in group['versiones'].items():
            yield tech, expected, entry
        for entry in group.get('retirados', []):
            yield tech, entry['version'], entry


def principal_compatible(principal, meta, catalog, kind):
    """El insight debe traer la versión ya normalizada; aquí solo se compara."""
    if not isinstance(principal, dict):
        raise ValueError()
    name, detected = principal.get('tecnologia'), principal.get('version')
    if not isinstance(name, str) or not isinstance(detected, str):
        raise ValueError()
    if not tecnologia_compatible(name, meta, catalog):
        return False
    try:
        version(detected, meta['tecnologia'] == 'jdk')
        return fuente_compatible(meta['tecnologia'], meta['version'], {'tipo': kind, 'version_principal': detected})
    except Blocked:
        return False


def comprobar_correspondencia(text, meta, catalog, kind, confirmed=False):
    aliases = nombres_tecnologia(meta, catalog)
    normalized_text = normalizar_cita(text)
    if not any(re.search(r'(?i)(?<!\w)' + re.escape(name) + r'(?!\w)', normalized_text) for name in aliases):
        for other, label in catalog['tecnologias'].items():
            if other != meta['tecnologia'] and any(re.search(r'(?i)(?<!\w)' + re.escape(n) + r'\s+(?:v)?\d+(?:\.\d+)*', normalized_text) for n in (other, label)):
                block('FUENTE_VERSION_INCOMPATIBLE', 'La fuente acredita otra tecnología o versión incompatible; no se cargó.')
    found = set()
    for name in aliases:
        for match in re.finditer(r'(?i)(?<!\w)' + re.escape(name) + r'\s+(?:version\s+|v)?(\d+(?:\.\d+){0,3})(?!\w|\.\d)', normalizar_cita(text)):
            found.add(match.group(1))
    if found:
        compatible = [v for v in found if principal_compatible({'tecnologia': meta['tecnologia'], 'version': v}, meta, catalog, kind)]
        if not compatible:
            block('FUENTE_VERSION_INCOMPATIBLE', 'La fuente acredita otra tecnología o versión incompatible; no se cargó.')
        if len(compatible) == 1 and all(v in compatible or ('.' not in v and meta['tecnologia'] != 'jdk') for v in found):
            return {'principal': {'tecnologia': meta['tecnologia'], 'version': compatible[0]}, 'confirmada_usuario': False}
    if not confirmed:
        block('FUENTE_VERSION_AUSENTE', 'La fuente no acredita inequívocamente la tecnología y versión solicitadas; no se cargó. Revisa el contenido y confirma expresamente su correspondencia antes de repetir.')
    return {'principal': None, 'confirmada_usuario': True}


def multipart_upload(fields, raw, name, mime):
    boundary = 'documentation-' + os.urandom(18).hex()
    chunks = []
    for key, value in fields.items():
        chunks.append((f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n').encode())
    safe_name = re.sub(r'[^A-Za-z0-9._-]', '_', name)
    chunks.append((f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{safe_name}"\r\nContent-Type: {mime}\r\n\r\n').encode() + raw + b'\r\n')
    chunks.append(f'--{boundary}--\r\n'.encode())
    return b''.join(chunks), 'multipart/form-data; boundary=' + boundary


def inventario_local(root):
    reader = root / 'scripts/inventario-versiones.mjs'
    command = ['node', str(reader)] if reader.exists() else [sys.executable, '-B', '-E', str(root / 'scripts/inventario-versiones.py')]
    result = subprocess.run(command, cwd=root.parent, capture_output=True, text=True, timeout=20)
    try:
        value = json.loads(result.stdout)
        if result.returncode or value['formato'] != 1 or not isinstance(value['servicios'], list):
            raise ValueError()
        return value
    except (ValueError, KeyError, TypeError):
        block('INVENTARIO', 'No se pudo leer el inventario local; revisa los archivos de versiones.')


def tecnologias_usadas(inventory, catalog, resoluciones_bom=None):
    resoluciones_bom = resoluciones_bom or {}
    result = {}
    for service in inventory['servicios']:
        found = {}
        def add(tech, item):
            found.setdefault(tech, []).append(item)
        if inventory['stack'] == 'mysql':
            for item in service['tecnologias']:
                add(item['id'], item)
        else:
            groups = {'java': [service['java']] if 'java' in service else [],
                      'plugin': service.get('plugins', []), 'dependencia': service.get('dependencias', []),
                      'bom': service.get('boms', [])}
            for kind, items in groups.items():
                for item in items:
                    identity = item.get('id') or item.get('coordenada') or item.get('nombre')
                    matches = [d for d in catalog.get('detectores', []) if (d['tipo'] == kind or (kind == 'dependencia' and d['tipo'] == 'bom_gestionado')) and
                               (kind == 'java' or d.get('identificador') == identity or
                                (d.get('prefijo') and identity and identity.startswith(d['prefijo'])))]
                    if kind == 'dependencia' and item['estado'] == 'del_bom' and any(
                            identity and identity.startswith(c['prefijo']) for c in catalog.get('cubiertas_por_boot', [])):
                        continue
                    if matches:
                        for detector in matches:
                            target_item = item
                            if item.get('estado') == 'del_bom' and detector.get('bom_propiedad'):
                                try:
                                    bom_version, _ = version_bom_del_servicio(service, inventory, detector['bom'])
                                    target_item = dict(item, aviso_bom=aviso_bom(service, bom_version, inventory) if detector['bom'] == BOOT_BOM else None)
                                    cached = resoluciones_bom.get(service['nombre'], {}).get(detector['tecnologia'])
                                    if resolucion_vigente(cached, detector, bom_version, identity):
                                        target_item = dict(target_item, version=cached['version'], estado='literal', origen_bom=detector['bom'])
                                except Blocked as error:
                                    target_item = dict(item, error_bom=error.code + ': ' + error.message.replace('TECNOLOGIA', detector['tecnologia']))
                            elif item.get('estado') == 'del_bom' and detector.get('bom'):
                                bom_coord = detector['bom']
                                bom_match = next((b for b in service.get('boms', []) if b.get('coordenada') == bom_coord), None)
                                bom_ver = bom_match.get('version') if bom_match else None
                                if not bom_ver and bom_coord == 'org.springframework.boot:spring-boot-dependencies':
                                    bom_ver = inventory.get('base', {}).get('spring-boot')
                                if bom_ver:
                                    target_item = dict(item, version=bom_ver, estado='literal', origen_bom=bom_coord)
                            add(detector['tecnologia'], target_item)
                    elif identity:
                        add((kind + ':' + identity) if kind == 'plugin' else identity, item)
        result[service['nombre']] = {}
        for tech, items in found.items():
            versions = {i['version'] for i in items if i.get('version') is not None}
            known = len(versions) == 1 and all(i['estado'] == 'literal' for i in items)
            result[service['nombre']][tech] = {'version': next(iter(versions)) if known else None,
                'estado': 'literal' if known else 'no_resoluble', 'declaraciones': items}
    return result


def remedio_fuente_aportada(origen):
    if origen == 'usuario-archivo':
        command = 'cargar NOTEBOOK --archivo RUTA --tipo TIPO --documentacion-publica'
    else:
        command = 'cargar NOTEBOOK URL --usuario-url --tipo TIPO'
    return ('revisa con ' + command + ' y, tras aprobar su hash, repite con '
            '--sha256-aprobado SHA256 --confirmar; añade --confirmar-correspondencia solo si '
            'la correspondencia no es inequívoca y el usuario la confirma')


def normalizar_version_detectada(valor: str) -> str:
    return re.sub(r'^[vV](?=\d)', '', valor)


def fuente_compatible(tech, project, source):
    principal = source.get('version_principal')
    if isinstance(principal, str):
        principal = normalizar_version_detectada(principal)
    if not isinstance(project, str) or not isinstance(principal, str):
        return False
    try:
        return principal == project if source['tipo'] in ('notas', 'requisitos') else version(principal, tech == 'jdk') == version(project, tech == 'jdk')
    except Blocked:
        return False


def validar_url_fuente(url_str):
    if not isinstance(url_str, str) or not url_str:
        block('CATALOGO_PROYECTO', 'URL de fuente vacía o inválida.')
    if '{version}' not in url_str and '{serie}' not in url_str:
        block('CATALOGO_PROYECTO', 'URL de fuente inválida: debe contener el marcador {version} o {serie}; nunca una URL sin versión.')
    parsed = urllib.parse.urlsplit(url_str)
    if parsed.scheme != 'https' or not parsed.hostname:
        block('CATALOGO_PROYECTO', 'URL de fuente inválida: debe usar https y tener host.')
    if parsed.username or parsed.password or '@' in parsed.netloc:
        block('CATALOGO_PROYECTO', 'URL de fuente inválida: no se permiten credenciales en la URL.')
    if parsed.query:
        query_lower = parsed.query.lower()
        for token in ('token=', 'key=', 'password=', 'secret=', 'auth=', 'api_key=', 'apikey='):
            if token in query_lower:
                block('CATALOGO_PROYECTO', f'URL de fuente inválida: contiene credenciales en parámetros ({token}).')


def validar_catalogo_proyecto(data, base_catalog):
    if not isinstance(data, dict):
        block('CATALOGO_PROYECTO', 'catalogo-proyecto.json debe ser un objeto JSON.')
    keys_permitidas = {'tecnologias', 'fuentes', 'detectores', 'cubiertas_por_boot', 'agregado_en', 'dominios_oficiales'}
    for k in data:
        if k not in keys_permitidas:
            block('CATALOGO_PROYECTO', f'catalogo-proyecto.json contiene clave desconocida: {k}')

    tecs = data.get('tecnologias', {})
    if not isinstance(tecs, dict):
        block('CATALOGO_PROYECTO', 'catalogo-proyecto.json: "tecnologias" debe ser un objeto.')
    for t_id, t_name in tecs.items():
        if not isinstance(t_id, str) or not isinstance(t_name, str):
            block('CATALOGO_PROYECTO', 'catalogo-proyecto.json: "tecnologias" debe mapear identificadores a nombres.')
        if not re.fullmatch(r'[a-z0-9][a-z0-9_-]*', t_id):
            block('CATALOGO_PROYECTO', f'catalogo-proyecto.json: identificador de tecnología inválido: {t_id}')
        if t_id in base_catalog.get('tecnologias', {}):
            block('CATALOGO_PROYECTO', f'catalogo-proyecto.json: la tecnología "{t_id}" ya está en el catálogo base; no se puede redefinir.')

    domains = data.get('dominios_oficiales', {})
    if not isinstance(domains, dict) or any(t not in tecs for t in domains):
        block('CATALOGO_PROYECTO', 'Solo se declaran dominios oficiales para tecnologías nuevas del proyecto.')
    for rules in domains.values():
        if not isinstance(rules, list) or any(not isinstance(r, dict) or not isinstance(r.get('host'), str) or not re.fullmatch(r'[a-z0-9.-]+', r['host']) or not isinstance(r.get('ruta', '/'), str) or not r.get('ruta', '/').startswith('/') for r in rules):
            block('CATALOGO_PROYECTO', 'Reglas de dominios oficiales inválidas.')
    fuentes = data.get('fuentes', [])
    if not isinstance(fuentes, list):
        block('CATALOGO_PROYECTO', 'catalogo-proyecto.json: "fuentes" debe ser una lista.')
    base_fuente_ids = {f.get('id') for f in base_catalog.get('fuentes', [])}
    proyecto_fuente_ids = set()
    for f in fuentes:
        if not isinstance(f, dict):
            block('CATALOGO_PROYECTO', 'catalogo-proyecto.json: cada fuente debe ser un objeto.')
        f_id = f.get('id')
        if not isinstance(f_id, str) or not re.fullmatch(r'P[1-9][0-9]*', f_id):
            block('CATALOGO_PROYECTO', 'catalogo-proyecto.json: cada fuente debe tener un id P seguido de un entero positivo; no se permite el prefijo B, F o S.')
        if f_id in base_fuente_ids:
            block('CATALOGO_PROYECTO', f'catalogo-proyecto.json: la fuente "{f_id}" ya está en el catálogo base; no se puede redefinir.')
        if f_id in proyecto_fuente_ids:
            block('CATALOGO_PROYECTO', f'catalogo-proyecto.json: "id" de fuente duplicado en el proyecto: "{f_id}".')
        proyecto_fuente_ids.add(f_id)

        f_tec = f.get('tecnologia')
        if f_tec not in tecs and f_tec not in base_catalog.get('tecnologias', {}):
            block('CATALOGO_PROYECTO', f'catalogo-proyecto.json: fuente "{f_id}" referencia tecnología desconocida "{f_tec}".')
        if f.get('tipo') not in SOURCE_TYPES:
            block('CATALOGO_PROYECTO', f'catalogo-proyecto.json: tipo de fuente inválido en "{f_id}": {f.get("tipo")}.')
        validar_url_fuente(f.get('url', ''))
        if set(re.findall(r'\{([^}]+)\}', f['url'])) - {'version', 'serie', 'ruta', 'tema', 'tag', 'ruta-migracion', 'version-guiones'}:
            block('CATALOGO_PROYECTO', 'El patrón contiene un marcador desconocido.')

    detectores = data.get('detectores', [])
    if not isinstance(detectores, list):
        block('CATALOGO_PROYECTO', 'catalogo-proyecto.json: "detectores" debe ser una lista.')

    base_detectores = base_catalog.get('detectores', [])
    base_cubiertas = base_catalog.get('cubiertas_por_boot', [])

    for d in detectores:
        if not isinstance(d, dict):
            block('CATALOGO_PROYECTO', 'catalogo-proyecto.json: cada detector debe ser un objeto.')
        d_tec = d.get('tecnologia')
        if d_tec not in tecs and d_tec not in base_catalog.get('tecnologias', {}):
            block('CATALOGO_PROYECTO', f'catalogo-proyecto.json: detector referencia tecnología desconocida "{d_tec}".')
        d_tipo = d.get('tipo')
        if d_tipo == 'java':
            block('CATALOGO_PROYECTO', 'catalogo-proyecto.json: el tipo de detector "java" no está permitido en el catálogo del proyecto; el JDK ya está cubierto en el catálogo base.')
        if d_tipo not in ('dependencia', 'plugin', 'bom', 'bom_gestionado'):
            block('CATALOGO_PROYECTO', f'catalogo-proyecto.json: tipo de detector inválido: {d_tipo}.')

        ident = d.get('identificador')
        pref = d.get('prefijo')
        if d_tipo in ('dependencia', 'plugin', 'bom', 'bom_gestionado') and not ident and not pref:
            block('CATALOGO_PROYECTO', f'catalogo-proyecto.json: detector de tipo "{d_tipo}" requiere "identificador" o "prefijo".')
        if d.get('bom_propiedad') and (d.get('bom') not in BOMS_ADMITIDAS or d_tipo != 'dependencia' or not isinstance(d.get('identificador'), str) or not re.fullmatch(r'[A-Za-z0-9_.-]+', str(d['bom_propiedad']))):
            block('CATALOGO_PROYECTO', 'bom_propiedad necesita dependencia exacta y propiedad literal de una BOM admitida (Spring Boot o Spring Cloud).')
        if d_tipo == 'bom_gestionado' and not d.get('bom'):
            block('CATALOGO_PROYECTO', 'catalogo-proyecto.json: detector de tipo "bom_gestionado" requiere indicar "bom".')

        # Comprobar colisión con catálogo base
        for bd in base_detectores:
            b_tipo = bd.get('tipo')
            if d_tipo == b_tipo or {d_tipo, b_tipo}.issubset({'dependencia', 'bom_gestionado'}):
                b_ident = bd.get('identificador')
                b_pref = bd.get('prefijo')
                if ident and b_ident and ident == b_ident:
                    block('CATALOGO_PROYECTO', f'catalogo-proyecto.json: el detector para "{ident}" ya está cubierto por el catálogo base.')
                if ident and b_pref and ident.startswith(b_pref):
                    block('CATALOGO_PROYECTO', f'catalogo-proyecto.json: el detector para "{ident}" choca con el prefijo "{b_pref}" del catálogo base.')
                if pref and b_ident and b_ident.startswith(pref):
                    block('CATALOGO_PROYECTO', f'catalogo-proyecto.json: el prefijo "{pref}" choca con el detector "{b_ident}" del catálogo base.')
                if pref and b_pref and (pref.startswith(b_pref) or b_pref.startswith(pref)):
                    block('CATALOGO_PROYECTO', f'catalogo-proyecto.json: el prefijo de detector "{pref}" choca con el catálogo base.')

        for cb in base_cubiertas:
            cb_pref = cb.get('prefijo', '')
            if ident and ident.startswith(cb_pref):
                block('CATALOGO_PROYECTO', f'catalogo-proyecto.json: la coordenada "{ident}" ya está cubierta por Boot en el catálogo base.')
            if pref and (pref.startswith(cb_pref) or cb_pref.startswith(pref)):
                block('CATALOGO_PROYECTO', f'catalogo-proyecto.json: el prefijo "{pref}" ya está cubierto por Boot en el catálogo base.')

    cubiertas = data.get('cubiertas_por_boot', [])
    if not isinstance(cubiertas, list):
        block('CATALOGO_PROYECTO', 'catalogo-proyecto.json: "cubiertas_por_boot" debe ser una lista.')
    for c in cubiertas:
        if not isinstance(c, dict) or not isinstance(c.get('prefijo'), str):
            block('CATALOGO_PROYECTO', 'catalogo-proyecto.json: cada elemento de "cubiertas_por_boot" debe tener "prefijo".')


def cargar_catalogo(root):
    base_file = root / 'assets/documentacion/catalogo.json'
    base = json.loads(base_file.read_text(encoding='utf-8'))
    proj_file = root / 'catalogo-proyecto.json'
    if not proj_file.exists():
        return base
    try:
        raw = proj_file.read_text(encoding='utf-8')
        data = json.loads(raw)
    except (OSError, ValueError):
        block('CATALOGO_PROYECTO', 'catalogo-proyecto.json es ilegible o no es JSON válido; revisa el archivo.')
    validar_catalogo_proyecto(data, base)
    fusion = {
        'tecnologias': dict(base.get('tecnologias', {})),
        'fuentes': list(base.get('fuentes', [])),
        'detectores': list(base.get('detectores', [])),
        'cubiertas_por_boot': list(base.get('cubiertas_por_boot', []))
    }
    fusion['dominios_oficiales'] = dict(base.get('dominios_oficiales', {}))
    fusion['dominios_oficiales'].update(data.get('dominios_oficiales', {}))
    fusion['tecnologias'].update(data.get('tecnologias', {}))
    fusion['fuentes'].extend(data.get('fuentes', []))
    fusion['detectores'].extend(data.get('detectores', []))
    fusion['cubiertas_por_boot'].extend(data.get('cubiertas_por_boot', []))
    return fusion


def ampliar_catalogo(root, tech, name, detectors_raw, sources_raw, confirmed, dominios_oficiales=None):
    with bloqueo_agents(root):
        return _ampliar_catalogo(root, tech, name, detectors_raw, sources_raw, confirmed, dominios_oficiales)


def _ampliar_catalogo(root, tech, name, detectors_raw, sources_raw, confirmed, dominios_oficiales=None):
    if not re.fullmatch(r'[a-z0-9][a-z0-9_-]*', tech):
        block('ARGUMENTOS', 'El identificador de tecnología debe contener solo letras minúsculas, números y guiones.')

    base_catalog = json.loads((root / 'assets/documentacion/catalogo.json').read_text(encoding='utf-8'))
    proj_path = root / 'catalogo-proyecto.json'

    original_bytes = leer_bytes_opcionales(proj_path)
    original_hash = huella_bytes(original_bytes)
    if original_bytes is not None:
        try:
            proj_data = json.loads(original_bytes.decode('utf-8'))
        except (OSError, ValueError):
            block('CATALOGO_PROYECTO', 'catalogo-proyecto.json existente es ilegible; corrígelo antes de ampliarlo.')
    else:
        proj_data = {'tecnologias': {}, 'fuentes': [], 'detectores': [], 'cubiertas_por_boot': []}

    existing_tech = tech in base_catalog['tecnologias'] or tech in proj_data.get('tecnologias', {})
    if existing_tech:
        if name is not None or detectors_raw or not sources_raw or dominios_oficiales is not None:
            block('CATALOGO_PROYECTO', 'Para una tecnología existente añade solo fuentes; no se puede redefinir nombre, detectores ni dominios oficiales.')
        name = base_catalog['tecnologias'].get(tech, proj_data.get('tecnologias', {}).get(tech))
    elif not name or not name.strip() or not detectors_raw or not sources_raw:
        block('ARGUMENTOS', 'Una tecnología nueva requiere nombre, detector y fuentes.')

    new_detectors = []
    for d_raw in (detectors_raw or []):
        try:
            d = json.loads(d_raw) if isinstance(d_raw, str) else d_raw
        except ValueError:
            block('ARGUMENTOS', 'Detector inválido: debe ser un objeto JSON válido.')
        if not isinstance(d, dict):
            block('ARGUMENTOS', 'Detector inválido: debe ser un objeto JSON.')
        d = dict(d)
        d['tecnologia'] = tech
        new_detectors.append(d)

    new_sources = []
    for s_raw in (sources_raw or []):
        try:
            s = json.loads(s_raw) if isinstance(s_raw, str) else s_raw
        except ValueError:
            block('ARGUMENTOS', 'Fuente inválida: debe ser un objeto JSON válido.')
        if not isinstance(s, dict):
            block('ARGUMENTOS', 'Fuente inválida: debe ser un objeto JSON.')
        s = dict(s)
        s['tecnologia'] = tech
        if 'estado' not in s:
            s['estado'] = 'por verificar'
        new_sources.append(s)

    proposed = {
        'tecnologias': dict(proj_data.get('tecnologias', {})),
        'fuentes': list(proj_data.get('fuentes', [])),
        'detectores': list(proj_data.get('detectores', [])),
        'cubiertas_por_boot': list(proj_data.get('cubiertas_por_boot', []))
    }

    if not existing_tech:
        proposed['tecnologias'][tech] = name.strip()
    if 'dominios_oficiales' in proj_data:
        proposed['dominios_oficiales'] = copy.deepcopy(proj_data['dominios_oficiales'])

    if dominios_oficiales is not None:
        try:
            rules = json.loads(dominios_oficiales) if isinstance(dominios_oficiales, str) else dominios_oficiales
        except ValueError:
            block('ARGUMENTOS', 'dominios_oficiales debe ser una lista JSON de reglas host/ruta.')
        proposed.setdefault('dominios_oficiales', {})[tech] = rules

    now_iso = datetime.now(timezone.utc).isoformat()
    entry_detectors = []
    for d in new_detectors:
        d_copy = dict(d)
        if confirmed:
            d_copy['agregado_en'] = now_iso
        entry_detectors.append(d_copy)
    proposed['detectores'].extend(entry_detectors)

    entry_sources = []
    for s in new_sources:
        s_copy = dict(s)
        if confirmed:
            s_copy['agregado_en'] = now_iso
        entry_sources.append(s_copy)
    proposed['fuentes'].extend(entry_sources)

    validar_catalogo_proyecto(proposed, base_catalog)

    old_content = original_bytes.decode('utf-8') if original_bytes is not None else ''
    new_content = json.dumps(proposed, ensure_ascii=False, indent=2) + '\n'

    diff = "".join(difflib.unified_diff(
        old_content.splitlines(keepends=True),
        new_content.splitlines(keepends=True),
        fromfile='catalogo-proyecto.json' if proj_path.exists() else '/dev/null',
        tofile='catalogo-proyecto.json'
    ))

    if not confirmed:
        return {
            'confirmado': False,
            'mensaje': 'Validación correcta; se muestra el diff. Para persistir requiere aprobación literal y --confirmar.',
            'tecnologia': tech,
            'nombre': name.strip(),
            'detectores': entry_detectors,
            'fuentes': entry_sources,
            'diff': diff
        }

    try:
        staged = []
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=root, prefix='.catalogo-', delete=False) as stream:
                staged.append((Path(stream.name), proj_path))
                stream.write(new_content)
            comprobar_huella(proj_path, original_hash, 'CATALOGO_CAMBIADO', 'catalogo-proyecto.json')
            for temp_p, target_p in staged:
                os.replace(temp_p, target_p)
        finally:
            for temp_p, _ in staged:
                temp_p.unlink(missing_ok=True)
    except OSError as error:
        block('CATALOGO_PROYECTO', causa_os(
            'No se pudo guardar catalogo-proyecto.json; revisa el catálogo sin sobrescribirlo a mano.',
            error))

    return {
        'confirmado': True,
        'mensaje': 'Entrada añadida a .agents/catalogo-proyecto.json.',
        'archivo': str(proj_path),
        'tecnologia': tech,
        'nombre': name.strip(),
        'detectores': entry_detectors,
        'fuentes': entry_sources,
        'diff': diff
    }


class Registro:
    def __init__(self, root, catalog, secret=None):
        self.root, self.catalog, self.secret = root, catalog, secret
        self.path = root / 'documentacion.json'
        self._huella = None
        self._leido = False

    def read(self):
        self._leido = False
        try:
            raw = leer_bytes_opcionales(self.path)
            if raw is None:
                self._huella, self._leido = None, True
                return {'formato': 1, 'tecnologias': {}, 'servicios': {}}
            value = json.loads(raw.decode('utf-8'))
            self.validate(value)
            for _, _, entry in entradas_registradas(value):
                for source in entry['fuentes']:
                    source.setdefault('origen', 'catalogo')
                    source.setdefault('oficial', True)
            self._huella, self._leido = huella_bytes(raw), True
            return value
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
            block('REGISTRO', causa_os('documentacion.json es ilegible o tiene otro esquema; no se reconstruye adivinando.', error))

    def validate(self, data):
        if not isinstance(data, dict) or type(data.get('formato')) is not int or data['formato'] not in (1, 2):
            raise ValueError()
        if not isinstance(data.get('tecnologias'), dict) or not isinstance(data.get('servicios'), dict):
            raise ValueError()
        notebooks = set()
        for tech, group in data['tecnologias'].items():
            if not isinstance(tech, str) or not isinstance(group, dict) or not isinstance(group.get('versiones'), dict):
                raise ValueError()
            retired = group.get('retirados', [])
            if not isinstance(retired, list) or any(not isinstance(e, dict) or e.get('estado') != 'retirado' or not isinstance(e.get('version'), str) for e in retired):
                raise ValueError()
            entries = list(group['versiones'].items()) + [(e['version'], e) for e in retired]
            for expected, entry in entries:
                version(expected, tech == 'jdk')
                if not isinstance(entry.get('notebook'), str) or not entry['notebook'].startswith('notebook:') or entry.get('estado') not in ('activo', 'archivado', 'retirado') or not isinstance(entry.get('fuentes'), list):
                    raise ValueError()
                if entry['notebook'] in notebooks:
                    raise ValueError()
                notebooks.add(entry['notebook'])
                seen = set()
                for source in entry['fuentes']:
                    if not isinstance(source.get('id'), str) or not source['id'].startswith('source:') or source['id'] in seen:
                        raise ValueError()
                    seen.add(source['id'])
                    origin = source.get('origen', 'catalogo')
                    if origin not in ('catalogo', 'usuario-url', 'usuario-archivo') or type(source.get('oficial', True)) is not bool:
                        raise ValueError()
                    if origin == 'usuario-archivo':
                        name = source.get('archivo')
                        if data['formato'] != 2 or not isinstance(name, str) or not name or '/' in name or '\\' in name or name in ('.', '..') or source.get('url') or not re.fullmatch(r'[a-f0-9]{64}', str(source.get('archivo_sha256', ''))):
                            raise ValueError()
                    else:
                        url = urllib.parse.urlsplit(source['url'])
                        if url.scheme != 'https' or not url.hostname or url.username or url.password:
                            raise ValueError()
                    if type(source.get('retirada', False)) is not bool or (source.get('retirada') and source.get('valida')):
                        raise ValueError()
                    if type(source.get('valida')) is not bool or source.get('tipo') not in SOURCE_TYPES:
                        raise ValueError()
                    if source['valida'] and (not re.fullmatch(r'[a-f0-9]{64}', str(source.get('sha256', ''))) or not fuente_compatible(tech, expected, source)):
                        raise ValueError()
        resolutions = data.get('resoluciones_bom', {})
        if not isinstance(resolutions, dict):
            raise ValueError()
        for service_name, technologies in resolutions.items():
            if not isinstance(service_name, str) or not isinstance(technologies, dict):
                raise ValueError()
            for tech, resolution in technologies.items():
                if not isinstance(resolution, dict) or resolution.get('bom') not in BOMS_ADMITIDAS or not re.fullmatch(r'[a-zA-Z0-9_.-]+', str(resolution.get('propiedad', ''))) or not re.fullmatch(r'[a-f0-9]{64}', str(resolution.get('sha256_pom', ''))):
                    raise ValueError()
                version(resolution['version'])
                version(resolution['version_bom'])
                expected_url = url_pom_bom(resolution['bom'], resolution['version_bom'])
                if resolution.get('url_pom') != expected_url or not isinstance(resolution.get('dependencia'), str):
                    raise ValueError()
        for name, service in data['servicios'].items():
            if not isinstance(name, str) or not name or name == '..' or '/' in name or '\\' in name or service.get('ruta') != name or not isinstance(service.get('tecnologias'), dict):
                raise ValueError()
            for tech, binding in service['tecnologias'].items():
                if not isinstance(binding, dict) or binding.get('estado') not in ('asociado', 'pendiente', 'sin_documentacion'):
                    raise ValueError()
                if binding['estado'] == 'asociado':
                    if binding.get('version_documentacion') not in data['tecnologias'].get(tech, {}).get('versiones', {}):
                        raise ValueError()
                elif binding.get('version_documentacion') is not None:
                    raise ValueError()

    def usages(self, data=None):
        data = self.read() if data is None else data
        return tecnologias_usadas(inventario_local(self.root), self.catalog, data.get('resoluciones_bom', {}))

    def check(self, data=None, usages=None):
        data = self.read() if data is None else data
        usages = self.usages(data) if usages is None else usages
        errors, warnings = [], []
        required = self.catalog['tecnologias']
        prepare = 'lanza .agents/workflows/preparar-documentacion.md.'
        if not self.path.exists() and any(t in required for ts in usages.values() for t in ts):
            errors.append('DOCUMENTACION_FALTA: no existe .agents/documentacion.json; ' + prepare)
        for service, technologies in usages.items():
            bindings = data['servicios'].get(service, {}).get('tecnologias', {})
            for tech, project in technologies.items():
                if tech not in required:
                    warning = tech + ' no está en el catálogo de documentación; si la tarea la usa, añádela al catálogo con la sección "Ampliar el catálogo del proyecto" de .agents/workflows/preparar-documentacion.md'
                    if warning not in warnings:
                        warnings.append(warning)
                    continue
                for declaration in project.get('declaraciones', []):
                    if declaration.get('aviso_bom') and declaration['aviso_bom'] not in warnings:
                        warnings.append(declaration['aviso_bom'])
                    if declaration.get('error_bom'):
                        error = 'DOCUMENTACION_VERSION: ' + service + ': ' + tech + ' ' + declaration['error_bom']
                        if error not in errors:
                            errors.append(error)
                prefix = service + ': ' + tech + ' ' + str(project.get('version') or 'no_resoluble')
                origen_bom = next((d.get('origen_bom') for d in project.get('declaraciones', []) if d.get('origen_bom')), None)
                if origen_bom:
                    prefix += ' (desde ' + origen_bom + ')'
                if project['estado'] != 'literal':
                    errors.append('DOCUMENTACION_VERSION: ' + prefix + ' tiene versión no_resoluble; prepara su resolución documental con aprobación. Si está gestionada, usa la propiedad publicada de la BOM mediante resolver-bom; no fijes una versión en el build para superar este control.')
                    continue
                binding = bindings.get(tech, {})
                if binding.get('estado') == 'sin_documentacion':
                    errors.append('DOCUMENTACION_OBLIGATORIA: ' + prefix + ' tiene un vínculo histórico sin_documentacion; asocia fuentes válidas, sin borrar el registro; ' + prepare)
                    continue
                if binding.get('estado') != 'asociado':
                    errors.append('DOCUMENTACION_FALTA: ' + prefix + ' no tiene documentación asociada; ' + prepare)
                    continue
                entry = data['tecnologias'][tech]['versiones'][binding['version_documentacion']]
                if entry['estado'] == 'retirado':
                    errors.append('DOCUMENTACION_FALTA: ' + prefix + ' está retirada; prepara y carga de nuevo; ' + prepare)
                    continue
                if entry['estado'] == 'archivado':
                    errors.append('DOCUMENTACION_FALTA: ' + prefix + ' está archivada; reactívala con aprobación; ' + prepare)
                    continue
                valid = [source for source in entry['fuentes'] if source['valida']]
                if not valid:
                    errors.append('DOCUMENTACION_FALTA: ' + prefix + ' no tiene fuentes válidas; ' + prepare)
                for source in valid:
                    if not fuente_compatible(tech, project['version'], source):
                        errors.append('DOCUMENTACION_VERSION: ' + prefix + ' documentación=' + str(source['version_principal']) + ' (' + source['tipo'] + '); ' + prepare)
        for tech, group in data['tecnologias'].items():
            for expected, entry in group['versiones'].items():
                used = any(tech in technologies and any(fuente_compatible(tech, technologies[tech]['version'], source) for source in entry['fuentes'] if source['valida']) for technologies in usages.values())
                if entry['estado'] == 'activo' and not used:
                    warnings.append(tech + ' ' + expected + ' no tiene servicios que usen esa versión; propón archivarla con aprobación.')
        if errors:
            errors.append('Opciones: prepara o cambia la documentación y sus fuentes; o cambia las versiones mediante un plan aprobado, editando tú las claves de stack.yaml que correspondan.')
        return {'errores': errors, 'avisos': warnings}

    def markdown(self, data, usages):
        clean = lambda value: str(value if value is not None else '—').replace('|', '\\|').replace('\n', ' ')
        lines = ['# Documentación del proyecto', '', 'Generado desde documentacion.json; no editar a mano.',
                 'Versiones del proyecto observadas en la última escritura. El cotejo local vuelve a compararlas; el preflight comprueba además conexión e IDs por GET.', '',
                 '| Servicio | Tecnología | Versión en el proyecto | Versión de documentación | Estado |', '|---|---|---|---|---|']
        names = sorted(set(usages) | set(data['servicios']))
        for name in names:
            bindings = data['servicios'].get(name, {}).get('tecnologias', {})
            for tech in sorted(set(usages.get(name, {})) | set(bindings)):
                project = usages.get(name, {}).get(tech, {})
                binding = bindings.get(tech, {})
                doc_version = binding.get('version_documentacion')
                entry = data['tecnologias'].get(tech, {}).get('versiones', {}).get(doc_version)
                status = binding.get('estado', 'pendiente')
                if not project:
                    status = 'retirada; proponer archivado'
                elif project.get('estado') != 'literal':
                    status = 'no_resoluble'
                elif entry:
                    status = entry['estado']
                    if entry['estado'] == 'retirado':
                        status = 'retirado; prepara y carga de nuevo'
                    elif any(not fuente_compatible(tech, project['version'], s) for s in entry['fuentes'] if s['valida']):
                        status = 'incompatible'
                    elif entry['estado'] == 'activo':
                        status = 'compatible' if any(s['valida'] for s in entry['fuentes']) else 'sin fuentes válidas'
                lines.append('| ' + ' | '.join(map(clean, [name, tech, project.get('version'), doc_version, status])) + ' |')
        lines.extend(['', '## Notebooks registrados', '', '| Tecnología | Versión | Notebook | Estado |', '|---|---|---|---|'])
        for tech, group in sorted(data['tecnologias'].items()):
            for expected, entry in sorted(group['versiones'].items()):
                lines.append('| ' + ' | '.join(map(clean, [tech, expected, entry['notebook'], entry['estado']])) + ' |')
            for entry in group.get('retirados', []):
                lines.append('| ' + ' | '.join(map(clean, [tech, entry['version'], entry['notebook'], 'retirado (historial)'])) + ' |')
        return '\n'.join(lines) + '\n'

    def preparar_guardado(self, data, actualizado_en=None):
        data['formato'] = 2
        for _, _, entry in entradas_registradas(data):
            for source in entry['fuentes']:
                source.setdefault('origen', 'catalogo')
                source.setdefault('oficial', True)
        self.validate(data)
        data['actualizado_en'] = actualizado_en or datetime.now(timezone.utc).isoformat()
        payload = json.dumps(data, ensure_ascii=False, indent=2) + '\n'
        if self.secret and self.secret in payload:
            block('RESPUESTA', 'El registro contiene información protegida; no se guarda.')
        return payload

    def preparar_archivos(self, data, actualizado_en=None):
        try:
            payload = self.preparar_guardado(data, actualizado_en)
            return payload, self.markdown(data, self.usages(data))
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
            block('REGISTRO', causa_os('No se pudo preparar documentacion.json y su Markdown; revisa el registro sin sobrescribirlo a mano.', error))

    def save(self, data, *, actualizado_en=None):
        try:
            payload, markdown = self.preparar_archivos(data, actualizado_en)
            staged = []
            try:
                for name, content in [('documentacion.md', markdown), ('documentacion.json', payload)]:
                    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=self.root, prefix='.documentacion-', delete=False) as stream:
                        staged.append((Path(stream.name), self.root / name))
                        stream.write(content)
                if not self._leido:
                    block('REGISTRO', 'Lee el registro antes de guardarlo.')
                comprobar_huella(self.path, self._huella, 'REGISTRO_CAMBIADO', 'documentacion.json')
                for temporary, target in staged:
                    os.replace(temporary, target)
                self._huella = hashlib.sha256(payload.encode('utf-8')).hexdigest()
            finally:
                for temporary, _ in staged:
                    temporary.unlink(missing_ok=True)
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
            block('REGISTRO', causa_os('No se pudo guardar documentacion.json y su Markdown; revisa el registro sin sobrescribirlo a mano.', error))

    def comprobar_notebook_no_retirado(self, data, notebook):
        if any(e['notebook'] == notebook and e['estado'] == 'retirado' for _, _, e in entradas_registradas(data)):
            block('REGISTRO', 'Ese ID de notebook está retirado; prepara y carga de nuevo en otro notebook.')

    def book(self, data, tech, expected, notebook, state='activo'):
        self.comprobar_notebook_no_retirado(data, notebook)
        group = data['tecnologias'].setdefault(tech, {'versiones': {}})
        entry = group['versiones'].get(expected)
        if entry and entry['notebook'] != notebook:
            if entry['estado'] != 'retirado':
                block('REGISTRO', 'Ya hay otro notebook registrado para esa tecnología y versión; revisa antes de sustituirlo.')
            group.setdefault('retirados', []).append(dict(entry, version=expected))
            entry = None
        if entry is None:
            entry = {'notebook': notebook, 'estado': state, 'fuentes': []}
            group['versiones'][expected] = entry
        entry['estado'] = state
        return entry

    def source(self, meta, notebook, record, source):
        with bloqueo_agents(self.root):
            data = self.read()
            entry = self.book(data, meta['tecnologia'], meta['version'], notebook)
            item = {'id': record['fuente'], 'url': record.get('url'), 'tipo': record['tipo'], 'valida': bool(record.get('valida')),
                    'version_principal': (record.get('principal') or {}).get('version'), 'referenciadas': record.get('referenciadas', []),
                    'sha256': record.get('sha256'), 'motivo': record.get('motivo'), 'embedded': source.get('embedded') is True,
                    'embedded_chunks': source.get('embedded_chunks', 0)}
            for key in ('origen', 'oficial', 'archivo', 'archivo_sha256', 'contenido_sha256', 'mime', 'tamano', 'confirmada_usuario', 'evidencia_previa', 'procedencia_url', 'aprobacion_sha256', 'entrada'):
                if key in record:
                    item[key] = record[key]
            entry['fuentes'] = [s for s in entry['fuentes'] if s['id'] != item['id']] + [item]
            self.save(data)

    def diff_registro(self, data):
        payload, markdown = self.preparar_archivos(copy.deepcopy(data))
        old_payload = leer_bytes_opcionales(self.path)
        old_md = leer_bytes_opcionales(self.root / 'documentacion.md')
        old_payload_text = old_payload.decode('utf-8') if old_payload is not None else ''
        old_md_text = old_md.decode('utf-8') if old_md is not None else ''
        from_json = 'documentacion.json' if old_payload is not None else '/dev/null'
        from_md = 'documentacion.md' if old_md is not None else '/dev/null'
        diff_json = ''.join(difflib.unified_diff(old_payload_text.splitlines(True), payload.splitlines(True), fromfile=from_json, tofile='documentacion.json'))
        diff_md = ''.join(difflib.unified_diff(old_md_text.splitlines(True), markdown.splitlines(True), fromfile=from_md, tofile='documentacion.md'))
        return {'diff': diff_json, 'diff_documentacion_md': diff_md}

    def _apply_associate(self, data, service, tech, expected, remove=False, without=False, reason=None):
        if without and tech in self.catalog['tecnologias']:
            block('DOCUMENTACION_OBLIGATORIA', 'Esta tecnología está en el catálogo; asocia fuentes válidas mediante preparar-documentacion.md. No puedes omitir su documentación.')
        usages = self.usages(data)
        if remove:
            if service not in data['servicios']:
                block('SERVICIO', 'El servicio no está registrado.')
            data['servicios'][service]['tecnologias'].pop(tech, None)
        else:
            if service not in usages or tech not in usages[service]:
                block('SERVICIO_TECNOLOGIA', 'El servicio no usa esa tecnología según el inventario local.')
            project = usages[service][tech]
            if not without:
                entry = data['tecnologias'].get(tech, {}).get('versiones', {}).get(expected)
                if entry and entry['estado'] == 'retirado':
                    block('DOCUMENTACION_FALTA', 'El notebook está retirado; prepara y carga de nuevo.')
                if not entry or entry['estado'] != 'activo' or not any(s['valida'] for s in entry['fuentes']):
                    block('DOCUMENTACION', 'Prepara documentación válida de esa versión antes de asociarla.')
                if project['estado'] != 'literal' or any(not fuente_compatible(tech, project['version'], s) for s in entry['fuentes'] if s['valida']):
                    block('VERSION', 'La documentación no se puede cotejar con la versión del servicio; requiere un plan aprobado.')
            data['servicios'].setdefault(service, {'ruta': service, 'tecnologias': {}})['tecnologias'][tech] = {
                'version_proyecto_al_asociar': project['version'], 'version_documentacion': None if without else expected,
                'estado': 'sin_documentacion' if without else 'asociado', 'motivo': reason or 'Decisión explícita del usuario.', 'confirmada': True}
        return {'servicio': service, 'tecnologia': tech, 'version_documentacion': expected if not remove and not without else None}

    def associate(self, service, tech, expected, confirmed, remove=False, without=False, reason=None):
        if not confirmed:
            with bloqueo_agents(self.root):
                data = self.read()
                result = self._apply_associate(data, service, tech, expected, remove, without, reason)
                preview = self.diff_registro(data)
            return {'confirmado': False, **result, **preview}
        with bloqueo_agents(self.root):
            data = self.read()
            result = self._apply_associate(data, service, tech, expected, remove, without, reason)
            self.save(data)
        return {'confirmado': True, **result}

    def resolve(self, service, tech, supplied):
        data = self.read()
        usages = self.usages(data)
        if service not in usages or tech not in usages[service]:
            block('SERVICIO_TECNOLOGIA', 'El servicio no usa esa tecnología según el inventario local.')
        binding = data['servicios'].get(service, {}).get('tecnologias', {}).get(tech)
        if not binding or binding['estado'] != 'asociado':
            block('DOCUMENTACION', 'No hay documentación asociada a esa tecnología del servicio.')
        expected = binding['version_documentacion']
        entry = data['tecnologias'][tech]['versiones'][expected]
        project = usages[service][tech]
        if supplied is not None and supplied != expected:
            block('VERSION', 'La versión indicada no coincide con la documentación asociada al servicio.')
        if entry['estado'] == 'retirado':
            block('DOCUMENTACION_FALTA', 'El notebook está retirado; prepara y carga de nuevo.')
        if entry['estado'] != 'activo' or not any(s['valida'] for s in entry['fuentes']):
            block('DOCUMENTACION', 'La documentación asociada no está activa o carece de fuentes válidas.')
        if project['estado'] != 'literal' or any(not fuente_compatible(tech, project['version'], s) for s in entry['fuentes'] if s['valida']):
            block('VERSION', 'La documentación ya no corresponde a la versión del servicio; requiere un plan aprobado.')
        return expected, entry


class Client:
    def __init__(self):
        self.root = Path(__file__).resolve().parents[1]
        reader = self.root / 'scripts/stack.mjs'
        command = ['node', str(reader)] if reader.exists() else [sys.executable, '-B', '-E', str(self.root / 'scripts/stack.py')]
        def get(key):
            result = subprocess.run(command + ['get', key], capture_output=True, text=True, timeout=15)
            if result.returncode:
                block('CONFIGURACION', 'Revisa la clave ' + key + ' con el validador del stack.')
            return result.stdout.strip() or None
        self.config = {key: get('documentacion.' + key) for key in KEYS}
        timeout = self.config['timeout_chat'] or ''
        if not re.fullmatch(r'[1-9][0-9]*', timeout) or int(timeout) > 3600:
            block('CONFIGURACION', 'documentacion.timeout_chat debe ser un entero entre 1 y 3600 segundos.')
        self.timeout_chat = int(timeout)
        self.base = (self.config['url_api'] or '').rstrip('/')
        parsed = urllib.parse.urlsplit(self.base)
        if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            block('CONFIGURACION', 'url_api debe ser una dirección HTTP(S) sin credenciales ni parámetros.')
        self.secret = None
        env = self.config['variable_password']
        if env:
            if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', env):
                block('CONFIGURACION', 'variable_password solo admite el nombre de una variable.')
            self.secret = os.environ.get(env)
            if not self.secret:
                block('AUTENTICACION', 'Falta o está vacía la variable nombrada por documentacion.variable_password; configúrala y repite.')
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        self.catalog = cargar_catalogo(self.root)
        self.warnings = []
        self.public = PublicHTTP()
        self.registro = Registro(self.root, self.catalog, self.secret)
        if parsed.scheme == 'http' and parsed.hostname not in ('localhost', '127.0.0.1', '::1'):
            self.warnings.append('HTTP fuera del equipo local: revisa la protección de la API.')

    def request(self, method, path, payload=None, anonymous=False, timeout_override=None, multipart=None):
        headers = {'Accept': 'application/json'}
        if self.secret and not anonymous:
            headers['Authorization'] = 'Bearer ' + self.secret
        data = None if payload is None else json.dumps(payload).encode()
        if data is not None:
            headers['Content-Type'] = 'application/json'
        if multipart is not None:
            data, headers['Content-Type'] = multipart
        req = urllib.request.Request(self.base + path, data=data, headers=headers, method=method)
        model_request = method == 'POST' and (path in ('/api/chat/execute', '/api/search/ask/simple') or (path == '/api/search' and isinstance(payload, dict) and payload.get('type') == 'vector') or re.fullmatch(r'/api/sources/[^/]+/insights', path) is not None)
        timeout = self.timeout_chat * 3 if method == 'POST' and path == '/api/search/ask/simple' else self.timeout_chat if model_request else TIMEOUT
        if timeout_override is not None:
            timeout = timeout_override
        try:
            with self.opener.open(req, timeout=timeout) as response:
                raw = response.read(8_000_001)
                if len(raw) > 8_000_000:
                    block('TAMANO', 'La respuesta de la API supera el límite de lectura.')
                value = json.loads(raw) if raw else {}
                if self.secret and self.secret in json.dumps(value, ensure_ascii=False):
                    block('RESPUESTA', 'La API reflejó información protegida; respuesta descartada antes de guardarla.')
                return value
        except urllib.error.HTTPError as error:
            # Nunca mostrar cuerpo, URL completa, cabeceras ni el texto de la excepción.
            if error.code in (401, 403):
                block('AUTENTICACION', 'Open Notebook rechazó el acceso (HTTP ' + str(error.code) + '); revisa documentacion.variable_password y tu variable de entorno. No se muestran sus valores.')
            if error.code == 413:
                block('CONTEXTO', 'El contexto supera el tamaño admitido por la API.')
            if error.code == 422 and model_request and path != '/api/search':
                block('MODELO_CONFIG', 'Open Notebook rechazó el modelo configurado (HTTP 422); revisa el modelo por defecto o el proveedor. No se reintenta.')
            if error.code == 429:
                block('LIMITE_USO', 'Open Notebook devolvió HTTP 429 (límite de uso); revisa el límite o la cuota. No se reintenta.')
            if error.code in (400, 422):
                block('PETICION', 'La API rechazó el formato o tamaño de la petición; revisa el contrato REST.')
            if error.code >= 500 and model_request:
                block('MODELO_FALLO', 'El servidor devolvió HTTP ' + str(error.code) + ' al responder, transformar o buscar vectores; no se reintenta ni se muestra su cuerpo.')
            block('API_HTTP', 'Recibiste HTTP ' + str(error.code) + ' de la API; revisa su estado. No se reintenta.', error.code)
        except urllib.error.URLError as error:
            if model_request and isinstance(error.reason, TimeoutError):
                block('MODELO_TIMEOUT', 'Se agotó la espera de ' + str(timeout) + ' s del modelo; no se reintenta.')
            block('API_CAIDA', 'Open Notebook no responde en el plazo de ' + str(timeout) + ' s; arráncalo y repite el preflight. Si Open Notebook está arrancado, puede que tu herramienta bloquee la red local; ejecuta el comando fuera de su aislamiento.')
        except TimeoutError:
            if model_request:
                block('MODELO_TIMEOUT', 'Se agotó la espera de ' + str(timeout) + ' s del modelo; no se reintenta.')
            block('API_CAIDA', 'Open Notebook no responde en el plazo de ' + str(timeout) + ' s; arráncalo y repite el preflight. Si Open Notebook está arrancado, puede que tu herramienta bloquee la red local; ejecuta el comando fuera de su aislamiento.')
        except OSError:
            block('API_CAIDA', 'No puedes conectar con Open Notebook; arráncalo y repite el preflight. Si Open Notebook está arrancado, puede que tu herramienta bloquee la red local; ejecuta el comando fuera de su aislamiento.')
        except (ValueError, UnicodeError):
            block('API_FORMATO', 'La API no devolvió JSON válido.')

    def items(self, path):
        result = self.request('GET', path)
        if isinstance(result, list):
            return result
        if isinstance(result, dict):
            for key in ('items', 'notebooks', 'notes', 'models', 'transformations', 'insights', 'sources'):
                if isinstance(result.get(key), list):
                    return result[key]
        block('API_FORMATO', 'La API no devolvió una lista reconocible.')

    def connection(self):
        result = self.request('GET', '/api/models/defaults', timeout_override=CONNECTION_TIMEOUT)
        fields = ('default_chat_model', 'default_embedding_model', 'default_transformation_model')
        if not isinstance(result, dict) or any(field not in result for field in fields) or any(result[field] is not None and not isinstance(result[field], str) for field in fields):
            block('API_FORMATO', 'No recibiste los metadatos esperados; revisa documentacion.url_api y la compatibilidad de la API.')
        if self.secret is None:
            self.warnings.append('La API respondió sin contraseña; revisa su exposición en la red.')
        return {'conexion': 'ok', 'plazo_segundos': CONNECTION_TIMEOUT,
                'mensaje': 'Open Notebook responde; comprobación de metadatos sin modelos ni cambios.'}

    def remote_documentation(self):
        data = self.registro.read()
        usages = self.registro.usages(data)
        local = self.registro.check(data, usages)
        if local['errores']:
            block('DOCUMENTACION_FALTA', 'Completa el cotejo local antes de comprobar IDs remotos; lanza .agents/workflows/preparar-documentacion.md.')
        checked_books, checked_sources = {}, {}
        required = self.catalog['tecnologias']
        for service, technologies in usages.items():
            bindings = data['servicios'].get(service, {}).get('tecnologias', {})
            for tech in technologies:
                if tech not in required:
                    continue
                binding = bindings.get(tech, {})
                if binding.get('estado') != 'asociado':
                    continue  # El cotejo local estricto informa del vínculo faltante.
                entry = data['tecnologias'][tech]['versiones'][binding['version_documentacion']]
                identifier = entry['notebook']
                if identifier not in checked_books:
                    checked_books[identifier] = self.remote_item('/api/notebooks/', identifier)
                book = checked_books[identifier]
                if book is None or book.get('archived') is not False:
                    block('DOCUMENTACION_FALTA', service + ': ' + tech + ': no tienes el notebook activo; lanza .agents/workflows/preparar-documentacion.md.')
                existing = False
                for source in entry['fuentes']:
                    if not source['valida']:
                        continue
                    sid = source['id']
                    if sid not in checked_sources:
                        checked_sources[sid] = self.remote_item('/api/sources/', sid)
                    value = checked_sources[sid]
                    if value is not None:
                        existing = True
                if not existing:
                    block('DOCUMENTACION_FALTA', service + ': ' + tech + ': no tienes fuentes válidas registradas que sigan existiendo; lanza .agents/workflows/preparar-documentacion.md.')
        return {'notebooks_comprobados': sorted(checked_books), 'fuentes_comprobadas': sorted(checked_sources)}

    def remote_item(self, prefix, identifier):
        try:
            value = self.request('GET', prefix + urllib.parse.quote(identifier, safe=''), timeout_override=CONNECTION_TIMEOUT)
        except Blocked as error:
            if error.code == 'API_HTTP' and error.http_status == 404:
                return None
            raise
        if not isinstance(value, dict) or value.get('id') != identifier:
            block('API_FORMATO', 'No recibiste los metadatos del ID solicitado; revisa la compatibilidad de la API.')
        return value

    def notebook_remoto(self, identifier):
        value = self.remote_item('/api/notebooks/', identifier)
        if value is None:
            block('NOTEBOOK_AUSENTE', 'El notebook ya no existe; usa documentacion.py retirar-ausentes, después preparar y cargar.')
        return value

    def fuente_remota(self, identifier):
        value = self.remote_item('/api/sources/', identifier)
        if value is None:
            self.fuente_ausente()
        return value

    def fuente_ausente(self):
        block('FUENTE_AUSENTE', 'La fuente ya no está disponible; revisa documentacion.py retirar-ausentes (vista previa y --confirmar), después prepara/carga de nuevo y asocia.')

    def ausencias_registradas(self, data, notebook=None):
        entries = [e for _, _, e in entradas_registradas(data) if notebook is None or e['notebook'] == notebook]
        if notebook is not None and not entries:
            block('REGISTRO', 'El notebook indicado no está registrado.')
        books, sources = {}, {}
        for entry in entries:
            identifier = entry['notebook']
            if identifier not in books:
                books[identifier] = self.remote_item('/api/notebooks/', identifier)
            for source in entry['fuentes']:
                identifier = source['id']
                if identifier not in sources:
                    sources[identifier] = self.remote_item('/api/sources/', identifier)
        return {'notebooks': sorted(k for k, v in books.items() if v is None),
                'fuentes': sorted(k for k, v in sources.items() if v is None)}

    def listar_ausentes(self):
        return {'ausentes': self.ausencias_registradas(self.registro.read())}

    def retirar_ausentes(self, notebook=None, confirmed=False):
        with bloqueo_agents(self.root):
            data = self.registro.read()
            absent = self.ausencias_registradas(data, notebook)
            changed = False
            affected = set()
            for tech, expected, entry in entradas_registradas(data):
                if notebook is not None and entry['notebook'] != notebook:
                    continue
                if entry['notebook'] in absent['notebooks']:
                    if entry['estado'] != 'retirado':
                        entry['estado'] = 'retirado'
                        changed = True
                    affected.add((tech, expected, entry['notebook']))
                else:
                    for source in entry['fuentes']:
                        if source['id'] in absent['fuentes']:
                            updates = {'valida': False, 'motivo': 'FUENTE_AUSENTE', 'retirada': True}
                            if any(source.get(k) != v for k, v in updates.items()):
                                source.update(updates)
                                changed = True
                    if any(s['id'] in absent['fuentes'] for s in entry['fuentes']) and not any(s['valida'] for s in entry['fuentes']):
                        affected.add((tech, expected, entry['notebook']))
            for service in data['servicios'].values():
                for tech, binding in service['tecnologias'].items():
                    expected = binding.get('version_documentacion')
                    current = data['tecnologias'].get(tech, {}).get('versiones', {}).get(expected)
                    if current and (tech, expected, current['notebook']) in affected and binding['estado'] == 'asociado':
                        binding.update(estado='pendiente', version_documentacion=None)
                        changed = True
            preview = {'diff': '', 'diff_documentacion_md': ''}
            if changed:
                if confirmed:
                    self.registro.save(data)
                else:
                    preview = self.registro.diff_registro(data)
            return {'confirmado': confirmed, 'ausentes': absent, 'cambios': changed, **preview}

    def defaults(self):
        return self.request('GET', '/api/models/defaults')

    def model(self, kind):
        field = {'chat': 'modelo_chat', 'large_context': 'modelo_contexto_grande', 'transformation': 'modelo_transformacion'}[kind]
        selected = self.config[field]
        if not selected:
            defaults = self.defaults()
            selected = defaults.get('large_context_model' if kind == 'large_context' else 'default_' + kind + '_model')
        models = self.items('/api/models')
        if not selected or not any(m.get('id') == selected for m in models):
            block('MODELO', 'Falta un modelo configurado para ' + kind + '; configúralo en Open Notebook.')
        return selected

    def embedding_configured(self, defaults=None, models=None):
        defaults = self.defaults() if defaults is None else defaults
        models = self.items('/api/models') if models is None else models
        selected = defaults.get('default_embedding_model')
        return any(m.get('id') == selected and m.get('type') == 'embedding' for m in models)

    def vector_search(self, notebook, question, limit):
        if not isinstance(notebook, str) or not notebook:
            block('NOTEBOOK', 'La búsqueda vectorial exige un notebook concreto.')
        result = self.request('POST', '/api/search', {'query': question, 'type': 'vector',
            'notebook_id': notebook, 'search_sources': True, 'search_notes': False,
            'limit': limit, 'minimum_score': MINIMUM_VECTOR_SCORE})
        if isinstance(result, list):
            return result
        if isinstance(result, dict) and isinstance(result.get('results'), list):
            return result['results']
        block('API_FORMATO', 'La búsqueda vectorial no devolvió una lista de resultados reconocible.')

    def embedding_probe(self, notebook, meta, configured=None):
        try:
            available = self.embedding_configured() if configured is None else configured
            if not available:
                return {'embeddings_utilizables': False, 'error': 'EMBEDDINGS_NO_CONFIGURADOS'}
            # La consulta genera un vector incluso si aún no hay fragmentos indexados.
            query = 'Capacidades de ' + self.catalog['tecnologias'][meta['tecnologia']] + ' ' + meta['version']
            self.vector_search(notebook, query, 1)
            return {'embeddings_utilizables': True}
        except Blocked as error:
            return {'embeddings_utilizables': False, 'error': error.code}

    def state(self, notebook=None, prefix=None):
        defaults = self.defaults()
        models = self.items('/api/models')
        try:
            self.request('GET', '/api/models/defaults', anonymous=True)
            self.warnings.append('La API admite acceso sin contraseña; revisa su exposición en la red.')
            anonymous = True
        except Blocked as error:
            if error.code != 'AUTENTICACION':
                raise
            anonymous = False
        configured = self.embedding_configured(defaults, models)
        probes = []
        # Solo metadatos para seleccionar notebooks administrados del catálogo del stack.
        for nb in self.items('/api/notebooks'):
            if notebook is not None and nb.get('id') != notebook:
                continue
            if prefix is not None and not str(nb.get('name', '')).startswith(prefix):
                continue
            try:
                meta = json.loads(nb['description'])
            except (KeyError, TypeError, ValueError):
                continue
            if not isinstance(meta, dict) or meta.get('administrado_por') != OWNER or nb.get('archived') or meta.get('tecnologia') not in self.catalog['tecnologias']:
                continue
            if not isinstance(meta.get('version'), str) or not meta['version']:
                continue
            probes.append({'notebook': nb['id'], 'tecnologia': meta['tecnologia'], 'version': meta['version'],
                           **self.embedding_probe(nb['id'], meta, configured)})
        usable = all(p['embeddings_utilizables'] for p in probes) if probes else 'no comprobado'
        return {'modelos': {k: defaults.get('large_context_model' if k == 'large_context' else 'default_' + k + '_model') for k in ('chat', 'embedding', 'transformation', 'large_context')},
                'embeddings_configurados': configured, 'embeddings_utilizables': usable,
                'sondas': probes, 'sin_password': anonymous}

    def notebook(self, identifier):
        # Solo se obtiene el notebook solicitado, nunca el contenido de otros notebooks.
        nb = self.notebook_remoto(identifier)
        try:
            meta = json.loads(nb['description'])
        except (ValueError, KeyError, TypeError):
            block('PROPIEDAD', 'El notebook no tiene una descripción administrada compatible.')
        if meta.get('administrado_por') != OWNER or nb.get('archived'):
            block('PROPIEDAD', 'El notebook no está activo o no pertenece a esta documentación.')
        return nb, meta

    def prepare(self, tech, expected, prefix, reactivate=False, confirmed=False):
        if tech not in self.catalog['tecnologias']:
            block('TECNOLOGIA', 'La tecnología no pertenece al catálogo de este stack.')
        version(expected, tech == 'jdk')
        if prefix and prefix not in ('[prueba 08f] ', '[prueba 08g] '):
            block('PREFIJO', 'Solo se permite el prefijo reservado de prueba.')
        title = prefix + self.catalog['tecnologias'][tech] + ' ' + expected
        meta = {'administrado_por': OWNER, 'tecnologia': tech, 'version': expected}
        candidates = [n for n in self.items('/api/notebooks') if n.get('name') == title]
        if len(candidates) > 1:
            block('DUPLICADO', 'Hay varios notebooks con ese nombre; decide cuál usar.')
        if candidates:
            self.registro.comprobar_notebook_no_retirado(self.registro.read(), candidates[0]['id'])
            nb = self.notebook_remoto(candidates[0]['id'])
            try:
                existing = json.loads(nb['description'])
            except (KeyError, ValueError, TypeError):
                block('PROPIEDAD', 'La descripción no pertenece a documentación administrada.')
            if existing != meta:
                block('PROPIEDAD', 'La descripción no coincide; no se modifica ese notebook.')
            if nb.get('archived'):
                if not reactivate or not confirmed:
                    block('APROBACION', 'Reactivar el notebook requiere aprobación; añade --reactivar --confirmar.')
                with bloqueo_agents(self.root):
                    data = self.registro.read()
                    self.registro.book(data, tech, expected, nb['id'])
                self.request('PUT', '/api/notebooks/' + urllib.parse.quote(nb['id'], safe=''), {'archived': False})
                with bloqueo_agents(self.root):
                    data = self.registro.read()
                    self.registro.book(data, tech, expected, nb['id'])
                    self.registro.save(data)
        else:
            nb = None
        prompt = (self.root / 'assets/documentacion/capacidades-version.md').read_text()
        transforms = [t for t in self.items('/api/transformations') if t.get('name') == NAME]
        if len(transforms) > 1 or any(t.get('prompt') != prompt or t.get('apply_default') is not False for t in transforms):
            block('TRANSFORMACION', 'La transformación existente es distinta o automática; no se modifica.')
        model = self.model('transformation')
        transformation = transforms[0] if transforms else self.request('POST', '/api/transformations', {
            'name': NAME, 'title': NAME, 'description': 'Capacidades documentadas por versión',
            'prompt': prompt, 'apply_default': False, 'model_id': model})
        if nb is None:
            nb = self.request('POST', '/api/notebooks', {'name': title, 'description': json.dumps(meta, ensure_ascii=False)})
        return {'notebook': nb['id'], 'nombre': title, 'transformacion': transformation['id'], 'modelo': model}

    def notes(self, nb):
        return self.items('/api/notes?notebook_id=' + urllib.parse.quote(nb, safe=''))

    def note(self, nb, title, content):
        return self.request('POST', '/api/notes', {'notebook_id': nb, 'title': title, 'content': json.dumps(content, ensure_ascii=False)})

    def records(self, nb, kind):
        identities = {}
        for note in self.notes(nb):
            # Search devuelve IDs, no fragmentos: recuperar el cuerpo solo en este notebook.
            if not str(note.get('title', '')).startswith(kind + ':'):
                continue
            if not isinstance(note.get('content'), str):
                note = dict(note, **self.request('GET', '/api/notes/' + urllib.parse.quote(note['id'], safe='')))
            try:
                record = json.loads(note['content'])
            except (ValueError, KeyError, TypeError):
                continue
            if not isinstance(record, dict) or record.get('administrado_por') != OWNER:
                continue
            key = record.get('fuente') if kind == 'fuente' else record.get('clave')
            identities.setdefault(key, []).append((note, record))
        records = []
        for key in sorted(identities, key=str):
            group = identities[key]
            if len(group) == 1:
                records.append(group[0][1])
                continue
            ordered = []
            for note, record in group:
                if not (note.get('created') or note.get('created_at')):
                    note = dict(note, **self.request('GET', '/api/notes/' + urllib.parse.quote(note['id'], safe='')))
                created = note.get('created') or note.get('created_at')
                try:
                    fecha = datetime.fromisoformat(created.replace('Z', '+00:00'))
                    if fecha.tzinfo is None:
                        fecha = fecha.replace(tzinfo=timezone.utc)
                    fecha = fecha.astimezone(timezone.utc)
                except (ValueError, TypeError, AttributeError):
                    block('API_FORMATO', 'Hay notas administradas repetidas de una misma fuente o clave sin fecha interpretable; revisa sus metadatos en la API antes de elegir el registro vigente.')
                ordered.append((fecha, str(note.get('id', '')), record))
            # Solo ordenar notas de la misma identidad; el ID desempata fechas idénticas.
            ordered.sort(key=lambda item: (item[0], item[1]))
            records.extend(record for _, _, record in ordered)
        return records

    def text(self, source):
        content = source.get('full_text', source.get('content'))
        if not isinstance(content, str) or not content:
            block('API_FORMATO', 'Falta el texto completo de la fuente; no se puede verificar.')
        return content

    def poll_source(self, source_id):
        deadline = time.monotonic() + JOB_TIMEOUT
        while time.monotonic() < deadline:
            source = self.fuente_remota(source_id)
            status = source.get('status', source.get('processing_status'))
            if status in ('failed', 'error'):
                block('CARGA', 'La fuente falló durante su procesamiento.')
            if status in ('completed', 'complete', 'ready') or (status is None and isinstance(source.get('full_text'), str) and source['full_text']):
                self.text(source)
                return source
            time.sleep(1)
        block('PLAZO', 'La fuente no terminó dentro del plazo; no se repite su creación.')

    def check_url(self, url, entry, meta, probe=True):
        url_publica(url)
        if entry is None:
            if probe:
                self.public.fetch(url, 'HEAD')
            return
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme != 'https' or parsed.username or parsed.password or parsed.query or parsed.fragment:
            block('URL', 'La fuente debe ser HTTPS, oficial y sin credenciales ni parámetros.')
        pattern = re.escape(entry['url'])
        pattern = re.sub(r'\\\{[^}]+\\\}', r'[^?#]+', pattern)
        if not re.fullmatch(pattern, url):
            block('URL', 'La URL no corresponde a la entrada aprobada del catálogo.')
        expected = meta['version']
        accepted = [expected] if entry['tipo'] in ('notas', 'requisitos') else [expected, version(expected, meta['tecnologia'] == 'jdk')]
        path = urllib.parse.unquote(parsed.path)
        boundary = r'(?!\d|[.\-]\d)' if entry['tipo'] in ('notas', 'requisitos') else r'(?!\d)'
        if not any(re.search(r'(?<!\d)' + re.escape(v).replace(r'\.', r'[.\-]') + boundary, path) for v in accepted):
            block('URL_VERSION', 'La URL no acredita la versión o serie prevista para este tipo de fuente.')
        if probe:
            self.public.fetch(url, 'HEAD')

    def notebook_sources(self, notebook):
        found = []
        for offset in range(0, 10000, 100):
            page = self.items('/api/sources?notebook_id=' + urllib.parse.quote(notebook, safe='')
                              + '&limit=100&offset=' + str(offset) + '&sort_by=created&sort_order=asc')
            found.extend(page)
            if len(page) < 100:
                return found
        block('LIMITE', 'No se pudo comprobar toda la lista de fuentes del notebook.')

    def load(self, identifier, url, entry_id, confirmed, negative=False, *, archivo=None, usuario_url=False,
             tipo=None, publica=False, correspondencia=False, sha_aprobado=None, procedencia=None, revalidar=False):
        if revalidar and (archivo is not None or usuario_url or not entry_id):
            block('REVALIDAR', '--revalidar solo admite URL de fuentes del catálogo.')
        if revalidar and not confirmed:
            block('APROBACION', 'Revalidar requiere --confirmar.')
        self.registro.read()
        nb, meta = self.notebook(identifier)
        if (archivo is not None) == (url is not None) or (archivo and (entry_id or usuario_url)) or (url and bool(entry_id) == bool(usuario_url)):
            block('ARGUMENTOS', 'Elige una URL con entrada de catálogo, una usuario-url o un archivo; los modos son excluyentes.')
        user_source = bool(archivo or usuario_url)
        evidence = {}
        raw = text = mime = name = None
        if user_source:
            if tipo not in SOURCE_TYPES or negative:
                block('ARGUMENTOS', 'Indica el tipo de fuente; los controles negativos no admiten fuentes del usuario.')
            entry = {'tipo': tipo}
            if archivo:
                raw, text, mime, name = leer_archivo_publico(archivo, self.root.parent, publica)
                official = es_oficial(self.catalog, meta['tecnologia'], procedencia) if procedencia else False
                if procedencia:
                    self.check_url(procedencia, None, meta)
                evidence.update(origen='usuario-archivo', archivo=name, archivo_sha256=hashlib.sha256(raw).hexdigest())
            else:
                self.check_url(url, None, meta)
                raw, detected_mime = self.public.fetch(url)
                name = Path(urllib.parse.urlsplit(url).path).name or 'documentacion'
                if Path(name).suffix.lower() not in ('.pdf', '.html', '.htm', '.md', '.markdown', '.txt', '.adoc'):
                    name += '.pdf' if detected_mime == 'application/pdf' else '.html' if detected_mime == 'text/html' else '.txt'
                text, mime = extraer_documento(raw, name, detected_mime)
                official = es_oficial(self.catalog, meta['tecnologia'], url)
                evidence.update(origen='usuario-url', url=url, contenido_sha256=hashlib.sha256(raw).hexdigest())
            check = comprobar_correspondencia(text, meta, self.catalog, tipo, correspondencia)
            evidence.update(oficial=official, mime=mime, tamano=len(raw), confirmada_usuario=bool(usuario_url and correspondencia) or check['confirmada_usuario'],
                            evidencia_previa=check, aprobacion_sha256=hashlib.sha256(raw).hexdigest())
            if procedencia:
                evidence['procedencia_url'] = procedencia
            if not official:
                self.warnings.append('FUENTE_NO_OFICIAL: La fuente no está acreditada como oficial para esta tecnología; se registrará oficial=false. Requiere aprobación expresa.')
            if not confirmed:
                return {'propuesta': evidence, 'mensaje': 'Revisa contenido, procedencia y correspondencia; aprueba este sha256 con --sha256-aprobado y --confirmar. No se cargó.'}
            if sha_aprobado != evidence['aprobacion_sha256']:
                block('APROBACION_HASH', 'La aprobación no corresponde a los bytes revisados; revisa la propuesta y confirma su sha256 antes de cargar.')
        else:
            if tipo is not None or correspondencia or sha_aprobado or procedencia or publica:
                block('ARGUMENTOS', 'Las opciones de fuentes del usuario no se aplican al catálogo.')
            if not confirmed:
                block('APROBACION', 'Carga solo URL completas que el usuario haya aprobado; añade --confirmar.')
            entry = next((e for e in self.catalog['fuentes'] if e['id'] == entry_id and e['tecnologia'] == meta['tecnologia']), None)
            if entry is None:
                block('CATALOGO', 'La entrada no pertenece a la tecnología del notebook.')
            if negative:
                if not nb.get('name', '').startswith(('[prueba 08f] ', '[prueba 08g] ')):
                    block('CONTROL', 'El control sin versión solo se permite en un notebook de prueba.')
                parsed, official_url = url_publica(url), urllib.parse.urlsplit(entry['url'])
                if parsed.netloc != official_url.netloc:
                    block('URL', 'El control debe conservar el origen oficial sin parámetros.')
                self.public.fetch(url, 'HEAD')
            else:
                self.check_url(url, entry, meta)
            evidence.update(origen='catalogo', oficial=es_oficial(self.catalog, meta['tecnologia'], url), entrada=entry_id, url=url)
        with bloqueo_agents(self.root):
            local_data = self.registro.read()
            self.registro.book(copy.deepcopy(local_data), meta['tecnologia'], meta['version'], identifier)
        retired_sources = {source['id'] for _, _, e in entradas_registradas(local_data)
                           for source in e['fuentes'] if source.get('retirada')}
        # Deduplicar archivos por bytes, las URL por dirección y por membresía remota real.
        records = [r for r in self.records(identifier, 'fuente') if r.get('fuente') not in retired_sources]
        members = [m for m in self.notebook_sources(identifier) if m['id'] not in retired_sources]
        if archivo:
            existing = [r for r in records if r.get('archivo_sha256') == evidence['archivo_sha256']]
            existing_sources = [item for item in members if any(r.get('fuente') == item['id'] for r in existing)]
        else:
            existing = [r for r in records if r.get('url') == url]
            existing_sources = [item for item in members if (item.get('asset') or {}).get('url') == url or item.get('url') == url]
        if len(existing_sources) > 1:
            block('DUPLICADO', 'Ya hay varias fuentes con ese origen; no se añade otra.')
        if revalidar and not existing_sources:
            block('REVALIDAR', 'La URL no está en el notebook; cárgala sin --revalidar.')
        if existing_sources:
            source_id = existing_sources[0]['id']
            matched = [r for r in existing if r.get('fuente') == source_id]
            record = matched[-1] if matched else None
            registered = next((s for _, _, e in entradas_registradas(local_data)
                               if e['notebook'] == identifier for s in e['fuentes'] if s['id'] == source_id), None)
            aportada = next((r for r in (record, registered)
                             if r and r.get('origen') in ('usuario-url', 'usuario-archivo')), None)
            if aportada and not user_source:
                if revalidar:
                    block('REVALIDAR', 'La fuente tiene procedencia aportada por el usuario; no se revalida con --entrada: ' + remedio_fuente_aportada(aportada['origen']) + '.')
                if aportada['tipo'] != entry['tipo']:
                    block('CATALOGO', 'La fuente aportada se aprobó con tipo ' + aportada['tipo'] + ', distinto del tipo ' + entry['tipo'] + ' de la entrada; no se cambia su tipo: ' + remedio_fuente_aportada(aportada['origen']) + '.')
                # Reutilizar desde el catálogo tampoco convierte su procedencia en catálogo.
                evidence = {k: aportada[k] for k in ('origen', 'confirmada_usuario', 'procedencia_url',
                            'aprobacion_sha256', 'oficial', 'contenido_sha256', 'archivo', 'archivo_sha256',
                            'mime', 'tamano', 'evidencia_previa') if k in aportada}
            source = {}
            valid = bool(record and record.get('valida') and record.get('version') == meta['version'])
            reason = record.get('motivo', 'registro sin validación') if record else 'Fuente existente sin registro validado; no se vuelve a cargar'
            if valid or user_source:
                source = self.fuente_remota(source_id)
            if valid:
                valid = digest(self.text(source)) == record.get('sha256')
                if not valid:
                    reason = 'El texto cambió; fuente excluida hasta revisión, sin recargar.'
            if user_source and (not valid or (usuario_url and correspondencia)):
                self.comprobar_url_final(source, url)
                escanear_contenido(self.text(source))
                if usuario_url and normalizar_cita(text) != normalizar_cita(self.text(source)):
                    block('FUENTE_TEXTO', 'El texto guardado difiere de la fuente revisada; revisa retirar-ausentes si falta el objeto. Si existe, aporta otra URL o archivo público revisado; no lo borres a mano.')
                transformation_id, embed = self.preparar_validacion_carga(identifier, meta)
                record = dict(evidence, administrado_por=OWNER, fuente=source_id,
                              tipo=entry['tipo'], version=meta['version'], valida=False)
                result = self.finalizar_carga(identifier, meta, entry, record, transformation_id,
                                             url, embed, negative, True, usuario_url, text, revalidar=True)
                return dict(result, reutilizada=True)
            if revalidar and not valid:
                transformation_id, embed = self.preparar_validacion_carga(identifier, meta)
                record = dict(evidence, administrado_por=OWNER, fuente=source_id,
                              tipo=entry['tipo'], version=meta['version'], valida=False)
                return self.finalizar_carga(identifier, meta, entry, record, transformation_id,
                                            url, embed, negative, False, False, None, revalidar=True)
            if not valid:
                if aportada or user_source:
                    reason += '; ' + remedio_fuente_aportada((aportada or evidence)['origen'])
                else:
                    reason += '; usa --revalidar --confirmar para validarla de nuevo'
            local_record = dict(record or {})
            local_record.update(evidence)
            if aportada and not user_source:
                local_record.pop('entrada', None)
            local_record.update(fuente=source_id, url=aportada.get('url') if aportada else url,
                                tipo=entry['tipo'], valida=valid, motivo=reason)
            if user_source:
                try:
                    escanear_contenido(self.text(source))
                except Blocked as error:
                    local_record.update(valida=False, motivo=error.code)
                    self.registro.source(meta, identifier, local_record, source)
                    self.note(identifier, 'fuente:' + source_id, local_record)
                    raise
            self.registro.source(meta, identifier, local_record, source)
            return {'fuente': source_id, 'valida': valid, 'reutilizada': True, 'motivo': reason}
        if existing:
            self.fuente_ausente()
        transformation_id, embed = self.preparar_validacion_carga(identifier, meta)
        if archivo:
            multipart = multipart_upload({'type': 'upload', 'notebooks': json.dumps([identifier]), 'embed': str(embed).lower(), 'transformations': '[]', 'delete_source': 'false', 'async_processing': 'false'}, raw, name, mime)
            created = self.request('POST', '/api/sources', multipart=multipart)
        else:
            created = self.request('POST', '/api/sources/json', {'type': 'link', 'url': url, 'notebooks': [identifier], 'embed': embed, 'transformations': [], 'async_processing': False})
        source_id = created['id']
        record = dict(evidence, administrado_por=OWNER, fuente=source_id, tipo=entry['tipo'], version=meta['version'], valida=False)
        return self.finalizar_carga(identifier, meta, entry, record, transformation_id,
                                    url, embed, negative, user_source, usuario_url, text)

    def preparar_validacion_carga(self, identifier, meta):
        transforms = [t for t in self.items('/api/transformations') if t.get('name') == NAME]
        prompt = (self.root / 'assets/documentacion/capacidades-version.md').read_text()
        if len(transforms) != 1 or transforms[0].get('prompt') != prompt or transforms[0].get('apply_default') is not False:
            block('TRANSFORMACION', 'Ejecuta preparar; no hay una transformación propia compatible.')
        probe = self.embedding_probe(identifier, meta)
        embed = probe['embeddings_utilizables'] is True
        if not embed:
            self.warnings.append('Carga sin embeddings (' + probe['error'] + '); las consultas usarán chat.')
        return transforms[0]['id'], embed

    def finalizar_carga(self, identifier, meta, entry, record, transformation_id,
                        url, embed, negative, user_source, usuario_url, text, *, revalidar=False):
        source_id = record['fuente']
        source = {}
        self.registro.source(meta, identifier, record, source)
        try:
            source = self.poll_source(source_id)
            self.comprobar_url_final(source, url)
            if user_source or revalidar:
                escanear_contenido(self.text(source))
            if usuario_url and normalizar_cita(text) != normalizar_cita(self.text(source)):
                self.warnings.append('AVISO FUENTE_TEXTO: El texto extraído por Open Notebook difiere de la revisión local; se valida su contenido con validate_insight y se conserva el control de URL final.')
            insight = self.insight_version(source_id, transformation_id, revalidar=revalidar)
            self.validate_insight(record, source, insight, meta, entry, negative)
            if revalidar and embed:
                source = self.wait_embeddings(source_id)
        except Blocked as error:
            record.update(valida=False, motivo=error.code)
            self.registro.source(meta, identifier, record, source)
            self.note(identifier, 'fuente:' + source_id, record)
            raise
        if embed and not revalidar:
            source = self.wait_embeddings(source_id)
        self.registro.source(meta, identifier, record, source)
        self.note(identifier, 'fuente:' + source_id, record)
        return {'fuente': source_id, 'valida': record['valida'], 'detectadas': record['detectadas'],
                'motivo': record['motivo'], 'embed': embed, 'embedded': source.get('embedded') is True,
                'embedded_chunks': source.get('embedded_chunks', 0)}

    def comprobar_url_final(self, source, url):
        if url:
            final_urls = [u for u in (source.get('url'), (source.get('asset') or {}).get('url')) if u]
            if any(u != url for u in final_urls):
                block('URL_REDIRECCION', 'Open Notebook devolvió una URL distinta de la aprobada; la fuente queda excluida hasta revisión.')
            if not final_urls:
                self.warnings.append('URL_FINAL: Open Notebook no devolvió evidencia de URL final; se conserva solo la comprobación previa.')

    def insight_version(self, source_id, transformation_id, *, revalidar=False):
        path = '/api/sources/' + urllib.parse.quote(source_id, safe='') + '/insights'
        anteriores = {i['id'] for i in self.items(path)} if revalidar else set()
        result = self.request('POST', '/api/sources/' + urllib.parse.quote(source_id, safe='') + '/insights', {
            'transformation_id': transformation_id, 'model_id': self.model('transformation')})
        insight = result.get('content')
        if not isinstance(insight, str):
            command = result.get('command_id')
            if not command:
                block('API_FORMATO', 'La transformación no devolvió contenido ni command_id.')
            self.wait_job(command)
            insights = self.items('/api/sources/' + urllib.parse.quote(source_id, safe='') + '/insights')
            matching = [i for i in insights if i.get('source_id') == source_id and i.get('insight_type') == NAME
                        and (not revalidar or i.get('id') not in anteriores)]
            if len(matching) != 1:
                block('API_FORMATO', 'No hay un único insight propio para la fuente creada.')
            insight = matching[0].get('content')
        return insight

    def wait_embeddings(self, source_id):
        # Esperar el trabajo ya solicitado; no volver a crear ni a indexar la fuente.
        deadline = time.monotonic() + EMBEDDING_WAIT_TIMEOUT
        source = None
        while source is None or time.monotonic() < deadline:
            source = self.fuente_remota(source_id)
            chunks = source.get('embedded_chunks', 0)
            if source.get('embedded') is True and isinstance(chunks, int) and not isinstance(chunks, bool) and chunks > 0:
                return source
            remaining = deadline - time.monotonic()
            if remaining > 0:
                time.sleep(min(EMBEDDING_POLL_INTERVAL, remaining))
        self.warnings.append(source_id + ': embeddings pendientes; embedded_chunks=' + str(source.get('embedded_chunks', 0)))
        return source

    def wait_job(self, identifier):
        deadline = time.monotonic() + JOB_TIMEOUT
        while time.monotonic() < deadline:
            job = self.request('GET', '/api/commands/jobs/' + urllib.parse.quote(identifier, safe=''))
            status = job.get('status')
            if status in ('failed', 'error', 'cancelled', 'canceled'):
                block('MODELO_FALLO', 'La transformación falló; revisa el modelo. No se repite la petición.')
            if status in ('completed', 'complete', 'success', 'succeeded'):
                if isinstance(job.get('result'), dict) and job['result'].get('success') is False:
                    block('MODELO_FALLO', 'La transformación terminó con fallo; no se reintenta.')
                return
            time.sleep(1)
        block('PLAZO', 'La transformación sigue pendiente; no se repite. Consulta su trabajo ' + identifier + '.')

    def validate_insight(self, record, source, insight, meta, entry, negative=False):
        if not isinstance(insight, str):
            block('API_FORMATO', 'Falta el contenido del insight propio.')
        section = re.search(r'(?ims)^#{1,3}\s+Versi[oó]n[ \t]*\n(.*?)(?=^#{1,3}\s|\Z)', insight)
        principal, references = None, []
        try:
            body = section.group(1).strip() if section else ''
            body = re.sub(r'^```(?:json)?\s*|\s*```$', '', body)
            data = json.loads(body)
            principal = data.get('principal')
            references = data.get('referencias', [])
            if not isinstance(principal, dict) or not isinstance(references, list):
                raise ValueError()
            if any(not isinstance(item, dict) or not isinstance(item.get('tecnologia'), str) or not isinstance(item.get('version'), str) for item in references):
                raise ValueError()
            detected = principal.get('version')
            if not isinstance(principal.get('tecnologia'), str) or not isinstance(detected, str):
                raise ValueError()
            principal['version'] = normalizar_version_detectada(detected)
            for referencia in references:
                referencia['version'] = normalizar_version_detectada(referencia['version'])
            detected = principal['version']
            name_compatible = tecnologia_compatible(principal['tecnologia'], meta, self.catalog)
            compatible = principal_compatible(principal, meta, self.catalog, entry['tipo'])
            if not name_compatible and principal['tecnologia'].strip() and record.get('origen') == 'usuario-url' and record.get('confirmada_usuario') and not negative:
                version(detected, meta['tecnologia'] == 'jdk')
                if not nombre_de_otra_tecnologia(principal['tecnologia'], meta, self.catalog):
                    name_compatible = True
                    compatible = fuente_compatible(meta['tecnologia'], meta['version'], {'tipo': entry['tipo'], 'version_principal': detected})
            if not compatible:
                try:
                    version(detected, meta['tecnologia'] == 'jdk')
                except Blocked:
                    detected = None
            valid = compatible and not negative
            if not name_compatible:
                reason = 'tecnología principal no reconocida: ' + sanear_motivo(principal['tecnologia'])
            elif not compatible:
                reason = 'versión principal incompatible: ' + sanear_motivo(principal['version'])
            elif negative:
                reason = 'control negativo'
            else:
                reason = 'version principal compatible'
        except (ValueError, TypeError, AttributeError, Blocked):
            detected, valid = None, False
            reason = 'versión principal ausente, ambigua o sin tecnología inequívoca'
        if detected is None and record.get('confirmada_usuario') and not negative and (not isinstance(principal, dict) or not principal.get('tecnologia') or tecnologia_compatible(principal['tecnologia'], meta, self.catalog)):
            principal = {'tecnologia': meta['tecnologia'], 'version': meta['version']}
            valid, reason = True, 'correspondencia_confirmada_usuario; versión no atribuida al texto'
        if not valid and record.get('entrada') == 'B10':
            reason += '; revisa la fuente y, si corresponde al tren solicitado, usa --usuario-url --confirmar-correspondencia con su hash aprobado'
        record.update(valida=valid, principal=principal, referenciadas=references,
                      detectadas=[detected] if detected else [], sha256=digest(self.text(source)), resumen=insight, motivo=reason)

    def chat_context(self, notebook, sources, level):
        mode = 'insights' if level == 'resumenes' else 'full content'
        built = self.request('POST', '/api/chat/context', {
            'notebook_id': notebook, 'context_config': {'sources': {sid: mode for sid in sources}}})
        context = built.get('context')
        if not isinstance(context, dict) or not isinstance(context.get('sources'), list):
            block('API_FORMATO', 'El constructor no devolvió un contexto de fuentes reconocible.')
        if any(item.get('id') not in sources for item in context['sources']) or context.get('notes'):
            block('CONTEXTO', 'El contexto contiene fuentes o notas no seleccionadas; se descarta.')
        if level == 'resumenes':
            # Si el modo no es reconocido, usar solo el insight ya validado como texto.
            expected = {sid: record['resumen'] for sid, (record, _) in sources.items()}
            matching = {item['id']: item for item in context['sources']}
            recognized = set(matching) == set(expected) and all(
                not matching[sid].get('full_text') and any(i.get('content') == summary for i in matching[sid].get('insights', []))
                for sid, summary in expected.items())
            if not recognized:
                context = {'sources': [{'id': sid, 'title': source.get('title') or sid,
                    'insights': [{'insight_type': NAME, 'content': record['resumen']}]} for sid, (record, source) in sources.items()], 'notes': []}
                self.warnings.append('Modo insights no reconocido: se usa el resumen validado como texto del contexto.')
            else:
                # Excluir insights de transformaciones ajenas, aunque el servidor los añada.
                for item in context['sources']:
                    item['insights'] = [i for i in item.get('insights', []) if i.get('content') == expected[item['id']]]
        return context, built.get('token_count', 'no disponible')

    def chat(self, notebook, context, prompt, level):
        model = self.model('chat')
        session = self.request('POST', '/api/chat/sessions', {'notebook_id': notebook,
            'title': 'Consulta de documentación por versión', 'model_override': model})
        identifier = session.get('id')
        if not isinstance(identifier, str):
            block('API_FORMATO', 'La creación de sesión no devolvió id.')
        payload = {'session_id': identifier, 'context': context, 'message': prompt, 'model_override': model}
        try:
            try:
                result = self.request('POST', '/api/chat/execute', payload)
            except Blocked as error:
                if error.code == 'CONTEXTO' and level == 'fuente_completa' and self.config['modelo_contexto_grande']:
                    payload['model_override'] = self.model('large_context')
                    result = self.request('POST', '/api/chat/execute', payload)
                else:
                    raise
            messages = result.get('messages')
            if not isinstance(messages, list) or not messages or messages[-1].get('type') != 'ai':
                block('API_FORMATO', 'La respuesta de chat no termina en un mensaje ai.')
            return {'response': messages[-1].get('content'), 'usage': result.get('usage', 'no disponible')}
        finally:
            try:
                self.request('DELETE', '/api/chat/sessions/' + urllib.parse.quote(identifier, safe=''))
            except Blocked:
                self.warnings.append('No se pudo borrar la sesión creada: ' + identifier + '; límpiala antes de terminar.')

    def native_answer(self, notebook, tech, expected, key, question, sources):
        model = self.model('chat')
        prompt = (question + '\nPara cada dato de la respuesta, incluye entre comillas la frase literal '
                  'de la documentación de la que sale y el id de su fuente. '
                  'Solo se admiten citas de estas fuentes: ' + ', '.join(sources))
        result = self.request('POST', '/api/search/ask/simple', {'question': prompt, 'notebook_id': notebook,
            'strategy_model': model, 'answer_model': model, 'final_answer_model': model})
        if not isinstance(result, dict) or not isinstance(result.get('answer'), str):
            block('API_FORMATO', 'Ask no devolvió answer como texto; revisa el contrato REST.')
        verified, unverified = self.quoted_data(result['answer'], sources)
        if not verified:
            self.warnings.append('Ask sin frases verificadas; se pasa a resúmenes y, si hace falta, texto completo.')
            return None
        answer = {'nivel': 'embeddings', 'respuesta': result['answer'], 'verificada': True,
                  'datos_verificados': verified, 'datos_sin_verificar': unverified,
                  'uso_en_plan': 'Solo los datos_verificados pueden usarse en un plan.',
                  'tokens': 'no disponible', 'tokens_aproximados': 'no disponible'}
        note = {'administrado_por': OWNER, 'clave': key, 'tecnologia': tech, 'version': expected,
                'pregunta': question, 'hashes_fuentes': {item['fuente']: sources[item['fuente']][0]['sha256']
                                                       for item in verified}, 'resultado': answer}
        self.note(notebook, 'respuesta:' + key, note)
        return answer

    def quoted_data(self, answer, sources):
        verified, unverified = [], []
        # Comparar marcado normalizado en ambos lados; guardar siempre la cita original.
        for paragraph in re.split(r'\n[ \t]*\n', answer):
            if not paragraph.strip():
                continue
            quotes = list(re.finditer(r'"([^"]+)"|“([^”]+)”|«([^»]+)»', paragraph))
            if not quotes:
                unverified.append({'dato': paragraph, 'motivo': 'Sin frase literal entre comillas.'})
            for match in quotes:
                quote = next(part for part in match.groups() if part is not None)
                # El id debe estar citado en el mismo párrafo; no atribuir por parecido.
                cited = set(re.findall(r'\bsource:[A-Za-z0-9_-]+', paragraph))
                sid = next((sid for sid in sources if sid in cited and cita_presente(quote, self.text(sources[sid][1]))), None)
                if sid is None or not quote.strip():
                    unverified.append({'cita': quote, 'motivo': 'Falta una fuente admitida citada con ese texto literal.'})
                else:
                    # Solo la frase literal queda aprobada, no la prosa circundante del modelo.
                    verified.append({'dato': quote, 'cita': quote, 'fuente': sid, 'url': sources[sid][0].get('url') or sources[sid][0].get('archivo')})
        return verified, unverified

    @staticmethod
    def approximate_tokens(context):
        # Estimación del contexto por caracteres/4; no es consumo facturado ni incluye el sistema.
        return (len(json.dumps(context, ensure_ascii=False)) + 3) // 4

    def ask(self, tech, question, expected=None, service=None):
        started, levels = time.monotonic(), []
        def finish(result):
            if 'datos_verificados' not in result and result.get('verificada') and result.get('cita'):
                result = dict(result, datos_verificados=[{'cita': result['cita'], 'fuente': result['fuente'], 'url': result['url']}], datos_sin_verificar=[])
            data = result.get('datos_verificados', [])
            return dict(result, tiempo_segundos=round(time.monotonic() - started, 3),
                        frases_verificadas=len(data), frases_sin_verificar=len(result.get('datos_sin_verificar', [])),
                        paso_a_resumenes='resumenes' in levels, paso_a_texto_completo='fuente_completa' in levels)
        if not question.strip() or len(question) > 500 or re.search(r'[\r\n`{};]|\$\{|(?:/home/|/tmp/|[A-Za-z]:\\)|(?:^|\s)(?:\.{0,2}/|[\w.-]+/)[^\s]+|\b(?:SELECT|INSERT|UPDATE|DELETE)\b|(?:password|token|secret)\s*[:=]|\b(?:class|import|def|function)\s+\w+', question, re.I):
            block('PRIVACIDAD', 'Formula una sola pregunta genérica sin código, datos, rutas ni credenciales.')
        if tech not in self.catalog['tecnologias']:
            block('TECNOLOGIA', 'La tecnología no pertenece al catálogo.')
        associated = None
        if service is not None:
            expected, associated = self.registro.resolve(service, tech, expected)
        if expected is None:
            block('ARGUMENTOS', 'Sin --servicio debes indicar --version.')
        version(expected, tech == 'jdk')
        wanted = self.catalog['tecnologias'][tech] + ' ' + expected
        if associated is not None:
            nb, meta = self.notebook(associated['notebook'])
        else:
            candidates = [n for n in self.items('/api/notebooks') if n.get('name') in (wanted, '[prueba 08f] ' + wanted, '[prueba 08g] ' + wanted) and not n.get('archived')]
            if len(candidates) != 1:
                block('NOTEBOOK', 'No hay un único notebook activo para esta tecnología y versión.')
            nb, meta = self.notebook(candidates[0]['id'])
        if meta['tecnologia'] != tech or meta['version'] != expected:
            block('VERSION', 'La descripción del notebook no coincide con la versión solicitada.')
        identifier = nb['id']
        records = self.records(identifier, 'fuente')
        latest = {r['fuente']: r for r in records}
        sources = {}
        member_ids = {item['id'] for item in self.notebook_sources(identifier)}
        for source_id, record in latest.items():
            if associated is not None and not any(src['id'] == source_id and src['valida'] and src.get('sha256') == record.get('sha256') for src in associated['fuentes']):
                continue
            if source_id not in member_ids or not record.get('valida') or record.get('version') != expected:
                continue
            source = self.request('GET', '/api/sources/' + urllib.parse.quote(source_id, safe=''))
            if digest(self.text(source)) == record.get('sha256'):
                sources[source_id] = (record, source)
        if not sources:
            block('FUENTES', 'No hay fuentes válidas sin cambios para esta versión.')
        vector_sources = {sid: item for sid, item in sources.items() if item[1].get('embedded') is True}
        for sid in sources.keys() - vector_sources.keys():
            self.warnings.append(sid + ': embeddings pendientes; solo disponible en resúmenes y texto completo')
        key = digest(tech + '\n' + expected + '\n' + ' '.join(question.casefold().split()))
        self.request('POST', '/api/search', {'query': question, 'type': 'text', 'notebook_id': identifier})
        # El buscador no devuelve necesariamente fragmentos: solo se aceptan notas de este notebook.
        for note in reversed(self.records(identifier, 'respuesta')):
            if note.get('clave') == key and self.verify(note, sources):
                return finish(dict(note['resultado'], nivel='notas', tokens=0, tokens_contexto=0, tokens_aproximados=0))
        prompt = ('Responde solo desde el contexto. Devuelve JSON sin bloques Markdown con respuesta, fuente '
                  '(id exacto) y cita literal continua de como máximo ocho palabras; '
                  'si no hay evidencia devuelve respuesta NO ENCONTRADO, sin cita. No inventes citas. Pregunta: ' + question)
        if vector_sources and self.embedding_configured():
            levels.append('embeddings')
            verified = self.native_answer(identifier, tech, expected, key, question, vector_sources)
            if verified:
                return finish(verified)
        elif vector_sources:
            self.warnings.append('Embeddings no configurados; se usa la ruta de chat con resúmenes.')
        for level in ('resumenes', 'fuente_completa'):
            levels.append(level)
            context, context_tokens = self.chat_context(identifier, sources, level)
            result = self.chat(identifier, context, prompt, level)
            result['tokens_aproximados'] = context_tokens if isinstance(context_tokens, int) else self.approximate_tokens(context)
            verified = self.answer(identifier, tech, expected, key, result, sources, level, question)
            if verified:
                return finish(verified)
        return finish({'nivel': 'fuente_completa', 'respuesta': 'NO ENCONTRADO', 'verificada': False, 'tokens': 'no disponible', 'datos_verificados': [], 'datos_sin_verificar': []})

    def verify(self, note, sources):
        result = note.get('resultado', {})
        if 'datos_verificados' in result:
            data = result['datos_verificados']
            hashes = note.get('hashes_fuentes', {result.get('fuente'): note.get('sha256')})
            return isinstance(data, list) and bool(data) and all(
                isinstance(item, dict) and item.get('fuente') in sources
                and isinstance(item.get('cita'), str) and bool(item['cita'].strip())
                and cita_presente(item['cita'], self.text(sources[item['fuente']][1]))
                and hashes.get(item['fuente']) == sources[item['fuente']][0]['sha256'] for item in data)
        sid, quote = result.get('fuente'), result.get('cita')
        return sid in sources and isinstance(quote, str) and bool(quote.strip()) and cita_presente(quote, self.text(sources[sid][1])) and note.get('sha256') == sources[sid][0]['sha256']

    def answer(self, nb, tech, expected, key, result, sources, level, question):
        response = result.get('response', result)
        if isinstance(response, str):
            try:
                response = json.loads(re.sub(r'^```(?:json)?\s*|\s*```$', '', response.strip()))
            except ValueError:
                self.warnings.append('Respuesta sin estructura verificable; descartada.')
                return None
        if not isinstance(response, dict):
            return None
        record = sources.get(response.get('fuente'))
        if record is None:
            return None
        answer = {'nivel': level, 'respuesta': response.get('respuesta'), 'fuente': response.get('fuente'),
                  'cita': response.get('cita'), 'url': record[0].get('url') or record[0].get('archivo'), 'verificada': True,
                  'tokens': result.get('usage', 'no disponible'),
                  'datos_verificados': [{'dato': response.get('cita'), 'cita': response.get('cita'),
                                         'fuente': response.get('fuente'), 'url': record[0].get('url') or record[0].get('archivo')}],
                  'datos_sin_verificar': [], 'uso_en_plan': 'Solo los datos_verificados pueden usarse en un plan.'}
        if 'tokens_aproximados' in result:
            answer['tokens_aproximados'] = result['tokens_aproximados']
            answer['tokens_contexto'] = result['tokens_aproximados']
        note = {'administrado_por': OWNER, 'clave': key, 'tecnologia': tech, 'version': expected,
                'sha256': record[0]['sha256'], 'pregunta': question, 'resultado': answer}
        if not answer['respuesta'] or answer['respuesta'] == 'NO ENCONTRADO' or not self.verify(note, sources):
            self.warnings.append('Cita no literal en la fuente; respuesta descartada.')
            return None
        self.note(nb, 'respuesta:' + key, note)
        return answer

    def _meta_notebook_administrado(self, identifier):
        nb = self.notebook_remoto(identifier)
        try:
            meta = json.loads(nb['description'])
        except (KeyError, TypeError, ValueError):
            block('PROPIEDAD', 'El notebook no pertenece a la documentación administrada.')
        if meta.get('administrado_por') != OWNER:
            block('PROPIEDAD', 'No se archivan notebooks ajenos.')
        self.registro.comprobar_notebook_no_retirado(self.registro.read(), identifier)
        return nb, meta

    def servicios_que_usan_notebook(self, data, meta):
        current = self.registro.usages(data)
        entry = data['tecnologias'].get(meta['tecnologia'], {}).get('versiones', {}).get(meta['version'])
        if entry and entry['estado'] == 'retirado':
            return []
        usados = []
        for name, service in data['servicios'].items():
            binding = service['tecnologias'].get(meta['tecnologia'], {})
            if name in current and binding.get('estado') == 'asociado' and binding.get('version_documentacion') == meta['version']:
                usados.append(name)
        return sorted(usados)

    def archive(self, identifier, confirmed=False):
        nb, meta = self._meta_notebook_administrado(identifier)
        if not confirmed:
            with bloqueo_agents(self.root):
                data = self.registro.read()
                usados = self.servicios_que_usan_notebook(data, meta)
                if usados:
                    block('DOCUMENTACION_EN_USO', 'Otro servicio sigue asociado; actualiza los vínculos antes de archivar. Servicios: ' + ', '.join(usados))
                data_preview = copy.deepcopy(data)
                self.registro.book(data_preview, meta['tecnologia'], meta['version'], identifier, 'archivado')
                preview = self.registro.diff_registro(data_preview)
            return {'confirmado': False, 'notebook': identifier, 'archivado': False, 'servicios_en_uso': usados, **preview}
        with bloqueo_agents(self.root):
            data = self.registro.read()
            self.comprobar_archivado(data, meta, identifier)
        if not nb.get('archived'):
            self.request('PUT', '/api/notebooks/' + urllib.parse.quote(identifier, safe=''), {'archived': True})
        with bloqueo_agents(self.root):
            data = self.registro.read()
            self.comprobar_archivado(data, meta, identifier)
            self.registro.save(data)
        return {'confirmado': True, 'notebook': identifier, 'archivado': True}

    def comprobar_archivado(self, data, meta, identifier):
        usados = self.servicios_que_usan_notebook(data, meta)
        if usados:
            block('DOCUMENTACION_EN_USO', 'Otro servicio sigue asociado; actualiza los vínculos antes de archivar. Servicios: ' + ', '.join(usados))
        self.registro.book(data, meta['tecnologia'], meta['version'], identifier, 'archivado')


def main():
    parser = Parser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('comprobar-conexion')
    existence = commands.add_parser('comprobar-existencia')
    existence.add_argument('--listar-ausentes', action='store_true')
    retire = commands.add_parser('retirar-ausentes')
    retire.add_argument('--notebook')
    retire.add_argument('--confirmar', action='store_true')
    state = commands.add_parser('estado')
    selection = state.add_mutually_exclusive_group()
    selection.add_argument('--notebook')
    selection.add_argument('--prefijo')
    prep = commands.add_parser('preparar')
    prep.add_argument('--tecnologia', required=True)
    prep.add_argument('--version', required=True)
    prep.add_argument('--prefijo', default='')
    prep.add_argument('--reactivar', action='store_true')
    prep.add_argument('--confirmar', action='store_true')
    load = commands.add_parser('cargar')
    load.add_argument('notebook')
    load.add_argument('url', nargs='?')
    load.add_argument('--archivo')
    load.add_argument('--entrada')
    load.add_argument('--usuario-url', action='store_true')
    load.add_argument('--tipo', choices=SOURCE_TYPES)
    load.add_argument('--documentacion-publica', action='store_true')
    load.add_argument('--confirmar-correspondencia', action='store_true')
    load.add_argument('--sha256-aprobado')
    load.add_argument('--procedencia-url')
    load.add_argument('--confirmar', action='store_true')
    load.add_argument('--control-sin-version', action='store_true')
    load.add_argument('--revalidar', action='store_true')
    ask = commands.add_parser('preguntar')
    ask.add_argument('tecnologia')
    ask.add_argument('pregunta')
    ask.add_argument('--version')
    ask.add_argument('--servicio')
    archive = commands.add_parser('archivar')
    archive.add_argument('notebook')
    archive.add_argument('--confirmar', action='store_true')
    associate = commands.add_parser('asociar')
    associate.add_argument('--servicio', required=True)
    associate.add_argument('--tecnologia', required=True)
    associate.add_argument('--version')
    associate.add_argument('--confirmar', action='store_true')
    action = associate.add_mutually_exclusive_group()
    action.add_argument('--quitar', action='store_true')
    action.add_argument('--sin-documentacion', action='store_true')
    associate.add_argument('--motivo')
    amp = commands.add_parser('ampliar-catalogo')
    amp.add_argument('--tecnologia', required=True)
    amp.add_argument('--nombre')
    amp.add_argument('--detector', action='append', default=[])
    amp.add_argument('--fuente', action='append', default=[])
    amp.add_argument('--dominios-oficiales', help='Lista JSON de reglas host/ruta, solo para tecnología nueva.')
    amp.add_argument('--confirmar', action='store_true')
    rb = commands.add_parser('resolver-bom')
    rb.add_argument('--servicio', required=True)
    rb.add_argument('--tecnologia', required=True)
    rb.add_argument('--confirmar', action='store_true')
    client = None
    args = None
    try:
        args = parser.parse_args()
        root = Path(__file__).resolve().parents[1]
        if getattr(args, 'confirmar', False) and (
                args.command in ('cargar', 'asociar', 'archivar', 'resolver-bom', 'ampliar-catalogo', 'retirar-ausentes')
                or (args.command == 'preparar' and args.reactivar)):
            comprobar_escritura_registro(root)
        if args.command == 'resolver-bom':
            result = resolver_bom(root, cargar_catalogo(root), args.servicio, args.tecnologia, args.confirmar)
            print(json.dumps({'estado': 'ok', 'operacion': args.command, **result}, ensure_ascii=False))
            return 0
        if args.command == 'ampliar-catalogo':
            result = ampliar_catalogo(root, args.tecnologia, args.nombre, args.detector, args.fuente, args.confirmar, args.dominios_oficiales)
            print(json.dumps({'estado': 'ok', 'operacion': args.command, 'avisos': [], **result}, ensure_ascii=False))
            return 0
        client = Client()
        if args.command == 'comprobar-conexion':
            result = client.connection()
        elif args.command == 'comprobar-existencia':
            result = client.listar_ausentes() if args.listar_ausentes else client.remote_documentation()
        elif args.command == 'retirar-ausentes':
            result = client.retirar_ausentes(args.notebook, args.confirmar)
        elif args.command == 'estado':
            result = client.state(args.notebook, args.prefijo)
        elif args.command == 'preparar':
            result = client.prepare(args.tecnologia, args.version, args.prefijo, args.reactivar, args.confirmar)
        elif args.command == 'cargar':
            result = client.load(args.notebook, args.url, args.entrada, args.confirmar, args.control_sin_version, archivo=args.archivo, usuario_url=args.usuario_url, tipo=args.tipo, publica=args.documentacion_publica, correspondencia=args.confirmar_correspondencia, sha_aprobado=args.sha256_aprobado, procedencia=args.procedencia_url, revalidar=args.revalidar)
        elif args.command == 'preguntar':
            result = client.ask(args.tecnologia, args.pregunta, args.version, args.servicio)
        elif args.command == 'asociar':
            result = client.registro.associate(args.servicio, args.tecnologia, args.version, args.confirmar, args.quitar, args.sin_documentacion, args.motivo)
        else:
            result = client.archive(args.notebook, args.confirmar)
        output = {'estado': 'ok', 'operacion': args.command, 'avisos': client.warnings, **result}
        text = json.dumps(output, ensure_ascii=False)
        if client.secret and client.secret in text:
            block('RESPUESTA', 'La respuesta contiene información protegida y se descartó.')
        print(text)
        return 0
    except Blocked as error:
        print(json.dumps({'estado': 'bloqueado', 'operacion': getattr(args, 'command', None), 'error': {'codigo': error.code, 'mensaje': error.message}}, ensure_ascii=False))
        return 2
    except (KeyError, IndexError, AttributeError, TypeError, ValueError, OSError, subprocess.SubprocessError):
        print(json.dumps({'estado': 'bloqueado', 'operacion': getattr(args, 'command', None), 'error': {'codigo': 'CONTRATO', 'mensaje': 'Revisa la configuración o el contrato REST; no se imprimen datos de la respuesta.'}}, ensure_ascii=False))
        return 2


if __name__ == '__main__':
    sys.exit(main())
