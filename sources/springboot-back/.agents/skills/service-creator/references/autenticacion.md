<!-- si-archivo integraciones.autenticacion=clerk -->

## Modo autenticacion: propuesta para gateway existente

Si la entrada declara modo autenticacion, aplica solo este contrato y omite el contrato completo de creación (entrada, tareas, reglas y salida). Recibe approved-plan.md y feedback.md opcional. El plan aprobado identifica el gateway existente, paquete y cada archivo autorizado. No crea servicios ni asigna puertos ni copia wrapper. No ejecuta Gradle ni escribe producción.

Antes de proponer nada, comprueba SecurityConfig y cualquier cadena SecurityWebFilterChain equivalente. Si existe, informa "seguridad existente, sin tocar", escribe service-report.md y termina sin code-changes aplicable; nunca añade una segunda cadena. Una identificación ambigua devuelve bloqueado.

Usa assets/gateway/SecurityConfig.template.java para proponer la clase ausente, agrega solo la dependencia OAuth2 Resource Server ausente y la propiedad pública issuer-uri necesaria desde application.template.yaml. No reemplaza la configuración completa ni cambia rutas, CORS o el contrato de errores. Enumera los matchers públicos y solo acepta los expresamente aprobados, por método/prefijo. No implementa roles.
<!-- si devops.infraestructura=jenkins-kubernetes -->
Conserva issuer global en local; solo en perfiles de entradas con desplegar true integra la propiedad del issuer en el documento activado por k8s desde assets/gateway/application-k8s.fragment.yaml. Si ya hay documento k8s, propone el cambio mínimo de su propiedad sin duplicar el documento. Los destinos y sufijos salen del plan cotejado con el stack. No propone cuentas ni Jenkinsfile.
<!-- fin -->

Escribe OUT_DIR/code-changes.auth.md con frontmatter artefacto, skill, estado, entradas_leidas y fecha, y una sección por archivo con contenido/diff aplicable; documenta API pública con Javadoc/WHY. Escribe también OUT_DIR/service-report.md con estado, archivos propuestos, dependencia y propiedades añadidas o ya presentes, comandos y salida literal, y riesgos/bloqueos. Una segunda ejecución no reescribe seguridad existente. No lee archivos de secretos, account/, kubeconfig o .env; application*.yaml solo por claves públicas permitidas de configuración, nunca completo. No escribe stack.yaml ni improvisa un issuer faltante.

