# LiAn V62.6.0 — VALIDACIÓN FINAL RECTIFICADA

## Correcciones de raíz
- Match Search ahora nunca entrega una tarjeta cruda sin probabilidades: una coincidencia única se resuelve mediante el mismo endpoint de Intelligence/Model.predict usado por el calendario.
- Búsqueda individual de equipo trabaja con ventana móvil de 30 días futuros y 30 días históricos de contexto; el índice local ya no es autoridad de cobertura.
- Se mantiene búsqueda estricta A vs B.
- Google se incorpora como capa opcional de descubrimiento/hints; no crea ni valida un fixture por sí solo. La autoridad estructurada sigue siendo la fusión de fuentes futbolísticas públicas.
- El background genera y persiste predicciones prepartido para la ventana futura; después del kickoff la predicción queda congelada para evitar fuga de información.
- Se corrige serialización de numpy scalars para que las probabilidades puedan persistirse en SQLite/evidence.
- Se reduce/capa la ventaja de local para que no domine el ensemble: HA histórico se reduce 45% y se limita a 0.10 goles; base-rate global baja de 15% a 8%.
- Progol continúa utilizando exactamente Model.predict() y conserva concursos históricos sin regenerarlos.

## Validación
- 45 archivos de prueba.
- 178 tests individuales: todos PASS.
- 20 casos multi-liga aleatorizados.
- Prueba Google CSE mock.
- Prueba búsqueda offline de partido futuro con probabilidades 1/X/2.
- Prueba de congelación de predicción prepartido después del kickoff.
- Python compileall PASS.
- Node app.js --check PASS.
- HTTP smoke PASS.

## Política de integridad
Una predicción histórica solo se evalúa si existía antes del resultado. Los históricos no sustituyen fixtures actuales. Ninguna fuente individual define por sí sola la cobertura global.
