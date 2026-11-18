-- si-archivo integraciones.gestion_usuarios=organizaciones|aplicacion
-- Esquema mínimo; nombres lógicos adaptados al instanciar, sin DROP de tablas existentes.
-- si integraciones.gestion_usuarios=organizaciones
CREATE TABLE IF NOT EXISTS __Organizaciones__ (
 __OrganizacionId__ INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 __Nombre__ VARCHAR(250) NOT NULL,
 __ClerkOrganizationId__ VARCHAR(255) NOT NULL UNIQUE,
 __FechaCreacion__ DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
 __FechaModificacion__ DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
-- fin
CREATE TABLE IF NOT EXISTS __EstadoPerfiles__ (
 __EstadoPerfilId__ INT NOT NULL PRIMARY KEY,
 __EstadoPerfil__ VARCHAR(50) NOT NULL UNIQUE,
 __Descripcion__ TEXT,
 __FechaCreacion__ DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
 __FechaModificacion__ DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS __Perfiles__ (
 __PerfilId__ INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
 __ClerkUserId__ VARCHAR(250) UNIQUE,
 __Nombres__ VARCHAR(250) NOT NULL,
 __Apellidos__ VARCHAR(250) NOT NULL,
 __Correo__ VARCHAR(250) NOT NULL UNIQUE,
 __EstadoPerfilId__ INT NOT NULL DEFAULT 1,
-- si integraciones.gestion_usuarios=organizaciones
 __OrganizacionId__ INT NOT NULL,
 FOREIGN KEY (__OrganizacionId__) REFERENCES __Organizaciones__(__OrganizacionExternaId__),
-- fin
 __FechaCreacion__ DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
 __FechaModificacion__ DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
 FOREIGN KEY (__EstadoPerfilId__) REFERENCES __EstadoPerfiles__(__EstadoPerfilId__)
);
