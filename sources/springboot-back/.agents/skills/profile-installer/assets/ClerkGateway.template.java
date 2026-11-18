// si-archivo integraciones.gestion_usuarios=organizaciones|aplicacion
package __PAQUETE__.services;
public interface ClerkGateway {
// si integraciones.gestion_usuarios=organizaciones
    void invitar(int perfilId, String correo, String organizacion, String invitador);
    String buscar(int perfilId, String correo, String organizacion);
// si integraciones.gestion_usuarios=aplicacion
    void invitar(int perfilId, String correo);
    String buscar(int perfilId, String correo);
// fin
}
