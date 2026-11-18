// si-archivo integraciones.gestion_usuarios=organizaciones|aplicacion
package __PAQUETE__.security;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.*;
import org.springframework.security.config.Customizer;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.oauth2.jwt.*;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.http.HttpMethod;

/** WHY: las operaciones administrativas requieren JWT incluso si se accede sin gateway. Sin roles. */
@Configuration
public class PerfilSecurityConfig {
    @Bean @Lazy
    JwtDecoder perfilJwtDecoder(@Value("${clerk.issuer-uri}") String issuer) {
        return NimbusJwtDecoder.withIssuerLocation(issuer).build();
    }
    @Bean SecurityFilterChain perfilSecurity(HttpSecurity http, @Lazy JwtDecoder perfilJwtDecoder) throws Exception {
        return http.cors(Customizer.withDefaults()).csrf(csrf -> csrf.disable())
            .sessionManagement(session -> session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            .authorizeHttpRequests(auth -> auth
                .requestMatchers(HttpMethod.POST,"/solicitar-acceso","/webhooks/clerk").permitAll()
// si integraciones.gestion_usuarios=organizaciones
                .requestMatchers(HttpMethod.GET,"/organizaciones/listarorganizaciones").permitAll()
// fin
                .requestMatchers("/actuator/**").permitAll()
                .anyRequest().authenticated())
            .oauth2ResourceServer(oauth -> oauth.jwt(jwt -> jwt.decoder(perfilJwtDecoder))).build();
    }
}
