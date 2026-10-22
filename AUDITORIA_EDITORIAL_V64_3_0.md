# Auditoría editorial V64.3.0

## Lógica
- La fuente TheSportsDB nunca certifica cobertura global.
- Un resultado vacío de una fuente nunca significa "no hay partidos".
- Si los tres feeds amplios están vacíos, se activa recuperación ESPN por liga.
- Match Intelligence no depende de una sola fuente para descubrir un equipo.
- La ventana de 30 días es inclusiva: hoy + 29 días.
- No se mezclan resultados históricos con fixtures futuros.

## Código
- `py_compile` aplicado a todo `backend`.
- `node --check` aplicado a `frontend/app.js`.
- No se añadieron excepciones silenciosas al nuevo flujo de recuperación.
- Se conservan los fallbacks existentes.

## Texto
- Se eliminaron referencias de versión 64.2.0 en las superficies runtime activas.
- Se mantiene la separación explícita entre plataforma V64.3.0 y motor predictivo V64.0.0.
- No se afirma cobertura completa cuando las fuentes no la demuestran.
