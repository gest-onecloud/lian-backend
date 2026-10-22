# LiAn V61.1.4 — VALIDACIÓN EXHAUSTIVA SEPTEMBER ACTIVE

## Problema raíz
V61.1.1/V61.1.2 calcularon correctamente la fecha de México, pero el flujo principal de Match Intelligence usaba `/api/universal-match` sin ejecutar el refresh dinámico. Además quedaron defaults de 11 días en `fixture_sync.py` y `server.py`. La base empaquetada contenía principalmente histórico de agosto, por lo que el buscador seguía devolviendo agosto.

## Corrección definitiva
- `/api/universal-match` ahora ejecuta refresh de 30 días desde `America/Mexico_City` antes de resolver una búsqueda nueva.
- `/api/search` conserva el mismo comportamiento de refresh.
- `FixtureSync.sync_window_cached` y `sync_window` usan 30 días por defecto.
- `/api/calendar-window` usa 30 días.
- Resolver universal e índice inteligente priorizan coincidencias explícitas `LOCAL vs VISITANTE` y después fecha actual/futura.
- No existe una fecha o mes fijo de septiembre en producción.
- Los históricos no se eliminan ni se reescriben.
- Si las fuentes externas fallan, LiAn no inventa partidos y devuelve diagnóstico de refresh.

## Regresión
- pytest: 112 passed, 0 failed.
- unittest: 93 passed, 0 failed.
- Python compileall: PASS.
- Versiones runtime sincronizadas en backend/modelo/frontend: 61.1.4.
- No quedan tokens runtime 61.1.1 ni ventanas days=11 en backend/frontend/tests actuales.

## Casos de septiembre usados como regresión
- Valencia CF vs FC Barcelona — 2026-09-06.
- FC Barcelona vs Feyenoord — 2026-09-09.
- Levante UD vs FC Barcelona — 2026-09-13.
- FC Barcelona vs Racing Club — 2026-09-16.
- Sevilla FC vs FC Barcelona — 2026-09-19.

Estos casos son expectativas de regresión, no seeds de producción.
