package __PAQUETE__.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.reactive.CorsWebFilter;
import org.springframework.web.cors.reactive.UrlBasedCorsConfigurationSource;

/**
 * Configuración global de CORS para Spring Cloud Gateway (WebFlux / Reactivo).
 *
 * <p>Se exponen DOS beans a partir de la MISMA fuente de configuración:</p>
 * <ul>
 *   <li>{@link CorsWebFilter} – filtro de bajo nivel que el Gateway aplica antes
 *       de enrutar la petición.</li>
 *   <li>{@link UrlBasedCorsConfigurationSource} (nombrado {@code corsConfigurationSource}) –
 *       detectado automáticamente por {@code .cors(Customizer.withDefaults())} cuando el
 *       gateway valida autenticación. Sin este bean, el preflight OPTIONS devuelve
 *       401/403 sin headers CORS.</li>
 * </ul>
 *
// si devops.infraestructura=jenkins-kubernetes
 * <p>Los orígenes llegan de gateway.cors-origenes del perfil activo; los locales se
 * conservan en application.yaml y el documento k8s del perfil los sustituye.</p>
// si devops.infraestructura=ninguna
 * <p>Los orígenes permitidos están en `backend.cors_origenes` de `.agents/stack.yaml`:
 * la skill repite la línea `addAllowedOrigin` por cada valor de la lista.</p>
// fin
 */
@Configuration
public class CorsConfig {

    /**
     * Fuente de configuración CORS compartida entre el filtro del Gateway y Spring Security.
     * Al ser un bean con el nombre exacto {@code corsConfigurationSource}, Spring Security
     * lo detecta via {@code .cors(Customizer.withDefaults())} sin configuración adicional.
     */
    @Bean
// si devops.infraestructura=jenkins-kubernetes
    public UrlBasedCorsConfigurationSource corsConfigurationSource(GatewayProperties properties) {
// si devops.infraestructura=ninguna
    public UrlBasedCorsConfigurationSource corsConfigurationSource() {
// fin
        CorsConfiguration corsConfig = new CorsConfiguration();

// si devops.infraestructura=jenkins-kubernetes
        properties.corsOrigenes().forEach(corsConfig::addAllowedOrigin);
// si devops.infraestructura=ninguna
        // Orígenes permitidos: la skill repite esta línea por cada valor de
        // `<backend.cors_origenes>` (uno por origen):
        corsConfig.addAllowedOrigin("<backend.cors_origenes>");
// fin

        // Métodos HTTP permitidos
        corsConfig.addAllowedMethod("GET");
        corsConfig.addAllowedMethod("POST");
        corsConfig.addAllowedMethod("PUT");
        corsConfig.addAllowedMethod("DELETE");
        corsConfig.addAllowedMethod("OPTIONS"); // Preflight requests
        corsConfig.addAllowedMethod("PATCH");

        // Permitir todos los headers (incluye Authorization, Content-Type, etc.)
        corsConfig.addAllowedHeader("*");

        // Necesario para enviar el header Authorization con el token del navegador
        corsConfig.setAllowCredentials(true);

        // Cache del preflight en el navegador (1 hora)
        corsConfig.setMaxAge(3600L);

        // Aplicar a todas las rutas del Gateway
        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration("/**", corsConfig);
        return source;
    }
}
