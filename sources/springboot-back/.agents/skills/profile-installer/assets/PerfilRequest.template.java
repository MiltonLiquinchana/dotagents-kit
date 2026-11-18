// si-archivo integraciones.gestion_usuarios=organizaciones|aplicacion
package __PAQUETE__.model;
import jakarta.validation.constraints.*;
public record PerfilRequest(
    @NotBlank @Size(max=250) String nombres,
    @NotBlank @Size(max=250) String apellidos,
    @NotBlank @Email @Size(max=250) String correo,
    @NotNull @Min(EstadoPerfil.PENDIENTE) @Max(EstadoPerfil.INACTIVO) Integer estadoPerfilId
// si integraciones.gestion_usuarios=organizaciones
    ,@NotNull @Positive Integer organizacionId, String inviterUserId
// fin
) {}
