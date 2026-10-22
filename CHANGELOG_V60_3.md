# LiAn V60.3.0 — Cross-Competition Systematic Correction

## Objetivo
Corregir de forma general el sesgo que podía sobrevalorar al local cuando un partido de copa enfrenta equipos de distinto nivel doméstico.

## Cambios
- Registro temporal de competición doméstica para equipos 2026/27 presentes en el dataset de Carabao.
- Resolución `registry -> team prior -> historical inference -> unknown`.
- Puente competitivo simétrico y acotado: 85 Elo por nivel de diferencia, máximo ±255.
- Ajuste de expectativa de gol separado del ajuste Elo, también acotado.
- El resultado del partido objetivo nunca participa en la clasificación competitiva.
- El pick sigue siendo libre: 1/X/2; no se fuerza visitante.
- Se exponen competición y fuente de resolución en `features` para auditoría.
- Benchmark de cinco partidos con Birmingham–Brentford incluido explícitamente.
- Regresión completa heredada conservada.

## Validación
- 93 pruebas unitarias: PASS.
- `backend/validate.py`: PASS; SQLite íntegro, 202 registros, 39 tablas.
- Benchmark comparable disponible: 18 partidos.
- V60.2.0: 38.89% 1X2, 88.89% Top-2, Brier 0.6442, Log Loss 1.0593.
- V60.3.0: 61.11% 1X2, 88.89% Top-2, Brier 0.5610, Log Loss 0.9474.
- Cambio: +22.22 pp en 1X2, Brier -0.0833, Log Loss -0.1119.

## Benchmark de 5 partidos incluyendo Birmingham–Brentford
- V60.2.0: 20% 1X2, 80% Top-2.
- V60.3.0: 60% 1X2, 80% Top-2.
- Birmingham City 1–6 Brentford: V60.2.0 = 1 (fallo); V60.3.0 = 2 (acierto).

## Política
Esta mejora no se promociona por cinco partidos. El benchmark de cinco partidos es diagnóstico. La decisión de conservar el cambio se apoya en la comparación emparejada disponible y en métricas probabilísticas, además de la regresión completa.
