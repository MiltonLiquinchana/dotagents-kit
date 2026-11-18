// si-archivo integraciones.gestion_usuarios=organizaciones|aplicacion
import type { GestionApi,GestionResultado } from '@/domains/types/GestionTipos';
// si frontend.llamadas_api=navegador
export interface __ControladorInterfaz__ extends GestionApi {}
// si frontend.llamadas_api=servidor
export type __ControladorInterfaz__ = { [K in keyof GestionApi]: (...args: Parameters<GestionApi[K]>) => Promise<GestionResultado<Awaited<ReturnType<GestionApi[K]>>>> };
// fin
