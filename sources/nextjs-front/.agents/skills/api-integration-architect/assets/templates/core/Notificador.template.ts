// Punto único de avisos en pantalla para el núcleo. Las demás plantillas y las skills lo usan
// en lugar de importar directamente la librería de notificaciones: cambiar de librería o de modo
// significa cambiar solo esta plantilla y el contenedor del layout.
//
// La variante concreta se resuelve con las marcas del .agents (clave frontend.notificaciones):
// si frontend.notificaciones=react-toastify
// - Los avisos en pantalla van con `react-toastify` y la configuración de `ToastConfiguration`:
//   cada método llama a la librería; el segundo parámetro `mostrar` (opcional, la firma común
//   de abajo) se IGNORA en esta variante: el aviso se muestra siempre.
// fin
// si frontend.notificaciones=ninguna
// - Los avisos en pantalla van por `mostrar`, la función del componente que guarda el mensaje
//   en su estado y lo pinta en su área de alerta; la consola no vale, el usuario no la ve.
// fin
// si frontend.notificaciones=react-toastify
import { toast } from "react-toastify";
import {
  ERROR_TOAST_CONFIG,
  SUCCESS_TOAST_CONFIG,
  WARNING_TOAST_CONFIG,
} from "./constants/ToastConfiguration";

/** Firma de entrega del aviso, igual en las dos variantes del .agents. */
export type Mostrar = (mensaje: string) => void;

/**
 * Muestra un mensaje de error al usuario con la configuración de aviso de error.
 *
 * @param mensaje texto para el usuario
 * @param mostrar entrega el mensaje en la variante sin librería; aquí se ignora
 */
export function error(mensaje: string, mostrar?: Mostrar): void {
    toast.error(mensaje, ERROR_TOAST_CONFIG);
}

/**
 * Muestra una advertencia al usuario con la configuración de aviso de advertencia.
 *
 * @param mensaje texto para el usuario
 * @param mostrar entrega el mensaje en la variante sin librería; aquí se ignora
 */
export function advertencia(mensaje: string, mostrar?: Mostrar): void {
    toast.warning(mensaje, WARNING_TOAST_CONFIG);
}

/**
 * Muestra un mensaje de éxito al usuario con la configuración de aviso de éxito.
 *
 * @param mensaje texto para el usuario
 * @param mostrar entrega el mensaje en la variante sin librería; aquí se ignora
 */
export function exito(mensaje: string, mostrar?: Mostrar): void {
    toast.success(mensaje, SUCCESS_TOAST_CONFIG);
}
// fin
// si frontend.notificaciones=ninguna
/**
 * Firma para entregar un mensaje al componente que lo muestra en pantalla:
 * guarda `mensaje` en su estado y lo pinta en su área de alerta.
 */
export type Mostrar = (mensaje: string) => void;

/**
 * Envía un mensaje de error al componente que lo muestra en pantalla.
 *
 * @param mensaje texto para el usuario
 * @param mostrar función del componente que guarda el mensaje en su estado y lo pinta
 */
export function error(mensaje: string, mostrar?: Mostrar): void {
    mostrar?.(mensaje);
}

/**
 * Envía una advertencia al componente que la muestra en pantalla.
 *
 * @param mensaje texto para el usuario
 * @param mostrar función del componente que guarda el mensaje en su estado y lo pinta
 */
export function advertencia(mensaje: string, mostrar?: Mostrar): void {
    mostrar?.(mensaje);
}

/**
 * Envía un mensaje de éxito al componente que lo muestra en pantalla.
 *
 * @param mensaje texto para el usuario
 * @param mostrar función del componente que guarda el mensaje en su estado y lo pinta
 */
export function exito(mensaje: string, mostrar?: Mostrar): void {
    mostrar?.(mensaje);
}
// fin
