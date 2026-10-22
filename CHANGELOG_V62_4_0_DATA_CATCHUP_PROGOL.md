# LiAn V62.4.0 — DATA CATCH-UP + SEARCH RESPONSE HARDENING + PROGOL CURRENT

## Root corrections
- Rolling fixture refresh covers yesterday, today and the next 14 days.
- Background catch-up populates past fixtures before attempting result verification, so a PC outage no longer prevents the result from entering the learning pipeline.
- Universal search has a local-current fast path and bounded concurrent live discovery; slow providers no longer freeze the UI.
- API JSON serialization accepts numpy scalar values returned by statistical calculations.
- Current and previous-day fallback snapshots are bundled only as offline safety data; live sources remain authoritative when available.
- Progol current contest updated to 2349; 2348 remains available as historical benchmark. Contest ticket records now use the current Model.VERSION instead of a stale V60 marker.
- No prediction formula was deleted or replaced.

## Learning integrity
A historical result without an immutable pre-match prediction is displayed as historical/retrospective evidence but is not counted as a pre-match accuracy hit. This prevents leakage and false performance inflation.
