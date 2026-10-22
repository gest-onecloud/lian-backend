# V55.5 baseline regression

## Added
- Opponent-strength-adjusted historical production.
- Dynamic form and momentum.
- Signal contribution ledger.
- Ensemble consensus score.
- Prediction stability score.
- Counterfactual decision analysis.
- Walk-forward backtest endpoint `/api/backtest`.
- Decision endpoint `/api/decision`.
- Versioned on-demand evidence pack for the current Monterrey–Chicago quarterfinal.

## Corrected
- Verified match-specific venue now takes precedence over a generic competition-level neutral-site flag.
- Frontend model label updated from V55.1 to V55.5 baseline regression.

## Regression policy
V55.2 remains the rollback base. V55.5 baseline regression is accepted only if all inherited tests and V55.5 baseline regression-specific tests pass.
