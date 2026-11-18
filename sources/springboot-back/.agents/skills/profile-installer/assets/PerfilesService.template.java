// si-archivo integraciones.gestion_usuarios=organizaciones|aplicacion
package __PAQUETE__.services;
import java.util.*;
import __PAQUETE__.model.*;
public interface PerfilesService {
    int preRegistro(PreRegistroRequest data);
    int crear(PerfilRequest data);
    void actualizar(int id, PerfilRequest data);
    List<Map<String,Object>> listar(PerfilFiltro filtro);
    Map<String,Object> detalle(int id);
    List<Map<String,Object>> estados();
    void reconciliar(int id);
// si integraciones.gestion_usuarios=organizaciones
    List<Map<String,Object>> organizaciones();
    void vincular(Integer perfilId, String userId, String correo, String organizacion);
// si integraciones.gestion_usuarios=aplicacion
    void vincular(Integer perfilId, String userId, String correo);
// fin
}
