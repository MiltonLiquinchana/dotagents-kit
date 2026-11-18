# Claves de `stack.yaml`

**Palabras que usan estas fichas**

- **`.agents`:** carpeta con las instrucciones y la configuración que usa el agente para trabajar en tu proyecto.
- **Plantilla:** archivo de ejemplo del que se parte para preparar instrucciones o proponer código adaptado al proyecto.
- **Generador:** programa `actualizar.py` que lee tus decisiones de `stack.yaml` y prepara `.agents` con las plantillas correspondientes.
- **Tarea o workflow:** instrucciones para un trabajo concreto, por ejemplo cambiar una versión o preparar documentación.
- **Plan aprobado:** propuesta de archivos y cambios que te enseña el agente y que solo aplica después de recibir tu sí.
- **Validador:** programa que comprueba que `stack.yaml` contiene las claves y los valores permitidos.
- **Comprobación previa (preflight):** revisión de una tarea que informa qué falta, qué difiere y qué impide continuar.
- **Registro `docs/decisiones-stack.md`:** si tu código no coincide con `stack.yaml`, la tarea te pregunta si quieres corregirlo en su plan (sí), conservar esa diferencia (no) o dejarla para revisión. Tu respuesta se guarda para ese valor y ese servicio: el no se recuerda en una línea sin volver a proponerlo; para revisión se recuerda con la opción de aplicarla.
- **Regenerar:** actualizar las instrucciones con `python3 -I -B .agents/actualizar.py --kit <KIT>`; sustituye `<KIT>` por la ruta del repositorio de plantillas. No cambia el código de tu aplicación.
- **Preparación del proyecto:** trabajo de `preparar-proyecto.sh`: crea archivos auxiliares que faltan y prepara exclusiones; lo ejecutas tú o lo autorizas expresamente.
- **Open Notebook:** aplicación que guarda las fuentes de documentación y permite consultar información de las versiones del proyecto con citas comprobables.
- **MCP:** conexión que permite al agente usar herramientas de un servidor externo, por ejemplo análisis de código o consultas de base de datos.
- **API:** rutas y operaciones que un programa ofrece a otro para intercambiar datos; por ejemplo, consultar pedidos.
- **Respaldo:** archivos que justifican lo explicado en una ficha; sus rutas son relativas al `.agents` generado.
- **URL:** dirección de un recurso o servidor, por ejemplo la API de documentación; no es una contraseña.
- **HTTP y HTTPS:** protocolos para comunicarse con una dirección web; HTTPS cifra esa comunicación.
- **Sandbox:** base de datos desechable y aislada para probar SQL sin usar tu base real.
- **Notebook (`.dbcnb`):** archivo que agrupa SQL en celdas; por ejemplo, tablas o pruebas.
- **Commit:** versión guardada de tus archivos en Git.
- **Rama:** línea de trabajo de Git, por ejemplo `development` o `feature/pedidos`.

Estas fichas explican tus decisiones de `stack.yaml`. Los ejemplos se adaptan a tu proyecto. Las alternativas siguen visibles y las claves sin uso se ocultan según tus opciones.

## version_esquema

**En resumen:** Identifica el formato de `stack.yaml`; déjalo como viene en el `stack.yaml` de ejemplo (`1`).

**Dónde se ve en tu proyecto:** Solo aparece en `stack.yaml`, por ejemplo `version_esquema: 1`. No es la versión de tu aplicación. El validador exige que exista la clave; cambiar el número no convierte un archivo de otro formato.

**Respaldo:** `scripts/stack.py`.

## proyecto.nombre

**En resumen:** Da una etiqueta reconocible a tu proyecto, por ejemplo `pedidos-sql`.

**Dónde se ve en tu proyecto:** En `stack.yaml`, por ejemplo `nombre: pedidos-sql`. Es una etiqueta para reconocer tu proyecto, no una orden para renombrar carpetas, paquetes o servicios.

**Para qué se usa:**
- El validador exige que exista la clave al revisar la configuración.
- Permite identificar el proyecto al leer su configuración; el nombre del código se decide en sus archivos.

**Qué pasa si está mal:** Si falta, el validador impide continuar. Una etiqueta equivocada puede confundirte al revisar la configuración, aunque no renombre tu aplicación.

**Cambiarla después:** Edita `stack.yaml`; no requiere regenerar ni ejecutar otra tarea por esta etiqueta.

**Si conservas el dato confirmado (por ejemplo, `pedidos-sql`):** Por ejemplo, reconoces este proyecto como `pedidos-sql` cuando revisas `stack.yaml`. Recomendado: un nombre que identifique el proyecto que ya tienes; confirma el detectado antes de usarlo.

**Respaldo:** `scripts/stack.py`.

## proyecto.stack

**En resumen:** Identifica el tipo de proyecto al que pertenece este `.agents`; conserva `mysql`.

**Dónde se ve en tu proyecto:** En `stack.yaml`, por ejemplo `stack: mysql`. El generador elige sus plantillas con este dato y el validador rechaza otro tipo de proyecto. Cambiarlo no transforma la tecnología del código existente.

**Respaldo:** `actualizar.py`; `scripts/stack.py`.

## base_de_datos.motor

**En resumen:** Identifica MySQL como el motor de base de datos admitido; conserva `mysql`.

**Dónde se ve en tu proyecto:** En `stack.yaml`, por ejemplo `motor: mysql`. Las instrucciones y las pruebas del sandbox usan ese motor; cambiar el texto no adapta el SQL a otro. La comprobación previa rechaza otro motor. Junto con la versión fija la imagen del sandbox, por ejemplo `mysql:8.4.2`.

**Respaldo:** `scripts/stack.py`; `scripts/preflight_stack.py`; `scripts/sql-sandbox.py`.

## base_de_datos.version

**En resumen:** Fija la versión de MySQL para la que se escribe y documenta tu SQL.

**Dónde se ve en tu proyecto:** Por ejemplo, `version: 8.4.2` corresponde a la versión que comunica quien administra tu servidor o devuelve `SELECT VERSION()`.

**Para qué se usa:**
- Antes de algunas tareas el agente pregunta al servidor su versión mediante `SELECT VERSION()` y avisa si no coincide; sin conexión informa que no pudo comprobarla.
- La comparación usa la precisión declarada: `8.4` acepta cualquier `8.4.x`; `8.4.2` compara los tres números. Si difiere del servidor, la tarea ofrece alinear documentación, sandbox y SQL con la versión declarada en su plan, conservar la diferencia o dejarla para revisión.

**Qué pasa si está mal:** Un SQL escrito para otra versión puede fallar en el servidor. La variable de entorno `SQL_SANDBOX_IMAGE`, si la defines, sustituye la imagen indicada por esta clave; el sandbox avisa si su servidor no coincide. Elegir una imagen no actualiza el servidor real.

**Cambiarla después:** Edita `stack.yaml` y usa la tarea `change-version` (prepara documentación, sandbox y revisión de objetos con un plan aprobado). Después de cambiarla, esa tarea te pedirá regenerar; hazlo cuando te lo pida. El servidor real lo actualizas tú.

**Si conservas la versión de tu servidor (`8.4.2`):** Por ejemplo, pedidos declara `8.4.2` porque es la versión confirmada del servidor y usa la imagen `mysql:8.4.2`. Recomendado: la versión real del servidor para probar y documentar la misma revisión.

**Si eliges `8.4`:** Por ejemplo, la imagen `mysql:8.4` puede probar una revisión 8.4 más nueva que la de tu servidor; la comparación acepta cualquier `8.4.x`. Conviene si quieres seguir la serie y asumes esa diferencia de revisión.

**Si eliges `9.5.0`:** Por ejemplo, el sandbox de pedidos usa `mysql:9.5.0`, el valor de la plantilla. Conviene si empiezas sin servidor y has elegido esa versión para tu proyecto.

**Respaldo:** `scripts/stack.py`; `scripts/registro_detectores.py`; `scripts/sql-sandbox.py`; `workflows/change-version.md`.

## base_de_datos.nombre

**En resumen:** Nombra el esquema, el grupo de tablas y otros objetos de tu proyecto dentro del servidor MySQL.

**Dónde se ve en tu proyecto:** Por ejemplo, `nombre: PedidosDB` corresponde a `USE PedidosDB;` en el SQL aprobado. No es el nombre del servidor MCP ni el nombre de una conexión.

**Para qué se usa:**
- La revisión SQL comprueba el esquema de los objetos que controla. El sandbox prepara ese esquema si el SQL no lo crea.
- Las propuestas del módulo de perfiles y el índice de notebooks usan ese nombre para identificar el destino.

**Qué pasa si está mal:** Otro nombre puede dirigir el SQL a un esquema equivocado o hacer que la revisión lo rechace. Declararlo no selecciona ni crea una conexión a una base real.

