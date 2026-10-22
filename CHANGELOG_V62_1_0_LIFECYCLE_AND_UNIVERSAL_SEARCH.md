# LiAn V62.1.0 — Lifecycle + Universal Search Generalization

## Objetivo
Conservar V62.0.0 y corregir sistemáticamente dos puntos: estado temporal de partidos y descubrimiento por equipo/pareja en todas las competiciones.

## Cambios
- Un partido cuya fecha México ya pasó nunca se presenta como PRÓXIMO.
- Con marcador verificado: FINALIZADO + marcador.
- Sin marcador verificado: RESULTADO PENDIENTE; no se inventa resultado.
- Calendario de fechas pasadas ejecuta verificación de resultados y, cuando existen resultados verificados, alimenta Post-Match y Adaptive Learning.
- Background verifica una ventana de 7 días anteriores de resultados en cada ciclo.
- ResultSync usa OR/fallback: snapshot verificado → ESPN → SofaScore → TheSportsDB.
- Universal Search agrega calendarios amplios y calendarios por liga; no se detiene ante la primera fuente no vacía.
- Identidad de equipos mejorada para FC/CF/Club y descriptores seguros como Laguna/City/United, evitando falsos positivos como Barcelona SC vs Barcelona.
- Búsquedas A vs B mantienen restricción dura de ambos lados.
- Histórico se conserva y se muestra separado; nunca sustituye un encuentro actual.

## Regresión
La suite completa debe ejecutarse antes de entrega. No se promueve una modificación que reduzca una mejora previamente validada.
