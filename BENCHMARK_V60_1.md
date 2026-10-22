# LiAn V60.3.0 — Benchmark profesional

Esta versión agrega un benchmark reproducible y leakage-safe para comparar la predicción histórica almacenada contra el modelo actual.

## Reglas
- Las predicciones históricas se leen de `predictions` y no se modifican.
- La nueva predicción usa solamente datos anteriores a la fecha del partido.
- El benchmark no escribe aprendizaje, reviews ni nuevas predicciones.
- 1/X/2 no se fuerza a local.
- Cinco partidos aleatorios sirven como control rápido, no como prueba de precisión estadística.
- La promoción de cambios exige mejora fuera de muestra y revisión de Brier/Log Loss.

## Endpoints
- `/api/benchmark?limit=200&seed=20260902`
- `/api/benchmark-5?seed=20260902`