**Cambiarla después:** Edita `stack.yaml`, sin regenerar por esta clave. Para migrar SQL o referencias existentes pide la tarea `build-database-feature` (propone cambios SQL y espera tu aprobación). El cambio de nombre no mueve tablas ni datos por sí solo.

**Si conservas el dato confirmado (por ejemplo, `PedidosDB`):** Por ejemplo, el SQL de pedidos utiliza `USE PedidosDB;` y el sandbox prepara ese esquema. Recomendado: conserva el nombre confirmado del esquema del proyecto para evitar apuntar a otro; sin uno previo, acuerda el nombre antes de crear objetos.

**Respaldo:** `scripts/sqlnb.py`; `scripts/sql-lint.py`; `scripts/sql-sandbox.py`.

<!-- si integraciones.gestion_usuarios=organizaciones|aplicacion -->
**Respaldo adicional:** scripts/render-perfiles.py.

<!-- fin -->
## base_de_datos.carpeta_notebooks

**En resumen:** Indica en qué carpeta del proyecto se guardan los notebooks SQL.

**Dónde se ve en tu proyecto:** Por ejemplo, `carpeta_notebooks: sql` ubica un archivo de tablas en `sql/PedidosTablas.dbcnb`. Es una carpeta relativa a la raíz, no el nombre de un archivo.

**Para qué se usa:**
- Los programas de índice, edición y revisión encuentran los notebooks bajo esa ruta.
- Si falta la carpeta, la comprobación previa avisa; al guardar el primer objeto aprobado puede crearse.

**Qué pasa si está mal:** Una ruta equivocada puede hacer que parezca que faltan objetos o llevar una escritura a otro lugar. Regenerar no mueve los notebooks.

**Cambiarla después:** Edita `stack.yaml`, sin regenerar. Si quieres trasladar archivos existentes, pide la tarea `build-database-feature` (propone cambios SQL y espera tu aprobación) con un plan aprobado que enumere sus rutas de origen y destino.

**Si conservas el dato confirmado (por ejemplo, `sql`):** Por ejemplo, los archivos de pedidos se guardan bajo `sql/`. Recomendado: conserva la carpeta detectada de tu proyecto, porque así las tareas encuentran los archivos existentes; sin carpeta, acuerda una ruta relativa.

**Respaldo:** `scripts/sqlnb.py`; `scripts/nb-edit.py`; `scripts/preflight_stack.py`.

## notebooks.tablas

**En resumen:** Nombra el notebook destinado a tablas.

**Dónde se ve en tu proyecto:** Por ejemplo, `PedidosTablas.dbcnb` se ubica bajo `base_de_datos.carpeta_notebooks`; si esa carpeta es `sql`, la ruta es `sql/PedidosTablas.dbcnb`.

**Para qué se usa:**
- Los programas usan este nombre para localizar el archivo de ese tipo y ordenar la carga del sandbox.
- `nb-edit.py upsert` sin `--book` elige este notebook por el tipo del objeto. Si falta el archivo, al guardar contenido aprobado se crea dentro de la carpeta de notebooks; generar `.agents` no lo crea.

**Qué pasa si está mal:** Otro nombre puede clasificar o guardar contenido en el archivo incorrecto. Que un archivo aún no exista no demuestra que sus objetos o pruebas se hayan ejecutado.

**Cambiarla después:** Edita `stack.yaml`, sin regenerar. Si el archivo ya existe y quieres renombrarlo, pide la tarea `build-database-feature` (propone cambios SQL y espera tu aprobación) y aprueba el movimiento; cambiar el nombre configurado no mueve el archivo.

**Si conservas el dato confirmado (por ejemplo, `PedidosTablas.dbcnb`):** Por ejemplo, una tabla de pedidos se localiza en `PedidosTablas.dbcnb`. Recomendado: conserva el archivo confirmado para ese tipo de contenido y evita mezclar objetos o pruebas en otro; el ejemplo no sustituye tu nombre real.

**Respaldo:** `scripts/sqlnb.py`; `scripts/nb-edit.py`; `workflows/references/full-route-db.md`.

## notebooks.procedimientos

**En resumen:** Nombra el notebook destinado a procedimientos almacenados.

**Dónde se ve en tu proyecto:** Por ejemplo, `PedidosProcedimientos.dbcnb` se ubica bajo `base_de_datos.carpeta_notebooks`; si esa carpeta es `sql`, la ruta es `sql/PedidosProcedimientos.dbcnb`.

**Para qué se usa:**
- Los programas usan este nombre para localizar el archivo de ese tipo y ordenar la carga del sandbox.
- `nb-edit.py upsert` sin `--book` elige este notebook por el tipo del objeto. Si falta el archivo, al guardar contenido aprobado se crea dentro de la carpeta de notebooks; generar `.agents` no lo crea.

**Qué pasa si está mal:** Otro nombre puede clasificar o guardar contenido en el archivo incorrecto. Que un archivo aún no exista no demuestra que sus objetos o pruebas se hayan ejecutado.

**Cambiarla después:** Edita `stack.yaml`, sin regenerar. Si el archivo ya existe y quieres renombrarlo, pide la tarea `build-database-feature` (propone cambios SQL y espera tu aprobación) y aprueba el movimiento; cambiar el nombre configurado no mueve el archivo.

**Si conservas el dato confirmado (por ejemplo, `PedidosProcedimientos.dbcnb`):** Por ejemplo, un procedimiento que lista pedidos se localiza en `PedidosProcedimientos.dbcnb`. Recomendado: conserva el archivo confirmado para ese tipo de contenido y evita mezclar objetos o pruebas en otro; el ejemplo no sustituye tu nombre real.

**Respaldo:** `scripts/sqlnb.py`; `scripts/nb-edit.py`; `workflows/references/full-route-db.md`.

## notebooks.funciones

**En resumen:** Nombra el notebook destinado a funciones.

**Dónde se ve en tu proyecto:** Por ejemplo, `PedidosFunciones.dbcnb` se ubica bajo `base_de_datos.carpeta_notebooks`; si esa carpeta es `sql`, la ruta es `sql/PedidosFunciones.dbcnb`.

**Para qué se usa:**
- Los programas usan este nombre para localizar el archivo de ese tipo y ordenar la carga del sandbox.
- `nb-edit.py upsert` sin `--book` elige este notebook por el tipo del objeto. Si falta el archivo, al guardar contenido aprobado se crea dentro de la carpeta de notebooks; generar `.agents` no lo crea.

**Qué pasa si está mal:** Otro nombre puede clasificar o guardar contenido en el archivo incorrecto. Que un archivo aún no exista no demuestra que sus objetos o pruebas se hayan ejecutado.

**Cambiarla después:** Edita `stack.yaml`, sin regenerar. Si el archivo ya existe y quieres renombrarlo, pide la tarea `build-database-feature` (propone cambios SQL y espera tu aprobación) y aprueba el movimiento; cambiar el nombre configurado no mueve el archivo.

**Si conservas el dato confirmado (por ejemplo, `PedidosFunciones.dbcnb`):** Por ejemplo, una función que calcula el total del pedido se localiza en `PedidosFunciones.dbcnb`. Recomendado: conserva el archivo confirmado para ese tipo de contenido y evita mezclar objetos o pruebas en otro; el ejemplo no sustituye tu nombre real.

**Respaldo:** `scripts/sqlnb.py`; `scripts/nb-edit.py`; `workflows/references/full-route-db.md`.

## notebooks.vistas

**En resumen:** Nombra el notebook destinado a vistas.

**Dónde se ve en tu proyecto:** Por ejemplo, `PedidosVistas.dbcnb` se ubica bajo `base_de_datos.carpeta_notebooks`; si esa carpeta es `sql`, la ruta es `sql/PedidosVistas.dbcnb`.

**Para qué se usa:**
- Los programas usan este nombre para localizar el archivo de ese tipo y ordenar la carga del sandbox.
- `nb-edit.py upsert` sin `--book` elige este notebook por el tipo del objeto. Si falta el archivo, al guardar contenido aprobado se crea dentro de la carpeta de notebooks; generar `.agents` no lo crea.

**Qué pasa si está mal:** Otro nombre puede clasificar o guardar contenido en el archivo incorrecto. Que un archivo aún no exista no demuestra que sus objetos o pruebas se hayan ejecutado.

**Cambiarla después:** Edita `stack.yaml`, sin regenerar. Si el archivo ya existe y quieres renombrarlo, pide la tarea `build-database-feature` (propone cambios SQL y espera tu aprobación) y aprueba el movimiento; cambiar el nombre configurado no mueve el archivo.

**Si conservas el dato confirmado (por ejemplo, `PedidosVistas.dbcnb`):** Por ejemplo, una vista de pedidos pendientes se localiza en `PedidosVistas.dbcnb`. Recomendado: conserva el archivo confirmado para ese tipo de contenido y evita mezclar objetos o pruebas en otro; el ejemplo no sustituye tu nombre real.

