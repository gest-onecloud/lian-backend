# LiAn V62.3.0 — VALIDACIÓN UNIVERSAL SEARCH ALL LEAGUES

## Root cause
The prior on-demand broad discovery could stop after the first non-empty ESPN response. A provider can return selected competitions while omitting Liga MX or another competition. Generic single-team search could therefore appear incomplete.

## Root correction
- Multi-source broad discovery no longer stops at the first non-empty provider.
- Independent daily broad calendar is merged with range results.
- Generic team search uses focused team discovery plus a broad cross-check.
- If focused discovery is empty, broad discovery expands to 14 days.
- Single-team results return all current/future candidates, deduplicated by date + canonical home/away.
- Explicit A vs B remains strict.
- Historical rows remain stored but are never substituted for current/future search results.
- No prediction/model algorithm was changed.
- Version identity is synchronized to 62.3.0.

## Validation executed
- Python compilation: PASS
- Version consistency: PASS
- Final unittest validation batches: 97 PASS, 0 FAIL, 0 ERROR
- New V62.2 search tests: PASS
- Lifecycle/search regression tests: PASS
- Professional engine tests: PASS

## Environment limitation
The full legacy harness also contains pytest-only tests and network-bound tests. This environment does not have pytest installed, and external football endpoints were not treated as a successful validation source. Therefore this report does not claim that live internet providers were verified here.

## Release rule
The package must still be run through the existing Windows launcher on the user's machine. A live-source failure blocks release and requires correction without removing previously validated functionality.
