# LiAn V55.7 — Adaptive Learning + Anti-Error

## Correcciones críticas
- El resultado real de un partido se deriva exclusivamente del marcador final verificado: `1`, `X` o `2`.
- La interfaz ya no decide `ACIERTO/FALLO` leyendo un registro de autopsia potencialmente antiguo o inconsistente.
- Las autopsias inconsistentes se reparan automáticamente y se registra la reparación en `learning_audit`.
- El caso Acassuso 1–2 San Telmo queda cubierto por una prueba de regresión: una predicción `1` debe ser `FALLO` y el resultado real `2`.

## Adaptive Learning Engine
- Historial de resultados y señales con aislamiento temporal.
- Calibración por resultado con suavizado bayesiano y límites estrictos.
- Rendimiento histórico por señal.
- Correcciones por competición únicamente con muestra previa suficiente.
- No se utiliza ningún resultado posterior a la fecha del partido para calcular su predicción.
- Las modificaciones están acotadas para impedir oscilaciones violentas del modelo.

## Seguridad
- No se eliminan partidos históricos.
- No se modifica la predicción prepartido después del resultado.
- La predicción almacenada sigue siendo la fuente de verdad para la autopsia.
- El marcador verificado es la fuente de verdad para determinar el acierto.
- Se mantiene el calendario por fecha y hora de México.