**Respaldo:** `scripts/sqlnb.py`; `scripts/nb-edit.py`; `workflows/references/full-route-db.md`.

## notebooks.triggers

**En resumen:** Nombra el notebook destinado a triggers, acciones automáticas ante cambios de una tabla.

**Dónde se ve en tu proyecto:** Por ejemplo, `PedidosTriggers.dbcnb` se ubica bajo `base_de_datos.carpeta_notebooks`; si esa carpeta es `sql`, la ruta es `sql/PedidosTriggers.dbcnb`.

**Para qué se usa:**
- Los programas usan este nombre para localizar el archivo de ese tipo y ordenar la carga del sandbox.
- `nb-edit.py upsert` sin `--book` elige este notebook por el tipo del objeto. Si falta el archivo, al guardar contenido aprobado se crea dentro de la carpeta de notebooks; generar `.agents` no lo crea.

**Qué pasa si está mal:** Otro nombre puede clasificar o guardar contenido en el archivo incorrecto. Que un archivo aún no exista no demuestra que sus objetos o pruebas se hayan ejecutado.

**Cambiarla después:** Edita `stack.yaml`, sin regenerar. Si el archivo ya existe y quieres renombrarlo, pide la tarea `build-database-feature` (propone cambios SQL y espera tu aprobación) y aprueba el movimiento; cambiar el nombre configurado no mueve el archivo.

**Si conservas el dato confirmado (por ejemplo, `PedidosTriggers.dbcnb`):** Por ejemplo, un trigger de pedidos se localiza en `PedidosTriggers.dbcnb`. Recomendado: conserva el archivo confirmado para ese tipo de contenido y evita mezclar objetos o pruebas en otro; el ejemplo no sustituye tu nombre real.

**Respaldo:** `scripts/sqlnb.py`; `scripts/nb-edit.py`; `workflows/references/full-route-db.md`.

## notebooks.eventos

**En resumen:** Nombra el notebook destinado a eventos, tareas programadas por MySQL.

**Dónde se ve en tu proyecto:** Por ejemplo, `PedidosEventos.dbcnb` se ubica bajo `base_de_datos.carpeta_notebooks`; si esa carpeta es `sql`, la ruta es `sql/PedidosEventos.dbcnb`.

**Para qué se usa:**
- Los programas usan este nombre para localizar el archivo de ese tipo y ordenar la carga del sandbox.
- `nb-edit.py upsert` sin `--book` elige este notebook por el tipo del objeto. Si falta el archivo, al guardar contenido aprobado se crea dentro de la carpeta de notebooks; generar `.agents` no lo crea.

**Qué pasa si está mal:** Otro nombre puede clasificar o guardar contenido en el archivo incorrecto. Que un archivo aún no exista no demuestra que sus objetos o pruebas se hayan ejecutado.

**Cambiarla después:** Edita `stack.yaml`, sin regenerar. Si el archivo ya existe y quieres renombrarlo, pide la tarea `build-database-feature` (propone cambios SQL y espera tu aprobación) y aprueba el movimiento; cambiar el nombre configurado no mueve el archivo.

**Si conservas el dato confirmado (por ejemplo, `PedidosEventos.dbcnb`):** Por ejemplo, un evento programado de pedidos se localiza en `PedidosEventos.dbcnb`. Recomendado: conserva el archivo confirmado para ese tipo de contenido y evita mezclar objetos o pruebas en otro; el ejemplo no sustituye tu nombre real.

**Respaldo:** `scripts/sqlnb.py`; `scripts/nb-edit.py`; `workflows/references/full-route-db.md`.

## notebooks.datos_prueba

**En resumen:** Nombra el notebook de datos de prueba que cargan los programas del sandbox; el agente nunca abre su contenido.

**Dónde se ve en tu proyecto:** Por ejemplo, `SemillasPrueba.dbcnb` se ubica bajo `base_de_datos.carpeta_notebooks`; si esa carpeta es `sql`, la ruta es `sql/SemillasPrueba.dbcnb`.

**Para qué se usa:**
- Identifica los datos sintéticos que los programas del sandbox cargan después de los objetos y antes de las pruebas.
- Los detectores excluyen ese archivo y sus alias del índice de revisión; el agente solo trata su nombre, aunque los datos sean sintéticos.

**Qué pasa si está mal:** Un nombre equivocado deja al sandbox sin los datos de prueba previstos. La restricción de lectura se refiere a quién abre el archivo, no a que esos datos deban ser personales o secretos.

**Cambiarla después:** Edita `stack.yaml`, sin regenerar. Si el archivo ya existe y quieres renombrarlo, pide la tarea `build-database-feature` (propone cambios SQL y espera tu aprobación) y aprueba el movimiento; cambiar el nombre configurado no mueve el archivo.

**Si conservas el dato confirmado (por ejemplo, `SemillasPrueba.dbcnb`):** Por ejemplo, los datos sintéticos que usan las pruebas de pedidos se localizan en `SemillasPrueba.dbcnb`. Recomendado: conserva el archivo confirmado para ese tipo de contenido y evita mezclar objetos o pruebas en otro; el ejemplo no sustituye tu nombre real.

**Respaldo:** `scripts/sqlnb.py`; `scripts/nb-edit.py`; `scripts/sql-sandbox.py`.

## notebooks.pruebas_procedimientos

**En resumen:** Nombra el notebook destinado a pruebas de procedimientos.

**Dónde se ve en tu proyecto:** Por ejemplo, `PruebasProcedimientos.dbcnb` se ubica bajo `base_de_datos.carpeta_notebooks`; si esa carpeta es `sql`, la ruta es `sql/PruebasProcedimientos.dbcnb`.

**Para qué se usa:**
- Los programas usan este nombre para localizar el archivo de ese tipo y ordenar la carga del sandbox.
- La edición exige indicar el libro con `--book`; guardar contenido aprobado crea el archivo si falta. La generación de `.agents` no lo crea.

**Qué pasa si está mal:** Otro nombre puede clasificar o guardar contenido en el archivo incorrecto. Que un archivo aún no exista no demuestra que sus objetos o pruebas se hayan ejecutado.

**Cambiarla después:** Edita `stack.yaml`, sin regenerar. Si el archivo ya existe y quieres renombrarlo, pide la tarea `build-database-feature` (propone cambios SQL y espera tu aprobación) y aprueba el movimiento; cambiar el nombre configurado no mueve el archivo.

**Si conservas el dato confirmado (por ejemplo, `PruebasProcedimientos.dbcnb`):** Por ejemplo, una prueba del listado de pedidos se localiza en `PruebasProcedimientos.dbcnb`. Recomendado: conserva el archivo confirmado para ese tipo de contenido y evita mezclar objetos o pruebas en otro; el ejemplo no sustituye tu nombre real.

**Respaldo:** `scripts/sqlnb.py`; `scripts/nb-edit.py`; `workflows/references/full-route-db.md`.

## notebooks.pruebas_funciones

**En resumen:** Nombra el notebook destinado a pruebas de funciones.

**Dónde se ve en tu proyecto:** Por ejemplo, `PruebasFunciones.dbcnb` se ubica bajo `base_de_datos.carpeta_notebooks`; si esa carpeta es `sql`, la ruta es `sql/PruebasFunciones.dbcnb`.

**Para qué se usa:**
- Los programas usan este nombre para localizar el archivo de ese tipo y ordenar la carga del sandbox.
- La edición exige indicar el libro con `--book`; guardar contenido aprobado crea el archivo si falta. La generación de `.agents` no lo crea.

**Qué pasa si está mal:** Otro nombre puede clasificar o guardar contenido en el archivo incorrecto. Que un archivo aún no exista no demuestra que sus objetos o pruebas se hayan ejecutado.

**Cambiarla después:** Edita `stack.yaml`, sin regenerar. Si el archivo ya existe y quieres renombrarlo, pide la tarea `build-database-feature` (propone cambios SQL y espera tu aprobación) y aprueba el movimiento; cambiar el nombre configurado no mueve el archivo.

**Si conservas el dato confirmado (por ejemplo, `PruebasFunciones.dbcnb`):** Por ejemplo, una prueba del total de pedidos se localiza en `PruebasFunciones.dbcnb`. Recomendado: conserva el archivo confirmado para ese tipo de contenido y evita mezclar objetos o pruebas en otro; el ejemplo no sustituye tu nombre real.

**Respaldo:** `scripts/sqlnb.py`; `scripts/nb-edit.py`; `workflows/references/full-route-db.md`.

## notebooks.pruebas_vistas

**En resumen:** Nombra el notebook destinado a pruebas de vistas.

