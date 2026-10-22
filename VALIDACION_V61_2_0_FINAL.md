# LiAn V62.0.0 — Validación final

## Problema raíz corregido
La búsqueda universal detenía el descubrimiento en vivo cuando el índice local devolvía `ambiguous`. En una búsqueda de un equipo con varios históricos (por ejemplo, Barcelona), esto impedía consultar las fuentes actuales. Además, el buscador legado `/api/search` podía puntuar partidos ajenos aunque la consulta fuera un par explícito.

## Correcciones
- La ambigüedad histórica ya no bloquea la adquisición actual.
- Un par explícito A vs B exige ambos lados y orientación correcta.
- `/api/search` aplica la misma restricción semántica.
- Los históricos nunca sustituyen a un encuentro actual/futuro.
- Los tests que escribían fechas 2099 ahora usan bases temporales; la base entregada no queda contaminada por pruebas.

## Regresión
117/117 PASS.
Python compile PASS.
JavaScript syntax PASS.
SQLite integrity PASS.
Runtime versions sincronizadas en 62.0.0.
No quedan referencias runtime 61.1.9.
