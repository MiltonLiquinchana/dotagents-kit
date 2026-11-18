---
trigger: model_decision
description: Reglas de arquitectura SQL para MySQL, tipos de datos, claves foráneas, SPs, handlers y contratos.
---

# Reglas de Arquitectura SQL

Reglas obligatorias para mantener consistencia, rendimiento e integridad en el esquema de la base de datos MySQL. Toda decisión de diseño debe cumplirlas y se auditan antes de ejecutar en BD viva.

**OBLIGATORIO — Versiones del proyecto (MySQL)**: escribe SQL compatible e idiomático con `base_de_datos.version` de `.agents/stack.yaml`, la versión del servidor MySQL del proyecto (el sandbox la usa para sus pruebas), motor mysql. El inventario solo lee esa clave y no consulta servidores. Sin sintaxis de versiones posteriores. Si esa versión ofrece sentencias o sintaxis que resuelvan algo con menos código o de forma más clara, úsalas en lugar del patrón antiguo. Ejemplos: un CTE con `WITH` en lugar de subconsultas repetidas; la sintaxis vigente para restricciones check y valores por defecto (`DEFAULT (expresión)`) si la versión la admite; usa lo que la versión trata como vigente en lugar de lo que deprecó. La regla se aplica a todo el SQL que se escriba, conforme al plan o al completar la implementación. Si al escribir surge una duda sobre si algo existe en la versión del proyecto, consulta Open Notebook mediante el script de documentación; si faltan fuentes, detén la propuesta y solicita su preparación con aprobación; si sigue la duda, pregunta al usuario antes de usarla, y solo con preguntas genéricas sobre la librería y su versión (nunca código, datos ni rutas del proyecto).
El preflight comprueba la conexión con Open Notebook por GET y coteja el registro local: las tecnologías del catálogo requieren documentación activa y válida de su versión; una versión catalogada no resoluble bloquea. Las tecnologías fuera del catálogo avisan; si la tarea las usa, se requiere añadirlas al catálogo con la sección "Ampliar el catálogo del proyecto" de preparar-documentacion.md, sin suponer capacidades de su versión. Una retirada propone archivar solo sin usuarios. El usuario decide entre otra documentación/fuente o cambiar versiones mediante un plan aprobado.

## 1. Nomenclatura Estándar (Naming Conventions)

La convención efectiva se lee de `.agents/stack.yaml`. Los valores admitidos para tablas y columnas son PascalCase, snake_case y camelCase. El patrón de clave primaria contiene `{Entidad}` y se resuelve con el nombre de la entidad:
- **Tablas**: <nomenclatura.tablas>; plural: <nomenclatura.tablas_plural>. Ejemplos: Clientes, Pedidos, DetallesPedido (ejemplo con la convención recomendada).
- **Columnas**: <nomenclatura.columnas>; clave primaria: <nomenclatura.clave_primaria>.
- **Claves Foráneas**: nombre de la PK referenciada (ClienteId en Pedidos; ejemplo con la convención recomendada).
- **Procedimientos**: prefijo <nomenclatura.prefijo_procedimiento> seguido de acción; **funciones**: <nomenclatura.prefijo_funcion>; **vistas**: <nomenclatura.prefijo_vista>.
- **Eventos**: <nomenclatura.prefijo_evento>; **triggers**: <nomenclatura.prefijo_trigger>.
- **Índices**: prefijo <nomenclatura.prefijo_indice> seguido de tabla y columna (`idx_pedido_fecha_emision`; ejemplo con la convención recomendada).
- **Parámetros**: <nomenclatura.prefijo_parametro>; **variables locales**: <nomenclatura.prefijo_variable>.

## 2. Tipos de Datos y Rendimiento

- **Tipos**: usar el tipo de dato más restrictivo posible (`INT` en lugar de `BIGINT` si no se requiere, `VARCHAR(x)` con límites lógicos).
- **Fechas**: usar `DATETIME` para precisión completa o `TIMESTAMP` para cambios automáticos de zona horaria. Manejar zonas horarias de forma consistente (preferible UTC).
- **Booleanos**: usar `TINYINT(1)`.

## 3. Claves Primarias y Foráneas

- **PKs**: `INT AUTO_INCREMENT` con nombre `<nomenclatura.clave_primaria>`.
- **FKs**: obligatorias para integridad referencial.
- **Acciones de FK**: `ON DELETE RESTRICT ON UPDATE CASCADE`.
- **Toda FK debe tener índice asociado** para evitar escaneos completos en joins y checks de integridad.

## 4. Índices

- Indexar toda columna usada frecuentemente en `WHERE`, `JOIN` u `ORDER BY`.
- Evitar sobrecargar tablas con alta tasa de inserción/actualización: evaluar costo-beneficio antes de crear un índice.
- No crear índices redundantes o duplicados sin verificar los existentes con `SHOW INDEX FROM`.

## 5. Auditoría

