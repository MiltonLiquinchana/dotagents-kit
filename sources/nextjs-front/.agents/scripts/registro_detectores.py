"""Comparaciones de solo lectura del front; no ejecuta código de aplicación."""
import json
from pathlib import Path
import re
import subprocess

DATOS_ADMITIDOS = {}
EXCLUDED = {'.git', '.agents', 'node_modules', '.next', 'dist', 'build', 'coverage', '__tests__'}
EXTENSIONS = {'.ts', '.tsx', '.js', '.jsx', '.mjs'}


def result(state, why, files=(), evidence=None):
    return {'resultado': state, 'motivo': why, 'archivos': list(files),
            'evidencia': list(files) if evidence is None else evidence}


def safe(root, name):
    p = root / name
    if p.is_symlink() or any(x.is_symlink() for x in p.parents if x != root.parent):
        raise ValueError('enlace simbólico no inspeccionable')
    if not p.resolve().is_relative_to(root.resolve()):
        raise ValueError('ruta fuera del proyecto')
    return p


def read(root, name):
    return safe(root, name).read_text(encoding='utf-8')


def names(root, ctx):
    if '_nombres_front' not in ctx:
        r = subprocess.run(['git', 'ls-files', '-z'], cwd=root, capture_output=True, timeout=20)
        if r.returncode:
            raise ValueError('no se pudo inventariar Git')
        found = []
        for name in r.stdout.decode('utf-8').split('\0'):
            p = Path(name)
            if not name or p.is_absolute() or '..' in p.parts or any(x in EXCLUDED or x.startswith('.env') for x in p.parts):
                continue
            if p.suffix not in EXTENSIONS or re.search(r'\.(test|spec)\.', name):
                continue
            if safe(root, name).is_file():
                found.append(name)
        ctx['_nombres_front'] = sorted(set(found))
    return ctx['_nombres_front']


def clean(text):
    # Conservar literales e imports; quitar solo comentarios, sin confundir URLs.
    token = r'''"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|`(?:\\.|[^`\\])*`|/\*[\s\S]*?\*/|//[^\n]*'''
    return re.sub(token, lambda m: re.sub(r'[^\n]', ' ', m[0]) if m[0].startswith(('//', '/*')) else m[0], text)


def dependencies(root):
    data = json.loads(read(root, 'package.json'))
    out = set()
    for k in ('dependencies', 'devDependencies'):
        value = data.get(k, {})
        if not isinstance(value, dict):
            raise ValueError('dependencias no interpretables')
        out.update(value)
    return out


def imports(text):
    return list(re.finditer(r'''\b(?:import|export)\s+(?:(.*?)\s+from\s*)?["']([^"']+)["']''', clean(text), re.S))


def integration_files(root, ctx, package, completo=False):
    found = []
    for name in names(root, ctx):
        text = clean(read(root, name))
        matched = [m for m in imports(text) if package(m[2])]
        if matched:
            used = False
            for m in (matched if completo or len(found) < 5 else []):
                body = text[:m.start()] + text[m.end():]
                bindings = re.findall(r'\b[A-Za-z_$][\w$]*\b', m[1] or '')
                used |= any(re.search(r'\b' + re.escape(b) + r'\b', body) for b in bindings if b not in {'as', 'type'})
            found.append((name, text, used))
        elif re.search(r'''\b(?:require|import)\s*\(''', text):
            # No resolver dependencias dinámicas para certificar ausencia global.
            if package('@clerk/dynamic') and '@clerk/' in text or package('react-toastify') and 'react-toastify' in text:
                raise ValueError('import dinámico relevante')
    return found


def autenticacion(root, value='ninguna', completo=False, ctx=None, **kw):
    deps = dependencies(root)
    found = integration_files(root, ctx, lambda x: x.startswith('@clerk/'), completo)
    declared = any(x.startswith('@clerk/') for x in deps)
    sample = found if completo else found[:5]
    used = any(x[2] for x in sample)
    fixed = [n for n in ['app/layout.tsx','middleware.ts','proxy.ts','utils/ClerkToken.ts','utils/apiClient.ts'] if safe(root,n).is_file()]
    for n in fixed:
        text = clean(read(root,n))
        used |= any(m[2].startswith('@clerk/') for m in imports(text)) and bool(re.search(r'\b(?:ClerkProvider|useAuth|auth|clerkMiddleware)\s*[<(]', text))
    files = sorted(set(fixed + [x[0] for x in sample] + ['package.json']))
    if value == 'ninguna':
        return result('difiere' if declared or found else 'coincide', 'Clerk detectado con ninguna' if declared or found else 'sin Clerk en inventario completo', files)
    if not declared or not found:
        return result('difiere', 'autenticación clerk sin dependencia o uso detectable', files)
    return result('coincide' if used else 'no_determinable', 'dependencia y uso Clerk comprobados' if used else 'sin uso comprobable en la muestra de imports', files)


