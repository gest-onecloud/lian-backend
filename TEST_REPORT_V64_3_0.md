# Test Report — LiAn V64.3.0

## Root-cause correction
V64.2.0 had corrected provider URLs but still used one custom LiAn User-Agent across providers. V64.3.0 introduces provider-specific HTTP transport profiles and independent ESPN team-directory/schedule discovery. The calendar light path also recovers through ESPN league scoreboards when all broad feeds are empty.

## Test result
- Test modules: 54
- Tests collected: 227
- Tests executed individually: 227
- Result: 227 PASS / 0 FAIL
- Critical new V64.3 tests: 5 PASS
- V64.2 provider regression: 4 PASS
- V64.1 calendar/source tests: 7 PASS
- V63.1 calendar/intelligence tests: 6 PASS
- V64.0 deep audit: 9 PASS
- V64.0 prediction integrity: 5 PASS
- HTTP smoke: 8 PASS

## Static validation
- Python `py_compile` over backend: PASS
- `node --check frontend/app.js`: PASS
- `python backend/validate.py`: PASS
- SQLite integrity/schema validation: PASS
- Predictive core SHA256 unchanged: PASS

## Important limitation
The isolated development environment cannot make direct DNS/network calls to the public provider hosts. Therefore provider availability from the user's Windows machine is not falsely claimed as an end-to-end live test. The code paths were tested with deterministic provider payloads, transport/header assertions, fallback/recovery cases, and regression tests. A live installation will expose source failures in diagnostics instead of silently treating TheSportsDB's small response as complete coverage.