- Toda tabla nueva debe incluir, salvo justificación documentada en el plan:
  - `FechaCreacion DATETIME DEFAULT CURRENT_TIMESTAMP`
  - `FechaModificacion DATETIME ON UPDATE CURRENT_TIMESTAMP`
  - Si el dominio ya contiene una fecha equivalente a la de creación (por ejemplo, `FechaAlta`), puede usarse como columna de auditoría si el plan lo declara explícitamente. El linter mantiene su chequeo de nombres y, si no puede inferir esa equivalencia, su mensaje indica que debe documentarse en el plan y ajustarse la regla antes de persistir.

## 6. Procedimientos Almacenados

- Todo SP **nuevo o modificado** debe incluir `DECLARE EXIT HANDLER FOR SQLEXCEPTION`. Los SP existentes que aún no lo tienen se corrigen cuando se toquen o en una revisión planificada; el gate solo bloquea lo que el cambio introduce.
  - **SPs que modifican datos** (INSERT/UPDATE/DELETE/DDL): el handler hace `ROLLBACK` y luego `RESIGNAL`. Declaran un parámetro `OUT` de resultado (ej. `p_resultado INT`, 1 éxito, -1 error).
  - **SPs de solo lectura** (únicamente SELECT): el handler hace `RESIGNAL` sin `ROLLBACK` ni `START TRANSACTION`. No declaran `p_resultado` — devuelven el result set y los errores de validación se emiten con `SIGNAL`/`RESIGNAL`. Abrir o revertir transacciones desde un SP de lectura afecta la transacción del llamador.
- Usar lógica basada en conjuntos (set-based). Evitar cursores y loops innecesarios.
- Prohibido `SELECT *` en producción.

## 7. Persistencia y Control de Cambios

- Los objetos de BD se persisten en notebooks `.dbcnb` versionados del repositorio, no en migraciones Flyway/Liquibase. La fuente de verdad de estructura es el notebook correspondiente, no solo la BD viva.
- Todo objeto creado o modificado debe quedar persistido en el notebook **antes** de ejecutarse en la BD viva.
- Scripts destructivos (`DROP`, `TRUNCATE`, `ALTER` que trunque datos) requieren aprobación explícita en revisión y confirmación del usuario.
- Todo script persistido debe ser idempotente: `CREATE TABLE IF NOT EXISTS`, `CREATE PROCEDURE IF NOT EXISTS`, `DROP ... IF EXISTS` según corresponda.
- Cada tipo de objeto se persiste exclusivamente en su notebook canónico según los nombres del mapa `notebooks` de `.agents/stack.yaml`.

## 8. Contratos con el backend (consumidores)

Los procedimientos son la API de datos del backend (repositorio hermano, cuya ruta se declara en `.agents/rules/project.md`; sus ficheros `*Repository.java` contienen `CALL sp_...` y sus proyecciones). La **lista de parámetros** y los **alias del resultado** (nombre, orden y cantidad; el alias distingue mayúsculas y debe coincidir con el getter de la proyección Spring, p. ej. `getClienteId()` ↔ `ClienteId`) son un contrato público.

- **Antes de tocar un objeto existente**, identifica sus consumidores y decláralos en el Plan: `python3 -B -E .agents/scripts/db-index.py --object <nombre>` / `--table <Tabla>` (dentro de este repo, a partir de los notebooks) y `grep -rn "<nombre>" <ruta del backend hermano> --include=*.java` (solo lectura; nunca abras `application*.yaml` ni ficheros de secretos). Si el consumidor está en una rama que no es la actual del backend, usa `git -C <ruta del backend hermano> grep -n "<nombre>" <rama> -- '*.java'`.
- Cambios **aditivos** (una columna nueva al final del resultado) no exigen coordinación. **Renombrar, quitar o reordenar** un alias, o cambiar parámetros, rompe al consumidor: requiere confirmación explícita del usuario y un plan para actualizar el backend. Un consumidor sin atender es **Bloqueante** en la revisión de código.
- **Nunca expongas** columnas de credenciales en un resultado.
- **Límite**: la búsqueda es textual; no ve consumidores externos ni llamadas construidas dinámicamente.

## 9. Decisión sobre la nomenclatura de tablas y columnas

La nomenclatura efectiva es la sección `nomenclatura` de `.agents/stack.yaml`; las excepciones del proyecto se documentan en `.agents/rules/project.md`.

Ejemplos de clientes y pedidos: ejemplo con la convención recomendada; las convenciones efectivas se leen de `.agents/stack.yaml`.

Para triggers, `nomenclatura.prefijo_trigger` puede ser texto o una lista de prefijos: el primero se recomienda para objetos nuevos y todos se aceptan al validar existentes.

Si surge una duda de API en diseño, desarrollo o revisión, consulta mediante `python3 .agents/scripts/documentacion.py preguntar TECNOLOGIA "PREGUNTA_GENERICA" --version VERSION`. La referencia debe corresponder a la serie del proyecto (major.minor; JDK: mayor) y las notas al parche exacto. Solo se usa una cita verificada literalmente. Sin evidencia, pregunta; no envíes código, tablas, datos, rutas ni credenciales. Las decisiones del proyecto siguen en knowledge-base/ con tgrep.
