# VALIDACIÓN FINAL — LiAn V64.2.0

## Scope
Provider/calendar/Match Intelligence root-cause correction. Predictive core preserved byte-for-byte.

## Automated evidence
- 222 tests collected.
- 72 critical/regression tests passed after the provider fix.
- 41 provider + core + HTTP tests passed after the final SofaScore result-sync correction.
- Historical compatibility suites executed individually in prior validation; the isolated CI runner was retained because the legacy monolithic process can be stateful.
- `python backend/validate.py` => `VALIDATION PASS | sqlite=ok | records=230 | tables=42 | frontend=present | temporal-feature-store=present | legacy=none`
- `python -m py_compile $(find backend -name '*.py' -type f)` => PASS
- `node --check frontend/app.js` => PASS
- Predictive model SHA256 unchanged from V64.1.0: `ab9af7a7a98240bbbd86a8e4a6d34d5f3767e0c3efd98f77a7d0458d4e8294f9`

## Root-cause tests
1. SofaScore primary URL is `https://api.sofascore.com/api/v1/...`.
2. ESPN all-soccer has an alternate web API host.
3. If the primary ESPN host fails, the alternate host is actually attempted and parsed.
4. Broad calendar union preserves 6 independent fixtures from two sources in the test scenario.
5. A targeted Cruz Azul schedule returns five future fixtures: Santos, América, Inter Miami, Monterrey and Toluca.
6. Canonical UTC/Mexico duplicate handling remains active.
7. 30-day window remains exact.
8. Predictive model remains V64.0.0 and its bytes are unchanged.

## Live-data limitation
The development sandbox has no external DNS, so direct outbound calls to ESPN/SofaScore/FotMob cannot be executed from this isolated environment. The provider contract and fallback path are therefore validated with deterministic HTTP mocks, while current external schedules were independently cross-checked during the investigation.

## External cross-check used during investigation
Current public schedule sources show substantially more than three football fixtures on 4 September 2026. LiveScore.mobi lists Premier League, LaLiga, Bundesliga, Serie A, Ligue 1, Eredivisie, National League, MLS and additional competitions for that date. SoccerBase independently lists multiple competitions on the same date. Current Cruz Azul schedules list upcoming matches vs Santos (6 Sep), América (12 Sep), Inter Miami (16 Sep), Monterrey (19 Sep), and Toluca (26 Sep).

## Release rule
No predictive-weight change was made. This release exists to repair the provider/data acquisition path only.
