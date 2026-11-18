#!/usr/bin/env python3
"""Registro de decisiones y detectores deterministas de solo lectura."""
import argparse
from functools import lru_cache
import shlex
import datetime
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys


def cargar_datos(agents):
    path = agents / 'scripts/preflight_datos.py'
    spec = importlib.util.spec_from_file_location('preflight_datos', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@lru_cache(maxsize=None)
def cargar_detectores(agents):
    path = agents / 'scripts/registro_detectores.py'
    if not path.is_file():
        return {'DETECTORES': {}, 'condicion_activa': lambda *a, **k: (True, ''), 'aplicabilidad_servicio': lambda *a, **k: (True, '')}
    spec = importlib.util.spec_from_file_location('registro_detectores', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def contexto(agents, root):
    reader = agents / 'scripts/stack.mjs'
    cmd = ['node', str(reader)] if reader.exists() else ['python3', '-B', '-E', str(agents / 'scripts/stack.py')]
    r = subprocess.run(cmd + ['registro-datos'], cwd=root, capture_output=True, text=True, errors='replace')
    if r.stderr:
        print(r.stderr.strip(), file=sys.stderr)
    if r.returncode:
        raise ValueError('no se pudo obtener registro-datos del lector del stack: ' + (r.stdout + r.stderr).strip())
    return json.loads(r.stdout)


def validar_datos(agents, entradas):
    """Canal efímero con lista blanca del detector propio; nunca persiste datos."""
    mod = cargar_detectores(agents)
    permitidos = getattr(mod, 'DATOS_ADMITIDOS', {})
    result = {}
    for entrada in entradas:
        key, sep, value = entrada.partition('=')
        if not sep or key in result or key not in permitidos or len(value) > 80 or not re.fullmatch(permitidos[key], value):
            raise ValueError('dato inválido, duplicado o no admitido en este stack')
        result[key] = value
    return result


def celdas(line):
    cells, current, escaped = [], '', False
    for c in line.strip():
        if escaped:
            current += c; escaped = False
        elif c == '\\':
            escaped = True
        elif c == '|':
            cells.append(current.strip()); current = ''
        else:
            current += c
    if escaped:
        raise ValueError('escape incompleto')
    cells.append(current.strip())
    if len(cells) < 2 or cells[0] != '' or cells[-1] != '':
        raise ValueError('faltan separadores externos')
    return cells[1:-1]


def canon(v):
    if v is None:
        return ''
    if isinstance(v, bool):
        return 'true' if v else 'false'
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        if isinstance(v, float) and v.is_integer():
            return str(int(v))
        return str(v)
    if isinstance(v, str):
        return v
    if isinstance(v, (list, dict)):
        def orden(x):
            if isinstance(x, list):
                return [orden(i) for i in x]
            if isinstance(x, dict):
                return {k: orden(x[k]) for k in sorted(x)}
            return x
        return json.dumps(orden(v), ensure_ascii=False, separators=(',', ':'))
    return json.dumps(v, ensure_ascii=False, separators=(',', ':'))


def canon_valor(row, value):
    t = row.get('tipo', 'string')
    if t in ('nullable_string', 'list', 'json') and value in (None, ''):
        return ''
    if isinstance(value, str) and t in ('bool', 'nullable_string', 'list', 'json'):
        # valor ya canónico en texto de registro
        if t == 'bool':
            if value not in ('true', 'false'):
                raise ValueError('valor no canónico bool')
            return value
        if t == 'nullable_string':
            return value
        if t in ('list', 'json'):
            try:
                return canon(json.loads(value))
            except Exception as e:
                raise ValueError('valor no canónico ' + t)
    if t == 'bool':
        if isinstance(value, bool):
            return 'true' if value else 'false'
        if value in ('true', 'false', True, False):
            return 'true' if str(value) == 'True' or value == 'true' or value is True else 'false'
    if t == 'nullable_string':
        if value is None:
            return ''
        return str(value) if not isinstance(value, str) else value
    if t in ('list', 'json'):
        return canon(value)
    if isinstance(value, str):
        return value
    return canon(value)


def servicios_alcance(row, ctx):
    aplica = row.get('aplica', 'por_servicio')
    if aplica == 'proyecto':
        return ['*']
    if aplica == 'solo_gateway':
        gw = ctx.get('gateway')
        return [gw] if gw else []
    if aplica == 'sin_gateway':
        gw = ctx.get('gateway')
        return [s for s in ctx.get('servicios', []) if s != gw]
    return list(ctx.get('servicios', []))


def registro(root, ctx, checks, cond_fn):
    warnings, reminders, candidates = [], [], {}
    ctx['_nombres_aceptados'] = {}
    path = root / 'docs/decisiones-stack.md'
    if not path.exists():
        return warnings, reminders, set()
    try:
        lines = path.read_text(encoding='utf-8').splitlines()
    except (OSError, UnicodeError):
        return ['docs/decisiones-stack.md: archivo ilegible; no cuenta como registrado.'], [], set()
    expected = ['clave', 'valor', 'decisión', 'alcance', 'fecha']
    header = False
    for n, line in enumerate(lines, 1):
        if not line.lstrip().startswith('|'):
            continue
        try:
            cells = celdas(line)
            if cells in (expected, expected + ['nombres']):
                header = True
                continue
            if len(cells) in (5,6) and all(re.fullmatch(r':?-+:?', c) for c in cells):
                continue
            if not header or len(cells) not in (5,6):
                raise ValueError('cabecera o columnas inválidas')
            key, value, decision, scope, date = cells[:5]
            if key not in checks:
                raise ValueError('clave sin comprobación implementada en este stack')
            if decision not in ('no', 'para revisión', 'aplicado', 'sustituido'):
                raise ValueError('decisión inválida')
            if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', date):
                raise ValueError('fecha inválida')
            datetime.date.fromisoformat(date)
            services = json.loads(scope)
            if not isinstance(services,list) or not services or any(not isinstance(x,str) for x in services) or len(set(services)) != len(services):
                raise ValueError('alcance debe ser lista explícita no vacía sin duplicados')
            names = json.loads(cells[5]) if len(cells)==6 and cells[5] else []
            if not isinstance(names,list) or any(not isinstance(x,str) or not x for x in names) or names != sorted(set(names)):
                raise ValueError('nombres debe ser lista JSON ordenada de textos distintos')
            if names and not checks[key].get('por_nombre', False):
                warnings.append(f'docs/decisiones-stack.md:{n}: fila no válida: {key} no admite nombres; usa la fila sin la sexta columna')
                continue
            if key in ctx.get('no_comprobables', []):
                continue
            active, _ = cond_fn(ctx,key,checks[key])
            if not active:
                warnings.append(f'{key}: la clave no aplica en el estado actual; la fila de docs/decisiones-stack.md no tiene efecto.')
                continue
            if decision == 'sustituido' or decision == 'aplicado' and not checks[key].get('aplicado_cubre'):
                continue
            if canon_valor(checks[key],value) != canon_valor(checks[key],ctx['valores'].get(key)):
                warnings.append(f'{key}: la decisión no cubre el valor actual; se revisa la muestra.')
                continue
            targets = set()
            for aplica in checks[key].get('alcances_hallazgos',[checks[key].get('aplica','por_servicio')]):
                targets.update(servicios_alcance(dict(checks[key],aplica=aplica),ctx))
            missing = sorted(set(services)-targets)
            if missing:
                warnings.append(f'{path.name}:{n}: servicios/alcances inexistentes o no aplicables: {",".join(missing)}.')
            for service in services:
                if service in targets:
                    candidates.setdefault((key,service),[]).append((n,decision,date,names))
        except (ValueError,TypeError,KeyError) as error:
            warnings.append(f'docs/decisiones-stack.md:{n}: fila mal formada ({error}); no cuenta como registrada; corrígela dentro del plan aprobado.')
    if not header:
        return warnings+['docs/decisiones-stack.md: falta cabecera; ninguna fila cuenta como registrada.'], [], set()
    covered = set()
    grouped = {}
    for pair, rows in sorted(candidates.items()):
        seen = set()
        overlap = len(rows)>1 and any(not r[3] for r in rows)
        for _,_,_,names in rows:
            overlap |= bool(seen.intersection(names))
            seen.update(names)
        if overlap:
            warnings.append(f'{pair[0]} servicio={pair[1]}: filas vigentes solapadas; no cuentan como registradas.')
            continue
        if any(not r[3] for r in rows):
            covered.add(pair)
        else:
            ctx['_nombres_aceptados'][pair] = seen
        for _,decision,date,names in rows:
            if decision != 'aplicado':
                grouped.setdefault((pair[0],decision,date,tuple(names)),[]).append(pair[1])
    for (key,decision,date,names), services in sorted(grouped.items()):
        detail = f'{key}={canon_valor(checks[key],ctx["valores"].get(key))}: decisión {decision}; servicios={",".join(sorted(services))} ({date})'
        if names:
            detail += '; nombres=' + canon(list(names))
        reminders.append(detail + ('; pendiente registrado.' if decision=='no' else '; puedes aplicarlo en el plan de esta tarea.'))
    return warnings, reminders, covered


def restar_nombres(finding, aceptados):
    """Una excepción de nombres conocidos nunca cubre una lectura incierta."""
    original = set(finding.get('nombres', []))
    if finding.get('resultado') == 'no_determinable' or not original or not (original & aceptados):
        return finding
    f = dict(finding)
    removed = original & aceptados
    remaining = sorted(original - aceptados)
    pending = list(f.get('no_evaluados', {}).get('nombres', []))
    mapping = f.get('evidencia_por_nombre', {})
    evidence = [e for name in remaining for e in mapping.get(name, [name])]
    if pending:
        evidence += [f'No evaluados: {len(pending)}'] + ['no evaluado: '+n for n in pending]
        f['no_evaluados'] = {'cantidad': len(pending), 'nombres': pending}
    if 'evaluados' in f:
        counts = f.get('evaluados_por_nombre')
        if counts is not None:
            f['evaluados_por_nombre'] = {n:c for n,c in counts.items() if n not in removed}
            f['evaluados'] = sum(f['evaluados_por_nombre'].values())
        else:
            f['evaluados'] = max(0, f['evaluados'] - len(removed))
    visible = remaining + pending
    filemap = f.get('archivos_por_nombre')
    if filemap is not None:
        f['archivos'] = sorted({p for n in visible for p in filemap.get(n, [])})
        f['archivos_por_nombre'] = {n:filemap.get(n, []) for n in visible}
    else:
        f['archivos'] = [p for p in f.get('archivos', []) if p in visible or any(e == p or e.startswith(p+':') for e in evidence)]
    f['nombres'] = remaining
    f['evidencia'] = evidence
    f['evidencia_por_nombre'] = {n:mapping.get(n, [n]) for n in remaining}
    if not remaining:
        if not pending:
            return None
        f['resultado'] = 'no_determinable' if not f.get('evaluados', 0) else 'coincide'
        f['motivo'] = 'sin elementos evaluables' if f['resultado']=='no_determinable' else 'sin diferencias tras las excepciones de nombres'
        f['nombres'] = pending
    return f


def evaluar(root, agents, ctx, completo=False, services=None, workflow='', comprobar=True, phase='entrada'):
    detmod = cargar_detectores(agents)
    data = cargar_datos(agents)
    codes = data.catalogo(agents)
    if workflow and workflow not in codes['workflows']:
        raise ValueError('workflow desconocido: ' + workflow)
    ctx = dict(ctx, valores=dict(ctx.get('valores', {})), workflow=workflow, fase=phase,
               requiere_dato=codes['workflows'].get(workflow, {}).get('requiere_dato', False))
    hook = getattr(detmod, 'preparar_contexto', None)
    if hook:
        ctx = hook(ctx)
    config = json.loads((agents / 'config/registro-stack.json').read_text(encoding='utf-8'))
    checks = {}
    for row in config.get('comprobaciones', []):
        pattern = row['clave']
        keys = [k for k in ctx['valores'] if re.fullmatch(re.escape(pattern).replace(r'\*', r'[^.]+'), k)] if '*' in pattern else [pattern]
        for key in keys:
            checks[key] = dict(row, clave=key)

    DETECTORES = getattr(detmod, 'DETECTORES', {})
    cond_fn = getattr(detmod, 'condicion_activa', lambda c,k,r:(True,''))
    apply_fn = getattr(detmod, 'aplicabilidad_servicio', None)
    warnings, reminders, covered = registro(root, ctx, checks, cond_fn)
    selected = set(services or [])
    known = set(ctx.get('servicios', []))
    if selected == {'*'}:
        selected = set()
    if selected - known:
        raise ValueError('servicios desconocidos: ' + ','.join(sorted(selected - known)))
    result = []
    if not comprobar:
        return {'version': 1, 'avisos': warnings, 'recordatorios': reminders, 'resultados': []}
    wmeta = codes['workflows'].get(workflow, {}) if workflow else {}
    resuelve = set(wmeta.get('resuelve', []))
    alcance = wmeta.get('alcance', '')
    for key, row in sorted(checks.items()):
        activa, _ = cond_fn(ctx, key, row)
        if not activa:
            continue
        targets = servicios_alcance(row, ctx)
        iter_targets = targets
        if completo and selected and row.get('aplica') != 'proyecto':
            # completo on specific services for per-service checks
            iter_targets = [s for s in sorted(selected) if s in targets]
        for service in iter_targets:
            if service not in targets and service != '*':
                continue
            promoted = row.get('codigo_tocado') and service in selected and wmeta.get('grupo') in row.get('grupos_tocado', [])
            if (key, service) in covered and not row.get('alcances_hallazgos') and not promoted:
                continue
            if apply_fn:
                ok, why = apply_fn(root, ctx, key, row, service)
                if not ok:
                    continue
            value = ctx['valores'].get(key)
            try:
                valstr = canon_valor(row, value)
            except Exception:
                valstr = canon(value)
            if isinstance(value, str) and ('\n' in value or '\r' in value):
                warnings.append(key + ': valor multilínea no admitido; no cuenta como registrado.')
                continue
            fnname = row['completa' if completo else 'muestra']
            fn = DETECTORES.get(fnname)
            if not fn:
                warnings.append(key + ': detector no disponible en este stack.')
                continue
            try:
                finding = fn(root=root, service=service, value=value, completo=completo, ctx=ctx, row=row)
            except Exception as error:
                finding = {'resultado': 'no_determinable', 'motivo': 'falló el detector: ' + type(error).__name__, 'evidencia': [], 'archivos': []}
            findings = finding if isinstance(finding, list) else [finding]
            for f in findings:
                if not isinstance(f, dict):
                    f = {'resultado': 'no_determinable', 'motivo': 'detector inválido', 'evidencia': [], 'archivos': []}
                f = dict(f)
                f.setdefault('clave', key)
                f.setdefault('valor', valstr)
                f.setdefault('servicio', service)
                code = f.get('codigo') or row.get('codigo_si', {}).get(canon(value), row.get('codigo', 'STACK_CODIGO'))
                touched_code = row.get('codigo_tocado')
                touched = bool(touched_code and f.get('servicio') in selected and
                               wmeta.get('grupo') in row.get('grupos_tocado', []) and
                               (not row.get('campo_tocado') or f.get(row['campo_tocado'])))
                if (f['clave'], f['servicio']) in covered and not touched:
                    continue
                accepted = ctx.get('_nombres_aceptados', {}).get((f['clave'], f['servicio']), set())
                f = restar_nombres(f, accepted)
                if f is None:
                    continue
                if completo and selected and f['servicio'] != '*' and f['servicio'] not in selected:
                    continue
                if touched:
                    code = touched_code
                f['codigo'] = code
                clase = data.clase(codes, code, workflow, phase)
                if f.get('informativo'):
                    clase = 'aviso'
                if f.get('resultado') == 'difiere' and not f.get('informativo') and phase == 'entrada' and workflow and code in resuelve and not (row.get('informativo_vacio') and value in (None, '')):
                    scope = row.get('alcance', codes['codigos'][code].get('alcance', alcance))
                    if scope in ('todos_los_servicios', 'proyecto') or (scope == 'servicios_del_plan' and f['servicio'] in selected):
                        clase = 'plan'
                if clase == 'plan' and f.get('resultado') != 'difiere':
                    clase = 'aviso'
                if f.get('resultado') == 'no_determinable':
                    clase = 'aviso'
                f['clase'] = clase
                result.append(f)
    return {'version': 1, 'avisos': warnings, 'recordatorios': reminders, 'resultados': result}


def evidencia_visible(row, completo=False, contadores=None):
    lines = [line for item in row.get('evidencia', []) for line in str(item).splitlines()]
    key = row.get('clave', '')
    limit = max(0, 10 - (contadores or {}).get(key, 0))
    shown = lines if completo else lines[:limit]
    if contadores is not None:
        contadores[key] = contadores.get(key, 0) + len(shown)
    return shown + ([f'… y {len(lines)-len(shown)} más (--completo)'] if len(shown) < len(lines) else [])


def detalle(row, workflow='', datos=None):
    args = ['python3', '-I', '-B', '.agents/scripts/registro-stack.py', 'comprobar', '--completo',
            '--servicios', row.get('servicio', '*')]
    if workflow:
        args += ['--workflow', workflow]
    for key, value in sorted((datos or {}).items()):
        args += ['--dato', key + '=' + value]
    return shlex.join(args)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('accion', choices=['recordar', 'comprobar'])
    parser.add_argument('--completo', action='store_true')
    parser.add_argument('--dato', action='append', default=[])
    parser.add_argument('--servicios')
    parser.add_argument('--workflow', default='')
    parser.add_argument('--formato', choices=['texto', 'json'], default='texto')
    args = parser.parse_args()
    agents = Path(__file__).resolve().parents[1]
    try:
        datos = validar_datos(agents, args.dato)
    except ValueError:
        parser.error('dato inválido, duplicado o no admitido en este stack')
    try:
        git = subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True, errors='replace')
        if git.returncode:
            raise ValueError('no se ejecuta dentro de un repositorio git')
        root = Path(git.stdout.strip()).resolve()
        ctx = contexto(agents, root)
        ctx['datos'] = datos
        result = evaluar(root, agents, ctx, args.completo, args.servicios.split(',') if args.servicios else None, args.workflow, args.accion == 'comprobar')
        if args.accion == 'recordar':
            result['resultados'] = []
        if args.formato == 'json':
            print(json.dumps(result, ensure_ascii=False))
        else:
            for text in result['avisos'] + result['recordatorios']:
                print('AVISO [REGISTRO] ' + text)
            data = cargar_datos(agents).catalogo(agents)
            evidence_counts = {}
            for row in result['resultados']:
                if row.get('resultado') == 'coincide':
                    continue
                code = row.get('codigo', 'STACK_CODIGO')
                if row.get('informativo'):
                    print('AVISO [' + code + '] servicio=* ' + row['motivo'])
                    continue
                clase = row.get('clase', 'aviso')
                print({'plan': 'PARTE DEL PLAN', 'bloqueo': 'BLOCKED', 'aviso': 'AVISO'}[clase] + f' [{code}] servicio=' + str(row.get('servicio','*')) + ' clave=' + str(row.get('clave','')) + ' valor=' + str(row.get('valor','')) + ' resultado=' + str(row.get('resultado','')) + ' motivo=' + str(row.get('motivo','')))
                for evidence in evidencia_visible(row, args.completo, evidence_counts):
                    print('  ' + evidence)
                srv = row.get('servicio','*')
                print('Detalle opcional: ' + detalle(row, args.workflow, datos))
                remedio = data['codigos'].get(code, data['codigos'].get('STACK_CODIGO', {})).get('remedio','')
                print('RESULTADO codigo=' + code + ' clase=' + clase + ' servicio=' + str(srv) + ' remedio=' + json.dumps(remedio, ensure_ascii=False))
        return 0
    except (ValueError, OSError, UnicodeError, KeyError, TypeError, AttributeError) as error:
        print('BLOCKED [PLANTILLA] ' + str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
