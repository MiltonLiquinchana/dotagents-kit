/**
 * Configuración de Redux Store con Factory Pattern
 * 
 * Utiliza una función factory que genera una nueva tienda por cada solicitud,
 * garantizando el aislamiento entre diferentes usuarios y peticiones en SSR.
 */
import { configureStore } from "@reduxjs/toolkit";
// import TuSlice from "./features/TuState/TuSlice";

/**
 * Factory function para crear instancias de Redux Store
 * 
 * @returns Nueva instancia de Redux store configurada
 */
export const makeStore = () => {
  return configureStore({
    reducer: {
      // Registra aquí los slices del estado de la aplicación
      // tuState: TuSlice,
    },
  });
};

/**
 * Tipo que representa la instancia completa del store
 */
export type AppStore = ReturnType<typeof makeStore>;

/**
 * Tipo que representa el estado raíz de toda la aplicación
 */
export type RootState = ReturnType<AppStore["getState"]>;

/**
 * Tipo que representa la función dispatch tipada
 */
export type AppDispatch = AppStore["dispatch"];
