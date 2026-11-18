<!-- si frontend.llamadas_api=navegador -->
# Controller Providers — Referencia Técnica

Referencia para el patrón Provider de Controllers cuando 2 o más componentes comparten una misma instancia y contexto de error.

## Problema

Cuando múltiples componentes hermanos o en diferentes niveles del árbol necesitan invocar métodos del mismo Controller (por ejemplo, `PedidosController` o `ClientesController`):
* Instanciar múltiples controllers con `useRef` en cada componente duplica el registro en `ExceptionHandler` y crea instancias redundantes.
* Hacer prop-drilling a través de 3 o más niveles de componentes acopla la jerarquía visual innecesariamente.
* Crear un React Context estándar pasando `{ controller: new Controller(...) }` directamente en el `value` crea una nueva referencia en cada re-render, disparando warnings de SonarQube de *Context value stability* y re-renderizando innecesariamente a todos los consumidores.

## Solución: Provider con Referencia Estable + Custom Hook

### Arquitectura

```
<EntityProvider>  (Inicializa controller UNA sola vez con useRef o lazy useState)
  ├── ComponenteA  (consume via useEntityController())
  └── ComponenteB  (consume via useEntityController())
```

### Reglas Canónicas

1. **Estabilidad de Context Value (Cumplimiento SonarQube)**:
   - Se debe mantener la referencia con `useRef` con el objeto completo del contexto o con lazy `useState`:
   ```tsx
   const contextValueRef = useRef<EntityContextType | null>(null);
   if (!contextValueRef.current) {
       // Notificador muestra el aviso; sin librería, mostrar lo guarda en estado.
       const mostrarMensajeError = (msg: string) => Notificador.error(msg, setMensajeAlerta);
       const controller = new EntityController(mostrarMensajeError);
       contextValueRef.current = { controller };
   }
   ```
2. **Propagación Segura de Errores**:
   - El Provider inyecta el handler de UI (el que muestra el aviso en pantalla vía `Notificador`) al constructor del Controller.
   - El Controller lo registra en `ExceptionHandler.defineOnErrorDetect`.
   - Cualquier error en peticiones API bajo ese contexto de controller activará automáticamente el aviso sin requerir manejo manual de errores en los componentes hijos.
3. **Custom Hook Tipado**:
   - Cada Provider expone su hook `use<nomenclatura.controlador_implementacion>()`.
   - Valida que el contexto no sea `null`; si lo es, lanza un error claro: `'use<nomenclatura.controlador_implementacion> debe usarse dentro de [Entity]Provider'`.
   - Retorna directamente `context.controller` (la interface), no el objeto del contexto.

## Cuándo usar cada estrategia

| Escenario | Estrategia recomendada |
| :--- | :--- |
| Un solo componente usa el controller | `useRef` local en el componente (`controllerRef.current ??= new MyController(...)`) |
| 2 o más componentes comparten el controller | `EntityProvider` + `useEntityController()` |
| Estado global de datos (no controllers) | Redux Toolkit (`StoreProvider`) o Zustand |

## Templates

Los templates canónicos están disponibles en:
`assets/templates/providers/EntityProvider.template.tsx`
`assets/templates/providers/useEntityController.template.tsx`
`assets/templates/providers/StoreProvider.template.tsx`
`assets/templates/providers/store.template.ts`


<!-- si frontend.llamadas_api=servidor -->
# Acciones de servidor y estado de UI

La UI no instancia Controllers ni registra callbacks en el servidor. Invoca la Server Action de `app/<ruta>/actions.ts`; la acción crea un Controller por llamada y devuelve un resultado serializable.

```tsx
const resultado = await searchEntidadList(param);
if (!resultado.ok) {
    Notificador.error(resultado.mensaje, setMensajeAlerta);
    return;
}
setDatos(resultado.data);
```

El Controller captura `CustomError`, conserva `apiCode ?? errorCode` en `codigo` y `message` en `mensaje`. No devuelvas errores, funciones o instancias de clase a la pantalla. Para varias secciones comparte únicamente estado de UI con Context o hooks; las credenciales y las capas de acceso a API permanecen en el servidor. `Notificador` vive en el cliente y utiliza la variante de notificaciones generada.

<!-- fin -->
Ejemplos de clientes y pedidos: ejemplo con la convención recomendada; las convenciones efectivas se leen de `.agents/stack.yaml`.
