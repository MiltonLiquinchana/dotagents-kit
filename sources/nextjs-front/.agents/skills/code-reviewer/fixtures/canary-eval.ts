/**
 * canary-eval.ts — Fixture de canario para el Paso 0
 *
 * PROPÓSITO: verificar que las dos capas del gate están operativas.
 *
 * ESLint esperado   : error `no-eval` en línea 14
 * SonarQube esperado: `typescript:S1523` (CRITICAL, SECURITY=HIGH)
 *
 * NO MODIFICAR — este archivo es inmutable. Si falla el canario,
 * indica un problema de infraestructura, no de código de la feature.
 */
export const canary = (input: string): void => {
  eval(input); // CANARY — debe ser detectado por ESLint (no-eval) y SonarQube (typescript:S1523)
};
