// si-archivo integraciones.gestion_usuarios=organizaciones|aplicacion
package __PAQUETE__.controller;
import __PAQUETE__.security.SvixWebhookVerifier;
import __PAQUETE__.services.*;
import __PAQUETE__.implement.PerfilesServiceImpl;
import __PAQUETE__.repository.PerfilesRepository;
import __PAQUETE__.model.*;
import __PAQUETE__.configuration.PersistenciaErrors;
import tools.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.*;
import org.springframework.http.HttpHeaders;
import org.springframework.dao.DataIntegrityViolationException;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import java.security.SecureRandom;
import java.time.Instant;
import java.nio.charset.StandardCharsets;
import java.util.*;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

class GestionUsuariosTest {
    private final byte[] bytes=new byte[32];
    private final ObjectMapper json=new ObjectMapper();
    private final PerfilesService service=mock(PerfilesService.class);
    private SvixWebhookVerifier verifier;
    @BeforeEach void setup() {
        new SecureRandom().nextBytes(bytes);
        // WHY: secreto efímero creado por la prueba; nunca un valor en el repositorio.
        verifier=new SvixWebhookVerifier("wh"+"sec_"+Base64.getEncoder().encodeToString(bytes));
    }
    private HttpHeaders signed(String payload) throws Exception {
        String id="msg_prueba", timestamp=String.valueOf(Instant.now().getEpochSecond());
        Mac mac=Mac.getInstance("HmacSHA256");mac.init(new SecretKeySpec(bytes,"HmacSHA256"));
        String sign=Base64.getEncoder().encodeToString(mac.doFinal((id+"."+timestamp+"."+payload).getBytes(StandardCharsets.UTF_8)));
        HttpHeaders headers=new HttpHeaders(); headers.add("svix-id",id); headers.add("svix-timestamp",timestamp);headers.add("svix-signature","v1,"+sign);
        return headers;
    }
    private String payload() {
// si integraciones.gestion_usuarios=organizaciones
        // Metadata en la membresía, tal como documenta CreateOrganizationInvitationRequestBody.
        return """
          {"type":"organizationMembership.created","data":{"public_metadata":{"perfilId":8},"organization":{"id":"org_demo"},"public_user_data":{"user_id":"user_demo","identifier":"cliente@example.test"}}}
          """;
// si integraciones.gestion_usuarios=aplicacion
        return """
          {"type":"user.created","data":{"id":"user_demo","public_metadata":{"perfilId":8},"primary_email_address_id":"email_demo","email_addresses":[{"id":"email_demo","email_address":"cliente@example.test"}]}}
          """;
// fin
    }
    @Test void firmaValidaVinculaEventoDelModelo() throws Exception {
        var controller=new ClerkWebhookController(verifier,service,json);String body=payload();
        assertEquals(200,controller.webhook(body,signed(body)).getStatusCode().value());
// si integraciones.gestion_usuarios=organizaciones
        verify(service).vincular(8,"user_demo","cliente@example.test","org_demo");
// si integraciones.gestion_usuarios=aplicacion
        verify(service).vincular(8,"user_demo","cliente@example.test");
// fin
    }
    @Test void rechazaFirmaInvalidaYSinCabeceras() throws Exception {
        var controller=new ClerkWebhookController(verifier,service,json);String body=payload();
        assertEquals(400,controller.webhook(body,new HttpHeaders()).getStatusCode().value());
        HttpHeaders headers=signed(body);headers.set("svix-signature","v1,invalida");
        assertEquals(400,controller.webhook(body,headers).getStatusCode().value());verifyNoInteractions(service);
    }
    @Test void ignoraEventoAjenoFirmado() throws Exception {
        String body="{\"type\":\"session.created\",\"data\":{}}";
        assertEquals(200,new ClerkWebhookController(verifier,service,json).webhook(body,signed(body)).getStatusCode().value());
        verifyNoInteractions(service);
    }
    @Test void preRegistroImponePendienteYDevuelveIdReal() {
        PerfilesRepository repo=mock(PerfilesRepository.class);ClerkGateway clerk=mock(ClerkGateway.class);
        when(repo.call(eq("__SP_CREAR__"),any())).thenAnswer(inv -> {
            var data=json.readTree((String)inv.getArgument(1));assertEquals(EstadoPerfil.PENDIENTE,data.path("estadoPerfilId").asInt());
            assertEquals("cliente@example.test",data.path("correo").asString());assertFalse(data.has("clerkUserId"));
            return List.of(Map.<String,Object>of("perfilId",42L));
        });
        var target=new PerfilesServiceImpl(repo,clerk,json);
        assertEquals(42,target.preRegistro(new PreRegistroRequest("Cliente","Ejemplo"," CLIENTE@example.test "
// si integraciones.gestion_usuarios=organizaciones
            ,1
// fin
        ))); verifyNoInteractions(clerk);
    }
    @Test void duplicadoNoInvitaYProduceConflicto() {
        PerfilesRepository repo=mock(PerfilesRepository.class);ClerkGateway clerk=mock(ClerkGateway.class);
        var duplicate=new DataIntegrityViolationException("duplicado");when(repo.call(eq("__SP_CREAR__"),any())).thenThrow(duplicate);
        var target=new PerfilesServiceImpl(repo,clerk,json);
        assertThrows(DataIntegrityViolationException.class,() -> target.preRegistro(new PreRegistroRequest("Cliente","Ejemplo","cliente@example.test"
// si integraciones.gestion_usuarios=organizaciones
            ,1
// fin
        )));
        assertEquals(409,new PersistenciaErrors().duplicate(duplicate).getStatusCode().value());verifyNoInteractions(clerk);
    }
    @Test void reconciliacionUsaSdkSimuladoYVincula() {
        PerfilesRepository repo=mock(PerfilesRepository.class);ClerkGateway clerk=mock(ClerkGateway.class);
        Map<String,Object> data=new HashMap<>();data.put("perfilId",8);data.put("correo","cliente@example.test");
// si integraciones.gestion_usuarios=organizaciones
        data.put("clerkOrganizationId","org_demo");when(clerk.buscar(8,"cliente@example.test","org_demo")).thenReturn("user_demo");
// si integraciones.gestion_usuarios=aplicacion
        when(clerk.buscar(8,"cliente@example.test")).thenReturn("user_demo");
// fin
        when(repo.call("__SP_BUSCAR__",8,null)).thenReturn(List.of(data));
        when(repo.call("__SP_BUSCAR__",8,"cliente@example.test")).thenReturn(List.of(data));
        new PerfilesServiceImpl(repo,clerk,json).reconciliar(8);
        verify(repo).call("__SP_VINCULAR__",8,"user_demo");
    }
    @Test void httpDuplicadoEs409SinTrazaAunqueExistaAdviceGenerico() throws Exception {
        when(service.preRegistro(any(PreRegistroRequest.class))).thenThrow(new DataIntegrityViolationException("duplicado"));
        var mvc=org.springframework.test.web.servlet.setup.MockMvcBuilders
            .standaloneSetup(new PerfilesController(service))
            .setControllerAdvice(new __PAQUETE__.configuration.ExceptionController(),new PersistenciaErrors()).build();
        String body="""
          {"nombres":"Cliente","apellidos":"Ejemplo","correo":"cliente@example.test"
// si integraciones.gestion_usuarios=organizaciones
          ,"organizacionId":1
// fin
          }
          """;
        mvc.perform(org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post("/solicitar-acceso")
            .contentType("application/json").content(body))
            .andExpect(org.springframework.test.web.servlet.result.MockMvcResultMatchers.status().isConflict())
            .andExpect(org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath("$.<api_error.campo_mensaje>").value("Conflicto de datos"))
            .andExpect(org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath("$.trace").doesNotExist());
    }

}
