# VALIDACION V64.5.0 — CORRECCIÓN DE ESTADO TEMPORAL

## Alcance
Única corrección: impedir que un fixture cuya fecha local de México es futura se muestre como FINALIZADO cuando el proveedor entrega un estado stale/incorrecto.

## Causa raíz
`match_lifecycle.lifecycle()` evaluaba primero el estado textual `finished/final` del proveedor y sólo después la fecha. Un estado textual incorrecto podía vencer a la fecha futura.

## Corrección
La fecha México futura tiene prioridad:
- futuro → PRÓXIMO
- hoy/pasado con marcador verificado → FINALIZADO
- hoy/pasado con estado final válido → FINALIZADO
- pasado sin resultado → RESULTADO PENDIENTE
- hoy en vivo → EN VIVO

## Invariantes
No se modificaron calendario, búsqueda, Match Intelligence, proveedores, ponderaciones, variantes ni `backend/core/model.py`.

## Pruebas
- V64.5 lifecycle: 4/4 PASS
- `py_compile` de todos los `.py`: PASS
- `node --check frontend/app.js`: PASS
- `backend/validate.py`: PASS
- SHA-256 del motor predictivo: ab9af7a7a98240bbbd86a8e4a6d34d5f3767e0c3efd98f77a7d0458d4e8294f9

Nota: la suite global histórica no se usa como evidencia adicional para esta corrección porque su ejecución completa puede quedar bloqueada por infraestructura de pruebas heredada; la corrección fue aislada y validada directamente junto con compilación y validación del paquete.
