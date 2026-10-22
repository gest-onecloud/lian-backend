# LiAn V64.1.0 — Calendar Coverage & Match Intelligence

## Objetivo
Corregir dos fallos funcionales observados en V64.0.0: cobertura insuficiente de partidos del día y duplicación de un mismo fixture en Match Intelligence cuando una fuente expresa el horario en UTC y otra en hora de México.

## Cambios
- Añadido FotMob como tercera fuente independiente de calendario diario, usando su endpoint público de partidos por fecha como fuente de cobertura adicional.
- `FixtureSync.sync_day()` y `sync_day_light()` consultan ESPN_ALL + SofaScore + FotMob + TheSportsDB.
- Una respuesta vacía de fuentes live ya no se clasifica como `complete-empty`; queda como `incomplete` hasta que exista evidencia de cobertura.
- La vista de fecha con `refresh=1` usa la sincronización completa, incluyendo endpoints ESPN por competición, además de las fuentes amplias.
- Match Intelligence conserva hasta 30 fixtures para búsquedas de equipo.
- La identidad canónica de un fixture ya no depende del campo hora; evita duplicar Cruz Azul–Santos como 2026-09-06 20:00 y 2026-09-07 02:00 cuando son la misma representación.
- `/api/health` expone `version` de plataforma y `model_version` por separado.
- La UI muestra los conteos por fuente para que una supuesta cobertura completa sea auditable.
- El motor predictivo no fue modificado en esta versión; permanece V64.0.0.

## Regla de integridad
Ningún proveedor individual puede certificar por sí solo que el calendario mundial está completo. Si las fuentes discrepan materialmente, LiAn muestra cobertura parcial y conserva todos los eventos verificables sin inventar partidos.
