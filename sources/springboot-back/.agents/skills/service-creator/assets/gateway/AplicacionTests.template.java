package __PAQUETE__;

import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;

// si devops.infraestructura=jenkins-kubernetes
@SpringBootTest(properties = {"spring.main.cloud-platform=none", "spring.cloud.kubernetes.enabled=false"})
// si devops.infraestructura=ninguna
@SpringBootTest(properties = "spring.main.cloud-platform=none")
// fin
class __CLASE_PRINCIPAL__Tests {

    @Test
    void contextLoads() {
    }
}
