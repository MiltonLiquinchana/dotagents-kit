"""Comprobaciones exclusivas del frontend Next.js."""
import json
import os
from pathlib import Path
import shutil
import subprocess

TOOLS = ['node']
KEYS = ['sonarqube.url', 'frontend.eslint_config', 'frontend.gestor_paquetes', 'herramientas.agent_browser']
SOURCES_PREFIX = 'nextjs-'
CONTEXT_CODE = 'STACK_INVALIDO'
EXPENSIVE = ['LINTER', 'SONARQUBE']
PENDIENTE = 'Pendiente (lo hace el agente, no este script): proyecto en SonarQube + MCP responde + canario S1523.'
WORKFLOWS = ['implement-feature', 'bootstrap-project', 'change-version', 'preparar-documentacion']
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
    if text:
        print(text)


def contexto(p, ctx, params):
    p.gestor = params['frontend.gestor_paquetes']
    if p.gestor not in ('npm','pnpm','yarn'):
        p.add('STACK_INVALIDO', 'Gestor de paquetes no admitido.')
        return False
    return True


def estaticos(p, ctx, params):
    if p.workflow == 'implement-feature' and params['herramientas.agent_browser'] == 'true':
        cli = shutil.which('agent-browser')
        if not cli:
            p.add('HERRAMIENTA', 'CLI agent-browser no encontrada en PATH. Instálala con: npm install -g agent-browser && agent-browser install')
        else:
            env = os.environ.copy()
            env['AGENT_BROWSER_NO_VERSION_CHECK'] = '1'
            try:
                result = subprocess.run([cli, 'doctor', '--offline', '--quick'],
                                        capture_output=True, text=True, encoding='utf-8',
                                        errors='replace', timeout=60, env=env)
                if result.returncode:
                    output = '\n'.join(s for s in (result.stdout, result.stderr) if s)
                    p.add('HERRAMIENTA', 'agent-browser doctor falló: ' + (output or 'exit ' + str(result.returncode)))
            except subprocess.TimeoutExpired as error:
                def text(value):
                    return value.decode('utf-8', errors='replace') if isinstance(value, bytes) else value or ''
                output = '\n'.join(s for s in (text(error.stdout), text(error.stderr)) if s)
                p.add('HERRAMIENTA', 'agent-browser doctor falló: tiempo agotado (60 s)' + ('\n' + output if output else ''))
            except OSError as error:
                p.add('HERRAMIENTA', 'agent-browser doctor falló: ' + str(error))
    for tool in ['curl', 'npx' if p.gestor == 'npm' else p.gestor]:
        if not shutil.which(tool): p.add('HERRAMIENTA', tool + ' no encontrado en PATH.')
    if not eslint_local(p):
        p.add('DEPENDENCIAS', 'Falta ESLint local en node_modules/.')
    if not Path(params['frontend.eslint_config']).is_file(): p.add('PREPARACION', 'No existe la configuración ESLint preparada.')
    p.check('VERSIONES', ['node', p.agents / 'scripts/comprobar-versiones.mjs'])


def eslint_local(p):
    return Path('node_modules/eslint/bin/eslint.js').is_file() or p.gestor == 'yarn' and Path('.pnp.cjs').is_file()


def caros(p, ctx, params):
    executor = ['npx', '--no-install'] if p.gestor == 'npm' else ['pnpm', 'exec'] if p.gestor == 'pnpm' else ['yarn']
    if not eslint_local(p):
        p.add('DEPENDENCIAS', 'Falta ESLint local; no se ejecuta un resolvedor de paquetes.')
        return
    _, out = p.output(executor + ['eslint', '-c', params['frontend.eslint_config'], '.agents/skills/code-reviewer/fixtures/canary-eval.ts'])
    if 'no-eval' not in out:
        p.add('LINTER', 'Canario ESLint no reportó no-eval:\n' + out)
    else: print('✅ OK (regla no-eval detectada)')
    sonar(p, params)

def sonar(p, params):
    url = os.environ.get('SONARQUBE_URL', params['sonarqube.url'])
    rc, out, _ = p.run(['curl', '-s', '-m', '5', url + '/api/system/status'])
    if rc or not out:
        p.add('SONARQUBE', f'SonarQube no responde en {url} (curl exit {rc}). Revisa la red o SONARQUBE_URL.')
        return
    try:
        response = json.loads(out)
        state = response.get('status')
    except (ValueError, AttributeError, TypeError):
        state = None
    if not state:
        p.add('SONARQUBE', f'{url} responde, pero no es la respuesta de /api/system/status de SonarQube.\nRespuesta (primeros 200 caracteres): ' + out[:200])
    elif state != 'UP':
        p.add('SONARQUBE', f"SonarQube responde pero su estado es '{state}', no 'UP'. Espera a que termine de arrancar.")
    else:
        version = response.get('version')
        print(f'✅ OK (versión {version})')
        print('SONAR_SERVER_VERSION=' + str(version))


def remedio(code, text, p):
    if code == 'DEPENDENCIAS':
        gestor = getattr(p, 'gestor', '')
        if gestor in ('npm','pnpm','yarn'):
            return 'Usuario: con permiso para instalar, ejecuta ' + gestor + ' install y repite el workflow.' + (' Yarn admite ESLint local mediante node_modules o .pnp.cjs.' if gestor == 'yarn' else '')
    return text
