# LiAn V61.1.1 — DYNAMIC CALENDAR DATE / SEARCH FRESHNESS

## Objetivo
Eliminar la dependencia práctica de fechas históricas (por ejemplo agosto) en el buscador y hacer que el contexto de calendario siga automáticamente la fecha vigente de México.

## Cambios
- `America/Mexico_City` es la fuente única para determinar el día corriente.
- El buscador prioriza partidos de hoy y futuros antes que partidos históricos.
- Si una consulta no encuentra un partido actual/futuro, el backend actualiza automáticamente una ventana móvil de 11 días desde hoy y vuelve a buscar.
- Se conserva todo el histórico; no se borran partidos anteriores.
- El Background Engine usa la fecha de México y no UTC para fixtures/resultados.
- No hay fechas `2026-08-*` codificadas en la lógica de búsqueda.
- Las fuentes fallidas no generan datos inventados.

## Regresión
La suite heredada continúa siendo obligatoria. Esta versión añade pruebas de fecha dinámica, prioridad temporal y uso de zona horaria de México.
