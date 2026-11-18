package __PAQUETE__.configuration;

import java.time.OffsetDateTime;
import java.time.ZoneOffset;

/**
 * Record para representar la respuesta de una excepción.
 * Lleva la fecha y el campo de mensaje declarado en `api_error.campo_mensaje` de
 * `.agents/stack.yaml`. Sin traza: la traza se registra en el log y no sale nunca
 * en la respuesta.
 */
public record ExceptionResponse(
    OffsetDateTime timestamp,
    String <api_error.campo_mensaje>__CODIGO_COMPONENTE__
) {
    public ExceptionResponse {
        __NORMALIZAR_CODIGO__
    }

    // La firma de entrada conserva el código aunque el contrato no lo publique.
    public ExceptionResponse(String mensaje, String codigo) {
        this(OffsetDateTime.now(ZoneOffset.UTC), mensaje__CODIGO_ARGUMENTO__);
    }
}
