# LiAn V61.1.1 — VALIDACIÓN FINAL

## Objetivo
Corregir el comportamiento por el cual Match Search podía priorizar/mostrar partidos históricos de agosto aunque el calendario vigente de México ya estuviera en septiembre.

## Corrección
- Fecha actual calculada exclusivamente con `America/Mexico_City`.
- El buscador prioriza hoy/futuro.
- Si una búsqueda no tiene coincidencia hoy/futura, solicita automáticamente una ventana móvil de 11 días desde la fecha actual de México y vuelve a indexar/buscar.
- No se eliminan registros históricos.
- Background Engine usa fecha de México y calcula el día anterior respecto a México, no respecto a UTC.
- No se introdujo una fecha fija de septiembre; el mecanismo seguirá funcionando cuando cambie el mes y el día.

## Pruebas
- Regresión existente: **93 tests / 93 PASS / 0 FAIL / 0 ERROR**.
- Pruebas dinámicas adicionales: **4 PASS**.
- Compilación Python: **PASS**.
- Arranque HTTP: **PASS** (`/api/health` HTTP 200).
- `/api/search` devuelve `calendar_context.today_mx` y `window_days=11`: **PASS**.
- Prueba con modo de fixtures live deshabilitado: **PASS**; no se realizaron llamadas externas durante esta prueba.

## Nota
La disponibilidad concreta de partidos de una fecha futura depende de que las fuentes configuradas entreguen esos fixtures. Si una fuente falla, LiAn no inventa partidos; conserva histórico y registra el estado de cobertura.