**Dónde se ve en tu proyecto:** Por ejemplo, `PruebasVistas.dbcnb` se ubica bajo `base_de_datos.carpeta_notebooks`; si esa carpeta es `sql`, la ruta es `sql/PruebasVistas.dbcnb`.

**Para qué se usa:**
- Los programas usan este nombre para localizar el archivo de ese tipo y ordenar la carga del sandbox.
- La edición exige indicar el libro con `--book`; guardar contenido aprobado crea el archivo si falta. La generación de `.agents` no lo crea.

**Qué pasa si está mal:** Otro nombre puede clasificar o guardar contenido en el archivo incorrecto. Que un archivo aún no exista no demuestra que sus objetos o pruebas se hayan ejecutado.

**Cambiarla después:** Edita `stack.yaml`, sin regenerar. Si el archivo ya existe y quieres renombrarlo, pide la tarea `build-database-feature` (propone cambios SQL y espera tu aprobación) y aprueba el movimiento; cambiar el nombre configurado no mueve el archivo.

**Si conservas el dato confirmado (por ejemplo, `PruebasVistas.dbcnb`):** Por ejemplo, una prueba de pedidos pendientes se localiza en `PruebasVistas.dbcnb`. Recomendado: conserva el archivo confirmado para ese tipo de contenido y evita mezclar objetos o pruebas en otro; el ejemplo no sustituye tu nombre real.

**Respaldo:** `scripts/sqlnb.py`; `scripts/nb-edit.py`; `workflows/references/full-route-db.md`.

## notebooks.pruebas_triggers

**En resumen:** Nombra el notebook destinado a pruebas de triggers.

**Dónde se ve en tu proyecto:** Por ejemplo, `PruebasTriggers.dbcnb` se ubica bajo `base_de_datos.carpeta_notebooks`; si esa carpeta es `sql`, la ruta es `sql/PruebasTriggers.dbcnb`.

**Para qué se usa:**
- Los programas usan este nombre para localizar el archivo de ese tipo y ordenar la carga del sandbox.
- La edición exige indicar el libro con `--book`; guardar contenido aprobado crea el archivo si falta. La generación de `.agents` no lo crea.

**Qué pasa si está mal:** Otro nombre puede clasificar o guardar contenido en el archivo incorrecto. Que un archivo aún no exista no demuestra que sus objetos o pruebas se hayan ejecutado.

**Cambiarla después:** Edita `stack.yaml`, sin regenerar. Si el archivo ya existe y quieres renombrarlo, pide la tarea `build-database-feature` (propone cambios SQL y espera tu aprobación) y aprueba el movimiento; cambiar el nombre configurado no mueve el archivo.

**Si conservas el dato confirmado (por ejemplo, `PruebasTriggers.dbcnb`):** Por ejemplo, una prueba de la acción automática de pedidos se localiza en `PruebasTriggers.dbcnb`. Recomendado: conserva el archivo confirmado para ese tipo de contenido y evita mezclar objetos o pruebas en otro; el ejemplo no sustituye tu nombre real.

**Respaldo:** `scripts/sqlnb.py`; `scripts/nb-edit.py`; `workflows/references/full-route-db.md`.

## notebooks.pruebas_eventos

**En resumen:** Nombra el notebook destinado a pruebas de eventos.

**Dónde se ve en tu proyecto:** Por ejemplo, `PruebasEventos.dbcnb` se ubica bajo `base_de_datos.carpeta_notebooks`; si esa carpeta es `sql`, la ruta es `sql/PruebasEventos.dbcnb`.

**Para qué se usa:**
- Los programas usan este nombre para localizar el archivo de ese tipo y ordenar la carga del sandbox.
- La edición exige indicar el libro con `--book`; guardar contenido aprobado crea el archivo si falta. La generación de `.agents` no lo crea.

**Qué pasa si está mal:** Otro nombre puede clasificar o guardar contenido en el archivo incorrecto. Que un archivo aún no exista no demuestra que sus objetos o pruebas se hayan ejecutado.

**Cambiarla después:** Edita `stack.yaml`, sin regenerar. Si el archivo ya existe y quieres renombrarlo, pide la tarea `build-database-feature` (propone cambios SQL y espera tu aprobación) y aprueba el movimiento; cambiar el nombre configurado no mueve el archivo.

**Si conservas el dato confirmado (por ejemplo, `PruebasEventos.dbcnb`):** Por ejemplo, una prueba de la tarea programada de pedidos se localiza en `PruebasEventos.dbcnb`. Recomendado: conserva el archivo confirmado para ese tipo de contenido y evita mezclar objetos o pruebas en otro; el ejemplo no sustituye tu nombre real.

**Respaldo:** `scripts/sqlnb.py`; `scripts/nb-edit.py`; `workflows/references/full-route-db.md`.

## mcp.base_de_datos

**En resumen:** Nombra el servidor MCP donde configuraste las conexiones permitidas a tu base real.

**Dónde se ve en tu proyecto:** En `stack.yaml`, por ejemplo `base_de_datos: datos`. MCP permite usar herramientas externas: `datos` identifica el servidor, mientras `conexiones` enumera los nombres de conexión y los esquemas.

**Para qué se usa:**
- La tarea busca las herramientas de ese servidor y elige solo un destino declarado en `conexiones`.
- Antes de trabajar con una conexión real se comprueba su acceso en lectura, sin crear la conexión por escribir su nombre.

**Qué pasa si está mal:** Si el nombre del servidor MCP es incorrecto, la tarea no encuentra las herramientas de lectura para las conexiones que declaraste. Confirma ese nombre en tu herramienta; no es el nombre de una conexión ni del esquema.

**Cambiarla después:** Edita `stack.yaml`; no requiere regenerar. Con `conexiones: {}` no se llama a una base real. Confirma los nombres tú, sin entregar la configuración privada del servidor.

**Si conservas el dato confirmado (por ejemplo, `datos`):** Por ejemplo, las conexiones autorizadas de pedidos se buscan en el servidor `datos`. Recomendado: el nombre con que lo registraste; el nombre del esquema no sirve para identificar ese servidor.

**Respaldo:** `workflows/build-database-feature.md`; `workflows/change-version.md`; `scripts/stack.py`.

## conexiones.{nombre}

**En resumen:** Enumera las conexiones a bases reales que permites usar, con su nombre público y esquema.

**Dónde se ve en tu proyecto:** Por ejemplo, dentro de `conexiones`, `pedidos_pruebas: PedidosDB` identifica una conexión configurada en tu servidor MCP. No es una URL ni una contraseña.

**Para qué se usa:**
- Una entrada selecciona ese destino; con varias, se pregunta cuál usar. No se usa otra conexión expuesta por MCP que no hayas declarado.
- Una conexión declarada que falla detiene el primer paso de la tarea `build-database-feature` (prepara cambios SQL con un plan aprobado). Con `{}` continúa sin llamar a una base real.

**Qué pasa si está mal:** Un nombre o esquema incorrecto impide identificar el destino. Con `{}` la tarea continúa con notebooks y sandbox: solo se detienen, con aviso, los pasos que requieren base real. Una conexión declarada que falla sí detiene `build-database-feature`; `change-version` puede continuar sin conocer la versión real.

**Cambiarla después:** Edita `stack.yaml`, sin regenerar. Configura tú la conexión fuera de este archivo. Declarar nombres no crea conexiones ni sustituye los permisos de la tarea.

**Si conservas el dato confirmado (por ejemplo, `conexiones: {}`):** Por ejemplo, trabajas con notebooks y sandbox de pedidos sin acceder a `PedidosDB`: no se leen la versión real ni las tablas del servidor. Solo los pasos que necesitan esa base se detienen e informan. Recomendado: es la opción propuesta al preparar un proyecto sin necesidad de base real, porque evita autorizar accesos innecesarios.

**Si declaras una sola conexión (`pedidos_pruebas: PedidosDB`):** Por ejemplo, esa conexión de pedidos se usa y se identifica en el plan aprobado. Conviene si solo autorizas ese destino y no necesitas elegir entre varios.

**Si declaras varias conexiones:** Por ejemplo, declaras pedidos de pruebas y de revisión, y la tarea pregunta cuál utilizar. Conviene si necesitas ambos destinos y quieres decidir cada ejecución.

**Respaldo:** `workflows/build-database-feature.md`; `workflows/change-version.md`; `scripts/stack.py`.

## herramientas.codebase_memory

**En resumen:** Decide si el agente usa Codebase Memory para relacionar archivos y símbolos del código mediante su CLI.

**Dónde se ve en tu proyecto:** Se declara en `stack.yaml`. El índice vive en la caché local de CBM, no en el repositorio; cada máquina lo crea una vez. `.cbmignore` acompaña a `.agents/` y excluye `knowledge-base/` y `.agents/`.

