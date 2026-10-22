# LiAn V55.9.3 — REGRESSION FIXED

Incremental release from V55.9.2. Preserves Calendar Date Safe, Adaptive Learning, AntiError, Contextual Intelligence and Live Context.

Fixes:
- Reused one ErrorFingerprint engine per calendar prediction batch instead of rebuilding/scanning historical cases for every match.
- Converted V55.8/V55.9 validation tests to standard unittest so regression does not require pytest to be installed.
- Kept HTTP smoke tests under the existing network-disabled regression policy.
- Bumped runtime/manifest/frontend version consistently to 55.9.3.
- No prediction algorithm reset and no historical data replacement.

## Validación final
- Structural validation: PASS
- Regression: 68/68 tests PASS
- SQLite: OK, 170 records, 32 tables
- No pytest dependency in the regression suite.
- Clean database restored after regression execution.
