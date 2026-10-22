# LiAn V63.0.0 — VALIDACIÓN DE PROMOCIÓN

Fecha: 2026-09-04
Base: V62.6.0 ROOT RECTIFIED
Nueva versión: V63.0.0

## Regla de promoción
- Nunca se promueve si Accuracy empeora.
- Brier y Log Loss no pueden empeorar.
- Si Accuracy queda igual y las métricas probabilísticas mejoran, se permite promoción si las regresiones funcionales son cero.
- El test de 20 partidos es diagnóstico; no se presenta como prueba definitiva.

## Test congelado de 20 partidos
- Semilla: 20260904
- V62.6.0 Accuracy: 0.6000 (60.0%)
- V63.0.0 Accuracy: 0.6000 (60.0%)
- Delta Accuracy: +0.00 pp
- V62.6.0 Brier: 0.537368
- V63.0.0 Brier: 0.537340
- Delta Brier: -0.000028 (menor es mejor)
- V62.6.0 Log Loss: 0.912965
- V63.0.0 Log Loss: 0.912927
- Delta Log Loss: -0.000038 (menor es mejor)

## Validación walk-forward de 100 partidos
- V62.6.0: Accuracy 45.0%, Brier 0.646275, Log Loss 1.070529
- V63.0.0: Accuracy 45.0%, Brier 0.646262, Log Loss 1.070509
- Accuracy: sin degradación
- Brier: mejora mínima
- Log Loss: mejora mínima

## Validación histórica emparejada disponible (18 snapshots)
- V62.6.0: Accuracy 38.89%, Brier 0.644219, Log Loss 1.059347
- V63.0.0: Accuracy 61.11%, Brier 0.538363, Log Loss 0.918014
- Delta Accuracy: +22.22 pp
- Delta Brier: -0.105856
- Delta Log Loss: -0.141333

## Cambios incorporados
1. Strength of Schedule temporal: fuerza de los rivales recientes, calculada solo con partidos anteriores al cutoff.
2. Capa de calidad de XI/plantel: preparada para snapshots reales; si no hay datos de jugadores, permanece neutral y no inventa valor.
3. Persistencia Historical Master: warehouse histórico con identidad, resultado, ELO pre-match y calidad de dato.
4. Promotion Gate persistente: registra y rechaza regresiones predictivas.
5. Post-Match: una reconstrucción retrospectiva puede mostrar ACIERTO si la selección coincide, pero queda marcada como RETROSPECTIVE_DISPLAY_ONLY y no alimenta métricas pre-match.
6. Versión y regresiones sincronizadas a V63.0.0.

## Importante
No se declara +10 pp de mejora en el test congelado de 20: la Accuracy quedó en 60.0%, igual al baseline. La versión es promocionable bajo la nueva regla porque no degrada Accuracy y mejora Brier/Log Loss, además de incorporar infraestructura y señales nuevas sin inventar datos de plantel. El objetivo de +10 pp queda como objetivo de investigación, no como resultado fabricado.

## Datos históricos
El Historical Master contiene 110 partidos terminados de la base actual. La cobertura de jugadores sigue siendo 0 en la base actual; por eso la capa de plantel está preparada pero no se utiliza como señal fuerte hasta que se ingieran datos reales.
