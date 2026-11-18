// si-archivo integraciones.gestion_usuarios=organizaciones|aplicacion
package __PAQUETE__.implement;
import __PAQUETE__.services.*;
import __PAQUETE__.repository.PerfilesRepository;
import __PAQUETE__.model.*;
import __PAQUETE__.configuration.customexception.*;
import tools.jackson.databind.ObjectMapper;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import java.util.*;

@Service
@Transactional
public class PerfilesServiceImpl implements PerfilesService {
    private final PerfilesRepository repository;
    private final ClerkGateway clerk;
    private final ObjectMapper json;
    public PerfilesServiceImpl(PerfilesRepository repository, ClerkGateway clerk, ObjectMapper json) {
        this.repository=repository; this.clerk=clerk; this.json=json;
    }
    private Map<String,Object> first(List<Map<String,Object>> rows) {
        if (rows.isEmpty()) throw new CustomNotFoundException("Perfil no encontrado");
        return rows.getFirst();
    }
    private int number(Object value) { return ((Number)value).intValue(); }
    private String payload(String nombres, String apellidos, String correo, int estado
// si integraciones.gestion_usuarios=organizaciones
        ,int organizacion
// fin
    ) {
        Map<String,Object> data=new LinkedHashMap<>();
        data.put("nombres",nombres.trim()); data.put("apellidos",apellidos.trim());
        data.put("correo",correo.trim().toLowerCase(Locale.ROOT)); data.put("estadoPerfilId",estado);
// si integraciones.gestion_usuarios=organizaciones
        data.put("organizacionId",organizacion);
// fin
        return json.writeValueAsString(data);
    }
    @Override public int preRegistro(PreRegistroRequest data) {
        return number(first(repository.call("__SP_CREAR__",payload(data.nombres(),data.apellidos(),data.correo(),EstadoPerfil.PENDIENTE
// si integraciones.gestion_usuarios=organizaciones
            ,data.organizacionId()
// fin
        ))).get("perfilId"));
    }
    @Override public int crear(PerfilRequest data) {
        int id=number(first(repository.call("__SP_CREAR__",payload(data.nombres(),data.apellidos(),data.correo(),data.estadoPerfilId()
// si integraciones.gestion_usuarios=organizaciones
            ,data.organizacionId()
// fin
        ))).get("perfilId"));
        if (data.estadoPerfilId()==EstadoPerfil.INVITADO_A_CLERK) invitar(id,data);
        return id;
    }
    @Override public void actualizar(int id, PerfilRequest data) {
        Map<String,Object> anterior=detalle(id);
        repository.call("__SP_ACTUALIZAR__",id,payload(data.nombres(),data.apellidos(),data.correo(),data.estadoPerfilId()
// si integraciones.gestion_usuarios=organizaciones
            ,data.organizacionId()
// fin
        ));
        if (data.estadoPerfilId()==EstadoPerfil.INVITADO_A_CLERK && number(anterior.get("estadoPerfilId"))!=EstadoPerfil.INVITADO_A_CLERK) invitar(id,data);
    }
    private void invitar(int id, PerfilRequest data) {
// si integraciones.gestion_usuarios=organizaciones
        var perfil=first(repository.call("__SP_BUSCAR__",id,null));
        clerk.invitar(id,data.correo(),Objects.toString(perfil.get("clerkOrganizationId"),""),data.inviterUserId());
// si integraciones.gestion_usuarios=aplicacion
        clerk.invitar(id,data.correo());
// fin
    }
    @Override @Transactional(readOnly=true) public List<Map<String,Object>> listar(PerfilFiltro filtro) {
        return repository.call("__SP_LISTAR__",
// si integraciones.gestion_usuarios=organizaciones
            filtro.organizacionId(),
// fin
            filtro.busqueda());
    }
    @Override @Transactional(readOnly=true) public Map<String,Object> detalle(int id) { return first(repository.call("__SP_DETALLE__",id)); }
    @Override @Transactional(readOnly=true) public List<Map<String,Object>> estados() { return repository.call("__SP_ESTADOS__"); }
// si integraciones.gestion_usuarios=organizaciones
    @Override @Transactional(readOnly=true) public List<Map<String,Object>> organizaciones() { return repository.call("__SP_ORGANIZACIONES__"); }
    @Override public void vincular(Integer perfilId, String userId, String correo, String organizacion) {
        var data=first(repository.call("__SP_BUSCAR__",perfilId,correo));
        if (!Objects.equals(data.get("clerkOrganizationId"),organizacion)) throw new CustomConflictException("Organización incompatible");
        repository.call("__SP_VINCULAR__",data.get("perfilId"),userId);
    }
// si integraciones.gestion_usuarios=aplicacion
    @Override public void vincular(Integer perfilId, String userId, String correo) {
        var data=first(repository.call("__SP_BUSCAR__",perfilId,correo));
        repository.call("__SP_VINCULAR__",data.get("perfilId"),userId);
    }
// fin
    @Override public void reconciliar(int id) {
        var data=first(repository.call("__SP_BUSCAR__",id,null));
// si integraciones.gestion_usuarios=organizaciones
        String org=Objects.toString(data.get("clerkOrganizationId"),"");
        String user=clerk.buscar(id,data.get("correo").toString(),org);
// si integraciones.gestion_usuarios=aplicacion
        String user=clerk.buscar(id,data.get("correo").toString());
// fin
        if (user==null || user.isBlank()) throw new CustomNotFoundException("La invitación todavía no fue aceptada");
// si integraciones.gestion_usuarios=organizaciones
        vincular(id,user,data.get("correo").toString(),org);
// si integraciones.gestion_usuarios=aplicacion
        vincular(id,user,data.get("correo").toString());
// fin
    }
}
