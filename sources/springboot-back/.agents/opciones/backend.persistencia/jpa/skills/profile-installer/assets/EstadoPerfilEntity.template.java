// si-archivo integraciones.gestion_usuarios=organizaciones|aplicacion
package __PAQUETE__.entity;
import jakarta.persistence.*;
@Entity @Table(name="__TABLA_ESTADOS__")
public class EstadoPerfilEntity {
 protected EstadoPerfilEntity() {}
 @Id @Column(name="__COL_ESTADO_ID__") private Integer id;
 @Column(name="__COL_ESTADO__",nullable=false,unique=true) private String estado;
 @Column(name="__COL_DESCRIPCION__") private String descripcion;
 @Column(name="__COL_CREACION__",insertable=false,updatable=false) private java.time.LocalDateTime fechaCreacion;
 @Column(name="__COL_MODIFICACION__",insertable=false,updatable=false) private java.time.LocalDateTime fechaModificacion;
}