**Para qué se usa:**
- El preflight comprueba la CLI `codebase-memory-mcp` y el índice real del proyecto; si el índice existe, lo reindexa en la entrada para incorporar los cambios. En el cierre solo comprueba su estado.
- Las consultas del código y sus actualizaciones se condicionan a esta clave. Las decisiones documentadas en `knowledge-base/` se consultan con `tgrep`.

**Qué pasa si está mal:** Si falta la CLI, informa `HERRAMIENTA`; si falta el proyecto o el índice no está listo, informa `GRAFO`. Un índice vacío, degradado al indexar o que no se pudo actualizar produce `GRAFO_AVISO`. El tratamiento depende del workflow según el catálogo de códigos. La falta de preparación de `.cbmignore` se informa como `PREPARACION`. Desactivar la clave omite el grafo y conserva los demás controles.

**Cambiarla después:** Edita `stack.yaml`; esta clave no requiere regenerar. Al activarla, usa la tarea `codebase-memory` para indexar el proyecto antes de `preparar-documentacion`. La clave antigua `herramientas.graphify` sigue aceptándose como alias cuando falta la nueva; si existen ambas, gana `herramientas.codebase_memory`. Renombra la antigua para retirar el aviso de validación.

**Si conservas lo detectado en tu código (por ejemplo, `false`):** Trabajas en pedidos sin preparar el índice. Mantén la decisión y las herramientas del proyecto; activar el grafo añade su preparación y sus controles.

**Si eliges `true`:** Consultas las relaciones del código de pedidos en el índice local. La plantilla de este stack usa `false`: los notebooks `.dbcnb` no quedan cubiertos por CBM. Los objetos se consultan con `db-index.py` y el MCP de lectura existente; CBM solo complementa el SQL fuera de notebooks.

**Respaldo:** `.agents/scripts/codebase-memory.py`; `.agents/scripts/preflight.py`; `.agents/rules/codebase-memory.md`; `.agents/workflows/codebase-memory.md`; `.agents/scripts/stack.py`.

## git.rama_base

**En resumen:** Elige desde qué punto de Git quieres revisar los cambios de tu tarea.

**Dónde se ve en tu proyecto:** En `stack.yaml`, por ejemplo `rama_base: development`, si creaste `feature/pedidos` desde esa rama. No aparece en el código de tu aplicación.

**Para qué se usa:**
- La comprobación previa lee esta decisión, pero no la transmite automáticamente al análisis de cambios.
- El análisis admite una base explícita con `--base`; sin ella compara con el último commit de la rama actual.

**Qué pasa si está mal:** Escribir una rama aquí no basta para que el análisis compare con ella. Si pasas una referencia inexistente al comando, este no puede calcular los cambios esperados.

**Cambiarla después:** Edita `stack.yaml`, sin regenerar. Para cambiar la comparación efectiva, pide que el comando de análisis reciba la referencia mediante `--base`; el valor de esta clave no se propaga solo.

**Si eliges `null`:** Por ejemplo, el análisis sin `--base` revisa los cambios de pedidos que aún no están en un commit. Recomendado si dejas que el agente haga los cambios y tú haces el commit al final.

**Si eliges `development`:** Por ejemplo, declaras tu intención de comparar `feature/pedidos` con `development`; en este stack hay que pasar también `--base development` al análisis. Conviene si haces commits intermedios y necesitas revisarlos.

**Respaldo:** `scripts/preflight.py`; `scripts/touched-objects.py`; `scripts/sql-lint.py`.

## nomenclatura.tablas

**En resumen:** Elige cómo se escriben los nombres de tablas.

**Dónde se ve en tu proyecto:** Por ejemplo, `DetallesPedido` aparece en `CREATE TABLE` del notebook correspondiente. El estilo de letras es independiente del singular o plural de las tablas.

**Para qué se usa:**
- Las propuestas SQL usan esa convención; la propuesta de perfiles también adapta sus nombres.
- Si difiere `nomenclatura.tablas` del código, la tarea te ofrece corregir tablas en su plan, conservar la diferencia o dejarla para revisión.
- La propuesta de perfiles adapta estos nombres y sus referencias y los registra en el contrato; no renombra el esquema existente.

**Qué pasa si está mal:** Un estilo no admitido detiene el validador. Mezclar convenciones puede dejar referencias difíciles de mantener; cambiar esta clave no renombra lo existente.

**Cambiarla después:** Edita `stack.yaml` y regenera. Para adaptar objetos existentes usa la tarea `build-database-feature` (propone cambios SQL y espera tu aprobación); el plan aprobado debe contemplar también las referencias que cambian.

**Si conservas lo detectado en tu código (por ejemplo, `snake_case`):** Por ejemplo, pedidos usa `detalles_pedido`, en minúsculas con guiones bajos. Recomendado: mantén la convención del esquema existente para no renombrar sus objetos, columnas o firmas sin necesidad.

**Si eliges `PascalCase`:** Por ejemplo, pedidos usa `DetallesPedido`, con cada palabra empezando en mayúscula. Conviene si empiezas sin nombres previos: la plantilla propone `PascalCase`.

**Si eliges `camelCase`:** Por ejemplo, pedidos usa `detallesPedido`, empezando en minúscula y con mayúsculas en las palabras siguientes. Conviene si quieres cambiar a esta convención, con los nombres concretos del ejemplo y sus referencias en el plan aprobado.

**Respaldo:** `scripts/stack.py`; `rules/architecture-rules.md`; `scripts/sql-lint.py`; `scripts/registro_detectores.py`.

## nomenclatura.tablas_plural

**En resumen:** Decide si propones nombres de tablas en plural o singular.

**Dónde se ve en tu proyecto:** Por ejemplo, `CREATE TABLE Pedidos` utiliza plural, mientras `CREATE TABLE Pedido` utiliza singular. No describe cuántas filas contiene la tabla.

**Para qué se usa:**
- El diseño y la propuesta de perfiles usan esa convención antes de aplicar el estilo de letras.
- Si difiere `nomenclatura.tablas_plural` del código, la tarea te ofrece corregir el uso de plurales en su plan, conservar la diferencia o dejarla para revisión.
- La propuesta de perfiles adapta estos nombres y sus referencias y los registra en el contrato; no renombra el esquema existente.

**Qué pasa si está mal:** Otro criterio mezcla convenciones y no cambia automáticamente tablas ni referencias existentes. El validador exige `true` o `false`.

**Cambiarla después:** Edita `stack.yaml` y regenera. Para adaptar objetos existentes usa la tarea `build-database-feature` (propone cambios SQL y espera tu aprobación); el plan aprobado debe contemplar también las referencias que cambian.

**Si conservas lo detectado en tu código (por ejemplo, `false`):** Por ejemplo, la tabla se llama `Pedido`, aunque contenga muchos pedidos. Recomendado: mantén la convención del esquema existente para no renombrar sus objetos, columnas o firmas sin necesidad.

**Si eliges `true`:** Por ejemplo, la tabla de pedidos se llama `Pedidos`. Conviene si empiezas sin nombres previos: la plantilla propone `true`.

**Respaldo:** `scripts/stack.py`; `rules/architecture-rules.md`; `scripts/sql-lint.py`.

<!-- si integraciones.gestion_usuarios=organizaciones|aplicacion -->
**Respaldo adicional:** scripts/render-perfiles.py.

<!-- fin -->
## nomenclatura.columnas

**En resumen:** Elige cómo se escriben los nombres de columnas.

**Dónde se ve en tu proyecto:** Por ejemplo, `FechaCreacion` aparece en la definición de una columna del notebook correspondiente. El estilo de letras es independiente del singular o plural de las tablas.

**Para qué se usa:**
- Las propuestas SQL usan esa convención; la propuesta de perfiles también adapta sus nombres.
- Si difiere `nomenclatura.columnas` del código, la tarea te ofrece corregir columnas en su plan, conservar la diferencia o dejarla para revisión.
- La propuesta de perfiles adapta estos nombres y sus referencias y los registra en el contrato; no renombra el esquema existente.

**Qué pasa si está mal:** Un estilo no admitido detiene el validador. Mezclar convenciones puede dejar referencias difíciles de mantener; cambiar esta clave no renombra lo existente.

**Cambiarla después:** Edita `stack.yaml` y regenera. Para adaptar objetos existentes usa la tarea `build-database-feature` (propone cambios SQL y espera tu aprobación); el plan aprobado debe contemplar también las referencias que cambian.

**Si conservas lo detectado en tu código (por ejemplo, `snake_case`):** Por ejemplo, pedidos usa `fecha_creacion`, en minúsculas con guiones bajos. Recomendado: mantén la convención del esquema existente para no renombrar sus objetos, columnas o firmas sin necesidad.

**Si eliges `PascalCase`:** Por ejemplo, pedidos usa `FechaCreacion`, con cada palabra empezando en mayúscula. Conviene si empiezas sin nombres previos: la plantilla propone `PascalCase`.

