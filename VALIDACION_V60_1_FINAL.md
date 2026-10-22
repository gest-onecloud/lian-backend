# LiAn V60.3.0 — Validación final

## Cambios
- Benchmark profesional modelo anterior vs modelo actual.
- Benchmark aleatorio reproducible de 5 partidos.
- Walk-forward actual con Brier y Log Loss.
- Historical Intelligence con H2H ponderado por recencia y ajuste acotado.
- Historical base-rate guard estrictamente temporal para reducir sesgo de selección local/visitante.
- No se fuerza Local: 1/X/2 son salidas posibles.
- Calendar Safe, Data Fusion, deduplicación, Source Manager, Catch-Up, Background Engine, AntiError, Adaptive Learning, Post-Match y Progol conservados.

## Pruebas ejecutadas
- Sintaxis Python completa: PASS.
- Suite histórica de calendario: PASS.
- HTTP smoke: PASS en ejecución individual.
- V60 Background: PASS.
- Benchmark: PASS.
- V552/V553/V554/V555/V556/V557/V558/V5591/V5594/V5596/V5597/V559 live: PASS en ejecución individual.

El runner agregado heredado puede no finalizar correctamente en algunos entornos por su propio control de proceso; por eso la validación final también se ejecuta por archivo. No se declara una regresión global PASS basada en un proceso que no termina.

## Benchmark real sobre la base incluida
La base contiene 170 partidos y 79 predicciones históricas, pero solamente 18 de esas predicciones tienen partido terminado y son comparables directamente. Por ello no se falsifica un benchmark de 100 pares: se reportan 18 pares y 54 partidos para el walk-forward disponible.

### 5 aleatorios reproducibles
Semilla: 20260902.

- Ipswich Town 3-1 Leicester City: anterior 1 / actual 1 — ambos aciertos.
- Sheffield Wednesday 0-2 Wolverhampton Wanderers: anterior 1 / actual 1 — ambos fallos.
- Barnsley 3-2 Crewe Alexandra: anterior 1 / actual 1 — ambos aciertos.
- Nottingham Forest 0-2 Leeds United: anterior 1 / actual 1 — ambos fallos.
- Birmingham City 1-6 Brentford: anterior 1 / actual 1 — ambos fallos.

Resultado muestra 5: anterior 40%, nuevo 40%; Top-2 100% vs 100%.

### Comparación de los 18 pares disponibles
- Anterior 1X2: 38.89%.
- Nuevo 1X2: 33.33%.
- Anterior Top-2: 88.89%.
- Nuevo Top-2: 88.89%.
- Brier: 0.6442 → 0.6431 (mejora pequeña).
- Log Loss: 1.0593 → 1.0557 (mejora pequeña).

La conclusión es deliberadamente conservadora: V60.1 mejora ligeramente las métricas probabilísticas, pero todavía no demuestra una mejora de acierto 1X2 en esta muestra. No se fuerza una afirmación de 80%.
