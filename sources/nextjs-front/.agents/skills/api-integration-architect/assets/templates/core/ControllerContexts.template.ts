/**
 * Constantes para los contextos de manejo de errores
 * Centraliza todos los contextos disponibles para evitar errores de tipeo
 * y facilitar el mantenimiento.
 * 
 * Agrega una entrada por cada nuevo Controller que crees en el proyecto.
 */
export const CONTROLLER_CONTEXTS = {
  // Agrega aquí tus contextos de controladores
  // Ejemplo:
  // LECTURA_CONTROLLER: "lectura-controller",
  // PEDIDOS_CONTROLLER: "pedidos-controller",
} as const;

// Tipo derivado para TypeScript
export type ErrorContext = (typeof CONTROLLER_CONTEXTS)[keyof typeof CONTROLLER_CONTEXTS];
