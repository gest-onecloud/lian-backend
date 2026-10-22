# LiAn V64.5.0 — Corrección puntual de estado temporal

## Causa raíz
Algunas fuentes pueden entregar `finished/final` para un fixture cuya fecha local de México todavía es futura. La lógica anterior priorizaba ese estado antes de validar la fecha.

## Corrección
Un fixture con fecha México futura se presenta como `PRÓXIMO`, independientemente del estado textual del proveedor. Partidos de hoy/pasados conservan sus reglas anteriores.

## Alcance
No se modifican calendario, búsqueda, Match Intelligence, proveedores, ponderaciones, variantes ni motor predictivo.
