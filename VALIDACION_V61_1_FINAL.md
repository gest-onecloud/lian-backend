# LiAn V61.1.0 — Validación final

Base: V61.0.0. Estrategia: evolución incremental, sin eliminación de módulos previos.

## Suite
- `python -m unittest discover -s tests -p 'test_*.py' -q`
- Resultado: **93/93 PASS**

## Nuevas capacidades
- Universal Match Resolver: PASS
- Ambiguity protection: PASS
- Exact home/away pair resolution: PASS
- Prediction timeline endpoint: PASS
- Evidence timeline endpoint: PASS
- Data health endpoint: PASS
- Existing `/api/intelligence`: PASS
- Calendar Safe regression: PASS
- Cross-Competition regression: PASS
- Adaptive Learning / AntiError regression: PASS
- Background / Catch-Up regression: PASS

## Integrity rules
1. No historical pre-match prediction is overwritten.
2. Finished matches without stored pre-match prediction are marked retrospective and excluded from performance evaluation.
3. Search does not fabricate missing matches or data.
4. Ambiguous queries are not silently resolved.
5. Match-side ordering is respected for explicit `Home vs Away` queries.
6. External sources remain optional; no paid football API is mandatory.
7. New endpoints are read-only over prediction history and evidence timelines.

## Scope
V61.1 consolidates the planned Universal Resolver, Data Fusion/Health, Background Catch-Up, Prediction Timeline and professional validation work into one release. It does not claim that model accuracy is 80% or 100%; accuracy remains an empirical benchmark.
