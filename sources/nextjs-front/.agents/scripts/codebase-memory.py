#!/usr/bin/env python3
"""Resuelve, comprueba o indexa la raíz Git mediante la CLI de Codebase Memory."""
import argparse
import json
import os
import shutil
import subprocess
import sys


class Fallo(Exception):
    def __init__(self, mensaje, codigo=2):
        super().__init__(mensaje)
        self.codigo = codigo


def ejecutar(argv, env=None):
    try:
        return subprocess.run(argv, capture_output=True, text=True,
                              encoding='utf-8', errors='replace', env=env)
    except OSError as error:
        raise Fallo('BLOCKED: ' + str(error)) from error


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
        raise Fallo('BLOCKED: respuesta de CBM no es un objeto JSON')
    return data


def resolver(cli, env, raiz):
    offset = 0
    while True:
        result = ejecutar([cli, 'cli', '--quiet', 'list_projects', '--format', 'json',
                           '--limit', '500', '--offset', str(offset)], env)
        if result.returncode:
            raise Fallo('BLOCKED: list_projects: ' + detalle(result))
        data = objeto(result)
        if 'error' in data or not isinstance(data.get('projects'), list):
            raise Fallo('BLOCKED: list_projects: ' + detalle(result))
        for project in data['projects']:
            if not isinstance(project, dict):
                raise Fallo('BLOCKED: entrada inválida en list_projects')
            path, name = project.get('root_path'), project.get('name')
            if isinstance(path, str) and os.path.isabs(path) and os.path.realpath(path) == raiz:
                if not isinstance(name, str) or not name:
                    raise Fallo('BLOCKED: proyecto CBM sin name válido')
                return name
        if data.get('has_more') is False:
            raise Fallo('FALTA proyecto sin indexar', 1)
        if data.get('has_more') is not True or not data['projects']:
            raise Fallo('BLOCKED: paginación inválida de list_projects')
        offset += len(data['projects'])


def comprobar(cli, env, name):
    result = ejecutar([cli, 'cli', '--quiet', 'index_status', '--project', name,
                       '--format', 'json'], env)
    if result.returncode:
        raise Fallo('FALTA ' + (detalle(result) or 'index_status falló'), 1)
    try:
        data = objeto(result)
    except Fallo as error:
        raise Fallo('FALTA ' + str(error), 1) from error
    if 'error' in data or data.get('status') != 'ready':
        raise Fallo('FALTA ' + detalle(result), 1)
    nodes = data.get('nodes')
    if type(nodes) is not int or nodes < 0:
        raise Fallo('FALTA nodes inválido en index_status', 1)
    if nodes == 0:
        print('AVISO índice sin nodos')
    else:
        print(f'OK {name}: {nodes} nodos')
    return 0


def indexar(cli, env, raiz):
    result = ejecutar([cli, 'cli', '--quiet', '--json', 'index_repository',
                       '--repo-path', raiz], env)
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
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--resolver', action='store_true')
    group.add_argument('--comprobar', action='store_true')
    group.add_argument('--indexar', action='store_true')
    args = parser.parse_args()
    try:
        result = ejecutar(['git', 'rev-parse', '--show-toplevel'])
        if result.returncode or not result.stdout.strip():
            raise Fallo('BLOCKED: no se pudo resolver la raíz Git: ' + detalle(result))
        raiz = os.path.realpath(result.stdout.strip())
        cli = shutil.which('codebase-memory-mcp')
        if not cli:
            raise Fallo('BLOCKED: CLI codebase-memory-mcp no encontrada')
        env = dict(os.environ, CBM_ALLOWED_ROOT=raiz)
        if args.indexar:
            return indexar(cli, env, raiz)
        name = resolver(cli, env, raiz)
        if args.resolver:
            print(name)
            return 0
        return comprobar(cli, env, name)
    except Fallo as error:
        print(str(error))
        return error.codigo


if __name__ == '__main__':
    sys.exit(main())
