# LiAn V55.9.8 — PROFESSIONAL CALIBRATION & PROVENANCE

## Objetivo
Fortalecer la versión comercial sin eliminar las mejoras previas.

## Cambios
- Protección de procedencia: predicciones generadas el mismo día o después del partido no entrenan Adaptive Learning.
- Migración de registros históricos existentes para marcar como `learning_eligible=0` los que fueron generados después del partido.
- Feature history restringido a snapshots verdaderamente previos al partido.
- Nueva capa `ProfessionalMarkets`: mantiene 1X2 y agrega doble oportunidad como mercado selectivo separado.
- Decision Gate: `RECOMMEND`, `CAUTION` o `PASS`; no fuerza una selección cuando la evidencia es insuficiente.
- Comparación retrospectiva fija de 3 partidos para control interno, fuera de la plataforma y sin alimentar aprendizaje.
- Se conserva toda la información histórica; no se borran predicciones ni revisiones.

## Política de precisión
El 80% es un objetivo de validación, no una promesa. No se considera alcanzado hasta demostrarlo con una muestra walk-forward suficientemente grande y sin fuga temporal. La doble oportunidad y el 1X2 se miden por separado.

## Validación
- Python compileall: PASS
- Regresión: 81/81 PASS
- Comparativa retrospectiva fija: PASS (informativa; no entrena el modelo)
