package __PAQUETE__.configuration;

import __PAQUETE__.configuration.customexception.CustomConflictException;
import __PAQUETE__.configuration.customexception.CustomNotFoundException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.context.request.WebRequest;
// si backend.lombok=true
import lombok.extern.slf4j.Slf4j;
// fin
// si backend.persistencia=jpa
import org.springframework.orm.jpa.JpaSystemException;
// fin
// si backend.lombok=false
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
// fin

import java.util.Objects;
import java.util.stream.Collectors;

/**
 * Controlador de excepciones global para el microservicio __NOMBRE__.
 * Centraliza la gestión de excepciones: respuestas uniformes con la fecha y el campo de
 * mensaje de `api_error.campo_mensaje`. La traza se registra en el log y no sale nunca
 * en la respuesta. Si hay campo de código: NO_ENCONTRADO (404), CONFLICTO (409),
 * DATOS_INVALIDOS (400) y ERROR_INTERNO (500); las excepciones de negocio admiten
 * un código propio. Con campo_codigo null no se publica ese campo.
 */
// si backend.lombok=true
@Slf4j
// fin
@RestControllerAdvice
public class ExceptionController {
// si backend.lombok=false
    private static final Logger log = LoggerFactory.getLogger(ExceptionController.class);
// fin

    /**
     * Maneja cualquier excepción no controlada. Registra la traza en el log (ERROR) y
     * devuelve 500 con el mensaje de la excepción.
     */
    @ExceptionHandler(Exception.class)
    public final ResponseEntity<ExceptionResponse> handleAllException(Exception ex, WebRequest request) {
        log.error("Excepción interna del servidor no controlada: ", ex);
        ExceptionResponse exceptionResponse = new ExceptionResponse(ex.getMessage(), "ERROR_INTERNO");
        return new ResponseEntity<>(exceptionResponse, HttpStatus.INTERNAL_SERVER_ERROR);
    }

    /**
     * Maneja recursos inexistentes (404), con aviso en el log (WARN).
     */
    @ExceptionHandler(CustomNotFoundException.class)
    public final ResponseEntity<ExceptionResponse> handleCustomNotFoundException(CustomNotFoundException ex, WebRequest request) {
        log.warn("Recurso no encontrado: {}", ex.getMessage());
        ExceptionResponse exceptionResponse = new ExceptionResponse(ex.getMessage(), ex.getCodigo());
        return new ResponseEntity<>(exceptionResponse, HttpStatus.NOT_FOUND);
    }

    /**
     * Maneja conflictos de negocio o datos duplicados (409), con aviso en el log (WARN).
     */
    @ExceptionHandler(CustomConflictException.class)
    public final ResponseEntity<ExceptionResponse> handleCustomConflictException(CustomConflictException ex, WebRequest request) {
        log.warn("Conflicto de negocio detectado: {}", ex.getMessage());
        ExceptionResponse exceptionResponse = new ExceptionResponse(ex.getMessage(), ex.getCodigo());
        return new ResponseEntity<>(exceptionResponse, HttpStatus.CONFLICT);
    }

// si backend.persistencia=jpa
    /**
     * Maneja fallos de persistencia (409 para proteger la integridad transaccional),
     * con la causa raíz registrada en el log (ERROR).
     */
    @ExceptionHandler(JpaSystemException.class)
    public ResponseEntity<ExceptionResponse> handleSQLException(JpaSystemException ex, WebRequest request) {
        log.error("Error del sistema de persistencia (JPA): ", ex);
        Throwable rootCause = ex.getRootCause();
        String message = rootCause != null ? rootCause.getMessage() : ex.getMessage();
        ExceptionResponse exceptionResponse = new ExceptionResponse(message, "CONFLICTO");
        return new ResponseEntity<>(exceptionResponse, HttpStatus.CONFLICT);
    }
// fin

    /**
     * Maneja cuerpos JSON inválidos y campos de fecha con formato incorrecto (400).
     */
    @ExceptionHandler(HttpMessageNotReadableException.class)
    public ResponseEntity<ExceptionResponse> handleHttpMessageNotReadable(
            HttpMessageNotReadableException ex,
            WebRequest request) {
        log.warn("Request JSON inválido: {}", ex.getMessage());
        ExceptionResponse exceptionResponse = new ExceptionResponse(
                "La petición no es un JSON válido o un campo de fecha no cumple el formato esperado", "DATOS_INVALIDOS");
        return new ResponseEntity<>(exceptionResponse, HttpStatus.BAD_REQUEST);
    }

    /**
     * Convierte los errores de validación del request en una respuesta 400 uniforme.
     */
    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ExceptionResponse> handleMethodArgumentNotValid(
            MethodArgumentNotValidException ex,
            WebRequest request) {
        log.error("Error de validación: ", ex);
        String messages = ex.getBindingResult()
                .getFieldErrors()
                .stream()
                .map(fieldError -> Objects.requireNonNullElse(
                        fieldError.getDefaultMessage(),
                        "Error de validación"))
                .collect(Collectors.joining(", "));
        ExceptionResponse exceptionResponse = new ExceptionResponse(messages, "DATOS_INVALIDOS");
        return new ResponseEntity<>(exceptionResponse, HttpStatus.BAD_REQUEST);
    }
}
