# LiAn V61.1.4 — SEPTEMBER ACTIVE / DYNAMIC FIX

## Root cause found in V61.1.1
The runtime still contained 11-day synchronization defaults in fixture_sync.py and server.py, while the bundled database contained only August fixtures. Dynamic Mexico date calculation existed, but the search/calendar did not reliably populate the current/future window before resolving a query.

## Corrections
- 30-day rolling fixture window from America/Mexico_City.
- Search-triggered refresh uses the current Mexico date and force-refreshes the rolling window when no current/future result exists.
- Calendar-window uses the same 30-day rolling policy.
- Universal/intel search gives explicit `home vs away` matches strong priority and then applies temporal priority so current/future fixtures outrank stale August rows.
- No fixed month or fixed calendar date introduced.
- Historical rows are never deleted.
- No post-match result is used to alter pre-match predictions.

## Validation policy
The version is not considered complete until local regression, HTTP smoke, dynamic date tests, and explicit September fixture-resolution tests pass. External-source availability remains environment-dependent; LiAn records source failures instead of inventing fixtures.
