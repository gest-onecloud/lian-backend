# LiAn V62.0.0 — Universal Search Root Architecture

## Root cause fixed
The previous universal-search flow stopped live discovery whenever the local resolver returned `ambiguous`. A single-team query such as `Barcelona` naturally produced multiple historical rows, so the live discovery branch was never reached.

## Fix
- Historical ambiguity no longer blocks live discovery.
- Single-team search discovers current/future fixtures whenever local candidates contain no current/future fixture.
- Explicit A vs B searches always enforce both sides.
- `/api/search` also rejects unrelated fixtures for explicit pair queries.
- Test-only 2099 fixture rows were removed from the shipped database.
- Regression tests added for the exact Barcelona/Valencia failure path.

## Policy
Local history is evidence, not a substitute for a current fixture. Discovery errors remain visible and never silently promote stale history.
