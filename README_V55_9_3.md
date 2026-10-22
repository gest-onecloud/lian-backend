# LiAn V55.9.3 — REGRESSION FIXED

Release incremental over V55.9.2.

Preserves:
- Calendar Date Safe
- Adaptive Learning Core
- AntiError / Post-Match validation
- Contextual Intelligence
- Live Context
- Progol sections
- historical data and existing corrections

Fixes in this release:
1. Reuses one ErrorFingerprint engine per calendar batch, avoiding repeated historical scans.
2. Converts V55.8/V55.9 validation tests to standard unittest; pytest is no longer required.
3. HTTP test server is daemonized/reusable and teardown force-kills only if graceful termination fails.
4. VALIDAR_TODO.bat loads VERSION.txt before displaying the version.
5. Runtime version is consistently 55.9.3.

Final local validation:
- backend/validate.py: PASS
- unittest discovery: 68/68 PASS
- SQLite: OK | 170 records | 32 tables
