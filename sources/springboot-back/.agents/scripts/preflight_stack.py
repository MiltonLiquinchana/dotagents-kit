"""Comprobaciones exclusivas del backend Gradle."""
import json
import os
import re

TOOLS = ['node']
KEYS = ['backend.java']
SOURCES_PREFIX = 'springboot-'
CONTEXT_CODE = 'SERVICIOS'
EXPENSIVE = ['JDK', 'SONARQUBE', 'SONAR_MCP']
PENDIENTE = 'Pendiente (lo hace el agente, no este script): MCP SonarQube responde + canario S2077.'
WORKFLOWS = ['implement-microservice-feature', 'incorporate-service', 'change-version', 'preparar-documentacion']
# si integraciones.autenticacion=clerk
WORKFLOWS += ['add-authentication']
# fin
# si integraciones.gestion_usuarios=organizaciones|aplicacion
WORKFLOWS += ['add-user-management']
# fin

def antes_validar(p):
    return True


def reader(p, *args):
    return ['node', p.agents / 'scripts/stack.mjs', *args]


def python(p, name, *args):
    return ['python3', '-I', '-B', p.agents / 'scripts' / name, *args]

def avisos_validacion(p, text):
    seen = set()
    for line in text.splitlines():
        if line in seen:
            continue
        seen.add(line)
        if line.startswith('AVISO JDK_STACK:'):
            p.add('JDK_AVISO', line)
        else:
            print(line)


def contexto(p, ctx, params):
    if not ctx['servicios']:
        p.add('SERVICIOS', 'No se encontró ningún servicio con build.gradle y settings.gradle.')
        return False
    print(f"✅ OK ({len(ctx['servicios'])} servicios)")
    return True


def _touched_services(p, ctx):
    import subprocess
    def git(*args):
        r = subprocess.run(['git', *args], cwd=p.root, capture_output=True, text=True, errors='replace')
        return r.returncode, r.stdout
    rc, base = p.datos(p.reader('get', 'git.rama_base'))
    base = base.strip() if not rc else ''
    if not base:
        # Con rama_base null: upstream o ramas convencionales locales existentes.
        rc, upstream = git('rev-parse', '--abbrev-ref', '--symbolic-full-name', '@{upstream}')
        candidates = ([upstream.strip()] if not rc else []) + ['main', 'master', 'develop']
        _, current = git('branch', '--show-current')
        for candidate in candidates:
            rc, _ = git('rev-parse', '--verify', candidate)
            if not rc and candidate != current.strip():
                base = candidate
                print('Perfiles: git.rama_base null; se incluyen commits de la rama actual frente a ' + base + ' y cambios del árbol.')
                break
        if not base:
            print('Perfiles: git.rama_base null y sin base local disponible; solo cambios del árbol.')
    paths = set()
    if base:
        rc, out = git('diff', '--name-only', '--no-renames', '-z', base + '...HEAD')
        if not rc:
            paths.update(x for x in out.split('\0') if x)
    rc, out = git('status', '--porcelain', '-z')
    if not rc:
        records = iter(out.split('\0'))
        for record in records:
            if len(record) < 4:
                continue
            paths.add(record[3:])
            if 'R' in record[:2] or 'C' in record[:2]:
                paths.add(next(records, ''))
    return sorted({path.split('/',1)[0] for path in paths} & set(ctx.get('servicios', [])))


def servicios_registro(p, ctx):
    return _touched_services(p, ctx) if p.phase == 'cierre' and p.workflow and p.data['workflows'][p.workflow]['grupo'] == 'E' else []

def nombres_preflight(p):
    rc, out, err = p.run(p.python('servicios.py', 'nombres'))
    if rc:
        detalle = err.splitlines()[0] if err.splitlines() else 'sin diagnóstico público'
        p.add('NOMBRES', 'No se pudo calcular la identidad pública: ' + detalle)
        return
    try:
        items = json.loads(out)
        for item in items:
            for aviso in item['avisos']:
                p.add(aviso['codigo'], aviso['motivo'], item['servicio'])
    except (ValueError, KeyError, TypeError):
        p.add('PLANTILLA', 'nombres no devolvió el contrato JSON esperado.')


