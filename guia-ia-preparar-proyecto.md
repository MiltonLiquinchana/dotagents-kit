# Guía para la IA: preparar el `.agents` de un proyecto nuevo

> **Para la IA que lee esto.** El usuario te ha abierto en el workspace de **su proyecto** y te ha dado
> la ruta de `dotagents-kit`, la carpeta que contiene este archivo. Tu trabajo:
> 1. escribir **dos archivos** en su proyecto:
>    - `.agents/stack.yaml`, relleno con él a base de preguntas;
>    - `.agents/actualizar.py`, copiado del stack elegido;
> 2. ejecutar `actualizar.py` **una vez**, con su confirmación, para que genere el resto del `.agents`;
> 3. decirle qué sigue: en el back, cómo traer su primer servicio desde Spring Initializr con las
>    versiones y dependencias que eligió.
>
> En esta guía:
> - `<KIT>` es la ruta de `dotagents-kit` que te dio el usuario;
> - `<PROYECTO>` es la raíz del workspace del usuario;
> - `<SOURCES>` es `<KIT>/sources/<carpeta del stack elegido>/.agents`.

## Límites

**Escribes solo:**
- `<PROYECTO>/.agents/stack.yaml`;
- `<PROYECTO>/.agents/actualizar.py`.

El resto del `.agents` lo escribe `actualizar.py` en el paso 7. Tú no escribes nada más: ni otros archivos
del `.agents`, ni código, ni `.gitignore`, ni `git init`, ni commits.

**Lees solo:**
- de `<KIT>`: esta guía y, de `sources/*/.agents/`, `stack.yaml`, `config/opciones.yaml`,
  `config/requisitos.yaml`, `config/claves.md`, `actualizar.py` y `scripts/servicios.py`;
- de `<PROYECTO>/.agents/`, después de generarlo: las referencias de Initializr y las precondiciones de
  `bootstrap-project` que usa el paso 8, y las salidas de los comandos de los pasos 7 y 8;
- de `<PROYECTO>`: solo la lista blanca del paso 3, nombres de perfiles y lockfiles, ExceptionResponse.java
  y los literales de pipeline, entornos, manifiestos DevOps y Dockerfiles por F/H/I/J;
  nunca `account/`, `.env*`, secretos ni kubeconfig;
- nombres y metadatos con `ls -la <ruta>`, solo dentro de `<PROYECTO>` o `<KIT>`; nunca sobre
  `account/`, `.env*`, secretos ni kubeconfig. El manual se remite al usuario; tú no lo lees.
- única excepción fuera de `<PROYECTO>` y `<KIT>`: nombres de carpetas de JDK de Jenkins o del desarrollador con `ls -d <carpeta>/*/`,
  tanto en la máquina de Jenkins como en la del desarrollador, si el usuario indica la carpeta. Nunca otros proyectos.

**Nunca:**
- leas `.env*`, archivos de secretos (`secret*.yaml`, `secrets-*.yaml`), `kubeconfig*`, nada bajo una
  carpeta `account/`, ni la configuración de las herramientas del usuario (`~/.claude.json`,
  `opencode.json`, `~/.codex/`…);
- leas un `application*.yaml`, `application*.yml` o `application*.properties` entero (solo con la lista blanca del paso 3);
- ejecutes `actualizar.py` fuera del paso 7, ni con otras opciones que las de ese paso;
- instales nada, uses la red ni ejecutes comandos de base de datos, `kubectl`, Docker o Gradle;
- escribas un valor de credencial. De las credenciales solo se escriben **nombres** de variables. Si el
  usuario te pega un valor, no lo copies a ningún sitio y recuérdale que, si es real, lo rote.

Si algo no encaja con esta guía, **detente y pregunta**.

## Paso 1 — Comprobar el punto de partida

1. Si `<PROYECTO>/.agents/actualizar.py` o `<PROYECTO>/.agents/.generado.json` ya existen, el proyecto ya
   tiene un `.agents` generado. **Detente.** Dile al usuario que no hace falta esta guía: para cambiar
   opciones, edita `.agents/stack.yaml` y ejecuta
   `python3 -I -B .agents/actualizar.py --kit <KIT>`.
2. Si ya existe `<PROYECTO>/.agents/stack.yaml`, sin lo anterior, pregúntale si lo reutilizas como punto de
   partida o empiezas desde la plantilla.
3. Comprueba que `<KIT>/sources/` existe. Si no, la ruta no es la de `dotagents-kit`: pídela otra vez.

## Paso 2 — Elegir el stack

1. Lista los stacks que soporta `dotagents-kit`: para cada `<KIT>/sources/*/.agents/stack.yaml`, el
   valor de `proyecto.stack` y su carpeta. No uses una lista fija: puede haber stacks nuevos.
2. Propón el stack según lo que veas en `<PROYECTO>`, solo por nombres de archivo:

   | Señal en el proyecto | Stack |
   |---|---|
   | `package.json` con `next` en las dependencias | `nextjs` |
   | `build.gradle` y `settings.gradle` en carpetas del primer nivel (un build por servicio) | `springboot` |
   | sobre todo `.sql` o `.dbcnb`, sin `package.json` ni `build.gradle` | `mysql` |

3. Pregunta al usuario y espera su confirmación. Si el proyecto no encaja con ninguno, dile que
   `dotagents-kit` no lo soporta todavía y detente.

## Paso 3 — Detectar valores (solo lista blanca)

Lee `<SOURCES>/stack.yaml`, `config/claves.md`, `config/opciones.yaml` y `config/requisitos.yaml`, si existe.
Aquí solo lee y detecta con esta lista blanca; registra valores, ausencias y discrepancias sin explicar ni
preguntar todavía. Las explicaciones y las preguntas empiezan en el paso 4, después del glosario.

