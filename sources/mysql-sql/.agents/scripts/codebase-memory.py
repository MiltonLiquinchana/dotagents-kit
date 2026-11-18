#!/usr/bin/env python3
"""Resuelve, comprueba o indexa la raíz Git mediante la CLI de Codebase Memory."""
import argparse
import json
import os
import shutil
import signal
import subprocess
import sys


class Fallo(Exception):
    def __init__(self, mensaje, codigo=2):
        super().__init__(mensaje)
        self.codigo = codigo


class TiempoAgotado(Exception):
    pass


def positivo(valor):
    try:
        numero = int(valor)
    except ValueError as error:
        raise argparse.ArgumentTypeError('debe ser un entero > 0') from error
    if numero <= 0:
        raise argparse.ArgumentTypeError('debe ser un entero > 0')
    return numero


def ejecutar(argv, env=None, timeout=None):
    try:
        with subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              text=True, encoding='utf-8', errors='replace', env=env,
                              start_new_session=True) as proceso:
            try:
                out, err = proceso.communicate(timeout=timeout)
            except subprocess.TimeoutExpired as error:
                try:
                    os.killpg(proceso.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                proceso.communicate()
                raise TiempoAgotado from error
            return subprocess.CompletedProcess(argv, proceso.returncode, out, err)
    except OSError as error:
        raise Fallo('BLOCKED: ' + str(error)) from error


def consultar(argv, env, limite):
    try:
        return ejecutar(argv, env, timeout=limite)
    except TiempoAgotado as error:
        raise Fallo(f'BLOCKED: CBM no respondió en {limite} s') from error


def salida_literal(resultado):
    sys.stdout.write(resultado.stdout)
    sys.stderr.write(resultado.stderr)


def detalle(resultado):
    return '\n'.join(x.strip() for x in (resultado.stdout, resultado.stderr) if x.strip())


def objeto(resultado):
    try:
        data = json.loads(resultado.stdout)
    except ValueError as error:
        raise Fallo('BLOCKED: respuesta JSON inválida de CBM: ' + detalle(resultado)) from error
    if not isinstance(data, dict):
        raise Fallo('BLOCKED: respuesta de CBM no es un objeto JSON: ' + detalle(resultado))
    return data


def verificar_exit(resultado, herramienta):
    if not resultado.returncode:
        return
    try:
        data = json.loads(resultado.stdout)
    except ValueError:
        data = None
    if (resultado.returncode == 1 and isinstance(data, dict)
            and data.get('error') == 'project not found or not indexed'):
        raise Fallo('FALTA proyecto sin indexar', 1)
    raise Fallo('BLOCKED: ' + herramienta + ': ' +
                (detalle(resultado) or f'exit {resultado.returncode} sin diagnóstico'))


def resolver(cli, env, raiz, limite):
    offset, nombres = 0, []
    while True:
        result = consultar([cli, 'cli', '--quiet', 'list_projects', '--format', 'json',
                            '--limit', '500', '--offset', str(offset)], env, limite)
        verificar_exit(result, 'list_projects')
        data = objeto(result)
        if 'error' in data or not isinstance(data.get('projects'), list):
            raise Fallo('BLOCKED: list_projects: ' + detalle(result))
        for project in data['projects']:
            if not isinstance(project, dict):
                raise Fallo('BLOCKED: entrada inválida en list_projects: ' + detalle(result))
            path, name = project.get('root_path'), project.get('name')
            if isinstance(path, str) and os.path.isabs(path) and os.path.realpath(path) == raiz:
                if not isinstance(name, str) or not name:
                    raise Fallo('BLOCKED: proyecto CBM sin name válido: ' + detalle(result))
                nombres.append(name)
        if data.get('has_more') is False:
            break
        if data.get('has_more') is not True or not data['projects']:
            raise Fallo('BLOCKED: paginación inválida de list_projects: ' + detalle(result))
        offset += len(data['projects'])
    if not nombres:
        raise Fallo('FALTA proyecto sin indexar', 1)
    if len(nombres) > 1:
        raise Fallo('BLOCKED: varios proyectos CBM con esta raíz: ' + ', '.join(nombres) +
                    '; borra los que sobren con codebase-memory-mcp cli delete_project --project <nombre>')
    return nombres[0]


def comprobar(cli, env, name, limite):
    result = consultar([cli, 'cli', '--quiet', 'index_status', '--project', name,
                        '--format', 'json'], env, limite)
    verificar_exit(result, 'index_status')
    data = objeto(result)
    status, nodes = data.get('status'), data.get('nodes')
    if ('error' in data or not isinstance(status, str)
            or type(nodes) is not int or nodes < 0):
        raise Fallo('BLOCKED: index_status inválido: ' + detalle(result))
    if status != 'ready':
        print(f'AVISO índice en estado {status}; puede estar actualizándose')
    elif nodes == 0:
        print('AVISO índice sin nodos')
    else:
        print(f'OK {name}: {nodes} nodos')
    return 0


def indexar(cli, env, raiz, limite, timeout):
    try:
        anterior = resolver(cli, env, raiz, limite)
    except Fallo:
        anterior = None
    try:
        result = ejecutar([cli, 'cli', '--quiet', '--json', 'index_repository',
                           '--repo-path', raiz], env, timeout=timeout)
    except TiempoAgotado:
        print(f'AVISO reindexado sin terminar en {timeout} s; el índice anterior sigue disponible')
        return 0
    if result.returncode:
        salida_literal(result)
        return 2
    data = objeto(result)
    if data.get('isError'):
        salida_literal(result)
        return 2
    content = data.get('structuredContent')
    if not isinstance(content, dict):
        raise Fallo('BLOCKED: falta structuredContent de index_repository')
    nodes, name = content.get('nodes'), content.get('project')
    if type(nodes) is not int or nodes < 0 or not isinstance(name, str) or not name:
        raise Fallo('BLOCKED: project o nodes inválidos en index_repository')
    if content.get('status') == 'degraded':
        print(f'AVISO índice degradado: {nodes} nodos')
    else:
        print(f'✅ OK ({name}: {nodes} nodos)')
    if anterior is not None and name != anterior:
        print(f'AVISO el indexado creó o usó el proyecto {name}, distinto del resuelto {anterior}')
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--resolver', action='store_true')
    group.add_argument('--comprobar', action='store_true')
    group.add_argument('--indexar', action='store_true')
    parser.add_argument('--timeout', type=positivo, metavar='SEGUNDOS')
    args = parser.parse_args()
    if args.timeout is not None and not args.indexar:
        parser.error('--timeout solo es válido con --indexar')
    try:
        try:
            limite = positivo(os.environ.get('CBM_KIT_LIMITE_CONSULTA', '60'))
        except argparse.ArgumentTypeError as error:
            raise Fallo('BLOCKED: CBM_KIT_LIMITE_CONSULTA debe ser un entero > 0') from error
        result = ejecutar(['git', 'rev-parse', '--show-toplevel'])
        if result.returncode or not result.stdout.strip():
            raise Fallo('BLOCKED: no se pudo resolver la raíz Git: ' + detalle(result))
        raiz = os.path.realpath(result.stdout.strip())
        cli = shutil.which('codebase-memory-mcp')
        if not cli:
            raise Fallo('BLOCKED: CLI codebase-memory-mcp no encontrada')
        env = dict(os.environ, CBM_ALLOWED_ROOT=raiz)
        if args.indexar:
            return indexar(cli, env, raiz, limite, args.timeout)
        name = resolver(cli, env, raiz, limite)
        if args.resolver:
            print(name)
            return 0
        return comprobar(cli, env, name, limite)
    except Fallo as error:
        print(str(error))
        return error.codigo


if __name__ == '__main__':
    sys.exit(main())
