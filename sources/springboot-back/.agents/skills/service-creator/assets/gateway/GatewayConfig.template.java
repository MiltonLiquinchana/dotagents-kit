package __PAQUETE__.config;

// Imports de Spring Cloud Gateway (WebFlux)
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.cloud.gateway.route.RouteLocator;
import org.springframework.cloud.gateway.route.builder.RouteLocatorBuilder;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * Configuración programática de rutas para Spring Cloud Gateway.
 *
 * <p>Las rutas se declaran aquí, no en application.yaml. Este archivo trae UNA ruta de
 * ejemplo; la skill repite el bloque {@code .route(...)} por cada servicio de
 * `servicios.py nombres`, con base, context-path y destino de cada uno.</p>
 */
@Configuration
// si devops.infraestructura=jenkins-kubernetes
@EnableConfigurationProperties(GatewayProperties.class)
// si devops.infraestructura=ninguna
@EnableConfigurationProperties
// fin
public class GatewayConfig {

    // Cabeceras que cada request añadida por el Gateway lleva al servicio de destino:
    // identifican la request y el gateway que la procesó.
    private static final String X_REQUEST_SOURCE = "X-Request-Source";
    private static final String X_GATEWAY = "X-Gateway";

    /**
     * Una ruta por servicio. La repetición del bloque de ejemplo por cada servicio la
     * hace la siembra: base, context-path, perfil y puerto de cada uno, del resultado de
     * `servicios.py nombres`. El bloque de ejemplo desaparece al sembrar.
     *
     * @param builder constructor de rutas de Spring Cloud Gateway
     * @return RouteLocator con todas las rutas
     */
    @Bean
// si devops.infraestructura=jenkins-kubernetes
    public RouteLocator myRoutes(RouteLocatorBuilder builder, GatewayProperties properties) {
// si devops.infraestructura=ninguna
    public RouteLocator myRoutes(RouteLocatorBuilder builder) {
// fin
        return builder.routes()
                .route("__BASE_RUTA__-service-route", p -> p
                                .path("__CONTEXT_PATH_RUTA__/**")
                                .filters(f -> f
// si devops.infraestructura=jenkins-kubernetes
                                                .addRequestHeader(X_GATEWAY, "api-__BASE_RUTA__-" + properties.sufijo())
// si devops.infraestructura=ninguna
                                                .addRequestHeader(X_GATEWAY, "api-__BASE_RUTA__-__ENTORNO__")
// fin
                                                .addRequestHeader(X_REQUEST_SOURCE, "gateway")
                                                .retry(3))
// si devops.infraestructura=jenkins-kubernetes
                                .uri("lb://__BASE_RUTA__-" + properties.sufijo() + "-service"))
// fin
// si devops.infraestructura=ninguna
                                .uri("http://localhost:__PUERTO_RUTA__"))
// fin
                                .build();
    }
}
