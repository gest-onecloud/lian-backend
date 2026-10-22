# LiAn V62.6.0 — ROOT RECTIFICATION

- Search no longer returns a raw fixture without prediction probabilities.
- Single-team search uses a 30-day future discovery window and always permits live augmentation.
- Added optional Google discovery/hints; structured football sources remain authoritative.
- Search results preserve historical rows but never use them as a substitute for a current fixture.
- Home advantage is capped/shrunk to prevent venue bias from dominating the ensemble.
- Historical base-rate blend reduced from 15% to 8% to reduce structural home bias.
- Progol continues to use the exact same Model.predict() core.
- Added root-rectification regression tests.
