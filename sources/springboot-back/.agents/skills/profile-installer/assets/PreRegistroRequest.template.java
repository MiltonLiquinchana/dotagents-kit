// si-archivo integraciones.gestion_usuarios=organizaciones|aplicacion
package __PAQUETE__.model;
import jakarta.validation.constraints.*;
/** El contrato público no contiene estado, ClerkUserId ni invitador. */
public record PreRegistroRequest(
    @NotBlank @Size(max=250) String nombres,
    @NotBlank @Size(max=250) String apellidos,
    @NotBlank @Email @Size(max=250) String correo
// si integraciones.gestion_usuarios=organizaciones
    ,@NotNull @Positive Integer organizacionId
// fin
) {}
