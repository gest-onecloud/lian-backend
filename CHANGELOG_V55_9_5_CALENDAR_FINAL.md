# LiAn V55.9.5 — CALENDAR FINAL / DATE TRUTH CORE

## Objetivo
Estabilizar definitivamente el calendario para que una fecha de México corresponda únicamente a los partidos cuya hora de inicio resuelve a esa fecha en `America/Mexico_City`, evitando fugas, duplicados y respuestas incompletas tratadas como completas.

## Cambios
- ESPN `soccer/all/scoreboard` se convierte en la fuente primaria de amplitud para el calendario.
- TheSportsDB queda como fuente secundaria/cross-check; su límite del nivel gratuito de `eventsday` no puede definir la cobertura.
- Los eventos se validan por timestamp convertido a hora de México antes de insertarse.
- El identificador interno de fixtures incorpora fecha + fuente + event id para evitar colisiones entre días.
- El cache solo se considera válido cuando la cobertura es `complete`.
- Una respuesta parcial/incompleta nunca se congela como cache completo.
- Los seeds locales se descubren automáticamente; ya no existe un seed hard-coded para una sola fecha.
- `/api/calendar` es fixture-first: no bloquea la navegación esperando clima, jugadores u otras fuentes de contexto en vivo.
- Se devuelve `calendar_integrity` con fecha exacta, duplicados, cantidad devuelta y cantidad en DB.
- La UI muestra `coverage_status`, fuente primaria y estado de integridad.
- Se agregaron pruebas de autoridad de fuente amplia, cache, fecha México y aislamiento.

## Regla de arquitectura
`timestamp del evento -> America/Mexico_City -> fecha canónica -> deduplicación -> DB -> calendario`

Nunca se deriva la fecha de la URL solicitada si el timestamp verificable del evento contradice esa fecha.

## Validación
- Python compile: PASS
- Structural validation: PASS
- Regression: 74/74 tests, 0 failures
- Database restored after tests: 170 records
- Node syntax check: PASS
