# LiAn V64.0.0 — Prediction Integrity & Data Sufficiency Gate

## Objetivo
Corregir la causa estructural detectada en V63.x: el motor podía producir una distribución 1/X/2 aparentemente precisa para equipos sin historial específico, y la ventaja de sede podía convertirse en una selección aunque la evidencia futbolística fuera inexistente.

## Cambios
- Nuevo `data_sufficiency` por partido y por equipo.
- Mínimo operativo de 4 partidos previos verificables por equipo para habilitar una selección basada en datos de equipo.
- Los equipos con 0 historial y sin prior ya no generan una selección: `selection_eligible=false`, `decision=PASS`, `status=DATOS INSUFICIENTES`.
- La sede verificada permanece visible como metadata, pero no crea fuerza específica cuando ambos equipos están sin datos.
- La evidencia queda limitada cuando la puerta de datos no está satisfecha.
- La confianza queda limitada cuando la puerta de datos no está satisfecha.
- `Top Picks` y `Combinadas` excluyen partidos que no superan la puerta de selección.
- Se preservan probabilidades 1/X/2 como distribución matemática, pero se evita presentarlas como recomendación.
- Se mantiene la trazabilidad `base_model_version=63.0.0` y `model_version=64.0.0`.
- Background intenta un backfill histórico estructurado una vez cada 24 horas, con caché, usando los archivos históricos ya soportados por `HistoricalSync` cuando existe conectividad.
- Ventana operativa de fixtures/predicciones de background ampliada a 30 días.
- Regression runner aislado por copia privada del proyecto y `PYTHONPATH` explícito.

## Regla de promoción
Una nueva versión no se considera correcta porque una API responda 200. Debe superar pruebas de integridad de datos, leakage temporal, sensibilidad direccional, normalización, selección, UI/API, calendario y regresión.

## Limitación de entorno
Este entorno no dispone de DNS externo operativo; por ello no se afirma validación live contra ESPN/SofaScore/TheSportsDB. Las rutas live se validan mediante emulación/mocks y HTTP local. En una máquina con Internet debe ejecutarse el backfill y la verificación live antes de considerar completa la cobertura de fuentes.
