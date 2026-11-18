"""Adaptadores SQL de solo lectura; un único hijo aislado por evaluación."""
import json
from pathlib import Path
import re
import subprocess

DATOS_ADMITIDOS = {'version_real': r'[0-9]+\.[0-9]+\.[0-9]+'}


def result(state, why, evidence=None):
    return {'resultado':state,'motivo':why,'evidencia':evidence or [],'archivos':[]}


def preparar_contexto(ctx):
    version=ctx.get('version_stack', ctx['valores']['base_de_datos.version'])
    real=ctx.get('datos',{}).get('version_real')
    ctx['version_stack']=version
    ctx['valores']['base_de_datos.version']={'real':real,'stack':str(version)} if real else None
    active=ctx.get('requiere_dato') and ctx.get('fase')=='entrada'
    ctx['no_comprobables']=[] if active and real else ['base_de_datos.version']
    return ctx


def condicion_activa(ctx, key, row):
    return (bool(ctx.get('requiere_dato') and ctx.get('fase')=='entrada'), '') if key=='base_de_datos.version' else (True,'')


def batch(root, ctx, completo):
    key='_sql_registro_'+str(completo)
    if key not in ctx:
        args=['python3','-B','-E',str(root/'.agents/scripts/sql-lint.py'),'--registro','--sin-datos-prueba']
        if completo:args.append('--completo')
        try:
            p=subprocess.run(args,cwd=root,capture_output=True,text=True,encoding='utf-8',timeout=30)
            if p.returncode:raise ValueError()
            data=json.loads(p.stdout)
            if not isinstance(data['procedimientos'],list) or len(data['comprobaciones'])!=12:raise ValueError()
            ctx[key]=data
        except (OSError,ValueError,TypeError,KeyError,subprocess.TimeoutExpired):
            ctx[key]=None
    return ctx[key]


def gestion_usuarios(root, value='ninguna', ctx=None, completo=False, **kw):
    data=batch(root,ctx,completo)
    if data is None:return result('no_determinable','no se pudo obtener el índice SQL permitido')
    # Firmas comunes de render-perfiles.py. El prefijo puede ser el anterior.
    signatures=['listar_perfiles_filtrados','obtener_detalle_perfil','listar_estado_perfiles',
                'guardar_nuevo_perfil','actualizar_perfil','buscar_perfil_vinculacion','vincular_perfil_clerk']
    present={s for s in signatures if any(n.endswith(s) for n in data['procedimientos'])}
    good=not present if value=='ninguna' else len(present)==len(signatures)
    return result('coincide' if good else 'difiere','presencia de perfiles coherente' if good else 'módulo de perfiles contrario o incompleto',
                  ['presente: '+n for n in sorted(present)]+['ausente: '+n for n in signatures if n not in present])


def nomenclatura(root, ctx=None, row=None, completo=False, **kw):
    data=batch(root,ctx,completo)
    if data is None:return result('no_determinable','no se pudo obtener el índice SQL permitido')
    return data['comprobaciones'][row['clave']]


def version_real(root, value=None, **kw):
    if value is None:return dict(result('no_determinable','no se pudo comprobar la versión real'),informativo=True)
    declared=value['stack']
    if not re.fullmatch(r'[0-9]+(?:\.[0-9]+){0,2}',declared):
        return result('no_determinable','precisión de versión declarada no interpretable')
    wanted=declared.split('.')
    good=[int(x) for x in value['real'].split('.')[:len(wanted)]] == [int(x) for x in wanted]
    return result('coincide' if good else 'difiere','versión real igual a la precisión de stack.yaml' if good else f"base_de_datos.version={declared} no coincide con la versión real {value['real']}.")


DETECTORES = {'gestion_usuarios':gestion_usuarios,'nomenclatura_nombres':nomenclatura,
              'nomenclatura_contenido':nomenclatura,'version_real':version_real}
