// si-archivo integraciones.gestion_usuarios=organizaciones|aplicacion
import type { __EstadoPerfilResponse__ } from '@/domains/responses/__EstadoPerfilResponse__';
export class __EstadoPerfilModel__ {
  constructor(public readonly datos: __EstadoPerfilResponse__) {}
  static formatModelToResponse(model: __EstadoPerfilModel__): __EstadoPerfilResponse__ { return {...model.datos}; }
}
