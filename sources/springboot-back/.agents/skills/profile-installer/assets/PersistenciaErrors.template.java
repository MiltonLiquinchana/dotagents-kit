// si-archivo integraciones.gestion_usuarios=organizaciones|aplicacion
package __PAQUETE__.configuration;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.http.ResponseEntity;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.web.bind.annotation.*;
/** No devuelve SQL ni valores del proveedor en errores de integridad. */
@RestControllerAdvice
@Order(Ordered.HIGHEST_PRECEDENCE)
public class PersistenciaErrors {
    @ExceptionHandler(DataIntegrityViolationException.class)
    public ResponseEntity<ExceptionResponse> duplicate(DataIntegrityViolationException ex) {
        return ResponseEntity.status(409).body(new ExceptionResponse("Conflicto de datos","CONFLICTO"));
    }
}