| Stack | Lectura permitida | Para qué |
|---|---|---|
| `nextjs` | `package.json`; nombres de `next.config.*`, `eslint*.config.*`; bloque A para locks raíz | nombre, versión, dependencias, configuración y gestor |
| `nextjs` | nombres de archivos en `controllers/`, `services/`, `repository/`, `domains/` y `app/ui/` | nomenclatura |
| `springboot` | `build.gradle` y `settings.gradle` de cada servicio | Java, Boot, `group` y dependencias |
| `springboot` | `gradle.properties`: `grep -hoE '^[[:space:]]*org[.]gradle[.]java[.]installations[.]paths[[:space:]]*[=:].*' <servicio>/gradle.properties` | solo ruta JDK de desarrollo, sin `-r`, contexto ni continuar líneas con `\` |
| `springboot` | bloque B, desde `<PROYECTO>` | servicios, puertos, context-path y gateway; informa omisiones de puerto o context-path |
| `springboot` | `application*.yaml`, `.yml` y `.properties`, solo bloque C | perfiles, puertos, nombres de variables y estrategia JPA |
| `springboot` | nombres de `application-*.yaml`/`.yml`, bloque D | sufijos, quitando el `active:` de C; si falta, repetir tras confirmar `backend.perfil_local` en el paso 4 |
| `springboot` | solo `ExceptionResponse.java`, bloque E | `api_error.*`; registra si falta el manejador para decidir el contrato en el paso 4 |
| `springboot` | pipeline y Dockerfiles de los servicios de B, bloques F/H/J | IDs, etiquetas, rutas JDK, Slack y entornos; registra ausencias |
| `springboot` | declaraciones `NODO_GENERAL`, `NODO_COMPILACION`, `NODO_DOCKER` y etiquetas literales, F | `devops.nodos.general`, `.compilacion`, `.docker`, respectivamente; otros literales: propone por función y pregunta si dudas |
| `springboot` | nombres de `*Application.java` y estrategia por C | nomenclatura de clase y JPA |
| `mysql` | nombres de carpetas y `.dbcnb`; solo encabezados por G | carpeta y notebooks; G se aplaza hasta excluir datos de prueba en el paso 4 |
| todos | nombres de `devops/` y `Jenkinsfile*`, sin `account/`; en back, solo manifiestos por I | infraestructura; réplicas, recursos, puertos y registry |

**A — Gestor**, desde la raíz: registra si hay varios locks para resolverlo en el paso 4; mientras exista
el sobrante la comprobación previa seguirá avisando:

```bash
find . -maxdepth 1 -type f \( -name 'package-lock.json' -o -name 'pnpm-lock.yaml' -o -name 'yarn.lock' \) -print
```

**B — Servicios**, desde `<PROYECTO>`:

```bash
python3 -I -B <SOURCES>/scripts/servicios.py listar
```

**C — Configuración**: para `.yaml` y `.yml`, solo estas coincidencias. El nombre del proyecto se toma
de `settings.gradle` o de B, nunca de un `name:` genérico. No leas el archivo entero:

```bash
grep -nhoE '^[[:space:]]*(port|context-path|active):[[:space:]]*[^[:space:]]+' <archivo>
grep -oE '\$\{[A-Za-z_][A-Za-z0-9_]*' <archivo>
grep -nhoE 'physical-strategy:[[:space:]]*[^[:space:]]+' <archivo>
```

Para `.properties`, solo las mismas claves y los nombres de variables:

```bash
grep -nhoE '^[[:space:]]*(server[.]port|server[.]servlet[.]context-path|spring[.]application[.]name|spring[.]profiles[.]active)[[:space:]]*=[[:space:]]*[^[:space:]]+' <archivo.properties>
grep -oE '\$\{[A-Za-z_][A-Za-z0-9_]*' <archivo.properties>
```

**D — Sufijos**: usa el `active:` de C como `<perfil-local>`; si falta, aplaza D hasta confirmar
`backend.perfil_local` en el paso 4 y repítelo entonces. Sin resultados, no hay qué detectar:

```bash
find <servicio>/src/main/resources -maxdepth 1 -type f \( -name 'application-*.yaml' -o -name 'application-*.yml' \) -print | sed -E 's@.*/application-@@; s/\.ya?ml$//' | grep -vFx -- '<perfil-local>'
```

**E — Contrato de errores**: el contexto de ocho líneas solo se permite en ese archivo; si no basta, anótalo para el paso 4:

```bash
find <servicio>/src -type f -name 'ExceptionResponse.java' -print
grep -n -A 8 -E 'record[[:space:]]+ExceptionResponse[[:space:]]*\(' <ExceptionResponse.java>
```

**F/H/I/J — DevOps del back**, desde `<PROYECTO>`: F lee solo IDs (`credencial_kubeconfig`,
`credentialsId`), `credBd`, `slackChannel`, `PIPELINE_JAVA_HOME` y etiquetas; H, solo el mapa
entre `def getEnvironments()` y la primera línea `^}`; I, manifiestos; J, Dockerfiles de B.
Sustituye `<jenkinsfile>` por una ruta explícita de `devops/Jenkinsfile*` o la indicada; repite si hay
varias. Sustituye `<Dockerfiles-de-los-servicios-de-B>` por sus rutas explícitas (ninguna sin servicios). Con un pipeline fuera de `devops/`, adapta
solo la raíz del `find` a su carpeta. Si no hay pipeline, usa `'-'` como primer argumento y
registra esa ausencia. Si no existe la carpeta DevOps, omite el `find` y pasa `manifiestos=()`.
No amplíes archivos ni claves. Se excluyen líneas con `$` y marcadores `<…>` o `__…__`. En YAML
y Dockerfile se corta antes de `#`; en Groovy, solo antes de `//` fuera de comillas (se conserva
`#mi-ci`). Solo `credBd` y `slackChannel` vacíos se muestran como `null`. Si H no devuelve entradas
ni claves (mapa ausente o sin rellenar), registra la ausencia.

```bash
mapfile -d '' manifiestos < <(find devops -mindepth 3 -maxdepth 3 -type f \( -name 'deployment-*.yaml' -o -name 'service-*.yaml' \) -not -path '*/account/*' -print0 | sort -z)
python3 -I -B - '<jenkinsfile>' <Dockerfiles-de-los-servicios-de-B> "${manifiestos[@]}" <<'PY'
import re, sys
from pathlib import Path
q = r'''(?:'[^']*'|"[^"]*")'''
literal = q + r'|true|false'
def value(s):
    return s[1:-1] if s[:1] in ("'", '"') else s
def emit(path, n, text):
    print(f'{path}:{n}:{text}')
for arg in sys.argv[1:]:
    if arg == '-': continue
    path = Path(arg)
    inside = False
    pending = None
    for n, raw in enumerate(path.read_text(errors='replace').splitlines(), 1):
        pipeline = path.name.startswith('Jenkinsfile') or arg == sys.argv[1]
        if pipeline:
            s = re.sub(r"""'(?:\\.|[^'\\])*'|"(?:\\.|[^"\\])*"|//.*""",
                       lambda m: '' if m[0].startswith('//') else m[0], raw).rstrip()
            if re.match(r'^}', s): inside = False
            if re.search(r'\bdef\s+getEnvironments\s*\(\s*\)', s): inside = True
        else: s = raw.split('#', 1)[0].rstrip()
        if '$' in raw or re.search(r'<[^>]*>|__[A-Z_]+__', raw): continue
        if path.name.startswith(('deployment-', 'service-')):
            m = re.fullmatch(r'\s*(replicas|requests|limits|cpu|memory|nodePort|port|image):\s*(.*?)', s)
            if not m: continue
            key, v = m.groups()
            if key in ('requests', 'limits'):
                pending = (n, s) if not v else None
                continue
            if key == 'port' and not path.name.startswith('service-'): continue
            if not re.fullmatch(q + r'|[^\s\'"{}\[\]]+', v): continue
            if key == 'image':
                if '/' not in value(v): continue
                s = 'image: ' + value(v).split('/', 1)[0]
            if key in ('cpu', 'memory') and pending:
                emit(path, *pending); pending = None
            emit(path, n, s)
        elif path.name == 'Dockerfile':
            for pattern in (r'\bcurl\s+-L\s+([^\s;\\]+)', r'^\s*ENV\s+JAVA_HOME=([^\s;\\]+)\s*$'):
                m = re.search(pattern, s)
                if m: emit(path, n, m.group(0).strip())
        else:
            patterns = (rf'\b(?:NODO_GENERAL|NODO_COMPILACION|NODO_DOCKER|credBd|slackChannel|PIPELINE_JAVA_HOME)\s*=\s*{q}(?=\s*;?\s*(?://.*)?$)',
                        rf'\b(?:credencial_kubeconfig|credentialsId)\s*:\s*{q}(?=\s*(?:[,)]|$|//))',
                        rf'\blabel\s+{q}(?=\s*(?:$|}}|//))|\bnode\(label:\s*{q}\)')
            for pattern in patterns:
                for m in re.finditer(pattern, s):
                    text = m.group(0)
                    if inside and text.startswith('credencial_kubeconfig'): continue
                    if re.fullmatch(rf'(credBd|slackChannel)\s*=\s*(?:\'\'|"")', text):
                        text = text.split('=')[0].strip() + ' = null'
                    elif re.search(r'''(?:''|"")\)?$''', text): continue
                    emit(path, n, text)
            if inside:
                entry = rf'\s*(?:[\w-]+|{q})\s*:\s*\[\s*'
                field = rf'\s*(?:rama|sufijo|credencial_kubeconfig|imagen|desplegar|carpeta)\s*:\s*(?:{literal})\s*,?\s*'
                if re.fullmatch(entry, s) or re.fullmatch(field, s): emit(path, n, s)
PY
```

**G — SQL**: no ejecutes este bloque hasta identificar y excluir los datos de prueba en el paso 4.
Sobre cada notebook permitido, devuelve solo tipo/nombre de objeto, sin definidor ni filas de datos:

```bash
grep -ihoE 'CREATE[[:space:]]+(OR[[:space:]]+REPLACE[[:space:]]+)?((ALGORITHM[[:space:]]*=[[:space:]]*[^[:space:]]+|DEFINER[[:space:]]*=[[:space:]]*[^[:space:]]+|SQL[[:space:]]+SECURITY[[:space:]]+(DEFINER|INVOKER))[[:space:]]+)*(TEMPORARY[[:space:]]+|UNIQUE[[:space:]]+|FULLTEXT[[:space:]]+|SPATIAL[[:space:]]+)?(TABLE|PROCEDURE|FUNCTION|VIEW|TRIGGER|EVENT|INDEX)[[:space:]]+(IF[[:space:]]+NOT[[:space:]]+EXISTS[[:space:]]+)?(`?[[:alnum:]_]+`?\.)?`?[[:alnum:]_]+`?' <notebook-permitido.dbcnb> | grep -ioE '(TABLE|PROCEDURE|FUNCTION|VIEW|TRIGGER|EVENT|INDEX)[[:space:]]+(IF[[:space:]]+NOT[[:space:]]+EXISTS[[:space:]]+)?(`?[[:alnum:]_]+`?\.)?`?[[:alnum:]_]+`?'
```

