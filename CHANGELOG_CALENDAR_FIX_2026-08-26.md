# LiAn V55.6 — Calendar Date/Availability Fix

## Base preserved
- V55.6 Progol Sections remains the base.
- Progol, Revancha, Media Semana, 20 tickets, prediction core, adaptive learning, post-match autopsy, error fingerprint, venue intelligence and existing historical rows are preserved.

## Corrections
1. Future calendar requests no longer trigger a full 11-day network synchronization on every click.
2. A requested future date is synchronized independently with a 5-minute cache.
3. Network/provider failures are captured as diagnostics and do not turn a valid calendar request into an HTTP 500.
4. The frontend health LED now reflects the actual `/api/health` state. A failure loading a selected date is no longer mislabeled as an API failure.
5. Initial calendar date is resolved in `America/Mexico_City`; the old fixed 2026-08-25 value was removed.
6. The 10-day forward window remains supported.
7. A verified 2026-08-27 fixture seed was added for major competitions so the date is not empty when live sources are unavailable.
8. Date purity remains enforced: a provider event whose own date resolves to another Mexico date is rejected.
9. Result synchronization can be disabled in tests with `LIAN_DISABLE_LIVE_RESULTS=1`; production behavior remains online-first with verified-source safeguards.

## Validation
- Python syntax: PASS
- JavaScript syntax (`node --check`): PASS
- SQLite integrity: PASS
- Full regression suite: 61/61 PASS
- Calendar 2026-08-25: 23 matches
- Calendar 2026-08-26: 14 seeded major matches
- Calendar 2026-08-27: 42 seeded major matches
- Date isolation: PASS
- Progol sections: PASS
- Historical records retained: 170 records in the packaged database
