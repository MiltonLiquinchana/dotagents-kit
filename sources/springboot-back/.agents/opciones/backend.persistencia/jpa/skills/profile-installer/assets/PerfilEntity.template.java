// si-archivo integraciones.gestion_usuarios=organizaciones|aplicacion
package __PAQUETE__.entity;
import jakarta.persistence.*;
@Entity @Table(name="__TABLA_PERFILES__")
public class PerfilEntity {
 protected PerfilEntity() {}
 @Id @GeneratedValue(strategy=GenerationType.IDENTITY) @Column(name="__COL_PERFIL_ID__") private Integer id;
 @Column(name="__COL_CORREO__",nullable=false,unique=true) private String correo;
 @Column(name="__COL_CLERK_USER_ID__",unique=true) private String clerkUserId;
 @Column(name="__COL_NOMBRES__",nullable=false) private String nombres;
 @Column(name="__COL_APELLIDOS__",nullable=false) private String apellidos;
 @Column(name="__COL_ESTADO_ID__",nullable=false) private Integer estadoPerfilId;
// si integraciones.gestion_usuarios=organizaciones
 @Column(name="__COL_ORGANIZACION_ID__",nullable=false) private Integer organizacionId;
// fin
 @Column(name="__COL_CREACION__",insertable=false,updatable=false) private java.time.LocalDateTime fechaCreacion;
 @Column(name="__COL_MODIFICACION__",insertable=false,updatable=false) private java.time.LocalDateTime fechaModificacion;
}
