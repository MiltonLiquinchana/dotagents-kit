// si-archivo integraciones.gestion_usuarios=organizaciones|aplicacion
package __PAQUETE__.controller;
import __PAQUETE__.services.PerfilesService;
import __PAQUETE__.model.*;
import jakarta.validation.Valid;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import java.util.*;

@RestController
public class PerfilesController {
    private final PerfilesService service;
    public PerfilesController(PerfilesService service) { this.service=service; }
    @PostMapping("/solicitar-acceso") public ResponseEntity<Void> preRegistro(@Valid @RequestBody PreRegistroRequest data) {
        service.preRegistro(data); return ResponseEntity.status(201).build();
    }
    @PostMapping("/perfil/crearperfil") public ResponseEntity<Map<String,Integer>> crear(@Valid @RequestBody PerfilRequest data) {
        return ResponseEntity.status(201).body(Map.of("perfilId",service.crear(data)));
    }
    @PostMapping("/perfil/listarresumenperfiles") public List<Map<String,Object>> listar(@Valid @RequestBody PerfilFiltro data) { return service.listar(data); }
    @GetMapping("/perfil/obtenerdetalleperfil/{id}") public Map<String,Object> detalle(@PathVariable int id) { return service.detalle(id); }
    @PutMapping("/perfil/actualizarperfil/{id}") public ResponseEntity<Void> actualizar(@PathVariable int id,@Valid @RequestBody PerfilRequest data) {
        service.actualizar(id,data); return ResponseEntity.noContent().build();
    }
    @GetMapping("/estadosperfiles/listarestadosperfiles") public List<Map<String,Object>> estados() { return service.estados(); }
    @PostMapping("/perfil/{id}/vincular-clerk") public ResponseEntity<Void> reconciliar(@PathVariable int id) {
        service.reconciliar(id); return ResponseEntity.noContent().build();
    }
// si integraciones.gestion_usuarios=organizaciones
    @GetMapping("/organizaciones/listarorganizaciones") public List<Map<String,Object>> organizaciones() { return service.organizaciones(); }
// fin
}
