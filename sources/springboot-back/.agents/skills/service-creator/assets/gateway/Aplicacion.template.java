package __PAQUETE__;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
// si devops.infraestructura=jenkins-kubernetes
import org.springframework.cloud.client.discovery.EnableDiscoveryClient;
// fin

// Clase principal del gateway __NOMBRE__.
@SpringBootApplication
// si devops.infraestructura=jenkins-kubernetes
@EnableDiscoveryClient
// fin
public class __CLASE_PRINCIPAL__ {

	public static void main(String[] args) {
		SpringApplication.run(__CLASE_PRINCIPAL__.class, args);
	}

}
