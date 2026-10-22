# LiAn V62.3.0 — UNIVERSAL SEARCH ROOT HARDENING

## Objective
Make single-team and explicit-match search independent of the competition list. Any searchable football team must use the same discovery pipeline regardless of league or country.

## Root corrections
- Direct team discovery now runs before the rolling calendar refresh.
- SofaScore team schedules use five upcoming pages and two recent pages instead of two total pages.
- Team candidate resolution keeps a wider pool and prefers exact football entities.
- Search horizon increased to 60 days for team/pair resolution.
- Broad calendar cross-check expanded to 30 days for single-team searches.
- Pair discovery falls back to an independent broad calendar when team endpoints fail.
- Local synchronization remains persistence/acceleration, not a completeness gate.
- No league whitelist is used to decide whether a team is searchable.
- No prediction/model logic was changed.
- Historical rows are preserved.