El issuer de Clerk no se busca. Registra los comandos fallidos o sin salida para resolverlos en el paso 4;
**no abras el archivo para averiguarlo**, ni amplíes el alcance o el contexto permitido.

## Paso 4 — Preguntar

**No hay pregunta sin explicación.** Esta regla se aplica a las preguntas sobre claves del paso 4,
salvo la confirmación abreviada definida al final. Incluye primeras preguntas, detección inequívoca,
booleanas y respuesta libre (etiquetas, rutas, IDs). Reproduce el bloque de cada clave con las etiquetas
literales en negrita de `<SOURCES>/config/claves.md`: **En resumen:**, **Dónde se ve en tu proyecto:**,
**Para qué se usa:**, **Qué pasa si está mal:**, **Cambiarla después:** y los párrafos **Si …:** de sus
opciones. Conserva las etiquetas de la ficha; no las sustituyas por prosa sin rótulos. El bloque va en el
mismo mensaje que la pregunta, también en preguntas agrupadas (un bloque por clave) y seguidas.
Con herramienta de preguntas, antes de cada llamada escribe y comprueba en ese mismo turno el bloque
con sus etiquetas de cada clave que vas a preguntar; tras recibir una respuesta, nunca lances la pregunta
siguiente sin texto previo en ese turno: primero va, si procede, una línea por cada clave registrada sin
pregunta, con su valor y causa, y después el bloque de cada clave que vas a preguntar.
El aviso nunca sustituye al bloque, tampoco una línea dentro de la pregunta. La propia pregunta resume
en una línea **para qué se usa** y cada opción dice su consecuencia. No se exige bloque al glosario ni a
preguntas que no son claves, como la selección del notebook en SQL. Las preguntas anteriores al paso 4
(punto de partida y stack) no cambian. Una confirmación es volver a preguntar una clave cuyo bloque ya
mostraste, por ejemplo para confirmar un literal numérico o una respuesta escrita en «Other»; basta
repetir para qué se usa y la consecuencia. La primera pregunta de una clave nunca es una confirmación.
Escribe primero cualquier bloque que falte antes de preguntar.

Muestra una vez el glosario «Palabras que usan estas fichas» de `<SOURCES>/config/claves.md` antes de la primera pregunta.
En SQL, lista primero los nombres de notebooks y pregunta cuál contiene datos de prueba: ese y sus alias
no se abren nunca. Si duda, excluye también nombres con `datos`, `seed` o `prueba` (sin distinguir mayúsculas),
salvo los que confirme como permitidos. Solo entonces ejecuta G sobre los restantes, nunca sobre el excluido.
Si hay varios locks, pregunta cuál vale; el agente podrá quitar el sobrante en una tarea posterior, con tu aprobación.

1. **Avanza sección por sección; dentro de cada una, haz una pregunta por decisión y espera su respuesta
   antes de la siguiente.** Sigue el orden de `stack.yaml`, salvo en back y front: `autenticacion` antes
   de `gestion_usuarios`, por sus requisitos. Aplica la condición de explicación anterior con la ficha y lo detectado.
   No preguntes `version_esquema`, `proyecto.stack`, `backend.build`, `frontend.framework`,
   `base_de_datos.motor` ni los tres `documentacion.modelo_*`.
   - Antes de cada pregunta, lee entera la ficha de esa clave en `<SOURCES>/config/claves.md`: desde su encabezado `## <clave>` (en mapas libres, con `{nombre}`: `## devops.entornos.{nombre}.<campo>`) hasta la línea anterior al siguiente `## ` o el final del archivo, sin cortarla por número de líneas (`head`, `sed -n`, límites de lectura). Las marcas `<!-- si … -->` y `<!-- fin -->` de dentro son parte de la ficha, no su final. Copia de ella **Cambiarla después** y el párrafo `**Si …:**` de cada opción («Si eliges…», «Si conservas…», «Si declaras…», «Si cambias…»…); no los resumas ni los inventes.
     Excepción para todo `**Si conservas …**` con un valor entre comillas invertidas (con o sin
     «por ejemplo») y `**Dónde se ve en tu proyecto:** Por ejemplo, …`: sus valores son ejemplos de
     la ficha, nunca datos detectados ni «tu código» o «tu instalación». En «Dónde se ve», antepón
     «Ejemplo de la ficha:» al ejemplo. Si el dato detectado coincide con una opción «Si eliges …»,
     marca esa opción **Detectado:** con archivo y línea y omite «Si conservas …». Si no coincide,
     titula «Si conservas `<valor detectado>`» y copia el cuerpo intacto precedido de «Ejemplo de la
     ficha:». Sin detección, copia el párrafo precedido de «No lo detectamos en tu proyecto; ejemplo
     de la ficha:», dejando claro que su encabezado también pertenece al ejemplo.
   - Una decisión es un dato, salvo tres agrupaciones permitidas: `rama`/`imagen`/`desplegar` de un entorno;
     compartir/separar credencial; y los recursos y nodePorts de cada entorno que despliega.
     Para compartir/separar credenciales nuevas puedes ofrecer los IDs de ejemplo de la ficha
     (`jenkins-kubeconfig-file` compartida; `kubeconfig-dev` y `kubeconfig-main` separados), indicando
     «créala en Jenkins con exactamente este ID»; la alternativa es escribir otro ID. No hace falta
     preguntar antes si ya existe una. Para referencias a credenciales existentes pide sus IDs en
     respuesta libre. Los IDs confirmados van en `devops.entornos.<nombre>.credencial_kubeconfig`.
   - Por cada entorno que despliega, una sola pregunta sobre réplicas, CPU y memoria (petición y límite)
     y nodePorts aplicables: «valores detectados» solo con detección inequívoca del paso 3, o «valores de
     plantilla» solo sin detección, frente a «personalizar». Muestra la lista literal con unidades y origen;
     incluye el bloque de la ficha de cada clave. Si hay diferencias entre servicios o bloques, resuélvelas
     primero como se indica abajo. Solo al personalizar pregunta un dato cada vez, conservando la regla de
     literales numéricos. `cors_origenes` y `clerk_issuer_uri` siguen siendo preguntas propias.
   - No pidas «por texto: 1)… 2)…» ni vuelvas a preguntar lo respondido: di «ya elegiste que `development`
     construye y despliega» y pide solo lo pendiente. Cada pregunta se entiende por sí sola.
   - Cada opción explica su efecto. Un ejemplo del proyecto del usuario solo puede presentarse como tal
     si procede de la detección del paso 3, con archivo y línea. Conserva la recomendación detectada;
     sin dato previo, distingue el ejemplo de la ficha y el valor de plantilla. No dupliques esa opción
     con su literal de ejemplo.
     No ofrezcas valores rechazados, como un entorno sin acciones o `documentacion.url_api: null`, `imagen: ninguna` o un segundo `construir`.
   - Solo si las respuestas ya dadas, `config/requisitos.yaml` o una regla de combinación de esta guía
     (por ejemplo, `promover` exige `desplegar: true`) dejan un único valor válido, no lo preguntes:
     informa el valor y su causa (por ejemplo, «`main.desplegar` queda en `true` porque `promover` lo exige»).
     Que lo detectado coincida con la plantilla o con el valor por defecto no es una de esas causas:
     esa clave se pregunta con su bloque completo, como cualquier primera pregunta.
     Esto no cambia las claves que esta guía manda no preguntar o informar sin preguntar: las de la
     lista del ítem 1 y las de «no cambiar» del ítem 4, `gestion_usuarios: ninguna` cuando corresponde,
     `documentacion.modelo_*` y las claves dependientes que se quitan, entre otras indicadas expresamente.
     Si solo hay un valor real que proponer, el detectado, pregunta en texto, sin herramienta de preguntas,
     con el bloque completo y esta línea, rellenando valor, archivo y línea con la detección real:
     «Detectado: `<valor>` (`archivo:línea`). Responde «sí» para conservarlo o escribe otro valor.»
     Espera su respuesta: nunca hagas una pregunta de una sola opción ni decidas tú. No inventes una
     segunda opción, no dupliques el valor ni añadas una opción «Other» para salvar el límite de la herramienta.
   - Si los valores son números (réplicas, puertos), pon en cada opción el literal con su unidad (`1 réplica`, `2 réplicas`) o usa letras; si la respuesta es un número suelto y había opciones, confirma el valor literal antes de registrarlo.
   - El origen es «detectado», «valor por defecto» o «hay que decidirlo». Cita archivo y línea literal de
     lo detectado; informa diferencias entre archivos. Para lo no detectado explica dónde acabará el valor.
     Solo es detectado lo que devuelve el paso 3; un dato de plantilla parecido al del usuario no lo es.
   - Con herramienta de preguntas, incluye la línea detectada en el resumen de la pregunta. Las opciones
     son valores reales, sin huecos como `<ruta>`, con la explicación obligatoria en el mismo mensaje.
   - Para canal de Slack, etiquetas de nodos, `devops.registry`, URLs, orígenes CORS, issuer y referencias
     a credenciales existentes, pide respuesta libre con el ejemplo neutro de la ficha, nunca opciones
     derivadas del nombre del proyecto o de la carpeta ni «escribir ruta». Un dato detectado puede
     proponerse con su evidencia.
     Excepción explícita: para `devops.entornos.<e>.cors_origenes` y
     `devops.entornos.<e>.clerk_issuer_uri` del back, también puedes ofrecer reutilizar una respuesta
     equivalente ya confirmada en esta preparación, con los valores citados y las condiciones del bloque
     por entorno de abajo. Mantén siempre la alternativa de respuesta libre.
     Para una credencial nueva de Jenkins puedes ofrecer el ID de ejemplo
     de la ficha, diciendo «créala en Jenkins con exactamente este ID», o escribir otro ID.
     Si la respuesta coincide con `proyecto.nombre` o con el nombre de la carpeta en una clave que no es
     un nombre de proyecto, confirma que ese es el dato real antes de registrarlo. Si falta un dato
     obligatorio, dilo y espera su respuesta. No cites conversaciones anteriores a esta preparación ni claves inexistentes.
   - Si una respuesta por «Other» o respuesta libre no elige ninguna de las opciones de la pregunta,
     aclara cuál aplica antes de registrar el valor. Una ruta no responde si el nodo de Jenkins es esta
     máquina u otra: pregunta cuál corresponde y conserva la ruta como dato pendiente de atribuir.
   - Con `null`, `ninguna`, `false` o lista vacía permitida, explica **Cambiarla después**; no inventes
     `null` para una clave obligatoria.
   - DevOps (F/H/I/J): presenta **Detectado:** con archivo y línea y propone ese literal.
     `credBd` → `devops.credencial_bd_pruebas`; `slackChannel` → `devops.slack_canal`;
     `PIPELINE_JAVA_HOME` → `devops.java_home_nodo`; `curl -L` → `devops.jdk_url`;
     `ENV JAVA_HOME` → `devops.java_home_contenedor`. H aporta `devops.entornos.{nombre}`;
     `carpeta` se muestra como contexto y no se escribe en `stack.yaml`.
     En I, `requests` → `cpu_peticion`/`memoria_peticion`; `limits` → `cpu_limite`/`memoria_limite`.
     Ignora `ephemeral-storage`. Con varios bloques `resources` (sidecar/initContainer), muestra
     todos los bloques y pregunta; nunca elijas uno. Los bloques se distinguen por sus líneas.
     El servicio de `backend.gateway` da `gateway_nodo_puerto`; los demás dan
     `nodo_puerto_base = nodePort − (puerto de B − 8080)`: `8083` y `31003` → `31000`.
     Si difieren réplicas, recursos o bases entre servicios del entorno, muestra todos y pregunta.
     Solo toma `devops.registry` si coincide en todos los deployments; si difiere, muestra y pregunta.
     `cors_origenes` y `clerk_issuer_uri` no se detectan: ausencia esperada; pregúntalos según la regla de equivalentes confirmados y reutilización por entorno de este paso.
