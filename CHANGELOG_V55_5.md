# LiAn V55.5 — Error Intelligence & League Calibration

Base: V55.4 estable.

## Nuevas capacidades
- Inteligencia de errores por liga y equipo.
- Sesgos globales de local/empate/visitante.
- Segmentación por evidencia y confianza.
- Métricas Accuracy, Brier y Log Loss por segmento.
- Diagnóstico de patrones repetidos.
- Nuevo panel `Inteligencia de errores`.
- Endpoint `/api/error-intelligence`.
- Pesos del modelo protegidos: no hay recalibración automática con muestras pequeñas.
- Regla de adopción: muestra global >=100, segmento >=50 y mejora walk-forward fuera de muestra.

## Regresión
Se conserva V55.4 como base y se agrega únicamente la capa diagnóstica.
