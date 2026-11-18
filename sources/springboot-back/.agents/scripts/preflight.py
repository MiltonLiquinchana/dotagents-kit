#!/usr/bin/env python3
"""Núcleo común del preflight; las comprobaciones propias viven en preflight_stack.py."""
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import time


def modulo(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Preflight:
    def __init__(self, agents, data, workflow, phase, stack, data_module):
        self.agents, self.data, self.workflow, self.phase = agents, data, workflow, phase
        self.stack, self.data_module = stack, data_module
        self.findings, self.omissions = [], []
        self.finding_remedies = []
        self.root = Path.cwd()
        self.command = 'python3 -I -B .agents/actualizar.py --kit <KIT>'

    def local_path(self):
        rc, path = self.datos(['git', 'rev-parse', '--git-common-dir'])
        if rc or not path:
            raise ValueError('sin directorio git común')
        base = (self.root / path).resolve()
        nuevo = base / 'agents-kit-local.json'
        # Nombre anterior del archivo, hasta que el proyecto se regenere.
        return nuevo if nuevo.exists() or not (base / 'agents-harness-local.json').exists() else base / 'agents-harness-local.json'

    def origen(self):
        try:
            local = json.loads(self.local_path().read_text(encoding='utf-8'))
            if isinstance(local, dict) and isinstance(local.get('ruta'), str) and Path(local['ruta']).is_absolute() and Path(local['ruta']).is_dir():
                self.command = 'python3 -I -B .agents/actualizar.py --kit ' + shlex.quote(local['ruta'])
        except (OSError, UnicodeError, ValueError, TypeError, AttributeError):
            pass

    def add(self, code, message, service='*', recordatorio=False, clase=None):
        row = self.data['codigos'][code]
        cls = clase or self.data_module.clase(self.data, code, self.workflow, self.phase)
        remedy = row.get('remedio_recordatorio', row['remedio']) if recordatorio else row['remedio'].replace('{comando}', self.command)
        remedy = getattr(self.stack, 'remedio', lambda code, text, p: text)(code, remedy, self)
        self.findings.append((code, cls, service))
        self.finding_remedies.append(json.dumps(remedy, ensure_ascii=False))
        print({'bloqueo': 'BLOCKED', 'aviso': 'AVISO', 'plan': 'PARTE DEL PLAN'}[cls] + f' [{code}] servicio={service} {message}')
        if not recordatorio:
            print('Remedio: ' + remedy)
        print(f'RESULTADO codigo={code} clase={cls} servicio={service} remedio=' + json.dumps(remedy, ensure_ascii=False))

    def omit(self, code, dependency, service='*'):
        self.omissions.append(code)
        print(f'OMITIDO [{code}] (depende de {dependency}) servicio={service}')
        print(f'OMISION codigo={code} servicio={service} depende={dependency}')

    def run(self, args, cwd=None):
        """stdout son datos; stderr es diagnóstico. No se mezclan al decodificar JSON."""
        try:
            r = subprocess.run([str(a) for a in args], cwd=cwd, capture_output=True,
                               text=True, encoding='utf-8', errors='replace')
            return r.returncode, r.stdout.strip(), r.stderr.strip()
        except OSError as error:
            return 127, '', str(error)

    def output(self, args, cwd=None):
        rc, out, err = self.run(args, cwd)
        return rc, '\n'.join(x for x in (out, err) if x)

    def datos(self, args, cwd=None):
        rc, out, err = self.run(args, cwd)
        if err:
            print(err, file=sys.stderr)
        return rc, out

    def check(self, code, args, service='*', cwd=None):
        rc, text = self.output(args, cwd)
        if rc:
            self.add(code, text or 'La comprobación falló sin diagnóstico.', service)
        elif text:
            print(text)
        return rc == 0

    def python(self, name, *args):
        return self.stack.python(self, name, *args)

    def reader(self, *args):
        return self.stack.reader(self, *args)

    def branch(self, code, callback):
        try:
            return callback()
        except (OSError, UnicodeError, ValueError, KeyError, TypeError, AttributeError) as error:
            self.add(code, 'No se pudo completar esta comprobación: ' + str(error))
            return None

    def strict_blocked(self):
        return any(self.data['codigos'][c]['estricto'] == 'bloqueo' for c, _, _ in self.findings)

    def finish(self):
        counts = {c: sum(cls == c for _, cls, _ in self.findings) for c in ('bloqueo', 'aviso', 'plan')}
        first = next((c for c, cls, _ in self.findings if cls == 'bloqueo'), 'ninguno')
        rc = int(counts['bloqueo'] > 0)
        blocks = [
            (code, service, remedy)
            for (code, cls, service), remedy
            in zip(self.findings, self.finding_remedies)
            if cls == 'bloqueo'
        ]
        for i, (code, service, remedy) in enumerate(blocks, 1):
            print(f'REPASO bloqueo {i}/{counts["bloqueo"]} [{code}] servicio={service} remedio={remedy}')
        print(f'RESUMEN workflow={self.workflow or "estricto"} fase={self.phase} bloqueos={counts["bloqueo"]} plan={counts["plan"]} avisos={counts["aviso"]} omitidos={len(self.omissions)} primero={first} exit={rc}')
        return rc

    def corta(self, cause):
        self.omit('PREFLIGHT_RESTANTE', cause)
        return self.finish()

    def regeneracion(self):
        rc, actual = self.datos(self.reader('regenerar'))
        if rc:
            self.add('STACK_INVALIDO', actual); return False
        try:
            current = json.loads(actual)
            saved = json.loads((self.agents / '.generado.json').read_text())
            if 'regenerar' not in saved:
                self.add('REGENERAR', 'formato antiguo de .generado.json: regenera para poder comparar nomenclatura.*.'); return False
            old = saved['regenerar']
            if not isinstance(old, dict) or not old or not all(isinstance(v, str) for v in old.values()):
                raise ValueError('mapa regenerar inválido')
            changes = [f'{k} ({old.get(k, "<ausente>")} → {current.get(k, "<ausente>")})'
                       for k in sorted(set(old) | set(current)) if k not in old or k not in current or old[k] != current[k]]
            if changes:
                self.add('REGENERAR', 'cambiaste .agents/stack.yaml: ' + '; '.join(changes)); return False
        except (OSError, UnicodeError, ValueError, TypeError, AttributeError):
            self.add('REGENERAR', '.generado.json ausente, corrupto o con mapa inválido; no se puede comprobar la generación.'); return False
        return True

    def plantillas(self):
        try:
            local = json.loads(self.local_path().read_text(encoding='utf-8'))
            if set(local) != {'ruta', 'proyecto', 'commit'} or not all(isinstance(v, str) for v in local.values()):
                return
            route, project, commit = local['ruta'], local['proyecto'], local['commit']
            if not Path(route).is_dir() or not re.fullmatch(r'[0-9a-f]{40,64}', commit) or not re.fullmatch(r'[\w-]+', project):
                return
            if not (Path(route) / 'sources' / project).is_dir():
                return
            if not project.startswith(self.stack.SOURCES_PREFIX):
                return
            if self.output(['git', '-C', route, 'merge-base', '--is-ancestor', commit, 'HEAD'])[0]:
                return
            rc, count = self.output(['git', '-C', route, 'rev-list', '--count', commit + '..HEAD', '--', 'sources/' + project])
            if not rc and int(count) > 0:
                self.add('PLANTILLAS_NUEVAS', 'hay commits nuevos en sources/' + project + ' desde la generación de este .agents.')
        except (OSError, UnicodeError, ValueError, TypeError, KeyError, AttributeError):
            pass

    def documentos_locales(self):
        rc, out = self.output(self.python('comprobar-documentacion.py'))
        if not rc:
            if out: print(out)
            return
        found = False
        for line in out.splitlines():
            if line.startswith('BLOCKED: '):
                body = line[len('BLOCKED: '):]
                # Solo el formato anclado del comprobador atribuye un error a un servicio/tecnología.
                match = re.match(r'DOCUMENTACION_\w+: ([\w.-]+): ([\w.-]+) ', body)
                self.add('DOCUMENTACION' if match else 'DOCUMENTACION_GENERAL', line, match[1] if match else '*')
                found = True
            elif line.startswith('AVISO'):
                print(line)
        if not found:
            self.add('PLANTILLA', out or 'El cotejo documental falló sin diagnóstico.')

    def grafo(self, params):
        if params['herramientas.codebase_memory'] != 'true':
            self.omit('GRAFO', 'herramientas.codebase_memory=false')
            return
        cli = shutil.which('codebase-memory-mcp')
        if not cli:
            self.add('HERRAMIENTA', "CLI codebase-memory-mcp no encontrada en PATH. Instala solo el binario con: curl -fsSL https://raw.githubusercontent.com/DeusData/codebase-memory-mcp/main/install.sh | bash -s -- --skip-config")
            return
        try:
            result = subprocess.run([cli, '--version'], capture_output=True, text=True,
                                    encoding='utf-8', errors='replace', timeout=30)
            version = '\n'.join(x.strip() for x in (result.stdout, result.stderr) if x.strip())
        except (OSError, subprocess.TimeoutExpired):
            version = ''
        print('✅ OK (' + (version.splitlines()[0] if version else 'versión no informada') + ')')

        def mostrar(texto):
            for line in texto.splitlines():
                if line.startswith('AVISO'):
                    self.add('GRAFO_AVISO', line)
                else:
                    print(line)

        rc, out = self.output(self.python('codebase-memory.py', '--comprobar'))
        lines = out.splitlines()
        if rc or any(line.startswith(('BLOCKED', 'FALTA')) for line in lines):
            for line in lines:
                if line.startswith('AVISO'):
                    self.add('GRAFO_AVISO', line)
        if rc == 2 or any(line.startswith('BLOCKED') for line in lines):
            self.add('GRAFO', 'fallo de CBM (no del índice): ' + out)
            return
        if rc == 1 or any(line.startswith('FALTA') for line in lines):
            self.add('GRAFO', out)
            return
        if rc:
            self.add('GRAFO', 'fallo de CBM (no del índice): ' + out)
            return
        mostrar(out)
        if (self.phase == 'entrada' and self.workflow
                and self.data['workflows'][self.workflow]['grupo'] == 'E'):
            rc, out = self.output(self.python('codebase-memory.py', '--indexar', '--timeout', '120'))
            if rc:
                self.add('GRAFO_AVISO', 'el índice existe pero no se pudo actualizar: ' + out)
                for line in out.splitlines():
                    if line.startswith('AVISO'):
                        self.add('GRAFO_AVISO', line)
            else:
                mostrar(out)

    def registro(self, ctx):
        registry = self.registry
        services = getattr(self.stack, 'servicios_registro', lambda p,c: [])(self, ctx)
        result = registry.evaluar(self.root, self.agents, ctx, services=services, workflow=self.workflow, phase=self.phase)
        for text in result['avisos']:
            self.add('REGISTRO', text)
        for text in result['recordatorios']:
            self.add('REGISTRO', text, recordatorio=True)
        evidence_counts = {}
        for row in result['resultados']:
            if row['resultado'] != 'coincide':
                if row.get('informativo'):
                    self.add(row['codigo'], row['motivo'], recordatorio=True, clase='aviso')
                    continue
                self.add(row.get('codigo', 'STACK_CODIGO'), f'{row["clave"]}={row["valor"]} resultado={row["resultado"]}: {row["motivo"]}\n' +
                         '\n'.join(registry.evidencia_visible(row, contadores=evidence_counts)) + '\nDetalle: ' + registry.detalle(row, self.workflow, ctx.get('datos', {})), row['servicio'], clase=row['clase'])

    def notebook(self):
        # Son lecturas: se ejecutan aun cuando existan bloqueos estáticos.
        self.check('OPEN_NOTEBOOK', self.python('documentacion.py', 'comprobar-conexion'))
        rc, remote = self.datos(self.python('documentacion.py', 'comprobar-existencia'))
        if not rc:
            if remote: print(remote)
            return
        try:
            error_code = json.loads(remote)['error']['codigo']
        except (ValueError, KeyError, TypeError, AttributeError):
            error_code = ''
        code = 'DOCUMENTACION' if error_code == 'DOCUMENTACION_FALTA' else 'DOCUMENTACION_GENERAL' if error_code in {'REGISTRO', 'CATALOGO', 'CATALOGO_PROYECTO'} else 'OPEN_NOTEBOOK' if error_code else 'PLANTILLA'
        self.add(code, remote or 'Fallo de comprobar-existencia sin salida de datos.')

    def tgrep(self):
        _, initial = self.output(['tgrep', 'status', 'knowledge-base/'])
        if 'Server status' not in initial:
            print('(arrancando servidor daemon)...')
            with open(os.devnull, 'w') as sink:
                subprocess.Popen(['tgrep', 'serve', 'knowledge-base/'], stdin=subprocess.DEVNULL,
                                 stdout=sink, stderr=sink, start_new_session=True)
            time.sleep(1)
        for _ in range(3):
            _, out = self.output(['tgrep', 'status', 'knowledge-base/'])
            if 'Indexing:   complete' in out:
                print('✅ OK (Indexing: complete)')
                return
            time.sleep(2)
        self.add('TGREP', "El índice de tgrep no convergió a 'Indexing: complete' tras 3 intentos.\n" + out)

    def ejecutar(self):
        missing = False
        for tool in ['git', 'python3', 'jq', *self.stack.TOOLS]:
            if not shutil.which(tool):
                self.add('HERRAMIENTA', tool + ' no encontrado en PATH.')
                missing = True
        if missing: return self.corta('HERRAMIENTA')
        rc, root = self.datos(['git', 'rev-parse', '--show-toplevel'])
        if rc:
            self.add('REPOSITORIO', 'no se ejecuta dentro de un repositorio git.')
            return self.corta('REPOSITORIO')
        try:
            os.chdir(root)
            self.root = Path(root)
        except OSError:
            self.add('REPOSITORIO', 'no se pudo acceder a la raíz git.')
            return self.corta('REPOSITORIO')
        self.origen()
        if not self.stack.antes_validar(self): return self.corta('HERRAMIENTA')
        rc, validation = self.output(self.reader('validate'))
        if rc:
            self.add('STACK_INVALIDO', validation)
            return self.corta('STACK_INVALIDO')
        self.stack.avisos_validacion(self, validation)
        rc, ctxout = self.datos(self.reader('registro-datos'))
        if rc:
            self.add('STACK_INVALIDO', ctxout)
            return self.corta('STACK_INVALIDO')
        ctx = json.loads(ctxout)
        ctx['datos'] = getattr(self, 'datos_entrada', {})
        params = {}
        for key in ['herramientas.codebase_memory', 'git.rama_base', *self.stack.KEYS]:
            rc, val = self.datos(self.reader('get', key))
            if rc:
                self.add('STACK_INVALIDO', val)
                return self.corta('STACK_INVALIDO')
            params[key] = val
        if not self.stack.contexto(self, ctx, params): return self.corta(self.stack.CONTEXT_CODE)
        if not self.regeneracion(): return self.corta('REGENERAR')
        self.plantillas()
        rc, out = self.output(['bash', self.agents / 'scripts/preparar-proyecto.sh', '--comprobar'])
        if rc: self.add('PREPARACION' if rc == 1 else 'PLANTILLA', out)
        rc, dirty = self.datos(['git', 'status', '--porcelain'])
        if rc:
            self.add('REPOSITORIO', dirty)
            return self.corta('REPOSITORIO')
        if dirty: self.add('ARBOL_SUCIO', 'El working tree no está limpio:\n' + dirty)
        self.branch('PLANTILLA', lambda: self.stack.estaticos(self, ctx, params))
        self.branch('DOCUMENTACION_GENERAL', self.documentos_locales)
        self.branch('PLANTILLA', lambda: self.registro(ctx))
        self.branch('GRAFO', lambda: self.grafo(params))
        if not shutil.which('tgrep'): self.add('HERRAMIENTA', 'CLI tgrep no encontrada en PATH.')
        if not Path('knowledge-base').is_dir(): self.add('TGREP', 'No existe knowledge-base/.')
        self.branch('OPEN_NOTEBOOK', self.notebook)
        if self.strict_blocked():
            for code in ['TGREP', *self.stack.EXPENSIVE]:
                self.omit(code, 'BLOQUEOS_ESTRICTOS')
        else:
            self.branch('PLANTILLA', lambda: self.stack.caros(self, ctx, params))
            self.branch('TGREP', self.tgrep)
        if not any(c == 'bloqueo' for _, c, _ in self.findings):
            print(self.stack.PENDIENTE)
        return self.finish()


def workflows_admitidos(agents):
    names = set()
    for path in (agents / 'workflows').glob('*.md'):
        try:
            text = path.read_text(encoding='utf-8', errors='replace')
        except OSError:
            continue
        command = r'bash \.agents/scripts/preflight\.sh --workflow ' + re.escape(path.stem) + r' --fase (?:entrada|cierre)\b'
        if re.search(command, text):
            names.add(path.stem)
    return names


def uso(names=None):
    if names is None:
        names = workflows_admitidos(Path(__file__).resolve().parents[1])
    print('Uso: preflight.sh [--workflow W] [--fase entrada|cierre] [--dato clave=valor]...', file=sys.stderr)
    print('Workflows admitidos: ' + ', '.join(sorted(names)), file=sys.stderr)
    return 2


def main(argv):
    # La forma de argumentos se valida antes de abrir catálogo o módulos de datos.
    opts, seen = {'--workflow': '', '--fase': 'entrada'}, set()
    entradas = []
    while argv:
        key = argv[0]
        if key == '--dato' and len(argv) >= 2:
            if not re.fullmatch(r'[a-z_][a-z0-9_]*=[^\s=]{1,80}', argv[1]):
                return uso()
            entradas.append(argv[1])
            argv = argv[2:]
            continue
        if key not in opts or key in seen or len(argv) < 2:
            return uso()
        opts[key] = argv[1]
        seen.add(key)
        argv = argv[2:]
    if opts['--fase'] not in ('entrada', 'cierre'):
        return uso()
    agents = Path(__file__).resolve().parents[1]
    names = workflows_admitidos(agents)
    if '--workflow' in seen and opts['--workflow'] not in names:
        return uso(names)
    p = None
    try:
        dm = modulo('preflight_datos', agents / 'scripts/preflight_datos.py')
        data = dm.catalogo(agents)
        if set(data['workflows']) != names:
            raise ValueError('nombres de workflow y catálogo no coinciden')
        stack = modulo('preflight_stack', agents / 'scripts/preflight_stack.py')
        registry = modulo('registro_stack_datos', agents / 'scripts/registro-stack.py')
        try:
            datos = registry.validar_datos(agents, entradas)
        except ValueError:
            return uso(names)
        p = Preflight(agents, data, opts['--workflow'], opts['--fase'], stack, dm)
        p.registry = registry
        p.datos_entrada = datos
        return p.ejecutar()
    except (OSError, UnicodeError, ValueError, KeyError, TypeError, AttributeError, SyntaxError, ImportError, NameError) as error:
        if p:
            try:
                p.add('PLANTILLA', 'Fallo interno del comprobador: ' + str(error))
                return p.corta('PLANTILLA')
            except (KeyError, TypeError, AttributeError):
                pass  # El propio catálogo puede haber perdido PLANTILLA; emitir resumen mínimo.
        print('BLOCKED [PLANTILLA] catálogo o comprobador ilegible: ' + str(error))
        print('Remedio: Avisa al mantenedor de .agents; no modifiques scripts para superar el control.')
        print('RESULTADO codigo=PLANTILLA clase=bloqueo servicio=* remedio="Avisa al mantenedor de .agents"')
        print('RESUMEN workflow=estricto fase=entrada bloqueos=1 plan=0 avisos=0 omitidos=0 primero=PLANTILLA exit=1')
        return 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