2. **Los valores de la plantilla son de otro proyecto**: `devops.registry`, URLs, issuer de Clerk, canal de Slack,
   rutas del JDK, nombre de la base, orígenes CORS, `sonarqube.project_key` del front… Nunca los propongas como si fueran
   del usuario. Márcalos "hay que decidirlo", salvo que coincidan con lo detectado: esa coincidencia los marca
   "detectado" en la pregunta, con archivo y línea; no evita preguntarla con su bloque completo.
3. **Versiones** (`backend.java`, `backend.spring_boot`, la de `next`…): son las versiones **con las que
   el usuario va a trabajar**, y todo el `.agents` se genera con ellas (plantillas, comprobaciones del
   preflight, instrucciones para crear servicios). Explícale que:
   - si ya tiene código, recomienda lo detectado citando la línea (`JavaLanguageVersion.of(N)` e
     `id 'org.springframework.boot' version 'X'` en los `build.gradle`, `"next": "X"` en `package.json`)
     y **no menciones Initializr ni crear el proyecto**; si elige otra versión, avisa de `change-version` (paso 5);
   - solo si no hay servicios o proyecto, son las que elegirá al crearlo (por ejemplo, en Spring
     Initializr), así que conviene que estén disponibles allí;
   - `backend.java` es la versión mayor (`26`, no `26.0.1`). La ruta del JDK de tu máquina va en `backend.jdk_ruta_desarrollo`;
     las del nodo de Jenkins y de la imagen, en `devops.*`; todas de la misma versión mayor.
   En back pregunta `backend.jdk_ruta_desarrollo`: propone una sola ruta detectada con la fila permitida del paso 3;
   si hay varias, muestra las diferencias y pide elegir una. Si no hay ninguna, pide la ruta o `null` (no gestionarla).
   Para buscarla, lista solo nombres con `ls -d <carpeta>/*/` en la máquina del desarrollador; no inventes la ruta.
   Con `null` no se escribe ni se modifica `org.gradle.java.installations.paths`. Esta clave existe aunque no uses DevOps.
4. **No preguntes** las claves cuyo comentario dice "no cambiar" (`version_esquema`, `proyecto.stack`,
   `frontend.framework`, `backend.build`, `base_de_datos.motor`): se quedan como en la plantilla.
5. **Opciones** (las claves de `config/opciones.yaml`): ofrece solo sus valores permitidos y, para cada
   uno, su frase de «Si eliges…» de `claves.md`. Por ejemplo, con `devops.infraestructura: ninguna` el
   proyecto no recibe nada de Jenkins ni de Kubernetes.
6. **Requisitos entre opciones:** si `config/requisitos.yaml` dice que un valor exige otro (hoy,
   `gestion_usuarios` distinto de `ninguna` exige `autenticacion: clerk`), díselo al usuario al ofrecer
   ese valor y no aceptes una combinación que lo incumpla.
7. **`integraciones.gestion_usuarios`:** tras decidir `autenticacion` donde exista, explica los tres valores:
   - `ninguna`: sin gestión de usuarios;
   - `organizaciones`: cada perfil pertenece a una organización de Clerk y se invita a ella;
   - `aplicacion`: se invita a la aplicación, sin organizaciones.

   Con `autenticacion: ninguna`, informa `gestion_usuarios: ninguna` y su causa, sin preguntar.
   Con módulo existente conserva el modelo detectado; sin módulo recomienda `ninguna` salvo que lo pida.
   Si activa la gestión, avísale de que debe configurar Clerk con
   registro restringido (solo por invitación), porque sin roles cualquier usuario con sesión puede
   administrar; y de que conviene poner el mismo valor en la base, el back y el front, en ese orden.
   Si elige `ninguna`, dile que puede activarlo más tarde: cambiar el valor en los `stack.yaml`, ejecutar
   `python3 -I -B .agents/actualizar.py --kit <KIT>` (regeneración del paso 1) y lanzar `.agents/workflows/add-user-management.md`, en el orden base → back → front.
8. **`backend.group`** (stack `springboot`): el group de los servicios y la raíz de sus paquetes Java
   (por ejemplo, `com.empresa`). Propón el `group` detectado en los `build.gradle`; si no hay servicios,
   es "hay que decidirlo" y es el Group que pondrá en Spring Initializr. Solo letras, números, `_` y
   puntos: sin guiones.
9. **Nomenclatura** (`nomenclatura.*`): propón lo detectado en el paso 3 y, si no hay nada, el valor
   recomendado del comentario. Conserva los comodines (`{Entidad}`, `{AliasPascal}`, `{nombre}`). Respeta
   los valores permitidos que diga el comentario.
