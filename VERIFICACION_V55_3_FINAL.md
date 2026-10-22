# LiAn V55.5 baseline regression — Verificación final

Fecha de validación: 2026-08-25
Base: V55.2 Venue & Advanced Match Intelligence

## Regresión
- backend.validate.py: PASS
- Python compile: PASS
- JavaScript node --check: PASS
- 34 pruebas unit/integration: PASS
- SQLite integrity: PASS
- 114 registros preservados
- 18 tablas presentes
- V54/V54.1/V55/V55.2 heredadas: PASS
- V55.5 baseline regression Decision Intelligence: PASS
- API smoke: PASS
- ZIP re-extraído y vuelto a validar: PASS

## Nuevas funciones
- Estadística ajustada por fuerza del rival.
- Momentum y tendencia reciente.
- Consenso Poisson/ELO/Forma/Monte Carlo.
- Stability Score.
- Counterfactual: sin sede/sin forma.
- Ledger de señales y explicación de la elección.
- Walk-forward backtest.
- Evidencia on-demand versionada.
- Sede específica verificada prevalece sobre neutralidad genérica.

## Monterrey vs Chicago
Sede: SeatGeek Stadium, Bridgeview, Illinois.
Hosting: Chicago Fire FC.
La evidencia oficial del torneo identifica la sede y el hosting; el preview oficial reporta Chicago 4-1-0 en sus cinco partidos previos y Monterrey 3-0-2, además de que era el primer enfrentamiento entre ambos. Estas señales se incorporan como evidencia on-demand con fecha de corte previa al partido.

## Porcentajes finales precalculados para 2026-08-25
Formato: Local / Empate / Visitante

- CF Monterrey vs Chicago Fire FC: 25.8 / 26.1 / 48.1
- Club León vs Real Salt Lake: 30.0 / 25.5 / 44.6
- Sabah vs Hapoel Be’er Sheva: 39.0 / 25.8 / 35.3
- Cardiff City vs Norwich City: 42.4 / 26.2 / 31.4
- Doncaster Rovers vs Middlesbrough: 35.2 / 24.9 / 39.8
- Barnsley vs Crewe Alexandra: 41.0 / 26.3 / 32.7
- Blackburn Rovers vs Sheffield United: 39.4 / 26.0 / 34.5
- Blackpool vs Lincoln City: 35.4 / 24.6 / 40.0
- Cambridge United vs Millwall: 37.1 / 25.3 / 37.6
- Fleetwood Town vs Shrewsbury Town: 43.5 / 26.0 / 30.5
- Ipswich Town vs Leicester City: 46.6 / 24.4 / 29.0
- Plymouth Argyle vs Coventry City: 37.0 / 24.5 / 38.6
- Sheffield Wednesday vs Wolverhampton Wanderers: 40.9 / 25.9 / 33.1
- Southampton vs West Ham United: 47.8 / 24.3 / 27.9
- Stevenage vs Reading: 38.7 / 27.2 / 34.0
- Stoke City vs Hull City: 39.0 / 25.6 / 35.4
- Walsall vs Leyton Orient: 40.6 / 26.4 / 33.0
- Watford vs Peterborough United: 42.4 / 25.6 / 32.0
- Birmingham City vs Brentford: 41.1 / 26.3 / 32.6
- Nottingham Forest vs Leeds United: 39.8 / 27.1 / 33.1
- Valencia vs Real Betis: 40.1 / 25.6 / 34.3
- Bodø/Glimt vs NEC Nijmegen: 39.5 / 26.7 / 33.7
- LASK vs Celtic: 34.9 / 24.5 / 40.6

## Backtest
Muestra disponible: 36 partidos terminados del histórico local.
Accuracy walk-forward: 36.1%
Brier: 0.760
Log Loss: 1.240

Estos números NO se presentan como evidencia de que el modelo ya sea altamente preciso. La muestra es pequeña y la base histórica todavía es insuficiente. La política V55.5 baseline regression evita autoajustar pesos con esta muestra.

## Nota sobre partidos ya finalizados
Si un partido ya terminó, su resultado se usa para autopsia/aprendizaje posterior y nunca se retroinyecta en la predicción previa del mismo partido. Por ello los porcentajes precalculados son pre-match, no retrospectivos.
