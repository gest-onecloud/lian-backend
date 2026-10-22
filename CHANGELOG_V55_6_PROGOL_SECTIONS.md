# LiAn V55.6 — Progol Sections Patch

Base: LiAn V55.6 estable.

Esta entrega modifica exclusivamente el módulo Progol.

## Estructura
- Progol fin de semana 2348: 14 partidos + Revancha 7 partidos.
- Progol de media semana 810: 9 partidos.
- 20 quinielas persistentes por cada bloque.
- Cada partido muestra día y hora de México.
- Los demás módulos de LiAn no reciben cambios funcionales.

## Persistencia
Las quinielas nuevas se guardan en `progol_contest_tickets` con una clave independiente por concurso y bloque. No se eliminan ni regeneran las 20 quinielas existentes al volver a abrir Progol.

## Validación
- Python compile: PASS
- JavaScript `node --check`: PASS
- Progol section tests: 3/3 PASS
- HTTP smoke: 7/7 PASS
- Regresión completa: 53/53 PASS
- Base matches conservada: 114
- Tabla original `progol_tickets`: 20 registros conservados
- Nueva tabla aislada `progol_contest_tickets`: 60 registros (20 + 20 + 20)
