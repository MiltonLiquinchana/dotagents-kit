#!/usr/bin/env python3
# si-archivo integraciones.gestion_usuarios=organizaciones|aplicacion
"""Materializa SQL en OUT_DIR, sin modificar notebooks ni consultar otros proyectos."""
import argparse
import json
import re
from pathlib import Path
import yaml


def identifier(value):
    if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', value):
        raise ValueError('identificador SQL inválido')
    return value


def spelling(value, style):
    words = re.findall(r'[A-Z]+(?=[A-Z][a-z]|$)|[A-Z]?[a-z]+|[0-9]+', value)
    if style == 'snake_case':
        return '_'.join(w.lower() for w in words)
    if style == 'camelCase':
        return value[0].lower() + value[1:]
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
# si integraciones.gestion_usuarios=organizaciones
    parser.add_argument('--tabla-organizaciones')
    parser.add_argument('--pk-organizaciones')
    parser.add_argument('--columna-clerk')
    parser.add_argument('--columna-nombre')
# fin
    args = parser.parse_args()
    agents = Path(__file__).resolve().parents[1]
    stack = yaml.safe_load((agents/'stack.yaml').read_text())
    model = stack['integraciones']['gestion_usuarios']
    if model == 'ninguna':
        parser.error('gestión de usuarios desactivada')
    names = stack['nomenclatura']
    cols = ['PerfilId','ClerkUserId','Nombres','Apellidos','Correo','EstadoPerfilId','EstadoPerfil','Descripcion','FechaCreacion','FechaModificacion']
# si integraciones.gestion_usuarios=organizaciones
    cols += ['OrganizacionId','Nombre','ClerkOrganizationId']
# fin
    mapping = {c: spelling(c, names['columnas']) for c in cols}
    mapping['BASE_DATOS'] = identifier(stack['base_de_datos']['nombre'])
    entities = ['Perfil', 'EstadoPerfil']
# si integraciones.gestion_usuarios=organizaciones
    entities.append('Organizacion')
# fin
    for entity in entities:
        mapping[entity+'Id'] = identifier(spelling(names['clave_primaria'].replace('{Entidad}', entity), names['columnas']))
    tables = [('Perfiles','Perfil'),('EstadoPerfiles','EstadoPerfil')]
# si integraciones.gestion_usuarios=organizaciones
    tables.append(('Organizaciones','Organizacion'))
# fin
    for plural, singular in tables:
        mapping[plural] = spelling(plural if names['tablas_plural'] else singular, names['tablas'])
# si integraciones.gestion_usuarios=organizaciones
    mapping['OrganizacionExternaId'] = mapping['OrganizacionId']
    external = bool(args.tabla_organizaciones)
    if external:
        if model != 'organizaciones' or not all([args.pk_organizaciones,args.columna_clerk,args.columna_nombre]):
            parser.error('tabla existente exige modelo organizaciones, PK, columna Clerk y columna de nombre aprobadas')
        mapping.update(Organizaciones=identifier(args.tabla_organizaciones), OrganizacionExternaId=identifier(args.pk_organizaciones), ClerkOrganizationId=identifier(args.columna_clerk), Nombre=identifier(args.columna_nombre))
# fin
    for value in mapping.values():
        identifier(value)
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    assets = agents/'skills/profile-installer/assets'
    for path in sorted(assets.glob('*.template.sql')):
        sql = path.read_text()
        # Las marcas ya fueron resueltas por el generador; fallar si no lo fueron.
        if re.search(r'^-- (?:si|fin)', sql, re.M):
            raise ValueError('genera el .agents antes de instanciar')
# si integraciones.gestion_usuarios=organizaciones
        if external and path.name == 'tablas.template.sql':
            sql = re.sub(r'CREATE TABLE IF NOT EXISTS '+re.escape('__Organizaciones__')+r'\s*\(.*?\n\);\n', '', sql, count=1, flags=re.S)
# fin
        sql = re.sub(r'__(\w+)__', lambda m: identifier(mapping[m[1]]), sql)
        (out/path.name.replace('.template','')).write_text(sql)
    contract = {'version':1, 'modelo':model, 'tablas_columnas':mapping,
# si integraciones.gestion_usuarios=organizaciones
                'organizacion_existente':external,
# fin
                'estados':{'PENDIENTE':1,'INVITADO_A_CLERK':2,'ACTIVO':3,'INACTIVO':4},
                'nomenclatura':names, 'api':'pendiente del workflow back'}
    prefix = names['prefijo_procedimiento']
    parameter = names['prefijo_parametro']
    summary = ['perfilId','nombres','apellidos','correo','clerkUserId','estadoPerfilId','estadoPerfil']
    detail = summary+['fechaCreacion','fechaModificacion']
    filter_params = []
    binding_aliases = ['perfilId','correo','clerkUserId','estadoPerfilId']
# si integraciones.gestion_usuarios=organizaciones
    summary += ['organizacionId','organizacion']
    detail += ['organizacionId','organizacion']
    filter_params += [[parameter+'OrganizacionId','INT']]
    binding_aliases += ['organizacionId','clerkOrganizationId']
# fin
    procedures = {
        'listar_perfiles_filtrados': [filter_params+[[parameter+'Busqueda','VARCHAR(100)']],summary],
        'obtener_detalle_perfil': [[[parameter+'PerfilId','INT']],detail],
        'listar_estado_perfiles': [[],['estadoPerfilId','estadoPerfil']],
        'guardar_nuevo_perfil': [[[parameter+'DatosPerfil','JSON']],['perfilId']],
        'actualizar_perfil': [[[parameter+'PerfilId','INT'],[parameter+'DatosPerfil','JSON']],[]],
        'buscar_perfil_vinculacion': [[[parameter+'PerfilId','INT nullable'],[parameter+'Correo','VARCHAR(250) nullable']],binding_aliases],
        'vincular_perfil_clerk': [[[parameter+'PerfilId','INT'],[parameter+'ClerkUserId','VARCHAR(250)']],[]],
    }
# si integraciones.gestion_usuarios=organizaciones
    procedures['listar_organizaciones'] = [[],['organizacionId','nombre']]
# fin
    contract['procedimientos'] = {prefix+name:{'parametros':params,'alias_resultado':aliases}
                                  for name,(params,aliases) in procedures.items()}
    (out/'contrato-gestion-usuarios.md').write_text('# Contrato de gestión de usuarios\n\nNombres finales aprobados; el usuario entrega este archivo al back.\n\n```json\n'+json.dumps(contract,ensure_ascii=False,indent=2)+'\n```\n')
    print('SQL y contrato materializados en '+str(out))


if __name__ == '__main__':
    main()