10. **Claves que dependen de otra:** no preguntes una clave que, con lo que ha elegido el usuario, no se
    usa.
    - En el `stack.yaml` de la plantilla, el comentario `requerida_con: <condición>` dice cuándo se usa
      (`=` igual, `!=` distinto, `&&` «y»). Si la condición no se cumple, quita la clave de su
      `stack.yaml`; si la deja, el generador solo avisa «ya no se usa». Hoy: en el back,
      `variables_autenticacion` solo con `autenticacion: clerk` y `gestion_usuarios` distinto de
      `ninguna` (en el front, con `autenticacion: clerk`); `estrategia_fisica_jpa` solo con
      `persistencia: jpa`; y las de los entornos del punto 16.
    - Quita también todas las `devops.*` salvo `devops.infraestructura` con `infraestructura: ninguna`, y las
      claves de Clerk sin Clerk, incluidos issuer general, issuer por entorno y variables de autenticación.
    Díselo al usuario: al activar esa opción, el generador nombrará las claves que deberá volver a añadir.
11. **Credenciales:** `integraciones.variables_autenticacion` y cualquier clave cuyo comentario diga
    "solo NOMBRES" llevan nombres de variables de entorno (`CLERK_SECRET_KEY`), nunca valores. Si una
    respuesta parece un valor (empieza por `sk_`, `pk_` o `whsec_`, contiene `=` o es larga y aleatoria),
    no la escribas y pide el nombre. En el back, con `gestion_usuarios: organizaciones`, ofrece añadir
    `CLERK_DEFAULT_INVITER_USER_ID` (opcional: el invitador por defecto) a la lista de la plantilla.
12. **SonarQube (back y front):** informa que necesita Java ≥ 21 del PATH y pide permiso para ejecutar `cd "<PROYECTO>" && node .agents/scripts/instalar-sonar-mcp.mjs` en el paso 7.6, después de `validate`: descarga el servidor oficial con huella fijada en `~/.dotagentskit` (licencia SONAR Source-Available License v1.0). Comprueba solo que estén definidas `SONARQUBE_URL` y `SONARQUBE_TOKEN`, sin mostrar ni leer sus valores. Si faltan, pide al usuario exportarlas en el entorno de su herramienta. No preguntes el nombre de un MCP de SonarQube ni su URL para `stack.yaml`; el kit no depende de entradas del agente. Si no autoriza instalar, informa el bloqueo y no lo ejecutes. Un `SONARQUBE_MCP_JAR` propio existente y legible permite usar su instalación.
    **Otros nombres de MCP** (`mcp.*`, como el de MySQL): son los nombres registrados por el usuario; pregúntaselos sin leer la configuración de sus herramientas.
13. **`conexiones` (stack `mysql`):** decide si los agentes pueden ejecutar en una base real. Propón `{}`
    (ninguna) y explica que, si añade una conexión, los pasos que ejecutan en la base podrán usarla. Solo
    pon una conexión si el usuario lo pide expresamente.

    Formato de `{}`: va en la misma línea de la clave (`conexiones: {}`, conservando su comentario), y se
    quitan solo las líneas `<nombre>: <esquema>` de debajo y se conservan los comentarios. Un `{}` en una línea propia rompe el formato y el script se
    detiene.
14. **Listas** (`cors_origenes`, `variables_autenticacion`…): con el formato de la plantilla,
    `[valor1, valor2]`.
15. **Open Notebook es obligatorio:** informa que las tareas necesitan su API y modelos configurados; no preguntes si lo tiene funcionando.
    Pregunta por separado `documentacion.url_api`, `documentacion.variable_password` y `documentacion.timeout_chat`,
    explicando cada una con su ficha. Los tres `documentacion.modelo_*` quedan en `null` sin preguntar;
    informa en una línea que existen para fijar modelos más adelante. No leas ni cambies su configuración.
    Si existe `herramientas.documentacion`, quítala: con `ninguna` se bloquea la generación y con
    `open-notebook` avisa «ya no se usa».
    En back quita `sonarqube.project_key_patron` y `devops.jdk_herramienta`; completa `backend.jdk_ruta_desarrollo`; con `jenkins-kubernetes`, también `devops.jenkinsfile` y las tres `devops.nodos.*`.
16. **`devops.infraestructura` y `devops.entornos`** (back): explica la infraestructura con su ficha.
    Si elige `jenkins-kubernetes`:
    Pregunta `devops.jenkinsfile`: propone la ruta detectada por nombres `devops/Jenkinsfile*`; sin archivo, `devops/Jenkinsfile`.
    Si hay varios, pregunta cuál ejecuta; conservar su ruta evita renombrarlo. Cambiarla no renombra ni actualiza el Script Path de Jenkins.
    Para `devops.nodos.*`, pregunta primero «¿todo en un nodo?». Si sí, pregunta una etiqueta y úsala en las tres claves;
    si no, pregunta general, compilacion y docker por separado, proponiendo las etiquetas literales detectadas del pipeline elegido.
    General hace checkout/gates/despliegue/Slack; compilacion hace build/Sonar; docker construye/publica imágenes.
    Si la etapa Docker no encuentra el JAR, vuelve a compilar dentro de su propio nodo y ocupa otro ejecutor; con las tres etiquetas iguales, ese nodo necesita al menos tres ejecutores libres. Es la compilación de reserva.
    Jenkins usa la ruta de `devops.java_home_nodo`; no hace falta configurar un JDK en la administración de Jenkins.
    Pregunta qué entornos quiere (la plantilla trae `development` y `main`)
    y, para cada uno, sus claves en el orden de la
    plantilla. El nombre de la entrada es su carpeta `devops/<nombre>/`. Un entorno solo hace falta si
    construye o despliega: una rama sin entrada sigue compilando y pasando SonarQube. Explica:
    - `rama`: exacta o un prefijo `xxx/*`; dos entornos no pueden coincidir con la misma rama;
    - `imagen`: `construir` (primer entorno: construye y publica), `promover` (entorno posterior:
      reutiliza la imagen probada; exige `desplegar: true`); como máximo uno construye; `ninguna` no forma una combinación válida.
      No ofrezcas una entrada sin acciones; elimínala si solo necesitas compilar y analizar esa rama;
      con `promover`, `desplegar` queda en `true`: infórmalo y no lo preguntes; si otro entorno ya construye, no ofrezcas `construir`.
    - `desplegar`: con `false`, no preguntes réplicas, recursos, puertos, CORS ni issuer: ese entorno no
      tiene manifiestos;
    - `sufijo`: pregúntalo para todos, incluido `development`, con los perfiles detectados del paso 3;
    - `credencial_kubeconfig`: pregunta compartir/separar y los IDs juntos, con la detección del paso 3; si ya
      respondió, no repitas. Sin Jenkinsfile, ofrece los IDs de plantilla y di que debe crearlos en Jenkins.
    - `gateway_nodo_puerto` y `cors_origenes`: solo si hay gateway (`backend.gateway` distinto de `null`);
    - `clerk_issuer_uri`: el de ese entorno, solo con `autenticacion: clerk`.
    - Para `devops.entornos.<e>.cors_origenes` y `devops.entornos.<e>.clerk_issuer_uri`, si ya hay una
      respuesta equivalente confirmada en esta preparación, cita sus valores y la clave de origen:
      `backend.cors_origenes` / `integraciones.clerk_issuer_uri`, o la del entorno declarado antes en
      `devops.entornos`. Si hay varias, usa la del entorno anterior y, si no existe, la local. Explica en una
      línea la diferencia de contexto: la configuración local corresponde al navegador en la máquina del
      usuario; la del entorno corresponde al front desplegado (para Clerk, su issuer de autenticación).
      Como excepción a la regla de respuesta libre, ofrece «reutilizar [valores citados]» junto a la
      respuesta libre solo si se cumplen las condiciones siguientes. CORS requiere una lista no vacía
      de orígenes HTTP/HTTPS sin ruta ni barra final y que ningún origen sea `localhost`, `127.0.0.1`,
      `::1` ni una IP privada, en cualquier entorno con `desplegar: true`, incluido el primero.
      Si alguno lo es, cita los valores y explica que son direcciones locales o privadas que no se
      proponen para el navegador del front desplegado; pide solo respuesta libre. Para Clerk puedes
      ofrecer reutilizar el issuer confirmado si es HTTPS sin barra final, sin marcarlo como recomendado.
      Si los valores no cumplen el formato, pide solo respuesta libre y explica por qué.
      Mantén las condiciones anteriores: solo entornos con `desplegar: true`, CORS solo con gateway e
      issuer solo con `autenticacion: clerk`.
    - Si comparten clúster, avisa del consumo conjunto de réplicas y recursos antes de recomendarlos.
    - Propón `java_home_contenedor` por la carpeta del tar de `jdk_url` bajo `/opt/` y pide confirmación;
      si el nombre no permite saberla, pregunta sin descargar ni inventarla. Para `java_home_nodo`, pregunta
      si `devops.nodos.compilacion` es esta máquina; si lo es, pide la carpeta y lista solo nombres con
      `ls -d <carpeta>/*/`. Si no lo es, avisa de que la ruta no se puede comprobar desde aquí y pídela tal
      como existe en ese nodo (debe incluir `bin/javac`).
    - Pregunta por `devops.credencial_bd_pruebas`: ID de una credencial Jenkins de tipo «Username with
      password» para inyectar usuario y contraseña de la base de pruebas durante el build (recomienda marcar
      *Treat username as secret* para que el usuario no salga en el log), o `null` si no quieres inyectarla.
      Explica que, cuando hay credencial, el nodo de compilación debe definir `DB_HOST_<P>`, `DB_PORT_<P>` y
      `DB_NAME_<P>` (con `<P>` = perfil local en mayúsculas, por defecto `FEATURE`) en el formato que espera
      la URL JDBC de la plantilla del perfil. Sin credencial, el build no inyecta esas variables. Varios
      servicios comparten la misma base de pruebas de ese perfil en el nodo.
    Con `devops.infraestructura: ninguna` puede activarla después: cambiarla, añadir las claves que pida
    el generador y regenerar con `python3 -I -B .agents/actualizar.py --kit <KIT>` (paso 1);
    el siguiente workflow de escritura propone los artefactos con plan aprobado.
    Si el `stack.yaml` del usuario tiene `devops.rama_despliegue` y `devops.entorno`, propón convertirlos
    en una entrada de `devops.entornos` y pregúntale por los demás entornos.

