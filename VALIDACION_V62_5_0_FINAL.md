# LiAn V62.5.0 — VALIDACION FINAL

## Objetivo
Integrar el ciclo de datos historicos/catch-up y asegurar que Progol utilice exactamente el mismo Prediction Core que la plataforma normal, sin contaminar benchmarks historicos.

## Cambios
- Progol 2349/Revancha genera picks desde `Model.predict()` vigente.
- Concursos futuros con tickets de una version anterior regeneran sus tickets con la version actual.
- Concursos historicos permanecen inmutables para evitar leakage.
- Se conserva la diversidad de las 20 quinielas como capa de portafolio, sin sustituir las probabilidades del Prediction Core.
- Busqueda SofaScore amplificada a 5 paginas futuras y 2 historicas.
- Versionado sincronizado a 62.5.0.

## Pruebas
- 45 archivos de prueba presentes en el paquete.
- 170 tests contados/ejecutados individualmente en la bateria de regresion, todos PASS.
- Pruebas nuevas V62.5 Progol: PASS.
- Prueba nueva V62.6 multi-liga aleatorizada (20 casos): PASS.
- Python compileall: PASS.
- JavaScript `node --check frontend/app.js`: PASS.
- Auditoria de version runtime/frontend/model: PASS.

Nota: las pruebas HTTP que levantan servidores se ejecutaron como procesos aislados para evitar interferencia de puertos/procesos entre archivos. No se usa pytest como dependencia.

## Regla de integridad
Una prediccion historica solo se evalua si existia antes del resultado. Los concursos historicos no se regeneran al cambiar la version del motor.
