package __PAQUETE__.configuration.customexception;

import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.ResponseStatus;

// Marca esta excepción con el estado HTTP 409 Conflict
@ResponseStatus(HttpStatus.CONFLICT)
public class CustomConflictException extends RuntimeException {

    private static final long serialVersionUID = 1L;

    private final String codigo;

    // Constructor que acepta un mensaje de error
    public CustomConflictException(String message) {
        this(message, "CONFLICTO");
    }
    // Las features pueden proporcionar un código propio; nunca se conserva null/vacío.
    public CustomConflictException(String message, String codigo) {
        super(message);
        this.codigo = codigo == null || codigo.isBlank() ? "CONFLICTO" : codigo;
    }

    public String getCodigo() {
        return codigo;
    }
}