**Si eliges `camelCase`:** Por ejemplo, pedidos usa `fechaCreacion`, empezando en minúscula y con mayúsculas en las palabras siguientes. Conviene si quieres cambiar a esta convención, con los nombres concretos del ejemplo y sus referencias en el plan aprobado.

**Respaldo:** `scripts/stack.py`; `rules/architecture-rules.md`; `scripts/sql-lint.py`; `scripts/registro_detectores.py`.

## nomenclatura.clave_primaria

**En resumen:** Da el patrón del nombre de la columna que identifica cada fila de una entidad.

**Dónde se ve en tu proyecto:** Por ejemplo, `{Entidad}Id` produce `PedidoId` para pedidos; después se aplica el estilo de columnas, por ejemplo `pedido_id` si elegiste `snake_case`.

**Para qué se usa:**
- Las propuestas usan el patrón en la clave primaria y sus referencias entre tablas.
- Si difiere `nomenclatura.clave_primaria` del código, la tarea te ofrece corregir el patrón de la clave primaria en su plan, conservar la diferencia o dejarla para revisión.
- La propuesta de perfiles adapta estos nombres y sus referencias y los registra en el contrato; no renombra el esquema existente.

**Qué pasa si está mal:** Si falta `{Entidad}`, el validador se detiene. Un cambio sin adaptar referencias puede dejar relaciones que apunten a columnas con otro nombre.

**Cambiarla después:** Edita `stack.yaml` y regenera. Para adaptar objetos existentes usa la tarea `build-database-feature` (propone cambios SQL y espera tu aprobación); el plan aprobado debe contemplar también las referencias que cambian.

**Si conservas lo detectado en tu código (por ejemplo, `Id{Entidad}`):** Por ejemplo, la columna se propone como `IdPedido` antes de ajustar su estilo. Recomendado: mantén la convención del esquema existente para no renombrar sus objetos, columnas o firmas sin necesidad.

**Si eliges `{Entidad}Id`:** Por ejemplo, la columna identificadora de pedidos se propone como `PedidoId` antes de ajustar su estilo. Conviene si empiezas sin nombres previos: la plantilla propone `{Entidad}Id`.

**Respaldo:** `scripts/stack.py`; `rules/architecture-rules.md`; `scripts/sql-lint.py`.

<!-- si integraciones.gestion_usuarios=organizaciones|aplicacion -->
**Respaldo adicional:** scripts/render-perfiles.py.

<!-- fin -->
## nomenclatura.prefijo_procedimiento

**En resumen:** Fija cómo empieza el nombre de cada procedimiento almacenado nuevo.

**Dónde se ve en tu proyecto:** Por ejemplo, `sp_listar_pedidos` aparece en `CREATE PROCEDURE` del notebook correspondiente; el prefijo es la parte inicial del nombre, no un valor guardado en una tabla.

**Para qué se usa:**
- Las instrucciones y las propuestas SQL aplican el prefijo al procedimiento almacenado.
- Si difiere `nomenclatura.prefijo_procedimiento` del código, la tarea te ofrece corregir prefijo procedimiento en su plan, conservar la diferencia o dejarla para revisión.
- La propuesta SQL de perfiles aplica este prefijo y lo conserva en su contrato.

**Qué pasa si está mal:** Un prefijo vacío o con forma inválida de identificador detiene el validador. Cambiarlo sin adaptar nombres y referencias puede dejar llamadas incoherentes.

**Cambiarla después:** Edita `stack.yaml` y regenera. Para adaptar objetos existentes usa la tarea `build-database-feature` (propone cambios SQL y espera tu aprobación); el plan aprobado debe contemplar también las referencias que cambian.

**Si conservas lo detectado en tu código (por ejemplo, `proc_`):** Por ejemplo, pedidos usa `proc_listar_pedidos` para distinguir ese tipo. Recomendado: mantén la convención del esquema existente para no renombrar sus objetos, columnas o firmas sin necesidad.

**Si eliges `sp_`:** Por ejemplo, pedidos usa `sp_listar_pedidos` para ese tipo de nombre. Conviene si empiezas sin nombres previos: la plantilla propone `sp_`.

**Respaldo:** `scripts/stack.py`; `rules/architecture-rules.md`; `scripts/sql-lint.py`; `scripts/registro_detectores.py`.

## nomenclatura.prefijo_funcion

**En resumen:** Fija cómo empieza el nombre de cada función nueva.

**Dónde se ve en tu proyecto:** Por ejemplo, `fn_total_pedido` aparece en `CREATE FUNCTION` del notebook correspondiente; el prefijo es la parte inicial del nombre, no un valor guardado en una tabla.

**Para qué se usa:**
- Las instrucciones y las propuestas SQL aplican el prefijo a la función.
- Si difiere `nomenclatura.prefijo_funcion` del código, la tarea te ofrece corregir prefijo funcion en su plan, conservar la diferencia o dejarla para revisión.

**Qué pasa si está mal:** Un prefijo vacío o con forma inválida de identificador detiene el validador. Cambiarlo sin adaptar nombres y referencias puede dejar llamadas incoherentes.

**Cambiarla después:** Edita `stack.yaml` y regenera. Para adaptar objetos existentes usa la tarea `build-database-feature` (propone cambios SQL y espera tu aprobación); el plan aprobado debe contemplar también las referencias que cambian.

**Si conservas lo detectado en tu código (por ejemplo, `func_`):** Por ejemplo, pedidos usa `func_total_pedido` para distinguir ese tipo. Recomendado: mantén la convención del esquema existente para no renombrar sus objetos, columnas o firmas sin necesidad.

**Si eliges `fn_`:** Por ejemplo, pedidos usa `fn_total_pedido` para ese tipo de nombre. Conviene si empiezas sin nombres previos: la plantilla propone `fn_`.

**Respaldo:** `scripts/stack.py`; `rules/architecture-rules.md`; `scripts/sql-lint.py`; `scripts/registro_detectores.py`.

## nomenclatura.prefijo_vista

**En resumen:** Fija cómo empieza el nombre de cada vista nueva.

**Dónde se ve en tu proyecto:** Por ejemplo, `vw_pedidos_pendientes` aparece en `CREATE VIEW` del notebook correspondiente; el prefijo es la parte inicial del nombre, no un valor guardado en una tabla.

**Para qué se usa:**
- Las instrucciones y las propuestas SQL aplican el prefijo a la vista.
- Si difiere `nomenclatura.prefijo_vista` del código, la tarea te ofrece corregir prefijo vista en su plan, conservar la diferencia o dejarla para revisión.

**Qué pasa si está mal:** Un prefijo vacío o con forma inválida de identificador detiene el validador. Cambiarlo sin adaptar nombres y referencias puede dejar llamadas incoherentes.

**Cambiarla después:** Edita `stack.yaml` y regenera. Para adaptar objetos existentes usa la tarea `build-database-feature` (propone cambios SQL y espera tu aprobación); el plan aprobado debe contemplar también las referencias que cambian.

**Si conservas lo detectado en tu código (por ejemplo, `vista_`):** Por ejemplo, pedidos usa `vista_pedidos_pendientes` para distinguir ese tipo. Recomendado: mantén la convención del esquema existente para no renombrar sus objetos, columnas o firmas sin necesidad.

**Si eliges `vw_`:** Por ejemplo, pedidos usa `vw_pedidos_pendientes` para ese tipo de nombre. Conviene si empiezas sin nombres previos: la plantilla propone `vw_`.

**Respaldo:** `scripts/stack.py`; `rules/architecture-rules.md`; `scripts/sql-lint.py`; `scripts/registro_detectores.py`.

## nomenclatura.prefijo_evento

**En resumen:** Fija cómo empieza el nombre de cada evento programado nuevo.

**Dónde se ve en tu proyecto:** Por ejemplo, `ev_archivar_pedidos` aparece en `CREATE EVENT` del notebook correspondiente; el prefijo es la parte inicial del nombre, no un valor guardado en una tabla.

**Para qué se usa:**
- Las instrucciones y las propuestas SQL aplican el prefijo al evento programado.
- Si difiere `nomenclatura.prefijo_evento` del código, la tarea te ofrece corregir prefijo evento en su plan, conservar la diferencia o dejarla para revisión.
- La revisión de eventos comprueba además las reglas de cambios destructivos, repetición segura y uso de credenciales, sin dar por probadas ejecuciones reales.
- La revisión de eventos comprueba nombres y variables, operaciones destructivas, repetición segura, definidores, credenciales, secretos incrustados y sintaxis de comentarios.

**Qué pasa si está mal:** Un prefijo vacío o con forma inválida de identificador detiene el validador. Cambiarlo sin adaptar nombres y referencias puede dejar llamadas incoherentes.

