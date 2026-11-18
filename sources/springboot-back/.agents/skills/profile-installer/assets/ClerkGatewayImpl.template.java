// si-archivo integraciones.gestion_usuarios=organizaciones|aplicacion
package __PAQUETE__.implement;
import __PAQUETE__.services.ClerkGateway;
import __PAQUETE__.configuration.customexception.CustomConflictException;
import com.clerk.backend_api.Clerk;
import com.clerk.backend_api.models.operations.*;
import java.util.*;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

@Component
public class ClerkGatewayImpl implements ClerkGateway {
    private final Clerk clerk;
// si integraciones.gestion_usuarios=organizaciones
    private final org.springframework.core.env.Environment environment;
    public ClerkGatewayImpl(@Value("${clerk.secret-key}") String secret, org.springframework.core.env.Environment environment) {
        this.clerk=Clerk.builder().bearerAuth(secret).build(); this.environment=environment;
    }
    @Override public void invitar(int perfilId, String correo, String organizacion, String invitador) {
        String by=invitador;
        // WHY: el respaldo es opcional y se resuelve solo si el request no trae invitador.
        if (by==null || by.isBlank()) {
            try { by=environment.getProperty("clerk.default-inviter-user-id"); }
            catch (IllegalArgumentException ex) { throw new CustomConflictException("Falta el invitador de la organización"); }
        }
        if (by==null || by.isBlank()) throw new CustomConflictException("Falta el invitador de la organización");
        try {
            var body=CreateOrganizationInvitationRequestBody.builder().emailAddress(correo).inviterUserId(by)
                .role("org:member").publicMetadata(Map.of("perfilId",perfilId)).build();
            clerk.organizationInvitations().create(organizacion,Optional.of(body),Optional.empty());
        } catch (Exception ex) { throw new CustomConflictException("No se pudo enviar la invitación"); }
    }
    @Override public String buscar(int perfilId, String correo, String organizacion) {
        try {
            var filtered=clerk.organizationMemberships().list(ListOrganizationMembershipsRequest.builder()
                .organizationId(organizacion).emailAddress(List.of(correo)).limit(1L).build());
            var direct=filtered.organizationMemberships().map(x -> x.data()).orElse(List.of());
            if (!direct.isEmpty()) return direct.getFirst().publicUserData().map(x -> x.userId()).orElse(null);
            for (long offset=0;;offset+=100) {
                var response=clerk.organizationMemberships().list(ListOrganizationMembershipsRequest.builder()
                    .organizationId(organizacion).limit(100L).offset(offset).build());
                var page=response.organizationMemberships().map(x -> x.data()).orElse(List.of());
                for (var item:page) if (String.valueOf(perfilId).equals(String.valueOf(item.publicMetadata().get("perfilId"))))
                    return item.publicUserData().map(x -> x.userId()).orElse(null);
                if (page.size()<100) return null;
            }
        } catch (Exception ex) { throw new CustomConflictException("No se pudo reconciliar con Clerk"); }
    }
// si integraciones.gestion_usuarios=aplicacion
    public ClerkGatewayImpl(@Value("${clerk.secret-key}") String secret) { this.clerk=Clerk.builder().bearerAuth(secret).build(); }
    @Override public void invitar(int perfilId, String correo) {
        try {
            var body=CreateInvitationRequestBody.builder().emailAddress(correo).publicMetadata(Map.of("perfilId",perfilId)).build();
            clerk.invitations().create(Optional.of(body),Optional.empty());
        } catch (Exception ex) { throw new CustomConflictException("No se pudo enviar la invitación"); }
    }
    @Override public String buscar(int perfilId, String correo) {
        try {
            var direct=clerk.users().list(GetUserListRequest.builder().emailAddress(List.of(correo)).limit(1L).build()).userList().orElse(List.of());
            if (!direct.isEmpty()) return direct.getFirst().id();
            for (long offset=0;;offset+=100) {
                var page=clerk.users().list(GetUserListRequest.builder().limit(100L).offset(offset).build()).userList().orElse(List.of());
                for (var item:page) if (String.valueOf(perfilId).equals(String.valueOf(item.publicMetadata().get("perfilId")))) return item.id();
                if (page.size()<100) return null;
            }
        } catch (Exception ex) { throw new CustomConflictException("No se pudo reconciliar con Clerk"); }
    }
// fin
}
