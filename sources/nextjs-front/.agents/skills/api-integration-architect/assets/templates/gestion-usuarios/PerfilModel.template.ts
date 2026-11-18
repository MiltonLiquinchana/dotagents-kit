// si-archivo integraciones.gestion_usuarios=organizaciones|aplicacion
import type { __PerfilResponse__ } from '@/domains/responses/__PerfilResponse__';
export class __PerfilModel__ {
  constructor(public readonly datos: __PerfilResponse__) {}
  static formatModelToResponse(model: __PerfilModel__): __PerfilResponse__ { return { ...model.datos }; }
}
