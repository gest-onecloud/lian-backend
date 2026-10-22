# Reporte de pruebas V64.6.0

## Resultado
- Pruebas críticas/regresión ejecutadas por módulos: PASS.
- Suite global `pytest -q`: el proceso global no finaliza dentro del límite del entorno; no se usa como evidencia de 100% PASS.
- Módulos individuales ejecutados: PASS salvo el módulo `test_v640_deep_audit.py`, que completó sus 9 pruebas pero no terminó dentro del límite del proceso por comportamiento de cierre heredado; sus 9 casos produjeron PASS antes del timeout.

## Validaciones
- `python -m py_compile $(find backend -name '*.py' -type f)`: PASS
- `node --check frontend/app.js`: PASS
- `python backend/validate.py`: PASS
- SQLite integrity: PASS
- HTTP `/api/health`: PASS
- Prueba de selector en Chromium mediante DOM controlado: PASS para render, apertura, búsqueda, selección y filtrado.

## Prueba específica de UX
Escenario controlado con 3 ligas:
1. Render inicial: botón compacto, menú cerrado.
2. Apertura: menú visible y 3 opciones.
3. Búsqueda `Premier`: 1 opción visible.
4. Selección de primera liga: menú cerrado y 1 tarjeta visible.
5. Reapertura/Escape: cierre del menú.
6. Limpiar: retorno a todas las tarjetas.

## Integridad
El diff funcional frente a V64.5.0 está limitado a:
- selector visual de competencias;
- estilos del selector;
- versiones/documentación coherentes.
