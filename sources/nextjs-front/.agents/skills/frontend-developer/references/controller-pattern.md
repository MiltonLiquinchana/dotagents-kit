<!-- si-archivo frontend.llamadas_api=navegador -->
## Controller Pattern Básico (Un solo componente)

```tsx
const controllerRef = useRef<MyControllerInterface | null>(null);
useEffect(() => {
<!-- si frontend.notificaciones=react-toastify -->
    // El aviso lo pinta la librería de notificaciones a través de `Notificador`.
    const showErrorMessage = (msg: string) => Notificador.error(msg);
<!-- fin -->
<!-- si frontend.notificaciones=ninguna -->
    // Sin librería de avisos: el mensaje se muestra en la propia pantalla del componente
    // (área de alerta con su estado interno). `console.log` no vale: el usuario no lo ve.
    const showErrorMessage: Mostrar = (msg) => setMensajeAlerta(msg);
<!-- fin -->
    controllerRef.current ??= new MyController(showErrorMessage);
}, []);

if (!controllerRef.current) return;
```