def gestion_usuarios(root, value='ninguna', **kw):
    # Firmas de render-perfiles.mjs, destinos GestionProvider y PerfilesPage.
    expected = ['app/perfiles/page.tsx', 'app/ui/perfiles/GestionProvider.tsx']
    found = [n for n in expected if safe(root,n).is_file()]
    ok = not found if value == 'ninguna' else len(found) == len(expected)
    return result('coincide' if ok else 'difiere', 'presencia de perfiles coherente' if ok else 'módulo de perfiles contrario o incompleto', expected,
                  ['presente: '+n for n in found] + ['ausente: '+n for n in expected if n not in found])


def llamadas_api(root, value='', completo=False, ctx=None, **kw):
    if not safe(root, 'utils/apiClient.ts').is_file():
        return result('coincide', 'sin código aplicable')
    deps = dependencies(root)
    fixed = [n for n in ['utils/apiClient.ts', 'utils/HandleAxiosError.ts'] if safe(root,n).is_file()]
    if ctx['valores'].get('integraciones.autenticacion') == 'clerk' and safe(root,'utils/ClerkToken.ts').is_file():
        fixed.append('utils/ClerkToken.ts')
    texts = {n: clean(read(root,n)) for n in fixed}
    if 'axios' not in deps or value == 'servidor' and 'server-only' not in deps:
        return result('difiere', 'falta dependencia del patrón de llamadas API', ['package.json'])
    candidates = list(fixed)
    if completo:
        for n in names(root,ctx):
            if n.startswith(('utils/','services/','repository/','controllers/','app/')):
                t = clean(read(root,n))
                if re.search(r'\b(?:axios\s*[.(]|fetch\s*\()', t):
                    texts[n] = t
                    candidates.append(n)
    for n,t in texts.items():
        server = bool(re.search(r'''import\s*["']server-only["']''',t))
        public = 'process.env.NEXT_PUBLIC_API_BASE_URL' in t
        private = 'process.env.API_BASE_URL' in t
        if value == 'servidor' and public or value == 'navegador' and (private or server):
            return result('difiere', 'patrón de red contrario a llamadas_api', [n])
    client = texts['utils/apiClient.ts']
    if not re.search(r'axios\.create\s*\(',client):
        return result('no_determinable','cliente API no es la forma estática soportada',fixed)
    good = 'process.env.NEXT_PUBLIC_API_BASE_URL' in client if value == 'navegador' else 'process.env.API_BASE_URL' in client and bool(re.search(r'''import\s*["']server-only["']''',client))
    return result('coincide' if good else 'no_determinable','patrón de llamadas comprobado' if good else 'origen de API no determinable', sorted(set(candidates)))


def notificaciones(root, value='', completo=False, ctx=None, **kw):
    if not safe(root, 'utils/Notificador.ts').is_file():
        return result('coincide', 'sin código aplicable')
    deps = dependencies(root)
    found = integration_files(root,ctx,lambda x: x == 'react-toastify', completo)
    declared = 'react-toastify' in deps
    if value == 'ninguna' and (declared or found):
        return result('difiere','Toastify detectado con ninguna',['package.json']+[x[0] for x in found[:5]])
    text = clean(read(root,'utils/Notificador.ts'))
    if value == 'ninguna':
        good = bool(re.search(r'\bmostrar(?:\?\.)?\s*\(',text))
        return result('coincide' if good else 'no_determinable','adaptador propio comprobado' if good else 'adaptador propio no interpretable',['utils/Notificador.ts'])
    if not declared:
        return result('difiere','falta dependencia react-toastify',['package.json'])
    sample = found if completo else found[:5]
    layout = clean(read(root,'app/layout.tsx'))
    files = ['package.json','utils/Notificador.ts','app/layout.tsx']+[x[0] for x in sample]
    container = bool(re.search(r'<ToastContainer\b',layout))
    # Resolver solo componentes importados literalmente por layout, sin alias arbitrarios.
    for m in imports(layout):
        if container: break
        if not m[1] or not re.search(r'<(?:'+ '|'.join(re.findall(r'[A-Z]\w*',m[1])) +r')\b',layout):continue
        module=m[2]
        base = ('app/'+module if module.startswith('.') else module[2:] if module.startswith('@/') else '')
        if not base:continue
        for suffix in ('.tsx','.ts','/index.tsx'):
            n=str(Path(base+suffix))
            if safe(root,n).is_file():
                files.append(n)
                container |= bool(re.search(r'<ToastContainer\b',clean(read(root,n))))
    if not container and re.search(r'\b(?:dynamic|require)\s*\(', layout):
        return result('no_determinable', 'contenedor de layout no resoluble estáticamente', files)
    good = bool(re.search(r'\btoast\.(?:error|success|warning|info)\s*\(',text)) and container
    return result('coincide' if good else 'difiere','Toastify integrado' if good else 'falta adaptador o contenedor Toastify', sorted(set(files)))