17. **`herramientas.codebase_memory`:** `true` exige la CLI `codebase-memory-mcp` instalada; pregunta si la tiene. Si no, propón `false` o este comando para instalar solo el binario, sin ejecutarlo:
    `curl -fsSL https://raw.githubusercontent.com/DeusData/codebase-memory-mcp/main/install.sh | bash -s -- --skip-config`. El índice es local: se crea una vez por cada copia del repositorio (clon o worktree).
18. **`api_error.campo_codigo`** (back y front): antes de preguntar, muestra el ejemplo de `claves.md`, un
    cuerpo de error con y sin código, y para qué sirve; sin manejador, su respuesta define el contrato desde ahora. Recomienda `null` salvo que su API ya publique un
    código de negocio; se puede activar después.
19. **`integraciones.autenticacion`:** si elige `ninguna`, dile que puede activarla más tarde: cambiar a
    `clerk` en `stack.yaml`, regenerar con `python3 -I -B .agents/actualizar.py --kit <KIT>`
    (paso 1) y lanzar `.agents/workflows/add-authentication.md`
    (back y front). Si su gateway ya tiene seguridad, ese workflow solo informa y no la toca.

20. **(solo front) `herramientas.agent_browser`:** pregunta si quiere verificar la feature en el navegador después de la prueba de humo y si tiene preparada la CLI agent-browser y su navegador. Si no quiere o no tiene la CLI, usa `false`; no instales nada. Con `true`, el preflight comprueba la CLI y su diagnóstico local. La app debe apuntar a una API de desarrollo. Con Clerk, la instancia de desarrollo necesita el Test mode y el código por correo; los pasos únicos para preparar el usuario de prueba están en el apartado «Usuario de prueba de Clerk» del manual (no los repitas; indícale dónde están); con la protección contra bots activa, el paso queda `bloqueado` con la acción para el usuario.

## Paso 5 — Revisar con el usuario

1. Enseña el `stack.yaml` completo y una tabla de cambios frente a la plantilla: clave, antes, después y
   motivo, incluido cada `null` y cada clave quitada.
2. Comprueba que no haya credenciales ni valores de plantilla sin confirmar. La comprobación de formato
   completo la hace la simulación del paso 7.1; no declares que valida antes de ejecutarla.
3. Si no puedes confirmar que mostraste el bloque de alguna clave de la tabla (por ejemplo, porque la
   sesión se compactó), muestra su **En resumen:** y su **Qué pasa si está mal:** antes de pedir el sí;
   no vuelvas a preguntarla salvo que el usuario quiera cambiarla.
4. Si eligió versiones distintas de las detectadas, explica que necesitará `.agents/workflows/change-version.md` para alinear el
   código o que el usuario ajuste `stack.yaml`. Conserva este aviso también en el cierre.
5. **Espera un sí explícito.** Si pide cambios, aplícalos y vuelve a enseñarlo.

## Paso 6 — Escribir los dos archivos

1. **`<PROYECTO>/.agents/stack.yaml`:** parte de la plantilla; cambia los valores y quita o añade solo las
   claves y entradas del paso 4: sin uso, `conexiones`, entornos, `CLERK_DEFAULT_INVITER_USER_ID` y
   `herramientas.documentacion`. Conserva el orden y los comentarios de las demás líneas; nunca credenciales.
2. **`<PROYECTO>/.agents/actualizar.py`:** copia `<SOURCES>/actualizar.py` **añadiendo esta línea como
   segunda línea**, justo debajo de `#!/usr/bin/env python3`:

   ```
   # generado automáticamente; no editar aquí: los cambios se hacen en el repositorio de origen (sources)
   ```

   Así la copia es idéntica a la que generará el script, y en la primera ejecución no preguntará si
   sobrescribirse. Comprueba con `diff <SOURCES>/actualizar.py <PROYECTO>/.agents/actualizar.py` que la
   única diferencia es esa línea añadida tras la línea 1.

No crees ningún otro archivo.

## Paso 7 — Generar el `.agents`

En los pasos 7 y 8, cada orden con ruta relativa se ejecuta con `cd "<PROYECTO>" && <orden>` en la
misma llamada: sustituye `<PROYECTO>` por la ruta absoluta entre comillas. No uses un `pwd` aparte.
Las únicas órdenes que escriben en estos pasos son la generación con `--si` de 7.3 y la instalación
sin `--comprobar` de 7.6. Ejecuta cada una una vez; antes de repetirla por cualquier motivo, comprueba
su estado sin escribir, como se indica en esos puntos.

1. Ejecuta la simulación: valida el `stack.yaml` completo antes de generar y no escribe.
   Sin `--simular`, el generador no simula: sin acciones pendientes reescribe `.agents/.generado.json`
   sin preguntar. La simulación siempre lleva `--simular`.
   Resume su salida con estos comandos; conserva las salidas y fallos para el reporte final:

   ```bash
   cd "<PROYECTO>" && python3 -I -B .agents/actualizar.py --kit <KIT> --simular 2>&1 | grep -E '^(crear|modificar|borrar): ' | cut -d: -f1 | sort | uniq -c
   cd "<PROYECTO>" && python3 -I -B .agents/actualizar.py --kit <KIT> --simular 2>&1 | grep -E '^(falta en tu stack.yaml|ya no se usa|BLOCKED|ERROR|crearía)'
   ```

   Enséñale cuántos archivos crea, modifica y borra, y las líneas del segundo comando: avisos de claves,
   bloqueos y la nota de `rules/project.md`. Si el primer comando no devuelve nada y el segundo tampoco,
   ejecuta para mostrar las últimas 20 líneas:

   ```bash
   cd "<PROYECTO>" && python3 -I -B .agents/actualizar.py --kit <KIT> --simular 2>&1 | tail -n 20
   ```

2. Si hay un `BLOCKED` o un aviso, explícaselo, corrige con él `stack.yaml` (vuelve al paso 5) y repite la
   simulación. No sigas con avisos sin resolver.