**Cambiarla después:** Edita `stack.yaml` y regenera. Para adaptar objetos existentes usa la tarea `build-database-feature` (propone cambios SQL y espera tu aprobación); el plan aprobado debe contemplar también las referencias que cambian.

**Si conservas lo detectado en tu código (por ejemplo, `evento_`):** Por ejemplo, pedidos usa `evento_archivar_pedidos` para distinguir ese tipo. Recomendado: mantén la convención del esquema existente para no renombrar sus objetos, columnas o firmas sin necesidad.

**Si eliges `ev_`:** Por ejemplo, pedidos usa `ev_archivar_pedidos` para ese tipo de nombre. Conviene si empiezas sin nombres previos: la plantilla propone `ev_`.

**Respaldo:** `scripts/stack.py`; `rules/architecture-rules.md`; `scripts/sql-lint.py`; `scripts/registro_detectores.py`.

## nomenclatura.prefijo_trigger

**En resumen:** Elige los comienzos de nombre admitidos para los triggers, las acciones automáticas ante cambios de una tabla.

**Dónde se ve en tu proyecto:** Por ejemplo, `CREATE TRIGGER tr_pedidos_actualizar` usa `tr_`; un proyecto también puede tener nombres que empiezan por `trg_`.

**Para qué se usa:**
- La propuesta usa el primer prefijo; la revisión admite todos los declarados en la lista.
- Si difiere `nomenclatura.prefijo_trigger` del código, la tarea te ofrece corregir prefijo trigger en su plan, conservar la diferencia o dejarla para revisión.

**Qué pasa si está mal:** Una lista vacía o un prefijo con forma inválida detiene el validador. Retirar un prefijo admitido puede hacer que nombres existentes aparezcan como diferencias.

**Cambiarla después:** Edita `stack.yaml` y regenera. Para adaptar objetos existentes usa la tarea `build-database-feature` (propone cambios SQL y espera tu aprobación); el plan aprobado debe contemplar también las referencias que cambian.

**Si conservas lo detectado en tu código (por ejemplo, `tr_`):** Por ejemplo, los triggers de pedidos solo se proponen y aceptan con `tr_`. Recomendado: mantén la convención del esquema existente para no renombrar sus objetos, columnas o firmas sin necesidad.

**Si eliges `[tr_, trg_]`:** Por ejemplo, se proponen nombres como `tr_pedidos_actualizar` y también se aceptan los que empiezan por `trg_`. Conviene si empiezas sin nombres previos: la plantilla propone `[tr_, trg_]`.

**Respaldo:** `scripts/stack.py`; `rules/architecture-rules.md`; `scripts/sql-lint.py`.

## nomenclatura.prefijo_indice

**En resumen:** Fija cómo empieza el nombre de cada índice nuevo.

**Dónde se ve en tu proyecto:** Por ejemplo, `idx_pedido_fecha` aparece en `CREATE INDEX` del notebook correspondiente; el prefijo es la parte inicial del nombre, no un valor guardado en una tabla.

**Para qué se usa:**
- Las instrucciones y las propuestas SQL aplican el prefijo al índice.
- Si difiere `nomenclatura.prefijo_indice` del código, la tarea te ofrece corregir prefijo indice en su plan, conservar la diferencia o dejarla para revisión.
- La comprobación previa te avisa de índices cuyos nombres difieren del prefijo acordado; la revisión de cada objeto mantiene sus controles propios.

**Qué pasa si está mal:** Un prefijo vacío o con forma inválida de identificador detiene el validador. Cambiarlo sin adaptar nombres y referencias puede dejar llamadas incoherentes.

**Cambiarla después:** Edita `stack.yaml` y regenera. Para adaptar objetos existentes usa la tarea `build-database-feature` (propone cambios SQL y espera tu aprobación); el plan aprobado debe contemplar también las referencias que cambian.

**Si conservas lo detectado en tu código (por ejemplo, `ix_`):** Por ejemplo, pedidos usa `ix_pedido_fecha` para distinguir ese tipo. Recomendado: mantén la convención del esquema existente para no renombrar sus objetos, columnas o firmas sin necesidad.

**Si eliges `idx_`:** Por ejemplo, pedidos usa `idx_pedido_fecha` para ese tipo de nombre. Conviene si empiezas sin nombres previos: la plantilla propone `idx_`.

**Respaldo:** `scripts/stack.py`; `rules/architecture-rules.md`; `scripts/sql-lint.py`; `scripts/registro_detectores.py`.

## nomenclatura.prefijo_parametro

**En resumen:** Fija cómo empieza el nombre de cada parámetro nuevo.

**Dónde se ve en tu proyecto:** Por ejemplo, `p_pedido_id` aparece en `IN p_pedido_id INT` del notebook correspondiente; el prefijo es la parte inicial del nombre, no un valor guardado en una tabla.

**Para qué se usa:**
- Las instrucciones y las propuestas SQL aplican el prefijo al parámetro.
- Si difiere `nomenclatura.prefijo_parametro` del código, la tarea te ofrece corregir prefijo parametro en su plan, conservar la diferencia o dejarla para revisión.
- La propuesta SQL de perfiles aplica este prefijo y lo conserva en su contrato.

**Qué pasa si está mal:** Un prefijo vacío o con forma inválida de identificador detiene el validador. Cambiarlo sin adaptar nombres y referencias puede dejar llamadas incoherentes.

**Cambiarla después:** Edita `stack.yaml` y regenera. Para adaptar objetos existentes usa la tarea `build-database-feature` (propone cambios SQL y espera tu aprobación); el plan aprobado debe contemplar también las referencias que cambian.

**Si conservas lo detectado en tu código (por ejemplo, `arg_`):** Por ejemplo, pedidos usa `arg_pedido_id` para distinguir ese tipo. Recomendado: mantén la convención del esquema existente para no renombrar sus objetos, columnas o firmas sin necesidad.

**Si eliges `p_`:** Por ejemplo, pedidos usa `p_pedido_id` para ese tipo de nombre. Conviene si empiezas sin nombres previos: la plantilla propone `p_`.

**Respaldo:** `scripts/stack.py`; `rules/architecture-rules.md`; `scripts/sql-lint.py`; `scripts/registro_detectores.py`.

## nomenclatura.prefijo_variable

**En resumen:** Fija cómo empieza el nombre de cada variable local nueva.

**Dónde se ve en tu proyecto:** Por ejemplo, `v_total` aparece en `DECLARE v_total INT` del notebook correspondiente; el prefijo es la parte inicial del nombre, no un valor guardado en una tabla.

**Para qué se usa:**
- Las instrucciones y las propuestas SQL aplican el prefijo a la variable local.
- Si difiere `nomenclatura.prefijo_variable` del código, la tarea te ofrece corregir prefijo variable en su plan, conservar la diferencia o dejarla para revisión.
- La propuesta SQL de perfiles aplica este prefijo y lo conserva en su contrato.

**Qué pasa si está mal:** Un prefijo vacío o con forma inválida de identificador detiene el validador. Cambiarlo sin adaptar nombres y referencias puede dejar llamadas incoherentes.

**Cambiarla después:** Edita `stack.yaml` y regenera. Para adaptar objetos existentes usa la tarea `build-database-feature` (propone cambios SQL y espera tu aprobación); el plan aprobado debe contemplar también las referencias que cambian.

**Si conservas lo detectado en tu código (por ejemplo, `local_`):** Por ejemplo, pedidos usa `local_total` para distinguir ese tipo. Recomendado: mantén la convención del esquema existente para no renombrar sus objetos, columnas o firmas sin necesidad.

**Si eliges `v_`:** Por ejemplo, pedidos usa `v_total` para ese tipo de nombre. Conviene si empiezas sin nombres previos: la plantilla propone `v_`.

**Respaldo:** `scripts/stack.py`; `rules/architecture-rules.md`; `scripts/sql-lint.py`; `scripts/registro_detectores.py`.

## integraciones.gestion_usuarios

**En resumen:** Decide si preparas gestión de perfiles y si cada persona pertenece a una organización.

**Dónde se ve en tu proyecto:** En los perfiles de pedidos: con organizaciones cada persona pertenece a una; sin organizaciones se invita directamente a la aplicación. El SQL prepara las tablas y procedimientos del modelo elegido.

**Para qué se usa:**
- Selecciona las plantillas y la tarea del modelo elegido.
- Si difiere `integraciones.gestion_usuarios` del código, la tarea te ofrece corregir gestion usuarios en su plan, conservar la diferencia o dejarla para revisión.
- Prepara SQL, pruebas y contrato con cuatro estados: pendiente, invitado, activo e inactivo. No exige clave de autenticación SQL. Con organizaciones admite una tabla nueva o una existente aprobada.

