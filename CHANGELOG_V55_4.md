# LiAn V55.5 — Post-Match Autopsy + Adaptive Calibration

- Preserva las probabilidades prepartido almacenadas después de terminar un encuentro.
- Sincroniza resultados verificados con procedencia y fuente.
- Bootstrap verificado para resultados del 25/08/2026: Valencia 0-1 Betis y 17 partidos de Carabao Cup.
- Fallback de Internet mediante TheSportsDB para resultados finalizados que no estén en el snapshot; solo acepta coincidencia exacta de equipos y marcador final.
- Ejecuta Post-Match Autopsy automáticamente después de incorporar resultados.
- Añade Adaptive Calibration: mide Brier, Log Loss, accuracy, sesgos y recomendaciones.
- No cambia pesos automáticamente con muestras pequeñas; exige mínimo 100 observaciones globales, 50 por segmento y mejora walk-forward fuera de muestra.
- La interfaz muestra FINAL, fuente, ACIERTO/FALLO y diagnóstico de la autopsia.
