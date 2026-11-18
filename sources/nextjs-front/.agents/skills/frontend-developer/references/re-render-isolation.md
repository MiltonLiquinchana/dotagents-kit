# Aislamiento de Re-renders — Referencia Técnica

Referencia para los patrones de desacoplamiento de estado que evitan re-renders globales.

## Problema

Un componente Header actualiza un estado Redux (ej. rango de fechas vía `DateRangePicker`).
Si la Page lee ese estado y lo pasa como prop a una Section, **toda la Page se re-renderiza**
cada vez que el usuario cambia una fecha, incluyendo componentes hermanos que no dependen de esos datos.

## Solución: Patrón de Contenedor Autónomo + Trigger Ciego

### Arquitectura

```
Page (useRef solamente, CERO useState)
  ├── HeaderTrigger (onApplyFilter: () => void)
  │     └── DateRangePicker → actualiza Redux internamente
  │     └── Botón "Aplicar" → ejecuta onApplyFilter()
  │
  └── AutonomousSection (forwardRef + useImperativeHandle)
        ├── useSelector → lee Redux directamente (fechas)
        ├── useState → isLoading, data (locales)
        └── handleApplyFilter() → lee fechas de Redux → fetch
```

### Reglas Estrictas

1. **Firma vacía obligatoria**: La función expuesta en `useImperativeHandle` SIEMPRE tiene firma `() => void`.
   ```tsx
   export interface SectionRef {
       handleApplyFilter: () => void; // CERO parámetros
   }
   ```
2. **El Trigger NO pasa datos**: Solo recibe y ejecuta `onApplyFilter?.()`. No lee Redux para enviarlo.
3. **El Consumidor lee Redux directamente**: Usa `useSelector` internamente.
4. **La Page solo sostiene un `useRef`**: Cero `useState`, cero `useSelector`.
5. **Sin `useCallback` en `handleApplyFilter`**: Como se expone únicamente vía ref imperativa, omitir `useCallback` evita recreaciones innecesarias durante selección de fechas.

### Cuándo Aplicar

| Condición | Aplica |
|-----------|--------|
| El estado de una sección re-renderizaría componentes hermanos | ✅ Sí |
| La sección tiene un ciclo de vida de datos independiente | ✅ Sí |
| Solo existe una sección de datos en la página | ❌ No necesario |
| El estado es compartido globalmente | ❌ Usar Redux/Zustand directo |

### Cuándo Aplicar Patrón B (Suscripción Redux en el Consumidor)

| Condición | Aplica |
|-----------|--------|
| Un botón/header dispara una actualización → el consumidor la procesa | ✅ Sí |
| Pasar el estado como prop haría que el disparador también se re-renderice | ✅ Sí |
| El padre necesita transformar el estado antes de enviarlo al hijo | ❌ No |

## Templates

Los templates completos del trío Page + Trigger + Section están en:
`assets/templates/re-render-isolation/`

