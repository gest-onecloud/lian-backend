# VALIDACIÓN FINAL — LiAn V64.0.0

## Resultado
**V64.0.0 VALIDADA PARA ENTREGA EN EL ENTORNO DE PRUEBAS**.

### Integridad estática
- `python backend/validate.py` → PASS
- `python -m py_compile $(find backend -name '*.py' -type f)` → PASS
- `node --check frontend/app.js` → PASS
- SQLite `PRAGMA integrity_check` → `ok`
- registros base: 230
- tablas: 42

### Pruebas específicas V64
- `tests/test_v640_prediction_integrity.py` → **5/5 PASS**
- `tests/test_v640_deep_audit.py` → **9/9 PASS**

Incluyen:
- cero historial → no selección;
- neutralización de fuerza ficticia;
- mínimo histórico operativo;
- histórico insuficiente → bloqueo;
- efecto direccional de datos reales/sintéticos;
- probabilidades normalizadas;
- exclusión de Top Picks;
- explicación `DATOS INSUFICIENTES`;
- protección contra leakage temporal;
- versiones.

### Regresión crítica
- V63.2 UI contract → 6/6 PASS
- V63.1 calendar/intelligence → 6/6 PASS
- V62.6 root rectification → 8/8 PASS
- V62.4 data lifecycle → 3/3 PASS
- HTTP smoke → 8/8 PASS
- V63.0 integrity → 4/4 PASS
- V63.0/V62 cross-competition → 4/4 PASS
- V61/V62 universal search, ambiguity, range y all-leagues → PASS en ejecuciones individuales
- V54–V55 históricos relevantes → PASS en ejecuciones individuales

### Colecta
La suite contiene actualmente **199 tests recolectados** en **49 módulos**.
Los módulos se ejecutaron de forma individual/aislada para evitar contaminación por SQLite/WAL y procesos HTTP residuales de tests legacy.

### HTTP local
Validado con fixtures/results live desactivados:
- `/api/health` → 200, V64.0.0
- `/api/calendar?date=2026-09-03` → 200, fecha exacta
- `/api/competitions` → 200, lista no vacía
- `/api/universal-match?q=cruz azul` → 200, fixture 2026-09-06
- `/api/intelligence?match_id=...` → 200, resolución canónica exacta

### Caso de la captura
Para partidos sin historial específico, V64 devuelve:
- `selection_eligible=false`
- `decision=PASS`
- `status=DATOS INSUFICIENTES`
- evidencia limitada
- sin favorito
- exclusión de Top Picks/Combinadas

Por tanto, LiAn ya no convierte la ausencia de información en una falsa recomendación.

### Datos live
El contenedor de pruebas no tiene DNS externo operativo. No se afirma que los proveedores externos hayan sido comprobados en vivo desde este entorno. La versión incluye el mecanismo de backfill histórico y la integración multi-fuente; debe verificarse con conectividad real para medir cobertura live.
