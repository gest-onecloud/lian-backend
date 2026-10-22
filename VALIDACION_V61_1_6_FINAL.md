# LiAn V61.1.6 — VALIDACION FINAL

## Cambio principal
Corrección estructural del buscador universal: la frescura temporal ya no crea relevancia. Las consultas explícitas `A vs B` requieren ambos equipos; las consultas de un equipo requieren coincidencia con local/visitante. Un resultado histórico local no bloquea el descubrimiento dirigido de un partido actual/futuro.

## Regresión ejecutada
- `python backend/validate.py`: PASS
- `python -m unittest discover -s tests -p "test_*.py" -q`: 101/101 PASS
- Compilación `python -m compileall -q backend tests`: PASS
- HTTP local con fuentes live deshabilitadas: PASS
- Pruebas nuevas V61.1.6: exclusión de partidos irrelevantes, prioridad futuro sobre histórico y descubrimiento dirigido con mocks.

## Conservación
No se eliminan resultados históricos. No se modifica el motor de predicción, Adaptive Learning, AntiError, calendario protegido ni Post-Match salvo la sincronización de versión necesaria para la regresión.

## Nota de entorno
La validación de fuentes externas reales debe ejecutarse también en el PC del usuario porque el entorno de desarrollo utilizado para esta revisión no tiene resolución DNS/salida general a Internet.
