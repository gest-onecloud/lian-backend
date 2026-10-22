# VALIDACIÓN FINAL — LiAn V63.2.0

## Alcance

Base incremental: V63.1.0. No se reescribió el proyecto y no se alteró el motor predictivo.

## Pruebas

- 194 pruebas recolectadas en 48 módulos.
- Pruebas críticas y regresiones ejecutadas en procesos aislados.
- Bloques actuales validados: calendario, deduplicación, búsqueda universal, Match Intelligence, Post-Match, Progol, aprendizaje, datos, HTTP, integridad y contratos de versión.
- Último bloque crítico: **26 passed**.
- Bloque de endpoints HTTP: todos los endpoints principales ejercitados devolvieron HTTP 200 en emulación local.
- `python -m py_compile $(find backend -name '*.py' -type f)`: PASS.
- `node --check frontend/app.js`: PASS.
- `python backend/validate.py`: PASS.
- SQLite `PRAGMA integrity_check`: PASS.

## HTTP / UI contract test

Con fuentes live deshabilitadas para aislar la aplicación:

- `/api/health`: 200, plataforma 63.2.0.
- `/api/data-status`: plataforma 63.2.0, motor 63.0.0.
- `/api/system-audit`: plataforma 63.2.0, motor predictivo 63.0.0.
- `/api/calendar` para fechas de prueba: 200, fecha exacta.
- `/api/calendar-window`: ventana de 30 días.
- `/api/universal-match?q=cruz azul`: fixture canónico único en el seed local.
- `/api/intelligence?match_id=...`: resolución exacta por ID canónico.
- `/api/top-picks`: 200.
- `/api/combinations`: 200.
- `/api/progol?contest=2349`: 200.
- `/api/progol?contest=2348`: 200.
- `/api/progol?contest=810`: 200.
- `/api/error-intelligence`: 200.
- `/api/competitions`: 200 y no vacío cuando existen datos.

## Corrección Post-Match

Los partidos terminados sin predicción prepartido congelada quedan explícitamente como:

- `eligible_for_metrics = false`
- `evaluation_status = RETROSPECTIVE_DISPLAY_ONLY`
- UI: `SIN EVALUACIÓN`

Por lo tanto, una reconstrucción histórica no puede contaminar accuracy/Brier/Log Loss.

## Motor predictivo

No modificado en V63.2.0.

SHA-256 de `backend/core/model.py`:
`69eb8427d0896e61a6971fb8b5091cbd37f94a22ecb6330e754df3dfc34826ed`

## Limitación externa

El entorno aislado utilizado para esta validación no tiene DNS externo operativo; por ello ESPN/SofaScore/TheSportsDB no pudieron validarse contra Internet real desde este contenedor. Se probaron sus rutas mediante mocks deterministas y emulación HTTP local. La completitud real del calendario live debe confirmarse en la máquina con Internet del usuario.

## Estado

**VALIDADA PARA ENTREGA INCREMENTAL**.

No se afirma que el modelo tenga una tasa de acierto comercial garantizada. La muestra real disponible sigue siendo pequeña para una liberación comercial de predicciones.
