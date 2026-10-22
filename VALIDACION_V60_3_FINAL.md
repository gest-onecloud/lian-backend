# LiAn V60.3.0 — Validación Final

## Resultado
`PASS`

### Integridad
- SQLite: OK
- Registros: 202
- Tablas: 39
- Frontend: presente
- Feature Store temporal: presente
- Legacy runtime: none

### Regresión
`93/93 PASS`

### Corrección sistemática cross-competition
La clasificación doméstica se resuelve en orden temporal y auditable:
1. Registry vigente desde 2026-07-01.
2. Team prior.
3. Inferencia histórica previa a la fecha objetivo.
4. Unknown si no existe evidencia.

El puente es simétrico: si A está una división por debajo de B, A recibe -85 Elo y B +85 Elo. La diferencia también modifica de forma limitada la expectativa de gol. No se utiliza el resultado del propio partido para determinar el nivel competitivo.

### Birmingham City vs Brentford
Resultado real: 1-6.
- V60.2.0: 1 — FALLA.
- V60.3.0: 2 — ACIERTO.
- Birmingham: Championship.
- Brentford: Premier League.
- Ajuste competitivo: Birmingham -85 Elo / Brentford +85 Elo.
- Ajuste de goles: -0.17 para el local, simétrico para el visitante.

### Benchmark emparejado disponible
18 partidos con predicción histórica comparable:

| Métrica | V60.2.0 | V60.3.0 | Cambio |
|---|---:|---:|---:|
| 1X2 | 38.89% | 61.11% | +22.22 pp |
| Top-2 | 88.89% | 88.89% | 0 pp |
| Brier | 0.6442 | 0.5610 | -0.0833 |
| Log Loss | 1.0593 | 0.9474 | -0.1119 |

### Muestra de 5 incluyendo Birmingham
- V60.2.0: 20% 1X2 / 80% Top-2.
- V60.3.0: 60% 1X2 / 80% Top-2.

La muestra de cinco no se usa como prueba de suficiencia estadística; se conserva como comprobación rápida solicitada por el usuario.
