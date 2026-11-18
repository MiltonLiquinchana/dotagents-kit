// si-archivo integraciones.gestion_usuarios=organizaciones|aplicacion
package __PAQUETE__.controller;
import __PAQUETE__.security.SvixWebhookVerifier;
import __PAQUETE__.services.PerfilesService;
import __PAQUETE__.configuration.ExceptionResponse;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;
import org.springframework.http.*;
import org.springframework.web.bind.annotation.*;

@RestController
public class ClerkWebhookController {
    private final SvixWebhookVerifier verifier;
    private final PerfilesService service;
    private final ObjectMapper json;
    public ClerkWebhookController(SvixWebhookVerifier verifier,PerfilesService service,ObjectMapper json) {
        this.verifier=verifier;this.service=service;this.json=json;
    }
    @PostMapping("/webhooks/clerk") public ResponseEntity<?> webhook(@RequestBody String payload,@RequestHeader HttpHeaders headers) {
        try { verifier.verify(payload,headers); }
        catch (IllegalArgumentException ex) { return ResponseEntity.badRequest().body(new ExceptionResponse("Firma o cabeceras inválidas","DATOS_INVALIDOS")); }
        JsonNode event;
        try { event=json.readTree(payload); }
        catch (Exception ex) { return ResponseEntity.badRequest().body(new ExceptionResponse("JSON inválido","DATOS_INVALIDOS")); }
        JsonNode data=event.path("data");
// si integraciones.gestion_usuarios=organizaciones
        if (!"organizationMembership.created".equals(event.path("type").asString())) return ResponseEntity.ok().build();
        // WHY: SDK local confirma que la invitación copia public_metadata a la membresía.
        JsonNode metadata=data.path("public_metadata");
        JsonNode user=data.path("public_user_data");
        Integer perfilId=metadata.has("perfilId") ? metadata.path("perfilId").asInt() : null;
        String userId=user.path("user_id").asString(null);
        String correo=user.path("identifier").asString(null);
        String org=data.path("organization").path("id").asString(null);
        if (userId==null || org==null) return ResponseEntity.badRequest().body(new ExceptionResponse("Evento incompleto","DATOS_INVALIDOS"));
        service.vincular(perfilId,userId,correo,org);
// si integraciones.gestion_usuarios=aplicacion
        if (!"user.created".equals(event.path("type").asString())) return ResponseEntity.ok().build();
        JsonNode metadata=data.path("public_metadata");
        Integer perfilId=metadata.has("perfilId") ? metadata.path("perfilId").asInt() : null;
        String userId=data.path("id").asString(null);
        String correo=null;
        String primary=data.path("primary_email_address_id").asString(null);
        for (JsonNode email:data.path("email_addresses"))
            if (primary!=null && primary.equals(email.path("id").asString(null))) correo=email.path("email_address").asString(null);
        if (userId==null) return ResponseEntity.badRequest().body(new ExceptionResponse("Evento incompleto","DATOS_INVALIDOS"));
        service.vincular(perfilId,userId,correo);
// fin
        return ResponseEntity.ok().build();
    }
}
