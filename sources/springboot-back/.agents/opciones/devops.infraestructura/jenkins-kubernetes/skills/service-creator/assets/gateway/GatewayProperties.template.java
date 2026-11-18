package __PAQUETE__.config;

import java.util.List;
import org.springframework.boot.context.properties.ConfigurationProperties;

/** Propiedades públicas del gateway, obtenidas de la configuración del perfil activo. */
@ConfigurationProperties(prefix = "gateway")
public record GatewayProperties(String sufijo, List<String> corsOrigenes) {
    public GatewayProperties {
        if (sufijo == null || sufijo.isBlank()) throw new IllegalArgumentException("Falta gateway.sufijo");
        if (corsOrigenes == null || corsOrigenes.isEmpty()) throw new IllegalArgumentException("Falta gateway.cors-origenes");
        corsOrigenes = List.copyOf(corsOrigenes);
    }
}
