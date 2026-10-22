# LiAn V55.9.5 — REGRESSION / PERFORMANCE FIX

Base: V55.9.3. Incremental only; no project reset.

## Root causes fixed
- Historical `/api/calendar` requests were performing learning/result synchronization work that did not belong to read-only date navigation.
- Model prediction repeated expensive temporal ELO and feature-store queries for every match.
- Monte Carlo used 30,000 samples per match even though the exact Poisson distribution is already calculated; this created unnecessary latency in calendar batches.
- Regression execution could hang after a successful unittest suite because test subprocesses/threads were not lifecycle-safe.
- Several legacy version assertions and runtime labels still referenced prior versions.

## V55.9.5 behavior
- Historical calendar reads are read-only and do not trigger live synchronization or calibration.
- Temporal ELO is cached per `as_of` date within a model run.
- Team, opponent, league and baseline feature calculations are memoized within a model run.
- Monte Carlo is reduced to 6,000 deterministic samples per match; the exact Poisson calculation remains the primary component.
- Live result synchronization honors `LIAN_DISABLE_LIVE_RESULTS`.
- Live context honors `LIAN_DISABLE_LIVE_CONTEXT`.
- Regression uses an isolated project copy and terminates the test process once the final `OK`/failure state is observed, preventing a successful test run from being reported as a timeout.

## Verification
- Structural validation: PASS
- Python compileall: PASS
- HTTP smoke: PASS
- Regression: 71/71 tests PASS
- No runtime 55.9.3 token remains in production code/frontend.