**Qué pasa si está mal:** Un modelo distinto del contrato deja al back esperando columnas o relaciones que el SQL no tiene. El SQL no añade permisos por roles; en la integración completa, el back debe restringir invitaciones porque una sesión por sí sola no distingue administradores.

**Cambiarla después:** Edita `stack.yaml` y regenera. Usa la tarea `add-user-management` (prepara perfiles con un plan aprobado). Prepara primero el proyecto SQL, entrega su contrato al back y después lleva el contrato de la API al front. Elegir `ninguna` conserva los datos instalados. Retirarlo exige la tarea `build-database-feature` (propone cambios SQL y espera tu aprobación).

**Si conservas lo detectado en tu código (por ejemplo, `organizaciones`):** Por ejemplo, el SQL de pedidos incluye perfiles, organizaciones y la relación entre ambos. Sin código previo, la plantilla usa `ninguna`. Recomendado: conserva el modelo del contrato instalado para que SQL, API y pantallas sigan intercambiando los mismos datos.

**Si eliges `ninguna`:** Por ejemplo, pedidos no incorpora el módulo de perfiles. Conviene si no hay módulo previo: `ninguna` es la plantilla; elige `organizaciones` para perfiles asociados o `aplicacion` para una lista común.

**Si eliges `aplicacion`:** Por ejemplo, el SQL de pedidos incluye perfiles sin esa relación de organización. Conviene si no hay módulo previo: `ninguna` es la plantilla; elige `organizaciones` para perfiles asociados o `aplicacion` para una lista común.

**Respaldo:** `config/opciones.yaml`; `workflows/add-user-management.md`; `scripts/registro_detectores.py`.

## documentacion.url_api

**En resumen:** Indica dónde está la API de Open Notebook, que aporta la documentación que consultan las tareas.

**Dónde se ve en tu proyecto:** En `stack.yaml`, por ejemplo `url_api: http://127.0.0.1:6060`, si publicaste allí tu instalación. Es la dirección de la API, no la URL de una fuente documental ni una ruta del código.

**Para qué se usa:**
- Mantiene `.agents/documentacion.json` y `.agents/documentacion.md`, con fuentes vinculadas por servicio; comprueba conexión e IDs de documentos sin consultar modelos.
- La tarea `preparar-documentacion` propone fuentes; comprueba su oficialidad por servidor y ruta según `dominios_oficiales`. Apruebas la descarga mediante `propuesta.aprobacion_sha256`; las citas se verifican con el resumen criptográfico del texto extraído.
- Sin documentación activa válida o versión resoluble de una tecnología catalogada, se detiene. Una no catalogada avisa: puedes añadirla mediante «Ampliar el catálogo del proyecto» de esa tarea.

**Qué pasa si está mal:** Una dirección inválida o inaccesible detiene la comprobación. Admite HTTP(S) sin usuario, contraseña, consulta ni fragmento; HTTP fuera del equipo local genera aviso. Si el servicio está arrancado, comprueba también el aislamiento de tu herramienta.

**Cambiarla después:** Edita `stack.yaml`; se lee en cada uso, sin regenerar. Si cambias de instalación, revisa la documentación asociada: cambiar la dirección no transporta tus documentos al otro servidor.

**Si conservas el dato confirmado (por ejemplo, `http://127.0.0.1:6060`):** Por ejemplo, las consultas de documentación de pedidos usan la API que tú publicaste en ese puerto. Recomendado: tu dirección confirmada de Open Notebook; no elijas una dirección solo por aparecer en la plantilla.

**Respaldo:** `scripts/documentacion.py`; `scripts/comprobar-documentacion.py`; `workflows/preparar-documentacion.md`.

## documentacion.variable_password

**En resumen:** Nombra la variable que contiene la contraseña de Open Notebook, sin guardarla en el proyecto.

**Dónde se ve en tu proyecto:** En `stack.yaml`, por ejemplo `variable_password: DOCS_PASSWORD`. Solo se escribe el nombre; tú configuras su contenido fuera de ese archivo.

**Para qué se usa:**
- El cliente de documentación usa esa variable para autenticarse ante Open Notebook.
- Si declaras un nombre y la variable no existe o está vacía, informa de su ausencia antes de consultar; no prueba otras credenciales.

**Qué pasa si está mal:** Una variable ausente, vacía o incorrecta impide autenticarte. Su nombre admite letras, cifras y guion bajo, sin comenzar con cifra; no copies la contraseña en lugar del nombre.

**Cambiarla después:** Edita `stack.yaml`, sin regenerar. Al activar contraseña en el servidor, configura tú la variable y declara su nombre antes de repetir la consulta.

**Si eliges `null`:** Por ejemplo, tu instalación local de documentación de pedidos permite entrar sin contraseña. Al comprobar la conexión, el programa de documentación te avisa si acepta ese acceso. Recomendado: es la opción de la plantilla para una API sin contraseña; no sirve si tu instalación exige autenticación.

**Si eliges `DOCS_PASSWORD`:** Por ejemplo, la API de documentación de pedidos utiliza el contenido de esa variable para comprobar tu acceso. Conviene si tu instalación exige contraseña y has configurado esa variable; comprueba solo si está definida, sin mostrar su valor.

**Respaldo:** `scripts/documentacion.py`.

## documentacion.modelo_chat

**En resumen:** Elige el modelo que responde las preguntas de documentación.

**Dónde se ve en tu proyecto:** Con `modelo_chat: null` se usa el modelo de chat predeterminado de tu Open Notebook. Después puedes editar `stack.yaml`, sin regenerar, con un ID que hayas configurado, por ejemplo `modelo-documental`. Un ID inexistente detiene la consulta. No es una clave del proveedor y no cambia la configuración global del servidor.

**Respaldo:** `scripts/documentacion.py`.

## documentacion.modelo_contexto_grande

**En resumen:** Permite elegir un modelo para una fuente completa que exceda el contexto del chat normal.

**Dónde se ve en tu proyecto:** Con `modelo_contexto_grande: null` no eliges una alternativa especial; si la fuente no cabe, la consulta lo informa. Solo se usa como alternativa por tamaño con un ID explícito; no prueba otros proveedores. Después puedes editar `stack.yaml`, sin regenerar, con un ID que hayas configurado, por ejemplo `modelo-documental`. Un ID inexistente detiene esa alternativa. No es una clave del proveedor y no cambia la configuración global del servidor.

**Respaldo:** `scripts/documentacion.py`.

## documentacion.modelo_transformacion

**En resumen:** Elige el modelo que resume capacidades de una fuente documental.

**Dónde se ve en tu proyecto:** Con `modelo_transformacion: null` se usa el predeterminado de transformaciones de Open Notebook. Después puedes editar `stack.yaml`, sin regenerar, con un ID que hayas configurado, por ejemplo `modelo-documental`. Un ID inexistente detiene la consulta. No es una clave del proveedor y no cambia la configuración global del servidor.

**Respaldo:** `scripts/documentacion.py`.

## documentacion.timeout_chat

**En resumen:** Fija cuántos segundos se espera una respuesta de Open Notebook que necesite un modelo.

**Dónde se ve en tu proyecto:** En `stack.yaml`, por ejemplo `timeout_chat: 120` permite esperar hasta dos minutos; un modelo ejecutado en tu equipo puede necesitar más tiempo.

**Para qué se usa:**
- Limita preguntas, resúmenes y comprobaciones de búsqueda por significado: se busca texto relacionado, aunque no use las mismas palabras.
- Ask es una consulta que hace varias llamadas internas al modelo y dispone del triple. La comprobación previa de conexión usa cinco segundos por lectura y no cambia con esta clave.
- Las demás peticiones esperan `30` segundos; los trabajos asíncronos, `180`. Tras cargar un documento se comprueba su índice de búsqueda cada `5` segundos hasta `600`, sin volver a indexarlo.

**Qué pasa si está mal:** El validador exige un entero entre `1` y `3600`. `MODELO_TIMEOUT` significa respuesta no recibida a tiempo; `MODELO_FALLO`, error del servidor al responder, con su código HTTP y sin mostrar el cuerpo. No se reintenta ni se cambia de modelo por esos fallos.

**Cambiarla después:** Edita `stack.yaml`, sin regenerar. Esperar más no arregla una API inaccesible ni un proveedor caído; el procesamiento de documentos recién cargados tiene su propio plazo.

**Si eliges `120`:** Por ejemplo, esperas dos minutos por una respuesta sobre pedidos y hasta seis por Ask. Recomendado: es la espera de la plantilla para empezar con un límite razonable.

**Si eliges `240`:** Por ejemplo, das cuatro minutos a un modelo lento y hasta doce a Ask. Conviene si has observado respuestas que necesitan esa espera adicional, no un fallo de conexión.

**Respaldo:** `scripts/documentacion.py`; `scripts/stack.py`.
