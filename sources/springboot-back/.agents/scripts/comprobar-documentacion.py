#!/usr/bin/env python3
"""Cotejo local estricto del catálogo; diagnóstico explícito para reparar, sin red."""
import importlib.util
import json
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('documentacion_local', root / 'scripts/documentacion.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
try:
    if sys.argv[1:] not in ([], ['--diagnostico']):
        raise module.Blocked('ARGUMENTOS', 'Usa el cotejo estricto sin argumentos o --diagnostico únicamente para preparar/cambiar documentación.')
    diagnostic = sys.argv[1:] == ['--diagnostico']
    catalog = module.cargar_catalogo(root)
    result = module.Registro(root, catalog).check()
    if diagnostic:
        print('DIAGNÓSTICO: faltantes/desajustes para reparación; esto no valida una entrega ni sustituye el preflight.')
    for warning in result['avisos']:
        print(warning if warning.startswith('AVISO ') else 'AVISO: ' + warning)
    for error in result['errores']:
        print(('PENDIENTE: ' if diagnostic else 'BLOCKED: ') + error, file=sys.stderr)
    if not result['errores']:
        print('OK: comparación documental local completada, sin red.')
    sys.exit(1 if result['errores'] and not diagnostic else 0)
except module.Blocked as error:
    print('BLOCKED: ' + error.code + ': ' + error.message, file=sys.stderr)
    sys.exit(1)
except (ValueError, OSError, KeyError, TypeError):
    print('BLOCKED: no puedes leer el registro o inventario local; revisa su esquema sin sobrescribirlo.', file=sys.stderr)
    sys.exit(1)
