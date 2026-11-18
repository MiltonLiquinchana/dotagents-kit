# Decisiones sobre código existente

Antes de aprobar el plan, conserva los recordatorios y avisos del registro obtenidos por el preflight o por `python3 -I -B .agents/scripts/registro-stack.py comprobar`. Cuando conozcas los servicios de la tarea, ejecuta la comprobación de solo lectura con `--servicios` y el nombre de tu workflow mediante `--workflow` para precisar el alcance. Para un cambio pendiente sin decisión vigente, ofrece «sí» (incluirlo en este plan), «no» (registrar esa decisión y recordarla en una línea) y «para revisión» (recordar clave y servicios con opción de aplicarlo después). Ofrece `--completo` si el usuario pide más detalle. Una decisión «no» vigente no se vuelve a proponer. Especifica en el plan el valor canónico, los servicios explícitos, la respuesta, la modificación del registro y, si procede, los archivos de código. Escribe el registro solo tras aprobar el plan; al verificar lo aplicado guarda «aplicado» y conserva la decisión anterior como «sustituido». Los avisos ajenos al alcance de tu workflow se muestran como pendientes; no autorizan reparaciones. Si una fila es inválida, propone corregirla en vez de duplicarla.

El registro vive en `docs/decisiones-stack.md`, versionado fuera de `.agents`; no lo escribe el preflight ni el generador. Inclúyelo en la lista de archivos de approved-plan y comparar-plan.py. Para deshacer un «no», el usuario pide «quiero revisar los cambios registrados» y el plan lo pasa a «para revisión».

Cabecera inicial del archivo:

```markdown
# Decisiones sobre el stack

Este registro conserva decisiones del usuario sobre el código existente para un valor de stack.yaml.
Lo actualiza el agente únicamente dentro de un plan aprobado; no se edita a mano.
El alcance contiene una lista JSON explícita de servicios; «todos» es solo texto mostrado.
«aplicado» y «sustituido» son historial, salvo aplicado de base_de_datos.version: el mismo par real/stack cubre la comparación.

| clave | valor | decisión | alcance | fecha |
|---|---|---|---|---|
```

Escalares en forma canónica del lector del stack; listas/mapas como JSON compacto con claves ordenadas. Escapa contrabarras y barras verticales de la columna valor. Fecha AAAA-MM-DD, alcance JSON explícito sin comodines, salvo `["*"]` en filas de proyecto. No solapes filas vigentes: una fila sin nombres cubre toda la clave/servicio/valor; con nombres, cada nombre solo puede quedar en una fila vigente. Divide el alcance al cambiar solo parte de sus servicios, conservando la decisión de los demás. No marques aplicado sin verificar. Una decisión para otro valor no evita volver a comprobar. No amplíes servicios cubiertos al incorporar uno nuevo.

Las clases y remedios se definen solo en `.agents/config/codigos.yaml`: continúa solo con exit 0, revisa avisos, partes del plan y omitidos; exit 1 detiene salvo la excepción autorizada de preparación; exit 2 exige corregir la invocación. Un control omitido no demuestra que su infraestructura esté disponible. En change-version, los avisos ajenos solo van a pendientes; verifica su documentación propia por servicio, tecnología y versión, dejando lo no atribuible como pendiente. Solo los workflows que resuelven el código pueden incorporarlo al plan aprobado.


En este stack el único servicio es `.`; filas de proyecto usan `["*"]`. VERSION_REAL guarda el par JSON real/stack; un cambio de cualquiera invalida la decisión anterior. En E/D solo avisa; sí deriva al plan de change-version para documentación, sandbox y objetos hacia stack.yaml. No añade actualizaciones del servidor al plan de feature. Si no hay dato, muestra una línea «no se pudo comprobar la versión real» y no reutilices una versión de una ejecución anterior. Al pedir --completo con versión conocida, repite --dato version_real=V en la comprobación del registro; el CLI no consulta MCP ni persiste datos efímeros. Aplicado solo acredita trabajo local/documental verificado; no afirma que el servidor real cambió, y solo silencia la comparación del mismo par real/stack; si cambia cualquiera, se vuelve a comparar.


La tabla admite cinco columnas o una sexta columna opcional `nombres` al final: JSON compacto de nombres estables ordenados y sin duplicados. Ausente o [] cubre toda la clave, como las filas anteriores. Para nomenclatura guarda los nombres señalados: rutas del front, nombres de objeto o objeto.columna/objeto.parametro del SQL. Una fila no o para revisión acepta solo esos nombres para la clave/valor/alcance; se recuerda lo registrado y se comparan los demás, mostrando solo nombres nuevos. Con para revisión se conserva la opción de aplicarlos. Un cambio del valor en stack invalida la decisión. Incluye los nombres en el plan aprobado y no conviertas una aceptación parcial en una fila de clave completa. Los nombres no interpretables se indican como no evaluados, con su cantidad; la incertidumbre no se convierte en parte del plan.

VERSION_REAL se compara solo en la entrada de workflows con requiere_dato. Una fila aplicado cubre el par canónico {"real":…,"stack":…}; solo esa comprobación tiene aplicado_cubre. La precisión de stack manda: major.minor acepta el parche del servidor; major.minor.patch exige ese parche. En cierre, estricto y workflows documentales no se imprime VERSION_REAL.

Con integración ninguna, las diferencias de código usan STACK_CODIGO y las resuelven los workflows E genéricos, sin remitir a un add-* ausente. Con la integración activa se conserva su código y workflow propio. La resta de nombres solo opera sobre una lista no vacía y nunca descarta no_determinable. Tras la resta se actualizan evidencia, evaluados y archivos, conservando los No evaluados.

La aceptación por nombres solo se admite en las comprobaciones declaradas con `"por_nombre": true` en `config/registro-stack.json` (nomenclatura que devuelve nombres concretos). En las demás claves, usa la fila de cinco columnas o `nombres` vacío. Una lista no vacía produce «fila no válida: <clave> no admite nombres; usa la fila sin la sexta columna» y no cubre la comparación.