def api_error(root, value=None, row=None, **kw):
    name='utils/HandleAxiosError.ts'
    if not safe(root,name).is_file():
        return result('coincide', 'sin código aplicable')
    text=clean(read(root,name))
    constant='API_MESSAGE_FIELD' if row['clave'].endswith('campo_mensaje') else 'API_CODE_FIELD'
    matches=re.findall(r'\bconst\s+'+constant+r'''\s*(?::[^=;]+)?=\s*("(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|null)\s*;''',text)
    if len(matches)!=1:return result('no_determinable','constante API ausente, duplicada o calculada',[name])
    raw=matches[0]
    if raw.startswith("'") and '\\' in raw:
        return result('no_determinable', 'literal simple con escapes no interpretable', [name])
    actual=None if raw=='null' else json.loads(raw) if raw.startswith('"') else raw[1:-1]
    return result('coincide' if actual==value else 'difiere',constant+' '+('coincide' if actual==value else 'distinto del campo declarado'),[name])


LAYERS = {'modelo':('domains/models/',), 'request':('domains/request/',), 'response':('domains/responses/',),
          'repositorio_interfaz':('repository/','repositorio_implementacion'), 'repositorio_implementacion':('repository/','repositorio_interfaz'),
          'servicio_interfaz':('services/','servicio_implementacion'), 'servicio_implementacion':('services/','servicio_interfaz'),
          'controlador_interfaz':('controllers/','controlador_implementacion'), 'controlador_implementacion':('controllers/','controlador_interfaz'),
          'archivo_seccion_ui':('app/ui/',)}


def pattern(value):
    return re.compile('^'+re.escape(value).replace(r'\{Entidad\}',r'[A-Z][a-z0-9]+(?:[A-Z][a-z0-9]+)*').replace(r'\{nombre\}',r'[a-z0-9]+(?:-[a-z0-9]+)*')+'$')


def nomenclatura(root, value='', ctx=None, row=None, **kw):
    key=row['clave'].split('.')[-1]
    layer=LAYERS[key]
    regex=pattern(value)
    own=names(root,ctx)
    candidates=[]
    other=pattern(ctx['valores']['nomenclatura.'+layer[1]]) if len(layer)>1 else None
    bad=[]
    for n in own:
        if Path(n).name == 'index.ts' or n.endswith('.d.ts'):continue
        if not n.startswith(layer[0]):continue
        base=Path(n).name if key=='archivo_seccion_ui' else Path(n).stem
        if key=='archivo_seccion_ui' and (not n.endswith('.tsx') or not(regex.fullmatch(base) or re.search(r'section|seccion',base,re.I))):continue
        if key!='archivo_seccion_ui' and not n.endswith('.ts'):continue
        candidates.append(n)
        if regex.fullmatch(base) or other and other.fullmatch(base):continue
        bad.append(n)
    flagged=sorted(set(bad))
    return dict(result('difiere' if bad else 'coincide',
                       'nombres fuera del patrón actual' if bad else 'nombres coherentes' if candidates else 'sin nombres aplicables',
                       sorted(set(candidates)),flagged),
                nombres=flagged,evidencia_por_nombre={n:[n] for n in flagged}, evaluados=len(candidates),
                evaluados_por_nombre={n:1 for n in candidates}, archivos_por_nombre={n:[n] for n in candidates})


def gestor_paquetes(root, value='', **kw):
    locks={'package-lock.json':'npm','pnpm-lock.yaml':'pnpm','yarn.lock':'yarn'}
    present=[n for n in locks if safe(root,n).is_file()]
    if not present:return result('no_determinable','sin lockfile raíz; no se pudo determinar el gestor')
    good=len(present)==1 and locks[present[0]]==value
    return result('coincide' if good else 'difiere','lockfile del gestor declarado' if good else 'lockfiles incompatibles con el gestor declarado',present)


DETECTORES = {name: globals()[name] for name in ('autenticacion','gestion_usuarios','llamadas_api','notificaciones','api_error','nomenclatura','gestor_paquetes')}
