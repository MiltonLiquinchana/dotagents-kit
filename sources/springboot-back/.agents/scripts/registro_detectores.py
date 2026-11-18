"""Detectores específicos del stack backend (solo lectura)."""
import importlib.util
import json
import os
import re
import subprocess
from pathlib import Path


def _servicios_mod(root):
    agents = root / '.agents'
    path = agents / 'scripts' / 'servicios.py'
    spec = importlib.util.spec_from_file_location('servicios_mod', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _canon(v):
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
    return json.dumps(v, ensure_ascii=False, separators=(',', ':'), sort_keys=True)


def condicion_activa(ctx, key, row):
    # answer 6,7: evaluate like stack.mjs requerida_con
    valores = ctx.get('valores', {})
    if key == 'backend.jdk_ruta_desarrollo' and valores.get(key) in (None, ''):
        return False, 'ruta de desarrollo no gestionada'
    if key == 'nomenclatura.estrategia_fisica_jpa':
        return valores.get('backend.persistencia') == 'jpa', 'backend.persistencia=jpa'
    if key == 'integraciones.clerk_issuer_uri':
        return valores.get('integraciones.autenticacion') == 'clerk', 'integraciones.autenticacion=clerk'
    if key == 'integraciones.variables_autenticacion':
        return valores.get('integraciones.autenticacion') == 'clerk' and valores.get('integraciones.gestion_usuarios') != 'ninguna', 'requerida_con'
    if key.startswith('devops.'):
        if valores.get('devops.infraestructura') != 'jenkins-kubernetes':
            return False, 'devops.infraestructura=jenkins-kubernetes'
        entorno = re.fullmatch(r'devops\.entornos\.([^.]+)\.([^.]+)', key)
        if entorno:
            nombre, campo = entorno.groups()
            if campo in ('replicas', 'cpu_peticion', 'cpu_limite', 'memoria_peticion',
                         'memoria_limite', 'nodo_puerto_base', 'gateway_nodo_puerto',
                         'cors_origenes', 'clerk_issuer_uri'):
                if valores.get(f'devops.entornos.{nombre}.desplegar') != 'true':
                    return False, f'devops.entornos.{nombre}.desplegar=true'
            if campo in ('gateway_nodo_puerto', 'cors_origenes') and not ctx.get('gateway'):
                return False, 'backend.gateway!=null'
            if campo == 'clerk_issuer_uri' and valores.get('integraciones.autenticacion') != 'clerk':
                return False, 'integraciones.autenticacion=clerk'
        return True, ''
    return True, ''


def aplicabilidad_servicio(root, ctx, key, row, service):
    # api_error: si no exponen controladores, no se evalúan; si tienen @RestController sin manejador -> no_determinable handled in detector
    if key.startswith('api_error.'):
        if service in ('*', None):
            return False, ''
        svc = root / service / 'src/main/java'
        if not svc.is_dir():
            return False, ''
        has_rest = False
        for p in sorted(svc.rglob('*.java')):
            try:
                t = p.read_text(encoding='utf-8', errors='replace')
            except OSError:
                continue
            if re.search(r'@RestController\b', limpiar_java(t)):
                has_rest = True
                break
        if not has_rest:
            return False, 'sin controladores'
    return True, ''


def limpiar_java(text):
    return re.sub(r'//[^\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"',
                  lambda m: re.sub(r'[^\n]', ' ', m.group()), text)


def limpiar_gradle(text):
    tokens = r"\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'|/\*[\s\S]*?\*/|//[^\n]*"
    return re.sub(tokens, lambda m: re.sub(r'[^\n]', ' ', m.group())
                  if m.group().startswith(('/*', '//')) else m.group(), text)


def _result(estado, motivo, evidencia=None, archivos=None):
    return {'resultado': estado, 'motivo': motivo, 'evidencia': evidencia or [], 'archivos': archivos or []}


def lombok(root, service='*', value='false', completo=False, ctx=None, row=None, **k):
    folder = (root / service).resolve()
    evidence = []
    if not folder.is_relative_to(root.resolve()):
        return _result('no_determinable', 'servicio fuera del repositorio')
    def leer(p):
        if not p.resolve().is_relative_to(folder):
            raise ValueError('symlink fuera del servicio')
        return p.read_text(encoding='utf-8')
    try:
        build = folder / 'build.gradle'
        gradle = leer(build)
        gradle_code = limpiar_gradle(gradle)
        sources = sorted((folder / 'src/main/java').rglob('*.java'))
        mains = [p for p in sources if re.search(r'@(?:org\.springframework\.boot\.autoconfigure\.)?SpringBootApplication\b', limpiar_java(leer(p)))]
        literal = re.findall(r'(compileOnly|annotationProcessor|implementation|api)\s*(?:\(\s*)?[\'\"]org\.projectlombok:lombok(?::[^\'\"]*)?[\'\"]', gradle_code)
        files = sorted(set(mains + (sources + sorted((folder / 'src/test/java').rglob('*.java')) if completo else [])))
        for p in files:
            for n, line in enumerate(limpiar_java(leer(p)).splitlines(), 1):
                if re.search(r'\b(?:import\s+(?:static\s+)?lombok\.|lombok\.)', line):
                    evidence.append(f'{p.relative_to(root)}:{n}: uso/import Lombok')
        for n, line in enumerate(gradle_code.splitlines(), 1):
            if 'org.projectlombok:lombok' in line and not line.lstrip().startswith('//'):
                evidence.append(f'{build.relative_to(root)}:{n}: org.projectlombok:lombok')
        val = _canon(value)
        if val == 'false' and (literal or evidence):
            state, reason = 'difiere', 'la muestra contiene Lombok'
        elif 'io.freefair.lombok' in gradle_code or any('lombok' in line.lower() and re.search(r'libs\.|versionCatalog', line) for line in gradle_code.splitlines()):
            state, reason = 'no_determinable', 'plugin io.freefair.lombok o catálogo/alias no resoluble por esta muestra'
        elif len(mains) != 1:
            state, reason = 'no_determinable', f'se encontraron {len(mains)} clases principales @SpringBootApplication'
        elif val == 'true':
            state = 'coincide' if 'compileOnly' in literal and 'annotationProcessor' in literal else 'difiere'
            reason = 'configuración literal de dependencia y procesador'
        else:
            state, reason = 'coincide', 'sin usos detectados en el alcance de la muestra'
        return _result(state, reason, evidence, [str(build.relative_to(root))] + [str(p.relative_to(root)) for p in files])
    except (OSError, UnicodeError, ValueError) as error:
        return _result('no_determinable', str(error))


def persistencia(root, service='*', value='jpa', completo=False, ctx=None, row=None, **k):
    build = root / service / 'build.gradle'
    try:
        text = build.read_text(encoding='utf-8')
        code = limpiar_gradle(text)
        has_jpa = 'spring-boot-starter-data-jpa' in code
        has_jdbc = 'spring-boot-starter-jdbc' in code
        evidencia = []
        for n,line in enumerate(code.splitlines(),1):
            if 'spring-boot-starter-data-jpa' in line or 'spring-boot-starter-jdbc' in line:
                evidencia.append(f'{build.relative_to(root)}:{n}: {line.strip()}')
        val = str(value)
        if val == 'jpa':
            state = 'coincide' if has_jpa and not has_jdbc else 'difiere'
        elif val == 'jdbc':
            state = 'coincide' if has_jdbc and not has_jpa else 'difiere'
        else:
            state = 'no_determinable'
        if not has_jpa and not has_jdbc:
            if re.search(r'\blibs\.|apply\s+from\s*:', code):
                return _result('no_determinable', 'dependencia por catálogo o script no resoluble', [], [str(build.relative_to(root))])
            state = 'difiere'
        if state == 'coincide':
            motivo = 'dependencia coincide con backend.persistencia'
        else:
            motivo = 'dependencia de persistencia distinta del valor declarado'
        return _result(state, motivo, evidencia, [str(build.relative_to(root))])
    except (OSError, UnicodeError) as e:
        return _result('no_determinable', str(e))


def group(root, service='*', value='', completo=False, ctx=None, row=None, **k):
    build = root / service / 'build.gradle'
    try:
        text = build.read_text(encoding='utf-8')
        m = re.search(r"^\s*group\s*=?\s*['\"]([^'\"]*)['\"]", text, re.M)
        if not m:
            return _result('no_determinable', 'no se encontró group literal', [], [str(build.relative_to(root))])
        found = m.group(1)
        line = text[:m.start()].count('\n') + 1
        ev = [f'{build.relative_to(root)}:{line}: group = \'{found}\'']
        state = 'coincide' if found == str(value) else 'difiere'
        motivo = 'group coincide' if state == 'coincide' else 'group literal distinto del valor declarado'
        return _result(state, motivo, ev, [str(build.relative_to(root))])
    except (OSError, UnicodeError) as e:
        return _result('no_determinable', str(e))


def gateway_declarado(root, service='*', value=None, completo=False, ctx=None, row=None, **k):
    ctx = ctx or {}
    declared = ctx.get('valores', {}).get('backend.gateway', ctx.get('gateway'))
    declared_val = declared
    servicios = ctx.get('servicios', [])
    ev = []
    # detect existing gateway by starter
    existing = []
    for s in servicios:
        b = root / s / 'build.gradle'
        if b.is_file():
            try:
                t = limpiar_gradle(b.read_text(encoding='utf-8'))
                if 'spring-cloud-starter-gateway' in t:
                    existing.append(s)
                    ev.append(f'{s}/build.gradle: declara starter de gateway')
            except OSError:
                pass
    if declared_val in ('', None):
        if existing:
            return _result('difiere', 'hay gateway existente pero backend.gateway es null', ev)
        return _result('coincide', 'sin gateway declarado y sin gateway detectado')
    if str(declared_val) not in servicios:
        if not (root / str(declared_val)).is_dir():
            return dict(_result('difiere', 'backend.gateway declarado; carpeta pendiente de crear'), informativo=True)
        return _result('difiere', 'backend.gateway nombra un servicio que no existe', [f'backend.gateway={declared_val} no existe en servicios'])
    return _result('coincide', 'backend.gateway nombra un servicio existente', [f'backend.gateway={declared_val} existe'])


def cors_origenes(root, service='*', value=None, completo=False, ctx=None, row=None, **k):
    ctx = ctx or {}
    vals = ctx.get('valores', {})
    gateway = vals.get('backend.gateway', ctx.get('gateway'))
    if not gateway:
        return _result('no_determinable', 'sin gateway declarado')
    infra = vals.get('devops.infraestructura')
    esperado = value if isinstance(value, list) else (json.loads(value) if isinstance(value, str) and value.startswith('[') else value)
    if isinstance(esperado, str):
        try: esperado = json.loads(esperado)
        except Exception: pass
    # compare by canonical list
    try:
        mod = _servicios_mod(root)
        if infra == 'jenkins-kubernetes':
            # documento base de application.yaml del gateway
            items = mod.rutas_yaml_servicio(str(root), gateway, ['gateway.cors-origenes']) if hasattr(mod,'rutas_yaml_servicio') else []
            found = None
            for it in items:
                if it.get('documento') == 'base' and it.get('ruta') == 'gateway.cors-origenes':
                    found = it.get('valor')
            if found is None:
                return _result('no_determinable', 'no se encontró gateway.cors-origenes en documento base del gateway')
        else:
            found = _leer_cors_corsconfig(root, gateway)
            if found is None:
                return _result('no_determinable', 'no se encontró CorsConfig.java o addAllowedOrigin en el gateway')
        if _canon(found) == _canon(esperado):
            return _result('coincide', 'orígenes CORS coinciden', [f'{gateway}: {_canon(found)}'])
        return _result('difiere', 'backend.cors_origenes difiere de la configuración CORS del gateway', [f'esperado={_canon(esperado)}', f'encontrado={_canon(found)}'])
    except Exception as e:
        return _result('no_determinable', str(e))


def _leer_cors_corsconfig(root, gateway):
    base = root / gateway / 'src/main/java'
    if not base.is_dir():
        return None
    origins = []
    for p in sorted(base.rglob('CorsConfig.java')):
        try:
            t = p.read_text(encoding='utf-8')
        except OSError:
            continue
        origins += re.findall(r'addAllowedOrigin\("([^"]+)"\)', t)
    return origins if list(base.rglob('CorsConfig.java')) else None


def autenticacion(root, service='*', value='ninguna', completo=False, ctx=None, row=None, **k):
    ctx=ctx or {}; val=str(value)
    found=False; ev=[]
    for s in (ctx.get('servicios') or []):
        p=root/s/'build.gradle'
        if p.is_file() and 'spring-boot-starter-oauth2-resource-server' in limpiar_gradle(p.read_text(encoding='utf-8')):
            found=True; ev.append(str(p.relative_to(root)))
        items=_yaml_routes(root,s,['spring.security.oauth2.resourceserver.jwt.issuer-uri'])
        if items:
            found=True; ev.extend(it['archivo'] + ':' + str(it['linea']) for it in items)
    if val=='clerk':
        return _result('coincide' if found else 'difiere', 'código de autenticación Clerk detectado' if found else 'autenticación clerk activada sin código detectable', ev)
    if val=='ninguna':
        return _result('difiere' if found else 'coincide', 'se detecta configuración de autenticación con valor ninguna' if found else 'sin integración de autenticación detectada', ev)
    return _result('no_determinable','valor no soportado')


def gestion_usuarios(root, service='*', value='ninguna', completo=False, ctx=None, row=None, **k):
    val=str(value)
    # look for profile/usuario module hints
    hints = ['Profile', 'Invitacion', 'Invitation', 'gestion-usuarios', 'Perfil']
    found=[]
    candidates=sorted(p for s in (ctx or {}).get('servicios', []) for p in (root/s/'src/main/java').rglob('*.java'))
    for p in candidates:
        sp=str(p)
        if '/.agents/' in sp or '/build/' in sp: continue
        for h in hints:
            if h in p.name and ('webhook' in sp.lower() or 'perfil' in sp.lower() or 'profile' in sp.lower() or 'invitation' in sp.lower() or 'invitacion' in sp.lower()):
                found.append(str(p.relative_to(root))); break
    found = sorted(set(found))[:10]
    if val=='ninguna':
        return _result('difiere' if found else 'coincide', 'se detecta módulo de perfiles/usuarios con valor ninguna' if found else 'sin módulo de gestión de usuarios detectado', found)
    return _result('coincide' if found else 'difiere', 'módulo de gestión de usuarios detectado' if found else 'gestión de usuarios activada sin módulo detectable', found)


def _yaml_routes(root, service, routes):
    return _servicios_mod(root).rutas_yaml_servicio(str(root), service, routes)


def clerk_issuer_uri(root, service='*', value='', completo=False, ctx=None, row=None, **k):
    ctx=ctx or {}; vals=ctx.get('valores',{})
    expected=str(value)
    found=[]
    for s in (ctx.get('servicios') or []):
        items=_yaml_routes(root,s,['spring.security.oauth2.resourceserver.jwt.issuer-uri'])
        for it in items:
            if it.get('documento')=='base':
                found.append((s,it))
    if not found:
        return _result('no_determinable','no se encontró issuer-uri en documentos base')
    vals_found = sorted(set(str(it['valor']) for _,it in found))
    ev=[f"{it['archivo']}:{it['linea']} ({s}, base): issuer-uri={it['valor']}" for s,it in found]
    if len(vals_found)==1 and vals_found[0]==expected:
        return _result('coincide','issuer-uri coincide en documentos base', ev)
    return _result('difiere','issuer-uri difiere del valor declarado', ev+[f'esperado={expected}'])


def variables_autenticacion(root, service='*', value=None, completo=False, ctx=None, row=None, **k):
    ctx=ctx or {}
    esperado = value if isinstance(value,list) else (json.loads(value) if isinstance(value,str) and value.startswith('[') else [value] if value else [])
    names=set()
    mod=_servicios_mod(root)
    for s in (ctx.get('servicios') or []):
        for _, filas in mod.configuraciones(str(root), s):
            for fila in filas:
                names.update(n for n,_,_ in fila.get('variables',[]) if 'CLERK' in n or n in esperado)
    found=sorted(names)
    if sorted(esperado)==found:
        return _result('coincide','nombres de variables de autenticación coinciden', found)
    return _result('difiere','nombres de variables de autenticación difieren', [f'esperado={sorted(esperado)}', f'encontrado={found}'])


def clase_aplicacion(root, service='*', value='', completo=False, ctx=None, row=None, **k):
    # nombre por patrón {AliasPascal}
    try:
        mod=_servicios_mod(root)
        base = mod.calcular_nombres(str(root), service)[0]['base']
    except Exception:
        return dict(_result('no_determinable', 'base no determinable por servicios.py nombres'), nombres=[])
    parts=[p for p in re.split(r'[-_]', base) if p]
    pascal=''.join(p[:1].upper()+p[1:] for p in parts) if parts else base.capitalize()
    esperado = str(value).replace('{AliasPascal}', pascal)
    src = root/service/'src/main/java'
    if not src.is_dir():
        return dict(_result('no_determinable','sin src/main/java'), nombres=[])
    mains=[]
    for p in sorted(src.rglob('*.java')):
        try: t=limpiar_java(p.read_text(encoding='utf-8', errors='replace'))
        except OSError: continue
        if re.search(r'@(?:org\.springframework\.boot\.autoconfigure\.)?SpringBootApplication\b', t):
            mains.append(p)
    if len(mains)!=1:
        return dict(_result('no_determinable', f'se encontraron {len(mains)} clases principales @SpringBootApplication', [str(p.relative_to(root)) for p in mains]), nombres=[str(p.relative_to(root)) for p in mains], evidencia_por_nombre={str(p.relative_to(root)):[str(p.relative_to(root))] for p in mains})
    name=mains[0].stem
    ev=[f'{mains[0].relative_to(root)}: clase {name} (esperada {esperado})']
    if name==esperado:
        return dict(_result('coincide','nombre de clase aplicación coincide', ev), nombres=[])
    return dict(_result('difiere','nombre de clase aplicación difiere del patrón', ev), nombres=[str(mains[0].relative_to(root))], evidencia_por_nombre={str(mains[0].relative_to(root)):ev})


def estrategia_fisica_jpa(root, service='*', value='', completo=False, ctx=None, row=None, **k):
    esperado=str(value)
    items=_yaml_routes(root, service, ['spring.jpa.hibernate.naming.physical-strategy'])
    base=[it for it in items if it.get('documento')=='base']
    if not base:
        return _result('no_determinable','no se encontró physical-strategy en documento base')
    vals=sorted(set(str(it['valor']) for it in base))
    ev=[f"{it['archivo']}:{it['linea']} (base): physical-strategy={it['valor']}" for it in base]
    if len(vals)==1 and vals[0]==esperado:
        return _result('coincide','estrategia física JPA coincide', ev)
    return _result('difiere','estrategia física JPA difiere', ev+[f'esperado={esperado}'])


def api_error(root, service='*', value=None, completo=False, ctx=None, row=None, **k):
    field=(row or {}).get('clave','').split('.')[-1]
    src=root/service/'src/main/java'
    java=sorted(src.rglob('*.java'))
    advice=[p for p in java if re.search(r'@(?:RestControllerAdvice|ControllerAdvice)\b', limpiar_java(p.read_text(encoding='utf-8')))]
    if len(advice)!=1:
        return _result('no_determinable',f'se encontraron {len(advice)} manejadores de errores')
    code=limpiar_java(advice[0].read_text(encoding='utf-8'))
    # El tipo debe construirse en el manejador y publicarse como respuesta.
    types=set(re.findall(r'ResponseEntity<([A-Za-z_][A-Za-z0-9_]*)>',code)) & set(re.findall(r'new\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(',code))
    responses=[p for p in java if p.stem in types]
    if len(responses)!=1:
        return _result('no_determinable','tipo de respuesta del manejador ambiguo o no localizado')
    response=responses[0]
    text=limpiar_java(response.read_text(encoding='utf-8'))
    record=re.search(r'\brecord\s+'+re.escape(response.stem)+r'\s*\((.*?)\)\s*\{',text,re.S)
    if not record:
        return _result('no_determinable','respuesta no soportada: se requiere record con componentes literales')
    components=re.findall(r'\b[A-Za-z_][\w.<>]*\s+([A-Za-z_][A-Za-z0-9_]*)\s*(?:,|$)',record[1])
    if not components:
        return _result('no_determinable','componentes de respuesta no determinables')
    expected=value or None
    if field=='campo_codigo' and expected is None:
        # Forma canónica sin código: timestamp + el mensaje configurado, ningún componente adicional.
        message=(ctx or {}).get('valores',{}).get('api_error.campo_mensaje')
        ok=set(components)=={'timestamp',message}
    else:
        ok=expected in components
    return _result('coincide' if ok else 'difiere','componentes publicados por el record de error',
                   [str(advice[0].relative_to(root)), str(response.relative_to(root))+': '+','.join(components)])


def devops_estado(root, service='*', value='jenkins-kubernetes', completo=False, ctx=None, row=None, **k):
    ctx=ctx or {}; vals=ctx.get('valores',{})
    if vals.get('devops.infraestructura') != 'jenkins-kubernetes':
        return _result('coincide','DevOps no activado')
    # answer 2: one check emits findings per service (incl gateway) and one project *
    # emit all findings (project + per service) in one call
    findings = []
    jf = _jenkins_path(root, ctx)
    if jf.is_file():
        findings.append({'clave':'devops.infraestructura','valor':vals.get('devops.infraestructura','jenkins-kubernetes'),'servicio':'*','resultado':'coincide','motivo':'Jenkinsfile presente','evidencia':[str(jf.relative_to(root))],'codigo':'DEVOPS_ESTADO'})
    else:
        findings.append({'clave':'devops.infraestructura','valor':vals.get('devops.infraestructura','jenkins-kubernetes'),'servicio':'*','resultado':'difiere','motivo':'falta '+str(jf.relative_to(root)),'evidencia':['proyecto: falta '+str(jf.relative_to(root))],'codigo':'DEVOPS_ESTADO'})
    # El hallazgo de Jenkinsfile permanece aunque falle la identidad de servicios.
    servicios = list(ctx.get('servicios', []))
    try:
        identidades = {item['servicio']: item for item in _servicios_mod(root).calcular_nombres(root)}
    except Exception as error:
        for service in servicios:
            findings.append({'clave': 'devops.infraestructura', 'valor': vals.get('devops.infraestructura'),
                'servicio': service, 'resultado': 'no_determinable',
                'motivo': 'no se pudieron calcular nombres (' + type(error).__name__ + ')',
                'evidencia': [], 'codigo': 'DEVOPS_ESTADO'})
        return findings
    folders = sorted({key.split('.')[2] for key in vals if re.fullmatch(r'devops\.entornos\.[^.]+\.desplegar',key) and vals[key]=='true'})
    for service in servicios:
        try:
            item = identidades[service]
            expected = []
            for env in folders:
                files = item['devops'][env]['archivos']
                expected.extend(files[key] for key in ('deployment', 'service', 'pv', 'pvc') if files[key] is not None)
        except Exception as error:
            findings.append({'clave': 'devops.infraestructura', 'valor': vals.get('devops.infraestructura'),
                'servicio': service, 'resultado': 'no_determinable',
                'motivo': 'nombres del servicio o entorno no disponibles (' + type(error).__name__ + ')',
                'evidencia': [], 'codigo': 'DEVOPS_ESTADO'})
            continue
        missing = [name for name in expected if not (root/name).is_file()]
        if not (root/service/'Dockerfile').is_file(): missing.append(service + '/Dockerfile')
        findings.append({'clave': 'devops.infraestructura', 'valor': vals.get('devops.infraestructura'),
            'servicio': service, 'resultado': 'difiere' if missing else 'coincide',
            'motivo': 'faltan artefactos DevOps del servicio' if missing else 'artefactos DevOps presentes',
            'evidencia': ['falta ' + name for name in missing] if missing else [service], 'codigo': 'DEVOPS_ESTADO'})
    return findings


def _comparar(key, esperado, found, evidencia):
    if not found:
        return _result('no_determinable', 'no se encontró un valor literal para ' + key, evidencia)
    ok = all(_canon(v) == _canon(esperado) for v in found)
    return _result('coincide' if ok else 'difiere', key + (' coincide' if ok else ' difiere'), evidencia)


def _quitar_comentario_yaml(raw):
    s = raw.rstrip('\r\n')
    stripped = s.lstrip()
    if not stripped:
        return ''
    if stripped.startswith('#'):
        return ''
    m = re.match(r'^\s*("([^"\\]|\\.)*"|\'[^\']*\')(\s*)(.*)$', s)
    if m:
        val, sep, rest = m.group(1), m.group(3), m.group(4)
        if rest.startswith('#') or sep:
            return val
        return val
    m = re.match(r'^\s*(.*?)([ \t]+#.*)?$', s)
    if m:
        return m.group(1).strip()
    return s.strip()


def _manifiesto_valores(path, campo):
    # Manifiestos del proyecto; solo réplicas, nodePort y recursos (D19).
    parents=[]; found=[]
    for n,line in enumerate(path.read_text(encoding='utf-8').splitlines(),1):
        m=re.match(r'^( *)(?:- )?([A-Za-z][\w-]*):\s*(.*?)\s*$',line)
        if not m: continue
        indent,key,raw=len(m[1]),m[2],m[3]
        while parents and parents[-1][0]>=indent: parents.pop()
        keys=[k for _,k in parents]+[key]
        val = _quitar_comentario_yaml(raw)
        if campo in ('replicas','nodePort') and key==campo:
            v = val[1:-1] if len(val) >= 2 and val[0] == val[-1] and val[0] in '"\'' else val
            if re.fullmatch(r'\d+', v):
                found.append((n, int(v)))
        elif campo in ('cpu_peticion','cpu_limite','memoria_peticion','memoria_limite'):
            section='requests' if campo.endswith('peticion') else 'limits'
            leaf='cpu' if campo.startswith('cpu') else 'memory'
            v = val[1:-1] if len(val) >= 2 and val[0] == val[-1] and val[0] in '"\'' else val
            if keys[-3:]==['resources',section,leaf] and re.fullmatch(r'[\d.]+(?:m|Mi|Gi|Ki)?', v):
                found.append((n, v))
        parents.append((indent,key))
    return found


def devops_valores(root, service='*', value=None, completo=False, ctx=None, row=None, **k):
    ctx=ctx or {}; vals=ctx.get('valores',{}); key=(row or {}).get('clave','')
    activa, motivo = condicion_activa(ctx, key, row or {})
    if not activa:
        return _result('coincide', 'clave no aplicable: ' + motivo)
    jf=_jenkins_path(root, ctx)
    if key=='devops.slack_canal' and value in (None,''):
        return _result('difiere','canal de Slack no configurado',['sin canal de Slack: el pipeline no enviará avisos; si quieres recibirlos, pon `devops.slack_canal` en `.agents/stack.yaml`; el siguiente plan lo llevará al Jenkinsfile'])
    if key == 'devops.credencial_bd_pruebas':
        if not jf.is_file(): return _result('no_determinable','no existe '+str(jf.relative_to(root)))
        text = jf.read_text(encoding='utf-8')
        matches = list(re.finditer(r"credBd\s*=\s*'([^']*)'", text))
        if not matches:
            return _result('no_determinable', 'sin credBd literal en ' + str(jf.relative_to(root)))
        found = [m[1] for m in matches]
        esperado = '' if value in (None, '') else str(value)
        return _comparar(key, esperado, found, [f"{jf.relative_to(root)}:{text[:m.start()].count(chr(10))+1}: credBd={m[1]}" for m in matches])
    if key in ('devops.slack_canal','devops.registry'):
        if not jf.is_file():return _result('no_determinable','no existe '+str(jf.relative_to(root)))
        text=jf.read_text(encoding='utf-8')
        pattern = r"slackChannel\s*=\s*['\"]([^'\"]*)['\"]" if key.endswith('slack_canal') else r'docker\.build\(\s*[\'"]([^\'"$]+?)/\$\{serviceName\}:'
        matches=list(re.finditer(pattern,text))
        return _comparar(key,value,[m[1] for m in matches],[f'{jf.relative_to(root)}:{text[:m.start()].count(chr(10))+1}: {key}={m[1]}' for m in matches])
    m=re.fullmatch(r'devops\.entornos\.([^.]+)\.([^.]+)',key)
    if not m:return _result('no_determinable','clave fuera de la lista D19')
    env,campo=m.groups()
    if campo in ('cors_origenes','clerk_issuer_uri'):
        if campo=='clerk_issuer_uri' and vals.get('integraciones.autenticacion')!='clerk':
            return _result('coincide','autenticación inactiva')
        svcs=[ctx.get('gateway')] if campo=='cors_origenes' else ctx.get('servicios',[])
        if not any(svcs):return _result('coincide','sin gateway al que comparar CORS')
        ruta='gateway.cors-origenes' if campo=='cors_origenes' else 'spring.security.oauth2.resourceserver.jwt.issuer-uri'
        suffix=vals.get(f'devops.entornos.{env}.sufijo')
        if not suffix:return _result('no_determinable','sin sufijo del entorno')
        if campo == 'cors_origenes':
            known = set(ctx.get('servicios') or [])
            gateway = ctx.get('gateway')
            if gateway and gateway not in known:
                return _result('no_determinable', 'carpeta del gateway pendiente de crear', [f'gateway={gateway}'])
        items=[]
        for svc in svcs:
            if not svc:continue
            items.extend(it for it in _yaml_routes(root,svc,[ruta]) if it['documento']=='k8s' and Path(it['archivo']).name in (f'application-{suffix}.yaml',f'application-{suffix}.yml'))
        if value in (None, ''):
            return _result('no_determinable', 'valor no configurado para ' + key)
        expected=json.loads(value) if campo=='cors_origenes' and isinstance(value,str) else value
        return _comparar(key,expected,[it['valor'] for it in items],[f"{it['archivo']}:{it['linea']}: documento k8s {ruta}={_canon(it['valor'])}" for it in items])
    if campo in ('rama','credencial_kubeconfig','imagen','desplegar'):
        if not jf.is_file():return _result('no_determinable','no existe '+str(jf.relative_to(root)))
        text=jf.read_text(encoding='utf-8')
        body=re.search(r'def\s+getEnvironments\s*\(\s*\)\s*\{(.*?)\n\}',text,re.S)
        if not body:return _result('no_determinable','sin getEnvironments literal')
        block=re.search(r"(?:['\"]?"+re.escape(env)+r"['\"]?)\s*:\s*\[([^\[\]]*)\]",body[1],re.S)
        if not block:return _result('no_determinable','sin entorno literal '+env)
        fm=re.search(r'\b'+re.escape(campo)+r'''\s*:\s*(?:'([^']*)'|"([^"]*)"|(true|false))''',block[1])
        found=[] if not fm else [next(x for x in fm.groups() if x is not None)]
        return _comparar(key,value,found,[str(jf.relative_to(root))+': getEnvironments '+env+' '+campo])
    if campo not in ('replicas','cpu_peticion','cpu_limite','memoria_peticion','memoria_limite','nodo_puerto_base','gateway_nodo_puerto'):
        return _result('no_determinable','clave fuera de la lista D19')
    services=ctx.get('servicios',[])
    if campo=='gateway_nodo_puerto':services=[ctx['gateway']] if ctx.get('gateway') else []
    if campo=='nodo_puerto_base':services=[s for s in services if s!=ctx.get('gateway')]
    found=[]; ev=[]
    faltan=0
    mod=_servicios_mod(root)
    # Solo cuentan los servicios registrados en getServices() del Jenkinsfile (D1).
    registrados=None
    try:
        if jf.is_file():
            texto=jf.read_text(encoding='utf-8', errors='replace')
            entradas, err=mod.parsear_get_services(texto, str(jf.relative_to(root)))
            if err is None:
                registrados={e['directory'] for e in entradas}
    except (OSError, UnicodeDecodeError, ValueError):
        registrados=None
    if registrados is not None:
        descartados=sorted(s for s in services if s not in registrados)
        if descartados:
            ev.append(f'no cuentan {len(descartados)} servicio(s) sin registrar en getServices(): ' + ', '.join(descartados))
        services=[s for s in services if s in registrados]
    for svc in services:
        pattern='service-*.yaml' if campo in ('nodo_puerto_base','gateway_nodo_puerto') else 'deployment-*.yaml'
        paths=sorted((root/'devops'/env/svc).glob(pattern))
        if not paths:
            ev.append(f'falta {pattern} en devops/{env}/{svc}')
            faltan+=1
            continue
        for path in paths:
            values=_manifiesto_valores(path,'nodePort' if campo in ('nodo_puerto_base','gateway_nodo_puerto') else campo)
            if not values:
                ev.append('sin valor literal en '+str(path.relative_to(root)))
                faltan+=1
                continue
            for n,v in values:
                if campo=='nodo_puerto_base':
                    ports=mod.puertos_resueltos(str(root),svc,vals.get(f'devops.entornos.{env}.sufijo'))
                    if len(ports)!=1:
                        ev.append('puerto efectivo ambiguo o ausente en '+svc)
                        faltan+=1
                        continue
                    v=v-(ports[0]-8080)
                found.append(v);ev.append(f'{path.relative_to(root)}:{n}: {campo}={v}')
    if not found:
        return _result('no_determinable', 'no se encontró un valor literal para ' + key, ev)
    cmp=_comparar(key,value,found,ev)
    if cmp['resultado']=='difiere':
        return cmp
    if faltan > 0:
        return _result('no_determinable', f'{faltan} servicio(s) o manifiesto(s) sin valor comparable para {key}; los valores encontrados coinciden', ev)
    return cmp


def perfiles(root, service='*', value=None, completo=False, ctx=None, row=None, **k):
    # value canonical = expected profiles json list
    try:
        mod=_servicios_mod(root)
        esperado = value if isinstance(value,list) else json.loads(value) if isinstance(value,str) and value.startswith('[') else []
        # get perfiles info
        # cmd_perfiles prints json array; easier to compute via internal? call as subprocess to be safe
        r=subprocess.run(['python3','-I','-B', str(root/'.agents'/'scripts'/'servicios.py'),'perfiles',service], cwd=root, capture_output=True, text=True)
        if r.returncode!=0:
            return _result('no_determinable','no se pudo obtener perfiles del servicio: '+(r.stdout or r.stderr))
        data=json.loads(r.stdout)
        info=data[0] if isinstance(data,list) and data else (data if isinstance(data,dict) else None)
        if not info:
            return _result('no_determinable','sin información de perfiles')
        faltan=info.get('faltan',[])
        esper=info.get('esperados',[])
        ev=[]
        if faltan:
            ev=[f"{service}/src/main/resources/: faltan " + ', '.join(f'application-{f}.yaml' for f in faltan)]
            return dict(_result('difiere','faltan perfiles esperados: '+','.join(faltan), ev), faltan=faltan)
        # also if active differs from perfil_local
        perfil_local = info.get('perfil_local')
        activos = info.get('perfil_activo') or []
        if perfil_local and activos and perfil_local not in activos and not info.get('activos_variable'):
            ev=[f'perfil activo {activos} difiere de backend.perfil_local {perfil_local}']
            return _result('difiere','perfil activo difiere de backend.perfil_local', ev)
        if info.get('activos_variable') or not activos:
            return _result('no_determinable','perfil activo por variable o no declarado', [f'esperados={esper}'])
        return _result('coincide','perfiles esperados presentes', [f'esperados={esper}'])
    except Exception as e:
        return _result('no_determinable', str(e))


def _jenkins_path(root, ctx):
    name = (ctx or {}).get('valores', {}).get('devops.jenkinsfile')
    if not isinstance(name, str) or not name or Path(name).is_absolute() or '..' in name or '\\' in name:
        raise ValueError('devops.jenkinsfile no es una ruta relativa segura')
    path = root / name
    if not path.resolve().is_relative_to(root.resolve()) or any(x == 'account' or x.startswith('.env') for x in path.resolve().parts):
        raise ValueError('devops.jenkinsfile fuera del repositorio')
    return path


def jenkinsfile(root, service='*', value='', completo=False, ctx=None, row=None, **k):
    try:
        path = _jenkins_path(root, ctx)
        if path.is_file():
            return _result('coincide', 'Jenkinsfile presente en la ruta configurada', [str(path.relative_to(root))])
        candidates = sorted(str(p.relative_to(root)) for p in (root/'devops').glob('Jenkinsfile*') if p.is_file() and p.resolve().is_relative_to(root.resolve()))
        if candidates:
            return _result('difiere', 'falta la ruta configurada; hay otros Jenkinsfile', candidates)
        # DEVOPS_ESTADO ya emite la ausencia del proyecto; evitar otro aviso de valores.
        return _result('coincide', 'sin Jenkinsfile; ausencia informada por DEVOPS_ESTADO')
    except (OSError, ValueError):
        return _result('no_determinable', 'ruta de Jenkinsfile no determinable')


_NODO_CONST = {
    'general': 'NODO_GENERAL',
    'compilacion': 'NODO_COMPILACION',
    'docker': 'NODO_DOCKER',
}


def _resolver_nodo(root, text, tarea, expresion):
    mod = _servicios_mod(root)
    const = _NODO_CONST[tarea]
    decl_pat = re.compile(
        rf"^([ \t]*)(?:@\s*Field\b[ \t]+)?(?:(?:final|def|String)\b[ \t]+)*"
        rf"{re.escape(const)}\b[ \t]*=[ \t]*(.+)$",
        re.M,
    )
    primer_nivel = mod.gradle_primer_nivel(text)
    decls = []
    for m in decl_pat.finditer(text):
        linea_decl = text[:m.start()].count('\n') + 1
        segmento = m.group(0).lstrip()
        if segmento not in primer_nivel:
            continue
        valor = mod._literal_expresion(m.group(2).strip())
        decls.append((linea_decl, valor, m.group(2).strip()))
    expr = expresion.strip()
    if expr == const or re.fullmatch(rf'"\$\{{{re.escape(const)}\}}"', expr):
        if len(decls) != 1:
            return None, 'declaración ausente, repetida o no determinable'
        linea_decl, valor, _raw = decls[0]
        if valor is None:
            return None, 'declaración no literal'
        return (linea_decl, const, valor), None
    literal = mod._literal_expresion(expr)
    if literal is not None:
        return (None, None, literal), None
    return None, 'etiqueta no literal'


def nodos_jenkins(root, service='*', value='', completo=False, ctx=None, row=None, **k):
    key = (row or {})['clave']
    task = key.rsplit('.', 1)[-1]
    try:
        path = _jenkins_path(root, ctx)
        if not path.is_file():
            return _result('coincide', 'ausencia informada por DEVOPS_ESTADO')
        text = path.read_text(encoding='utf-8')
        mod = _servicios_mod(root)
        patterns = {'general': [r'\bagent\s*\{'],
            'compilacion': [r'\bdef\s+buildMicroservice\s*\([^)]*\)\s*\{', r'\bdef\s+analyzeMicroservice\s*\([^)]*\)\s*\{'],
            'docker': [r'\bdef\s+buildDockerImage\s*\([^)]*\)\s*\{']}
        found, ev = [], []
        for pattern in patterns[task]:
            blocks = mod.bloques_publicos(text, pattern)
            if len(blocks) != 1:
                return _result('no_determinable', 'bloque agent o función no determinable', ev)
            offset, body = blocks[0]
            candidate = r'\blabel\s+("(?:\$\{[^}]+\}|[^"])*"|\'[^\']*\'|[^\s;}]+)' if task == 'general' else r'\bnode\s*\(\s*label\s*:\s*("(?:\$\{[^}]+\}|[^"])*"|\'[^\']*\'|[^\s;)]+)\)'
            labels = list(re.finditer(candidate, body))
            if len(labels) != 1:
                return _result('no_determinable', 'etiqueta no determinable en el bloque', ev)
            resolved, err = _resolver_nodo(root, text, task, labels[0][1])
            if err:
                return _result('no_determinable', err, ev)
            line = text[:offset + labels[0].start()].count('\n') + 1
            func = 'agent' if task == 'general' else ('buildMicroservice' if 'buildMicroservice' in pattern else 'analyzeMicroservice' if 'analyzeMicroservice' in pattern else 'buildDockerImage')
            decl_line, const, label = resolved
            found.append(label)
            rel = str(path.relative_to(root))
            if decl_line is not None:
                ev.append(rel + ':' + str(decl_line) + ': ' + const + '=' + label)
                ev.append(rel + ':' + str(line) + ': ' + func + ' label=' + const)
            else:
                ev.append(rel + ':' + str(line) + ': ' + func + ' label=' + label)
        cmp = _comparar(key, value, found, ev)
        if cmp['resultado'] == 'difiere' and any('NODO_' in e and '=' in e for e in ev):
            const = _NODO_CONST[task]
            cmp['motivo'] = f'cambia la declaración {const} del Jenkinsfile con un plan aprobado'
        return cmp
    except (OSError, ValueError, KeyError):
        return _result('no_determinable', 'no se pudo obtener la etiqueta del Jenkinsfile configurado')


def jdk_ruta_desarrollo(root, service='*', value='', completo=False, ctx=None, row=None, **k):
    if value in (None, ''):
        return _result('coincide', 'ruta no gestionada')
    key = 'org.gradle.java.installations.paths'
    try:
        values = _servicios_mod(root).propiedades_permitidas(root, service).get(key, [])
        if any(v.get('malformada') for v in values):
            return _result('no_determinable', key + ' con formato no soportado')
        if any(v['continuada'] for v in values):
            return _result('no_determinable', key + ' continuada; no se lee la siguiente línea')
        ev = [service + '/gradle.properties:' + str(v['linea']) + ': ' + key + '=' + v['valor'] for v in values]
        if not values:
            return _result('difiere', 'falta ' + key)
        ok = len(values) == 1 and values[0]['valor'] == value
        return _result('coincide' if ok else 'difiere', key + (' coincide' if ok else ' difiere'), ev)
    except (OSError, ValueError):
        return _result('no_determinable', 'no se pudo obtener la propiedad JDK permitida')


DETECTORES = {
    'jenkinsfile': jenkinsfile,
    'nodos_jenkins': nodos_jenkins,
    'jdk_ruta_desarrollo': jdk_ruta_desarrollo,
    'lombok': lombok,
    'persistencia': persistencia,
    'group': group,
    'gateway_declarado': gateway_declarado,
    'cors_origenes': cors_origenes,
    'autenticacion': autenticacion,
    'gestion_usuarios': gestion_usuarios,
    'clerk_issuer_uri': clerk_issuer_uri,
    'variables_autenticacion': variables_autenticacion,
    'clase_aplicacion': clase_aplicacion,
    'estrategia_fisica_jpa': estrategia_fisica_jpa,
    'api_error': api_error,
    'devops_estado': devops_estado,
    'devops_valores': devops_valores,
    'perfiles': perfiles,
}
