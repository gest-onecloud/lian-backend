# Auditoría editorial V64.6.0

## Alcance
Cambio exclusivamente visual/UX del selector de competencias en `frontend/app.js` y `frontend/style.css`, más actualización coherente de versión.

## Revisión lógica
- Se conserva `selected = new Set()` y el mismo contrato `competition_id`.
- `renderDay()` continúa filtrando exactamente con `selected.has(m.competition_id)`.
- No se modifican endpoints, proveedores, calendario, Match Intelligence, predicción, ponderaciones ni variantes.
- El selector se posiciona de forma absoluta/fija dentro del contenedor y no empuja el contenido.
- Seleccionar una liga actualiza el mismo estado existente y cierra el panel.
- `Todos`, `Limpiar`, cierre exterior y Escape no alteran la fuente de datos.
- El buscador interno sólo oculta opciones visualmente; no modifica `data` ni el estado de filtros.

## Revisión de sintaxis
- `node --check frontend/app.js`: PASS
- `python -m py_compile` backend completo: PASS
- `backend/validate.py`: PASS

## Revisión de lenguaje/UI
- Textos en español coherentes: `Selecciona las ligas`, `Buscar liga…`, `Limpiar`, `Aplicar`.
- Etiquetas cortas para evitar expansión horizontal.
- `aria-expanded`, `aria-hidden`, `aria-haspopup` y etiqueta de cierre incluidos.
- Diseño responsive para anchos <=700px.

## Regla de no regresión
La modificación no cambia la lógica de partidos ni la lógica predictiva; únicamente sustituye la representación de los chips de competencias por un selector flotante compacto.
