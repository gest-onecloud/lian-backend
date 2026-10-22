# LiAn V55.9 — LIVE CONTEXT DATA ENGINE

Partida de V55.8. No reemplaza funcionalidades existentes.

## Nuevo
- LiveContextEngine con persistencia/provenance.
- Weather adapter Open-Meteo cuando existen coordenadas verificadas del estadio.
- Preparación para árbitro, XI confirmado/probable, fitness y contexto de viaje.
- Endpoint `/api/live-context?match_id=...`.
- ContextEngine consume el snapshot contextual antes del modelo.
- Datos faltantes permanecen neutrales; nunca se inventan.
- `VERSION=55.9`.

## Regla de seguridad
Solo se actualiza contexto pre-match; los resultados no alimentan el contexto futuro.
