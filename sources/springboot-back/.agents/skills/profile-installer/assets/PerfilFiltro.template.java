// si-archivo integraciones.gestion_usuarios=organizaciones|aplicacion
package __PAQUETE__.model;
import jakarta.validation.constraints.*;
public record PerfilFiltro(@Size(max=100) String busqueda
// si integraciones.gestion_usuarios=organizaciones
    ,@NotNull @Positive Integer organizacionId
// fin
) {}
