"""Datos de clasificación, sin dependencias externas ni lectura de configuración de herramientas."""
import json
from pathlib import Path


def catalogo(agents):
    result = {'workflows': {}, 'codigos': {}}
    section = None
    for raw in (agents / 'config/codigos.yaml').read_text(encoding='utf-8').splitlines():
        if not raw.strip() or raw.lstrip().startswith('#'):
            continue
        if raw in ('workflows:', 'codigos:'):
            section = raw[:-1]
        elif raw == 'version: 1':
            continue
        elif raw.startswith('  ') and section:
            key, value = raw.strip().split(': ', 1)
            if key in result[section]:
                raise ValueError('clave duplicada en codigos.yaml')
            result[section][key] = json.loads(value)
        else:
            raise ValueError('formato de codigos.yaml no admitido')
    if not result['workflows'] or not result['codigos']:
        raise ValueError('catálogo vacío')
    for row in result['codigos'].values():
        if row['estricto'] not in ('bloqueo', 'aviso') or row['corta'] not in ('no', 'rama', 'global'):
            raise ValueError('código inválido')
        for workflow in result['workflows'].values():
            for phase in ('entrada', 'cierre'):
                if row['clases'][workflow['grupo'] + '_' + phase] not in ('bloqueo', 'aviso', 'plan'):
                    raise ValueError('clase inválida')
    return result


def clase(data, code, workflow='', phase='entrada'):
    row = data['codigos'][code]
    return row['clases'][data['workflows'][workflow]['grupo'] + '_' + phase] if workflow else row['estricto']
