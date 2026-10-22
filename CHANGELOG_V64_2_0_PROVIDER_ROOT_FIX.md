# LiAn V64.2.0 — Provider Root Fix

## Root cause found
The calendar and Match Intelligence code was using the SofaScore web host (`www.sofascore.com/api/v1/...`) as the primary JSON endpoint. The public API is served from `api.sofascore.com/api/v1/...`. In the affected environment this caused SofaScore requests to fail, leaving TheSportsDB as the only successful broad source; its free Schedule Day endpoint is limited to 3 records. That exactly explains the repeated 3-match screen and why a single-team search could collapse to the one bundled Cruz Azul–Santos fixture.

## Changes
- SofaScore daily, team search, next and previous event endpoints now use `api.sofascore.com` first.
- Legacy `www.sofascore.com` remains only as a fallback for installations where the API host is unavailable.
- ESPN all-soccer now has an alternate `site.web.api.espn.com` fallback.
- The same corrected SofaScore host is used by result synchronization and broad calendar discovery.
- Predictive weights, variants and `backend/core/model.py` were not changed.
- Platform version: 64.2.0; predictive model remains 64.0.0.

## Why this is different
This is not a UI-only patch. The failing data path was corrected at the provider adapter layer, where the missing fixtures originated.
