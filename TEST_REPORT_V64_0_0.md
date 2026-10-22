# LiAn V64.0.0 — Exhaustive Test Report

## Collected suite
- 50 test modules
- 208 tests collected

## Final critical suite
- 49/49 PASS in combined critical execution
- Includes V64 deep audit/integrity, V63.2 UI, V63.1 calendar/intelligence, V62.6 root rectification, V62.4 lifecycle, V63.0 integrity and HTTP smoke.

## Individual regression execution
The legacy tree was executed module-by-module in isolated Python/pytest processes. The full set of collected tests was exercised; the only slow legacy search/lifecycle module (`test_v621_lifecycle_search.py`) was also run directly and completed 6/6 PASS in 15.07s.

Observed individual PASS totals across the 50 modules: **208/208**.

Some legacy tests use local HTTP servers or external-provider paths. Their processes are isolated/terminated and network-dependent behavior is not treated as live-provider proof.

## Static checks
- `python backend/validate.py` → PASS
- `python -m py_compile $(find backend -name '*.py' -type f)` → PASS
- `node --check frontend/app.js` → PASS
- SQLite `PRAGMA integrity_check` → `ok`

## Deep prediction audit
Verified:
1. zero-history teams cannot become a selection;
2. zero-history matches are explicitly marked `DATOS INSUFICIENTES`;
3. verified venue metadata remains visible but cannot create team strength when both teams have no evidence;
4. minimum four-match team history unlocks the operational gate;
5. three or fewer prior matches remain gated;
6. team data changes probabilities directionally;
7. future results do not change a pre-match prediction;
8. probabilities always remain finite and normalized;
9. gated matches are excluded from Top Picks/Combinadas;
10. model/platform versions are explicit.

## Live-source limitation
The test container has no external DNS connectivity. ESPN/SofaScore/TheSportsDB were therefore not validated against the public Internet from this environment. Their adapters were exercised through deterministic mocks/local HTTP where applicable. Live coverage must be confirmed on an Internet-connected deployment.
