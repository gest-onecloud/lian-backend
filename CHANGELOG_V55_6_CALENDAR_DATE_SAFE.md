# LiAn V55.6 — Calendar Date Safe

This is a surgical change on the validated V55.6 Progol Sections base.

## Fixed
- Canonical calendar date is America/Mexico_City, not the machine/UTC date.
- Fixture providers are now subject to a hard event-date gate.
- A provider event is rejected when its own date/timestamp resolves to a different Mexico date than requested.
- ESPN public scoreboard endpoints are added as a secondary fixture source for major competitions.
- TheSportsDB remains a secondary source but can no longer leak events across dates.
- Fixture times from ISO timestamps are converted to Mexico City time before storage.
- Yesterday is reconciled first so verified results can enter the existing Post-Match/Adaptive Calibration flow.
- Historical navigation remains local-first and does not trigger forward synchronization.
- The API response is filtered again by exact requested date as a final invariant.
- August 26, 2026 verified fixture seed is bundled so today's principal fixtures are available even before an Internet sync succeeds.

## Preserved
- V55.6 model, historical data, Progol Sections, 20-ticket generation, Post-Match Autopsy, Error Fingerprint, Adaptive Calibration, Explainability, Venue Intelligence and Decision Intelligence.
- No rows are deleted.
