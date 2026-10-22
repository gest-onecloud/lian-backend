# LiAn V63.1.0 — VALIDACIÓN FINAL

## Tipo de release
PLATFORM HARDENING / CALENDAR + MATCH INTELLIGENCE.

## Regla de promoción
La versión es promocionable porque no modifica el predictor. `backend/core/model.py` es byte-identical a V63.0.0 y su SHA-256 queda registrado en `MODEL_CORE_SHA256_V63_0_0.txt`.

No se presenta V63.1.0 como una mejora de Accuracy. Es una corrección funcional sin degradación del motor predictivo.

## Correcciones verificadas
- Match Intelligence resuelve por `match_id` exacto.
- Se elimina la posibilidad de saltar a otro fixture por fuzzy search de nombres.
- Se deduplica la representación Cruz Azul/Santos del 06/09 20:00 MX frente a 07/09 02:00 UTC cuando corresponde al mismo fixture.
- La búsqueda de un equipo muestra el conjunto actual/futuro de 30 días en lugar de ocultar el resto al auto-seleccionar una coincidencia.
- La ventana operativa es inclusiva: hoy → hoy + 29 días = 30 fechas.
- `/api/calendar-window` devuelve 30 días y no bloquea la interfaz con sincronización histórica de resultados.
- Background fixture/prediction coverage se extiende al horizonte de 30 días.
- Se eliminó el archivo temporal no-runtime `backend/core/model_v600.tmp.py`.

## Pruebas
- Python `py_compile`: PASS.
- Node `--check frontend/app.js`: PASS.
- `backend/validate.py`: PASS.
- `tests/test_v631_calendar_intelligence.py`: 6 PASS.
- `tests/test_v626_root_rectification.py`: 8 PASS.
- `tests/test_v619_universal_search_e2e.py`: 2 PASS.
- `tests/test_v619_universal_search_range.py`: 3 PASS.
- `tests/test_v622_search_all_leagues.py`: 3 PASS.
- `tests/test_v623_universal_all_leagues.py`: 3 PASS.
- `tests/test_v624_data_lifecycle.py`: 3 PASS.
- `tests/test_v630_integrity.py`: 4 PASS.
- `tests/test_http_smoke.py`: 8 PASS.
- `tests/test_v5597_professional.py`: 4 PASS.
- El resto de módulos de regresión históricos fueron ejecutados individualmente en las baterías de validación y no quedó ningún fallo pendiente.
- 47 módulos / 187 tests fueron recolectados en el árbol de regresión.

## Emulación/ejecución HTTP
Servidor ejecutado en puerto aislado con fixtures/resultados live deshabilitados. Verificados:
- `/api/health` → 200, V63.1.0.
- `/api/calendar?date=2026-09-03` → fecha exacta, 4 fixtures, sin duplicados.
- `/api/universal-match?q=cruz azul` → un fixture local futuro canónico, sin duplicado.
- `/api/intelligence?match_id=...` → mismo `match_id`, `resolution=CANONICAL_MATCH_ID`.
- `/api/calendar-window` → 30 fechas, hoy 2026-09-04 a 2026-10-03.

## Limitación de entorno
Este entorno aislado no tiene resolución DNS externa. Por ello no se afirma que ESPN/SofaScore/TheSportsDB hayan respondido en vivo aquí. Los contratos de integración se probaron con mocks deterministas y el servidor HTTP se ejecutó localmente. Antes de uso productivo debe ejecutarse una verificación live desde el equipo/servidor con Internet.
