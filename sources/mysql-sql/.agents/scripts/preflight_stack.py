"""Comprobaciones exclusivas del stack MySQL; PyYAML de usuario con -B -E."""
import json
import os
from pathlib import Path
import shutil

TOOLS = []
KEYS = ['base_de_datos.motor', 'base_de_datos.version', 'base_de_datos.carpeta_notebooks', 'base_de_datos.nombre']
SOURCES_PREFIX = 'sql-'
CONTEXT_CODE = 'STACK_INVALIDO'
EXPENSIVE = ['CONTENEDORES', 'SANDBOX']
PENDIENTE = 'La versión real la obtiene el agente con SELECT VERSION() en solo lectura antes del preflight de entrada de los workflows con plan; este script solo compara el dato version_real recibido.'
WORKFLOWS = ['build-database-feature', 'preparar-documentacion', 'change-version']
# si integraciones.gestion_usuarios=organizaciones|aplicacion
WORKFLOWS += ['add-user-management']
# fin

def python(p, name, *args):
    flags = ['-B', '-E'] if name in {'stack.py', 'db-index.py', 'sql-lint.py', 'sql-sandbox.py'} else ['-I', '-B']
    return ['python3', *flags, p.agents / 'scripts' / name, *args]


def reader(p, *args):
    return python(p, 'stack.py', *args)


def antes_validar(p):
    rc, text = p.output(['python3', '-B', '-E', '-c', 'import yaml'])
    if rc:
        p.add('HERRAMIENTA', "Falta PyYAML para leer los notebooks (.dbcnb). Instálalo con 'python3 -m pip install pyyaml'.\n" + text)
        return False
    return True


def avisos_validacion(p, text):
    if text:
        print(text)


def contexto(p, ctx, params):
    motor = params['base_de_datos.motor']
    if motor != 'mysql':
        p.add('STACK_INVALIDO', f"base_de_datos.motor de .agents/stack.yaml es '{motor}'; este .agents solo admite el motor mysql.")
        return False
    print(f"✅ OK (motor {motor}, esquema {params['base_de_datos.nombre']}, notebook-dir {params['base_de_datos.carpeta_notebooks']})")
    return True


def estaticos(p, ctx, params):
    folder = params['base_de_datos.carpeta_notebooks']
    if not Path(folder).is_dir():
        p.add('NOTEBOOKS_AVISO', f"la carpeta de notebooks '{folder}' no existe todavía; se creará al persistir el primer objeto.")
    else:
        rc, out = p.datos(p.python('db-index.py', '--sin-datos-prueba'))
        if rc: p.add('NOTEBOOKS', 'No se pudieron leer los notebooks permitidos; revisa el índice SQL sin datos de prueba.')
        else:
            try:
                index = json.loads(out)
                objects = index['objetos']
                total = sum(objects.values())
                if not total: p.add('NOTEBOOKS_AVISO', f"no hay ningún objeto en los notebooks de '{folder}' (carpeta vacía o sin celdas SQL).")
                else: print('✅ OK (' + ', '.join(f'{v} {k}' for k, v in objects.items()) + ')')
            except (ValueError, TypeError, AttributeError, KeyError) as error:
                p.add('NOTEBOOKS', 'Índice JSON inválido: ' + str(error))
    if p.check('REPOSITORIO', ['git', 'rev-parse', '--verify', '-q', 'HEAD^{commit}']):
        _, head = p.datos(['git', 'rev-parse', '--short', 'HEAD'])
        print('✅ OK (' + head + ')')
    p.check('LINTER', p.python('sql-lint.py', '--canary'))


def caros(p, ctx, params):
    engine = next((e for e in ('docker', 'podman') if shutil.which(e) and p.output([e, 'info'])[0] == 0), None)
    if not engine:
        p.add('CONTENEDORES', 'No hay docker ni podman operativos (el sandbox necesita un motor de contenedores).')
        p.omit('SANDBOX', 'CONTENEDORES')
        return
    expected = params['base_de_datos.motor'] + ':' + params['base_de_datos.version']
    image = os.environ.get('SQL_SANDBOX_IMAGE', expected)
    if image != expected:
        p.add('SANDBOX', 'SQL_SANDBOX_IMAGE fuerza otra imagen; el usuario debe retirarlo o alinearlo con ' + expected + '.', clase='aviso')
    rc, _ = p.output([engine, 'image', 'inspect', image])
    if rc:
        p.add('CONTENEDORES', f"La imagen {image} no está disponible localmente; el usuario debe prepararla. El agente no descarga imágenes.")
        p.omit('SANDBOX', 'CONTENEDORES')
        return
    print(f'✅ OK ({engine}, imagen {image})')
    p.check('SANDBOX', p.python('sql-sandbox.py', '--canary'))