def estaticos(p, ctx, params):
    nombres_preflight(p)
    import shutil
    if not shutil.which('curl'): p.add('HERRAMIENTA', 'curl no encontrado en PATH.')
    def svc_de_linea(line, default='*'):
        m = re.match(r'^(?:BLOCKED:\s+)?([\w.-]+)/(?:build\.gradle\b|gradle/wrapper/)', line)
        if m: return m.group(1)
        m = re.match(r'^OK:\s+([\w.-]+):', line)
        if m: return m.group(1)
        return default
    rc, text = p.output(['node', p.agents / 'scripts/comprobar-versiones.mjs'])
    if rc:
        lines = [line for line in text.splitlines() if line.startswith('BLOCKED')]
        if not lines: p.add('PLANTILLA', text or 'Comprobador de versiones sin diagnóstico.')
        for line in lines:
            svc = svc_de_linea(line)
            p.add('JDK' if 'bin/javac' in line else 'VERSIONES', line, svc)
    elif text: print(text)
    rc2, text2 = p.output(['node', p.agents / 'scripts/comparar-versiones.mjs'])
    if rc2:
        lines = [line for line in text2.splitlines() if line.startswith('BLOCKED') or line.startswith('AVISO')]
        if not lines: p.add('PLANTILLA', text2 or 'Comprobador de comparación sin diagnóstico.')
        for line in lines:
            if line.startswith('AVISO'):
                print(line); continue
            svc = '*' if 'difiere:' in line and ';' in line else svc_de_linea(line)
            p.add('VERSIONES', line, svc)
    elif text2: print(text2)
# si devops.infraestructura=jenkins-kubernetes
    detectores = p.registry.cargar_detectores(p.agents)
    try:
        jf = detectores._jenkins_path(p.root, ctx)
        if jf.is_file() and 'CONSTRUIR_TODO' not in jf.read_text(encoding='utf-8'):
            p.add('DEVOPS_VALORES', str(jf.relative_to(p.root)) + ': pipeline sin CONSTRUIR_TODO; pendiente de actualización')
    except (OSError, UnicodeError, ValueError):
        p.add('DEVOPS_VALORES', 'No se pudo comprobar la actualización del pipeline: ruta insegura o archivo ilegible.')
    p.check('ENTORNOS', p.python('servicios.py', 'validar-entornos'))
    p.check('JENKINS', p.python('servicios.py', 'validar-jenkins'))
# fin
    if ctx.get('gateway') and (p.root / ctx['gateway']).is_dir():
        rc, text = p.output(p.python('servicios.py', 'validar-gateway'))
        if rc in (1, 2):
            p.add('GATEWAY_RUTAS', 'incoherencias en rutas de GatewayConfig.java:\n' + text, ctx['gateway'])
        else:
            print('✅ OK (rutas del gateway)')
    for service in ctx['servicios']:
        if not os.access(p.root / service / 'gradlew', os.X_OK):
            p.add('WRAPPER', 'gradlew no existe o no es ejecutable.', service)


def caros(p, ctx, params):
    service = ctx['servicios'][0]
    rc, out = p.output(['sh', './gradlew', '-q', 'javaToolchains', '--console=plain'], p.root / service)
    blocks = re.split(r'(?m)^\s*\+ ', out)
    version = params['backend.java']
    valid = any(re.search(r'Language Version:\s*' + re.escape(version) + r'\b', b) and re.search(r'Is JDK:\s*true', b) for b in blocks)
    if rc:
        p.add('JDK', f"'gradlew javaToolchains' falló en {service}:\n" + out, service)
    elif not valid:
        p.add('JDK', f'Gradle no detecta un JDK {version} (Language Version: {version} con Is JDK: true); instala un JDK {version} o declara su ruta en org.gradle.java.installations.paths del gradle.properties del servicio.\n' + out, service)
    else:
        print(f"✅ OK (JDK {version} detectado por Gradle; {len(ctx['servicios'])} servicios con la misma versión)")
    sonar(p, params)

def sonar(p, params):
    rc, detalle = p.output(['node', p.agents / 'scripts/sonar-servidor.mjs', '--comprobar'])
    if rc:
        p.add('SONAR_MCP', detalle or 'No se pudo comprobar el servidor MCP del kit.')
        return
    url = os.environ['SONARQUBE_URL']
    rc, out, _ = p.run(['curl', '-s', '-m', '5', url + '/api/system/status'])
    if rc or not out:
        p.add('SONARQUBE', f'SonarQube no responde (curl exit {rc}). Revisa la red o SONARQUBE_URL.')
        return
    try:
        response = json.loads(out)
        state = response.get('status')
    except (ValueError, AttributeError, TypeError):
        state = None
    if not state:
        p.add('SONARQUBE', 'SONARQUBE_URL responde, pero no es la respuesta de /api/system/status de SonarQube.')
    elif state != 'UP':
        p.add('SONARQUBE', f"SonarQube responde pero su estado es '{state}', no 'UP'. Espera a que termine de arrancar.")
    else:
        version = response.get('version')
        print(f'✅ OK (versión {version})')
        print('SONAR_SERVER_VERSION=' + str(version))
