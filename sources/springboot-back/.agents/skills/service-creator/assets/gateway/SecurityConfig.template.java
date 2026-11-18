// si-archivo integraciones.autenticacion=clerk
// ==============================================================================
// SecurityConfig del gateway: solo se siembra con `integraciones.autenticacion: clerk`.
// No declara rutas públicas propias de ningún dominio: las públicas de gestión de
// usuarios se añaden por feature, aprobadas en el plan.
// si integraciones.gestion_usuarios=organizaciones|aplicacion
// La instalación de perfiles enumera webhook y pre-registro públicos en su contrato;
// solo se añaden al aprobar su plan, nunca se publica el CRUD administrativo.
// fin
// ==============================================================================
package __PAQUETE__.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.Customizer;
import org.springframework.security.config.web.server.ServerHttpSecurity;
import org.springframework.security.config.web.server.ServerHttpSecurity.CsrfSpec;
import org.springframework.security.web.server.SecurityWebFilterChain;

@Configuration
public class SecurityConfig {

	@Bean
	public SecurityWebFilterChain springSecurityFilterChain(ServerHttpSecurity http) {
		http
				// Enlazar CORS con la seguridad: withDefaults() detecta automáticamente el
				// bean corsConfigurationSource de CorsConfig, de modo que el preflight
				// OPTIONS se responde antes de que Security lo bloquee.
				.cors(Customizer.withDefaults())
				// Desactivar CSRF para APIs basadas en tokens (JWT)
				.csrf(CsrfSpec::disable)
				.authorizeExchange(authorize -> authorize
						// Actuator público (health, info y métricas para DevOps)
						.pathMatchers("/actuator/**").permitAll()
						// Cualquier otra petición requiere un token válido
						.anyExchange().authenticated())
				// Resource Server con los JWT de Clerk: el issuer viene de application.yaml
				.oauth2ResourceServer(oauth2 -> oauth2
						.jwt(Customizer.withDefaults()));
		return http.build();
	}
}
