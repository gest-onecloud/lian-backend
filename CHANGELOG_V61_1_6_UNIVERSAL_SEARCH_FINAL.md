# LiAn V61.1.6 — Universal Search Final

## Objetivo
Corregir la contaminación del buscador por partidos futuros no relacionados y asegurar que una consulta de equipo/partido no quede bloqueada por resultados históricos de agosto.

## Cambios
- La relevancia ahora es obligatoria antes de aplicar el bono temporal.
- `Equipo A vs Equipo B` exige coincidencia de ambos lados; un partido futuro ajeno nunca puede aparecer como candidato.
- Una consulta de equipo exige coincidencia con local/visitante; una consulta de competición conserva su comportamiento.
- La búsqueda universal ejecuta descubrimiento dirigido cuando el índice local solo contiene históricos para el equipo consultado.
- Se conserva el histórico y no se borran registros anteriores.
- Se sincronizó la versión runtime a 61.1.6.

## Regresión
Se añadieron pruebas unittest para: par explícito, equipo único, exclusión de fixtures irrelevantes y prioridad de próximos partidos sobre históricos.
