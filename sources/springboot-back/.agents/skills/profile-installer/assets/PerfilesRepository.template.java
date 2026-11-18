// si-archivo integraciones.gestion_usuarios=organizaciones|aplicacion
package __PAQUETE__.repository;
import java.util.List;
import java.util.Map;
public interface PerfilesRepository {
    List<Map<String,Object>> call(String procedure, Object... arguments);
}
