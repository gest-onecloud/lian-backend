# LiAn V61.1.0

Unified release consolidating the planned Universal Match Resolver, Data Fusion/Health, Background Catch-Up, Prediction Timeline and professional validation architecture without destructive rewrites.

Run: `LAUNCHER_LIAN.bat`
Background: `run_background.py`

API additions:
- `/api/universal-match?q=Home%20vs%20Away`
- `/api/data-health`
- `/api/prediction-timeline?match_id=...`

The system is local-first. External feeds are optional and must be configured by the user; LiAn never fabricates missing data.
