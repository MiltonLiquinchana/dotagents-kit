// si-archivo frontend.llamadas_api=servidor
/** Resultado serializable del controlador; codigo prioriza el código de negocio. */
export type Resultado<T> =
    | { ok: true; data: T }
    | { ok: false; codigo: string; mensaje: string };
