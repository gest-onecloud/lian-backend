# LiAn V62.3.0 — UNIVERSAL SEARCH ALL LEAGUES

## Root cause fixed
The on-demand broad calendar previously stopped after the first non-empty ESPN range response. A provider could therefore return Premier League/selected competitions while omitting Liga MX or another competition, making the local search appear incomplete.

## Changes
- Broad discovery no longer stops at the first non-empty provider response.
- Independent broad calendars are merged and deduplicated.
- Generic single-team searches use focused team discovery plus an independent broad-calendar cross-check.
- Broad fallback expands when focused team discovery returns no current/future fixture.
- Search results preserve all current/future matches for a team instead of collapsing to one local result.
- Explicit `A vs B` remains strict and requires both sides in the requested orientation.
- Historical matches are preserved but never substituted for a missing current/future fixture.
- No prediction/model algorithm was changed.
- No historical records are deleted.
- Version identity is synchronized across backend, model, learning, frontend and tests.
