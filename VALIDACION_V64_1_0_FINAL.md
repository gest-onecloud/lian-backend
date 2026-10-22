# VALIDACIÓN FINAL — LiAn V64.1.0

## Alcance
Corrección incremental sobre V64.0.0. No se reescribió el proyecto ni se alteró el núcleo predictivo V64.0.0.

## Pruebas
- 52 módulos de prueba presentes.
- 218 tests recolectados al cierre.
- Batería crítica después de los cambios finales: 54 PASS; batería final afectada por caché/versiones/calendario: 28 PASS.
- Baterías históricas ejecutadas individualmente por módulo: PASS, incluyendo los módulos lentos que requieren más tiempo de proceso.
- `python -m py_compile $(find backend -name '*.py' -type f)`: PASS.
- `node --check frontend/app.js`: PASS.
- `python backend/validate.py`: PASS.

## Pruebas específicas nuevas
1. Normalización de payload FotMob multi-liga sin pérdida de partidos.
2. Respuesta live vacía nunca se promociona a `complete-empty`.
3. Deducción de identidad canónica para representación México/UTC del mismo fixture.
4. Búsqueda de equipo conserva más de 20 candidatos y admite hasta 30.
5. Descubrimiento amplio puede aportar fixtures de múltiples ligas.
6. Hash del núcleo predictivo permanece estable dentro de V64.1.0.
7. `/api/health` expone plataforma V64.1.0 y motor V64.0.0.
8. Ventana calendario mantiene exactamente 30 fechas.
9. Búsqueda Cruz Azul no duplica la misma pareja por fecha/hora de proveedor.

## Limitación externa
El entorno de ejecución utilizado para esta validación no tiene resolución DNS externa estable. Por ello no se declara una prueba live directa contra ESPN/SofaScore/FotMob/TheSportsDB. Las rutas de integración se validaron con respuestas deterministas/mocks y HTTP local. La aplicación, al ejecutarse en una máquina con Internet, realizará las consultas reales.

## Criterio de liberación
La versión se considera validada para el cambio de cobertura/calendario, pero la cobertura mundial real sigue dependiendo de la disponibilidad de los proveedores. LiAn debe mostrar `partial`/`incomplete` cuando no pueda demostrar cobertura; nunca debe presentar una lista reducida como calendario completo.
