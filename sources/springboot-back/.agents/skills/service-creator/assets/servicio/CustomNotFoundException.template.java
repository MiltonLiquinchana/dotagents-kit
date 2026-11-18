package __PAQUETE__.configuration.customexception;

import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.ResponseStatus;

// Marca esta excepción con el estado HTTP 404 Not Found
@ResponseStatus(HttpStatus.NOT_FOUND)
public class CustomNotFoundException extends RuntimeException {

    private static final long serialVersionUID = 1L;

    private final String codigo;

    // Constructor que acepta un mensaje de error
    public CustomNotFoundException(String message) {
        this(message, "NO_ENCONTRADO");
    }
    // Las features pueden proporcionar un código propio; nunca se conserva null/vacío.
    public CustomNotFoundException(String message, String codigo) {
        super(message);
        this.codigo = codigo == null || codigo.isBlank() ? "NO_ENCONTRADO" : codigo;
    }

    public String getCodigo() {
        return codigo;
    }
}
