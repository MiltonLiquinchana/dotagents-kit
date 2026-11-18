#!/usr/bin/env python3
"""Inventario local: usa la versión declarada, sin consultar bases ni ejecutar sandbox."""
import importlib.util
import json
from pathlib import Path


def inventariar():
    reader = Path(__file__).with_name('stack.py')
    spec = importlib.util.spec_from_file_location('stack_local', reader)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    version = str(module.get('base_de_datos.version'))
    return {'formato': 1, 'stack': 'mysql', 'base': {'mysql': version},
            'servicios': [{'nombre': '.', 'ruta': '.', 'tecnologias': [{'id': 'mysql', 'version': version,
                'estado': 'literal', 'origen': '.agents/stack.yaml:base_de_datos.version'}]}], 'avisos': []}


if __name__ == '__main__':
    print(json.dumps(inventariar(), ensure_ascii=False, indent=2))
