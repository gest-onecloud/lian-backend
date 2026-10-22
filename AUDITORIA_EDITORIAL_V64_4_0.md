# Auditoría editorial y lógica V64.4.0

- No se presentan pruebas mock como pruebas live.
- Las afirmaciones de cobertura se condicionan a fuentes realmente alcanzables.
- Se elimina la recuperación masiva durante una caída total de red.
- La ventana de Match Intelligence se mantiene en 30 días.
- El modelo predictivo permanece separado de la plataforma.
- Las pruebas de regresión de versiones se actualizan para distinguir versión de plataforma y versión del motor.
- La suite de tests bloquea red externa y permite loopback, evitando hangs silenciosos.
- El paquete se revisa después de ser descomprimido y se valida desde su raíz.