3. Pídele un **"sí" explícito** para generar. Con el sí, ejecuta una vez:

   ```bash
   cd "<PROYECTO>" && python3 -I -B .agents/actualizar.py --kit <KIT> --si
   ```

   `--si` responde a la confirmación del script; en la primera generación no hay archivos editados a mano
   que pueda sobrescribir. La prohibición de `--si` se refiere solo al estado inicial del paso 1:
   si allí ya existía un `.agents` generado, esta guía se detiene; no lo fuerces.
   Si no sabes si la generación con `--si` llegó a ejecutarse (sesión compactada, herramienta cortada u
   orden fallida), no la relances: ejecuta la simulación de 7.1 y comprueba si existe el registro:

   ```bash
   cd "<PROYECTO>" && if test -f .agents/.generado.json; then printf 'registro presente\n'; else printf 'registro ausente\n'; fi
   ```

   - Sin `crear:`/`modificar:`/`borrar:` y con `.agents/.generado.json` presente, la generación está hecha:
     sigue con 7.5. Si se perdió la salida, aplica 7.4 y decláralo también en el reporte; no repitas la
     generación para recuperarla. La lista de variables la verá el usuario la próxima vez que regenere.
   - Con acciones pendientes, la generación está a medias: enséñalas, resuelve los avisos según 7.2,
     pide otro «sí» explícito y ejecuta 7.3 una vez.
   - Si falló porque el directorio no era `<PROYECTO>` (por ejemplo, «No such file» de la ruta del
     generador), ejecútala una vez con el `cd` correcto. Si escribió algo en otro directorio, informa
     la ruta y no lo borres.
   Estas comprobaciones prevalecen sobre el paso 1: un `.agents/.generado.json` creado por 7.3 durante
   esta guía no es un `.agents` previo. No afectan a la repetición legítima tras un `BLOCKED` de 7.5.
4. Enséñale la lista final de **variables de entorno** que imprime el script: solo nombres y si están
   "definida" o "no definida" en tu terminal, que puede no ser la suya. El script nunca muestra valores;
   tú tampoco los pidas. Si su salida se perdió, di «la salida de `--si` no está disponible» y basa el
   reporte en el siguiente recuento, la simulación y `validate`, sin inferir variables ni acciones perdidas:

   ```bash
   cd "<PROYECTO>" && find .agents -type f | wc -l
   ```

5. Ejecuta `validate` para enseñar los avisos que la simulación no muestra, como `PERFIL_LOCAL` y `JDK_STACK`.
   La simulación ya comprobó el formato completo; no repitas una lista de reglas en esta guía.

   | Stack | Comando |
   |---|---|
   | `springboot`, `nextjs` | `cd "<PROYECTO>" && node .agents/scripts/stack.mjs validate` |
   | `mysql` | `cd "<PROYECTO>" && python3 -B -E .agents/scripts/stack.py validate` |

   Si devuelve `BLOCKED`, corrige `stack.yaml`, repite 7.1–7.2, pide otro «sí» y ejecuta el comando de 7.3.
   Esta repetición pertenece a la generación iniciada por la guía; valida de nuevo y repite hasta que pase.
6. Solo en back y front, si el usuario autorizó la instalación del MCP de Sonar en el paso 4, ítem 12,
   ejecútala una vez después de `validate`:

   ```bash
   cd "<PROYECTO>" && node .agents/scripts/instalar-sonar-mcp.mjs
   ```

   Antes de repetirla por cualquier motivo, comprueba su estado sin escribir:

   ```bash
   cd "<PROYECTO>" && node .agents/scripts/instalar-sonar-mcp.mjs --comprobar
   ```

   Con `OK`, no la repitas. Si no da `OK`, informa el diagnóstico antes de reintentar la instalación
   autorizada. Sin autorización no instales; conserva el bloqueo en el reporte.

## Paso 8 — Reporte y siguientes pasos

El reporte final se basa solo en salidas mostradas, citando el comando de cada afirmación:

- de `cd "<PROYECTO>" && python3 -I -B .agents/actualizar.py --kit <KIT> --si` (paso 7): archivos creados, modificados
  y borrados, agrupados por tipo, opciones activas y variables definida/no definida, nunca valores;
  si se perdió esa salida, di «la salida de `--si` no está disponible» y usa el recuento de 7.4,
  la simulación y `validate`; no relances la generación ni presentes ese recuento como archivos creados;
- de `validate` (paso 7.5): resultado literal y todos sus avisos; no ocultes comandos fallidos;
- de la instalación autorizada del MCP de Sonar (paso 7.6), si aplica: resultado y bloqueos;
- en back, de `cd "<PROYECTO>" && python3 -I -B .agents/scripts/servicios.py listar`: servicios sin puerto o context-path,
  con su remedio en un plan de `.agents/workflows/incorporate-service.md`; usa la detección permitida para justificar omisiones;
- en back, de `cd "<PROYECTO>" && python3 -I -B .agents/scripts/servicios.py nombres`: muestra por servicio la clave Sonar y su origen para compararla con SonarQube;
  prioridad: systemProp del servicio, propiedad literal del build, group:nombre, o nombre; si no es determinable, muestra el motivo.
  Una propiedad fuera del repositorio puede cambiar la clave efectiva y este cálculo no la ve; no consultes SonarQube durante la guía.
  Si trae `sonarqube.project_key_patron` o `devops.jdk_herramienta`, indica quitarlas; las nuevas claves obligatorias bloquean hasta completarlas.
- de `cd "<PROYECTO>" && git status --short`: qué falta confirmar o ignorar, por ejemplo `logs/` sin ignorar.
No escribas «no existe X» sin un comando mostrado que lo respalde. Ante ausencia o conexión fallida
inesperada, comprueba la ruta exacta con `ls -la <ruta>`, solo dentro de `<PROYECTO>` o `<KIT>`, nunca sobre `account/`, `.env*`, secretos ni kubeconfig; sospecha del aislamiento de la herramienta y pide
repetir el comando fuera de él antes de pedir que arranque un servicio. No uses la red durante esta guía.

El reporte incluye siempre la siguiente lista en este orden, indicando qué condiciones se cumplen y
por qué. Antes de los prompts, explica en ese mismo reporte cómo lanzar los workflows: abre una
**sesión nueva** de tu IA en la raíz del proyecto. El agente lee `AGENTS.md` al empezar: abre otra sesión
después de preparar, fusionar o cambiar de rama. Crea antes una rama `feature/*` si trabajas por ramas
y pega el prompt del paso correspondiente. Las tareas de cambios presentan un plan y esperan tu
aprobación antes de escribir; codebase-memory conserva su recorrido de indexación, sin plan de cambios propio.

El reporte incluye, en el mismo mensaje que la lista, el texto completo de cada prompt aplicable,
cada uno en su bloque de código; nombrar el workflow no basta. Los prompts aplicables son, en lista
cerrada, los de los ítems 2 a 5 cuyo condicional se cumple, y los dos de adoptar/refactorizar de su
stack cuando el proyecto tiene código, marcados como opcionales. El ítem 1 (`preparar-proyecto.sh`)
es una orden para el usuario, no un prompt. En el ítem 4 entrega solo la variante que corresponde.
Los `[…]` y `<…>` de las plantillas de esta guía son instrucciones para ti: sustitúyelos, corchetes y
signos angulares incluidos, por los datos reales obtenidos en la preparación; el texto final no contiene
`[`, `]`, `<` ni `>` de marcador. No inventes un dato que falte: si no salió de la preparación, no
entregues ese prompt, di qué dato falta y cómo obtenerlo.

1. El usuario ejecuta `cd "<PROYECTO>" && bash .agents/scripts/preparar-proyecto.sh`, revisa y hace commit; la IA no lo ejecuta en esta guía:
   `chore: preparar el proyecto para .agents`. Los workflows requieren Git con árbol limpio: si falta
   repositorio o primer commit, lo prepara el usuario, nunca tú. Explica lo pendiente según `cd "<PROYECTO>" && git status --short`.
2. Si las versiones elegidas difieren del código detectado, ejecutar `.agents/workflows/change-version.md`
   (back, front y SQL según corresponda) antes de los workflows generales; o que el usuario ajuste `stack.yaml`.
   `change-version` carga su propia documentación: su entrada no bloquea por documentación faltante del catálogo.
   El prompt identifica las tecnologías cuyas versiones de `stack.yaml` difieren del código, con
   «detectada → elegida». El workflow propone BOM, trenes y plugins y el usuario los aprueba; el prompt
   no fija sus versiones.
   Prompt: «Sigue `.agents/workflows/change-version.md` para alinear el código con las versiones de
   `stack.yaml` que difieren [tecnología: detectada → elegida] en [servicios o rutas reales]. No edites
   `stack.yaml`; si hiciera falta cambiarlo, dilo y espera al usuario. El workflow propone BOM, trenes y
   plugins y yo los apruebo. Presenta el plan y espera mi aprobación antes de escribir».
