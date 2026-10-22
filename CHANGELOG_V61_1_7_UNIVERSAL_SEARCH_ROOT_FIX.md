# LiAn V61.1.7 — UNIVERSAL SEARCH ROOT FIX

## Problema confirmado
La V61.1.6 contenía una regresión en la ruta `/api/universal-match`: el flujo de descubrimiento dirigido utilizaba la variable `pair` sin inicializar. La excepción quedaba atrapada por el `try/except`, por lo que el error no detenía el servidor; en su lugar, el resultado local histórico permanecía visible. Esto explica exactamente el comportamiento observado al buscar `Barcelona`: aparecían Elche–Barcelona y Barcelona–Athletic en lugar de ejecutar el descubrimiento actual.

## Corrección de raíz
- Se extrajo el flujo completo de búsqueda a `universal_search(repo, term, mid)` para que la ruta HTTP no mantenga estado de consulta implícito.
- `pair=split_pair(term)` se calcula explícitamente antes de seleccionar `discover_pair` o `discover_team`.
- La ruta `/api/universal-match` delega exclusivamente en `universal_search`.
- Se conserva la política: un resultado histórico no puede sustituir una búsqueda actual/futura.
- Se conserva el calendario de 30 días, el histórico y la deduplicación.
- Se agregaron pruebas de runtime para consulta por pareja, consulta por equipo y fallo de descubrimiento sin promoción de históricos.
- Runtime sincronizado a V61.1.7.

## Alcance
No se reescribió el modelo de predicción ni se eliminaron correcciones anteriores. El cambio funcional está limitado al flujo de resolución universal y a la sincronización de versión.
