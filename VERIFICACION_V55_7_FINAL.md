# LiAn V55.7 — Verificación final

Fecha de compilación: 2026-08-27

## Cambios críticos verificados
- Resultado real derivado únicamente del marcador final verificado.
- `ACIERTO/FALLO` de la interfaz deriva de `result.correct`, no de un registro de autopsia antiguo.
- Autopsias inconsistentes se reparan y quedan auditadas.
- Caso de regresión: predicción Local (`1`) + marcador 1–2 = Visitante (`2`) => FALLO.
- Aprendizaje temporal: solo partidos estrictamente anteriores a la fecha de la nueva predicción.
- Calibración de resultados con suavizado y límites.
- Rendimiento histórico de señales persistido.
- `model_weights` y `feature_performance` persistidos para auditoría.
- Calendario por fecha conserva aislamiento temporal.
- Fechas futuras no ejecutan verificación de resultados innecesaria.
- Semillas locales verificadas no bloquean la interfaz esperando Internet.

## Pruebas
- Python compileall: PASS
- JavaScript `node --check`: PASS
- SQLite integrity: PASS
- Base de datos: 170 partidos
- Revisiones post-match: 18
- Historial adaptativo de resultados: 18
- Rendimiento de variables: 13
- Pesos adaptativos persistidos: 1 perfil global
- Tests regresión: 63/63 PASS en ejecuciones aisladas y verificadas

## Política antierror
1. Nunca usar el marcador del propio partido como feature prepartido.
2. Nunca sustituir la predicción prepartido almacenada por una predicción posterior.
3. Nunca marcar un partido como acierto sin comparar explícitamente `pick` contra el resultado derivado del marcador.
4. Nunca permitir que un resultado posterior a la fecha contamine una predicción histórica.
5. Toda reparación de una autopsia queda registrada.
6. Los ajustes adaptativos están limitados y deben ser auditables.
