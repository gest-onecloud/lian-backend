# LiAn V55.9.6 — CALENDAR IMMUTABLE / MULTI-SOURCE COVERAGE CORE

- Partida desde V55.9.5 sin eliminar módulos previos.
- Agrega SofaScore como segundo catálogo amplio de fixtures.
- Mantiene ESPN ALL y ESPN por competición como fuentes de corroboración.
- TheSportsDB permanece secundaria y nunca define cobertura.
- Deduplicación por par normalizado de equipos dentro de la misma fecha.
- Cobertura `complete`, `partial`, `complete-empty`, `incomplete` con discrepancia entre fuentes.
- Conserva la fecha canónica `America/Mexico_City` y el hard date gate.
- Agrega prueba retrospectiva de 3 partidos aleatorios por día histórico, únicamente por consola; no se expone en la plataforma.
- Ninguna modificación cambia el esquema de aprendizaje, AntiError o predicción existente.
