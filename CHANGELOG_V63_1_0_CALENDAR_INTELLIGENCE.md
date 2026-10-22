
## V63.2.0 — UI/Estado/Cache hardening
- Corrección de estados retrospectivos: nunca se muestran como FALLA/ACIERTO si no existe predicción prepartido.
- Separación explícita entre plataforma V63.2.0 y motor predictivo V63.0.0.
- Cache-control no-store para HTML/JS/CSS/API para evitar UI antigua en navegador.
- Corrección de /api/competitions y refresco de Inteligencia de errores.
# LiAn V63.1.0 — Calendar + Match Intelligence Rectification

## Baseline
V63.0.0. The predictive core `backend/core/model.py` was not modified.

## Fixed
- Match Intelligence resolves an opened fixture by canonical `match_id`; it no longer re-searches by team names and can jump to a different fixture.
- Universal Match Search deduplicates provider variants and the Mexico midnight UTC representation (example: Cruz Azul vs Santos, Sep 6 20:00 MX vs Sep 7 02:00 UTC).
- Single-team search exposes the complete current/future 30-day candidate set instead of auto-collapsing to one card.
- The 30-day window is inclusive: today through today + 29 days.
- `/api/calendar-window` now returns exactly 30 future days and no longer performs a 31-day historical learning sync in a UI request.
- Background fixture/prediction coverage was extended to the full 30-day forward window.
- Clearly unused temporary `backend/core/model_v600.tmp.py` and the local development backup generated during this patch were removed.

## Predictive-core protection
- No changes to model formulas, ensemble weights, learning weights, calibration logic, or predictive features in `backend/core/model.py`.
- SHA-256 of the predictive core is recorded in `MODEL_CORE_SHA256_V63_0_0.txt`.

## Validation
- Python compilation: PASS.
- Frontend Node syntax check: PASS.
- Static validation: PASS.
- HTTP smoke tests: PASS.
- Regression tests were executed per test module; calendar/search/intelligence regression additions also PASS.
- Live-provider access could not be exercised from this isolated build environment because external DNS/network access is unavailable. Provider-backed behavior was therefore validated with deterministic mocks and offline HTTP execution.
