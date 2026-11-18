#!/usr/bin/env python3
"""Verifica catálogo, invocaciones y clases del preflight; solo lectura.

Uso: python3 -I -B checkers/check-preflight-codigos.py [raiz_sources]
Comprueba fuentes o proyectos generados. No importa ni ejecuta scripts de .agents.
"""
import ast
import json
from pathlib import Path
import re
import sys


def leer(path):
    result = {'workflows': {}, 'codigos': {}}
    section = None
    for line in path.read_text().splitlines():
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        if line in ('workflows:', 'codigos:'):
            section = line[:-1]
        elif line == 'version: 1':
            continue
        elif line.startswith('  ') and section:
            key, raw = line.strip().split(': ', 1)
            if key in result[section]: raise ValueError('clave duplicada: ' + key)
            result[section][key] = json.loads(raw)
        else: raise ValueError('fila no reconocida: ' + line)
    return result


def check(project):
    errors = []
    agents = project / '.agents'
    try:
        data = leer(agents / 'config/codigos.yaml')
        workflows, codes = data['workflows'], data['codigos']
        seen = set()
        for f in sorted((agents / 'workflows').rglob('*.md')):
            for cmd in re.findall(r'`(bash \.agents/scripts/preflight\.sh[^`\n]*)`', f.read_text()):
                m = re.fullmatch(r'bash \.agents/scripts/preflight\.sh --workflow ([\w-]+) --fase (entrada|cierre)(?: --dato [a-z_][a-z0-9_]*=[^\s=]+)*', cmd)
                if not m:
                    if cmd == 'bash .agents/scripts/preflight.sh' and f.name == 'change-version.md': continue
                    errors.append(f'{f.name}: invocación sin workflow/fase válidos: {cmd}'); continue
                name, phase = m.groups(); seen.add(name)
                if name not in workflows: errors.append(f'{f.name}: workflow desconocido {name}')
                if name != f.stem: errors.append(f'{f.name}: cita el workflow ajeno {name}')
                if name == 'change-version' and phase == 'cierre': errors.append('change-version no ejecuta preflight al cierre')
        for name, row in workflows.items():
            if not (agents / 'workflows' / (name + '.md')).exists(): errors.append('workflow ausente: ' + name)
            if name not in seen: errors.append('workflow de catálogo no citado: ' + name)
            if row['grupo'] not in ('E', 'V', 'D'): errors.append('grupo inválido: ' + name)
            if set(row['resuelve']) - set(codes): errors.append('resuelve código inexistente: ' + name)
        if seen - set(workflows): errors.append('faltan workflows en catálogo')
        for code, row in codes.items():
            if not row['remedio'] or row['corta'] not in ('no', 'rama', 'global'): errors.append('remedio/corte inválido: ' + code)
            if row['estricto'] not in ('aviso', 'bloqueo'): errors.append('clase estricta inválida: ' + code)
            for wf in workflows.values():
                for phase in ('entrada', 'cierre'):
                    if row['clases'][wf['grupo'] + '_' + phase] not in ('aviso', 'bloqueo', 'plan'): errors.append('clase inválida: ' + code)
            if code in {'REGENERAR','PREPARACION','STACK_INVALIDO','HERRAMIENTA','REPOSITORIO','PLANTILLA','SERVICIOS'} and any(v != 'bloqueo' for v in row['clases'].values()): errors.append('no es bloqueo universal: ' + code)
        for g in ('V', 'D'):
            if codes['OPEN_NOTEBOOK']['clases'][g + '_entrada'] != 'bloqueo': errors.append('OPEN_NOTEBOOK no bloquea entrada ' + g)
        if not {'REGENERAR','PLANTILLA','HERRAMIENTA','STACK_CODIGO','REGISTRO'} <= set(codes): errors.append('faltan códigos base')
        # Comprobar que las emisiones literales del motor existen en algún catálogo del conjunto.
        for filename in ('preflight.py', 'preflight_stack.py', 'registro-stack.py', 'preflight_datos.py'):
            ast.parse((agents / 'scripts' / filename).read_text())
        if 'set -uo pipefail' not in (agents / 'scripts/preflight.sh').read_text(): errors.append('shell sin set -uo pipefail')
    except (OSError, ValueError, KeyError, TypeError, SyntaxError) as error:
        errors.append(str(error))
    return errors


def main():
    root = Path(sys.argv[1] if len(sys.argv) > 1 else 'sources')
    total = 0
    projects = sorted(p for p in root.iterdir() if (p / '.agents').is_dir())
    if not projects:
        print('No hay proyectos para comprobar.'); return 1
    for p in projects:
        errors = check(p); total += len(errors)
        print('##### ' + p.name)
        for error in errors: print('  ' + error)
    cores = set()
    stack_files = set()
    for p in projects:
        try:
            local_codes = leer(p / '.agents/config/codigos.yaml')['codigos']
            core = (p / '.agents/scripts/preflight.py').read_text()
            own = (p / '.agents/scripts/preflight_stack.py').read_text()
            cores.add(core)
            stack_files.add(own)
            if any(token in core for token in ("if stack ==", "ctx['stack']", "backend.java", "frontend.eslint_config", "base_de_datos.motor", "javaToolchains", "comprobar-versiones.mjs")):
                print('  El núcleo contiene comprobaciones propias de un stack'); total += 1
            names = []
            tree = ast.parse(own)
            for n in tree.body:
                if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'WORKFLOWS' for t in n.targets):
                    names = ast.literal_eval(n.value)
                elif isinstance(n, ast.AugAssign) and isinstance(n.target, ast.Name) and n.target.id == 'WORKFLOWS':
                    names += ast.literal_eval(n.value)
            if set(names) != set(leer(p / '.agents/config/codigos.yaml')['workflows']):
                print('  Nombres de uso y catálogo no coinciden'); total += 1
            for text in (core, own):
                for node in ast.walk(ast.parse(text)):
                    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in ('add', 'check') and node.args and isinstance(node.args[0], ast.Constant):
                        if node.args[0].value not in local_codes:
                            print(f'  Código emitido sin catálogo: {node.args[0].value}'); total += 1
        except (OSError, ValueError, KeyError, TypeError, AttributeError, SyntaxError) as error:
            print('  ' + str(error)); total += 1
    if len(cores) != 1:
        print('  El núcleo no es idéntico entre stacks'); total += 1
    print('Total de problemas: ' + str(total))
    return int(total > 0)


if __name__ == '__main__':
    sys.exit(main())
