# LiAn V64.3.0 — Provider Transport + Team Discovery Root Fix

## Root-cause audit of V64.2.0

V64.2.0 corrected provider URLs, but its HTTP transport still used one custom `LiAn/...` User-Agent for every provider. That was an invalid assumption: ESPN can reject spoofed browser/custom identities, while SofaScore/FotMob can require browser-like headers. The visible symptom — ESPN=0, SofaScore=0, FotMob=0, TheSportsDB=3 — is consistent with falling through to the only feed returning a small payload.

A second gap remained in Match Intelligence: team discovery depended primarily on TheSportsDB/SofaScore. If both were blocked, the search could not discover the team's future schedule even though ESPN's structured league/team schedule endpoints were available.

## V64.3.0 changes

- Provider-specific HTTP header profiles.
- ESPN requests no longer send a fake browser/User-Agent.
- SofaScore/FotMob receive browser-compatible headers.
- TheSportsDB receives a conventional browser profile but remains secondary.
- FixtureSync broad-empty recovery queries the configured ESPN league scoreboards.
- Match Intelligence adds an independent ESPN team-directory + team-schedule discovery path across configured soccer leagues.
- Team discovery remains capped at 30 returned future candidates.
- The 30-day window is exactly today through today+29.
- Predictive weights, variants and `backend/core/model.py` were not changed.
- Existing calendar date guards and canonical fixture deduplication are preserved.
