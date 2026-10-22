# LiAn V60.3.0 — Cross-Competition + Squad Strength Intelligence

- Added leakage-safe inference of a team's domestic competition from prior completed matches.
- Added explicit team competition registry support for cases with insufficient local history.
- Added bounded cross-competition goal-rate adjustment in addition to the ELO bridge.
- Added a targeted regression for Birmingham City vs Brentford.
- Preserved historical prediction records; no post-match result is used to alter the historical prediction.
- Benchmark remains 1/X/2 agnostic: the model is never forced to choose Local.
