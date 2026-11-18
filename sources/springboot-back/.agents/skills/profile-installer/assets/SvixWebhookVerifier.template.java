// si-archivo integraciones.gestion_usuarios=organizaciones|aplicacion
package __PAQUETE__.security;
import com.svix.Webhook;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpHeaders;
import org.springframework.stereotype.Component;
import java.util.*;

@Component
public class SvixWebhookVerifier {
    private final String secret;
    public SvixWebhookVerifier(@Value("${clerk.webhook-signing-secret}") String secret) { this.secret=secret; }
    public void verify(String payload,HttpHeaders headers) {
        for (String name:List.of("svix-id","svix-timestamp","svix-signature"))
            if (headers.getFirst(name)==null) throw new IllegalArgumentException("Faltan cabeceras Svix");
        Map<String,List<String>> normalized=new HashMap<>();
        headers.forEach((key,values) -> normalized.put(key.toLowerCase(Locale.ROOT),values));
        try { new Webhook(secret).verify(payload,normalized); }
        catch (Exception ex) { throw new IllegalArgumentException("Firma Svix inválida"); }
    }
}
