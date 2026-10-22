# LiAn V61.1.4 — Targeted Match Search

Fixes the remaining search gap: the rolling calendar can contain September fixtures while an explicit query such as `Valencia vs Barcelona` still returns no result because the pair is absent from the local index and the daily broad feeds did not populate it.

The primary UI route now keeps the existing rolling refresh, then performs targeted team-level discovery for explicit `Home vs Away` queries. It uses independent free public endpoints, merges candidate schedules, applies an exact home/away gate, deduplicates, and only then upserts verified events into the existing canonical match table.

No historical rows are deleted or rewritten. No fixture is synthesized without upstream event data.