3. Si `herramientas.codebase_memory` es `true`, ejecutar `.agents/workflows/codebase-memory.md` para crear el grafo antes de `preparar-documentacion`; sin grafo, el cierre de `preparar-documentacion` bloquea con `GRAFO`.
   Prompt: «Sigue `.agents/workflows/codebase-memory.md` para crear o actualizar el grafo de este proyecto desde su raíz».
4. Ejecutar `.agents/workflows/preparar-documentacion.md` después del commit y, si aplica, del grafo:
   propone URL oficiales, las carga con aprobación y comprueba versión y citas; servicios con igual versión
   comparten documentación. Si avisa de una librería fuera de catálogo, usar allí «Ampliar el catálogo del
   proyecto», nunca editarlo a mano. Si aplica el paso 2, `change-version` ya carga y asocia la documentación
   de las versiones que cambia; `preparar-documentacion` se sigue ejecutando para el cotejo global,
   el preflight de cierre y para completar lo que falte, reutilizando lo cargado.
   Si aplica el paso 2 y `change-version` no terminó, ejecútalo primero.
   Si aplica el paso 2, prompt: «Sigue `.agents/workflows/preparar-documentacion.md` para completar la
   documentación que falte según su diagnóstico, con las versiones que tenga ahora el código; reutiliza lo ya
   cargado. Muéstrame las fuentes y su revisión y espera mi aprobación antes de cargarlas o asociarlas».
   Sin el paso 2, prompt: «Sigue `.agents/workflows/preparar-documentacion.md` para preparar documentación de
   [tecnologías y versiones reales]. Muéstrame las fuentes y su revisión y espera mi aprobación antes de
   cargarlas o asociarlas».
   Ningún prompt del cierre enumera versiones de BOM, trenes ni plugins que dependan de otras elegidas;
   `preparar-documentacion` las obtiene de su diagnóstico.
5. Resto según el caso:
   - Back sin servicios: leer `.agents/skills/service-creator/references/servicio-initializr.md` y dar los
     valores reales obtenidos con `cd "<PROYECTO>" && node .agents/scripts/stack.mjs get <clave>`, incluidas las coordenadas
     de dependencias ya filtradas. El usuario trae el servicio desde Initializr y lo pega en la raíz;
     después usa `.agents/workflows/incorporate-service.md`. Los siguientes puede pedirlos a la IA o traerlos del mismo modo.
   - Proyectos con código (back con servicios, front existente o SQL con objetos): presenta solo los dos prompts de su stack que figuran abajo; son opcionales y el usuario decide si los usa.
   - Front sin Next.js: el usuario crea el proyecto con la versión elegida y su gestor (por ejemplo,
     `create-next-app` de esa versión con TypeScript), instala las precondiciones de `.agents/workflows/bootstrap-project.md` y
     luego lanza ese workflow. No crees el proyecto ni instales nada durante esta guía.
   - Con gestión de usuarios: `.agents/workflows/add-user-management.md` en orden SQL → back → front; Clerk con registro
     restringido por invitación.
   - Back con `devops.infraestructura: jenkins-kubernetes`: si falta `devops/` o el archivo declarado
     en `devops.jenkinsfile`, ofrece generar el Jenkinsfile y los manifiestos mediante
     `.agents/workflows/implement-microservice-feature.md` y `devops-engineer` en modo generar, con plan
     aprobado para todos los servicios y el gateway y sus entornos. `DEVOPS_ESTADO` informa de lo pendiente;
     no autoriza escrituras. Nunca restaures `devops/` ni `devops/*/account/` desde el historial de git.
     Prompt: «Sigue `.agents/workflows/implement-microservice-feature.md` para generar [ruta declarada del Jenkinsfile]
     y los manifiestos que faltan para [lista real de servicios y gateway] con sus entornos declarados.
     Usa `devops-engineer` en modo generar, enumera cada artefacto en el plan y espera mi aprobación antes
     de escribir. Genera desde las plantillas; nunca restaures `devops/` ni `devops/*/account/` desde el historial de git».
     Remite además al usuario a `<KIT>/manual-usuario.md`, apartado «DevOps y Jenkins»:
     quitar shallow clone, crear
     credenciales con los IDs acordados, merge sin squash/rebase hacia promover e imagen nueva antes del
     primer despliegue de ese entorno. Tú no ejecutas Jenkins.

Prompt: adoptar (back)
```text
Quiero alinear con el .agents de la raíz de este proyecto estos servicios que ya existen, uno por uno, con .agents/workflows/incorporate-service.md y un plan aprobado para cada servicio:
- <ruta exacta del servicio 1>
- <ruta exacta del servicio 2>
Si el workflow no reconoce el servicio, detente y dímelo; no lo fuerces. No reorganices el código de negocio. Al terminar cada servicio, espera a que yo haga commit antes del siguiente.
```

Prompt: refactorizar (back)
```text
Quiero refactorizar estos servicios con .agents/workflows/implement-microservice-feature.md; compáralos con .agents/rules/architecture-rules.md:
- <ruta exacta del servicio 1>
- <ruta exacta del servicio 2>
Propón un plan sin cambiar el comportamiento y espera mi aprobación; si afecta varios servicios, presenta primero el plan maestro.
```

Prompt: adoptar (front)
```text
Quiero revisar con el .agents de la raíz de este proyecto estos módulos que ya existen: compara su configuración y núcleo con stack.yaml y las reglas; no ejecutes bootstrap-project sobre el proyecto existente:
- <ruta del módulo 1>
- <ruta del módulo 2>
No hay workflow de adopción general: presenta diferencias y propón qué peticiones lanzar después con implement-feature, sin escribir cambios; espera mi decisión.
```

Prompt: refactorizar (front)
```text
Quiero refactorizar estos módulos con .agents/workflows/implement-feature.md; compáralos con .agents/rules/architecture-rules.md:
- <ruta del módulo 1>
- <ruta del módulo 2>
Propón un plan para adaptar carpetas y capas sin cambiar el comportamiento y espera mi aprobación antes de escribir.
```

Prompt: adoptar (sql)
```text
Quiero revisar con el .agents de la raíz de este proyecto estos objetos que ya existen: compara sus notebooks permitidos con stack.yaml y .agents/rules/architecture-rules.md, excluyendo datos de prueba antes de abrirlos:
- <objeto y notebook 1>
- <objeto y notebook 2>
No hay workflow de adopción dedicado: presenta diferencias y un plan, sin persistir ni ejecutar SQL; espera mi decisión.
```

Prompt: refactorizar (sql)
```text
Quiero refactorizar estos objetos con .agents/workflows/build-database-feature.md; compáralos con .agents/rules/architecture-rules.md y excluye los datos de prueba antes de leer:
- <objeto y notebook 1>
- <objeto y notebook 2>
Propón un plan sin cambiar el comportamiento, las firmas ni el esquema y espera mi aprobación antes de aplicar cambios.
```

La explicación de claves queda en `.agents/config/claves.md`; revisa `.agents/rules/project.md` con secciones
«por completar» solo si su creación aparece en la salida. Para cambiar una clave después, sigue su ficha:
solo opciones y nomenclatura exigen regeneración por configuración; otras pueden requerir un workflow.
Por ejemplo, `documentacion.timeout_chat` se lee al usarlo; `backend.lombok` exige regenerar; Slack necesita un plan para `Jenkinsfile`.
El usuario regenera con `cd "<PROYECTO>" && python3 -I -B .agents/actualizar.py --kit <KIT>` y relanza el workflow.
La tarea pregunta sí/no/para revisión por diferencias: sí propone corregir en su plan; no conserva
la diferencia recordada en una línea; para revisión la recuerda ofreciendo aplicarla. Se guarda por valor
y servicio en `docs/decisiones-stack.md`, según el glosario; la comprobación previa solo informa.
En SQL algunos workflows consultan `SELECT VERSION()` antes del preflight; esta guía no consulta la base.
Para cambiar versiones después, usa `.agents/workflows/change-version.md` en los tres stacks; en back alinea versiones
compartidas entre servicios. Ese workflow prepara documentación de destino y cierra con los pendientes
para el usuario, incluido commit y preflight. No necesita `.agents/workflows/preparar-documentacion.md` por adelantado.

Al cerrar, remite al usuario al apartado «Trabajar con los workflows» de `<KIT>/manual-usuario.md`.
