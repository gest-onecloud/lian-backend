# LiAn V63.2.0 — UI / Data Integrity Hardening

Base: V63.1.0. Incremental release. The predictive core was not modified.

## Correcciones verificadas

1. **Post-Match sin fuga de información**
   - Un partido terminado sin una predicción prepartido congelada ya no se presenta como `FALLA` o `ACIERTO`.
   - Se presenta como `SIN EVALUACIÓN` y `RETROSPECTIVE_DISPLAY_ONLY`.
   - Esto evita convertir una reconstrucción posterior al resultado en una métrica de rendimiento.

2. **Versiones separadas y explícitas**
   - Plataforma: V63.2.0.
   - Motor predictivo: V63.0.0.
   - Se corrigieron estados que todavía reportaban V60.0.0/V63.0.0 como versión de plataforma.

3. **Caché del navegador**
   - HTML, JS, CSS y API reciben `Cache-Control: no-store, max-age=0, must-revalidate`.
   - Esto evita que el navegador siga mostrando una interfaz V63.0/V63.1 después de instalar una versión nueva.

4. **Refresco de Inteligencia de errores**
   - El botón global `Actualizar` ahora conserva la vista `errors`; antes caía en `Centro de datos`.

5. **Competencias**
   - `/api/competitions` ya no devuelve una lista vacía fija; entrega las competencias existentes en el índice local.

6. **Partidos del día**
   - El encabezado dejó de llamar `verificados` a todos los partidos. Ahora distingue cantidad de partidos, evidencia y estado de cobertura.

7. **Progol**
   - La interfaz distingue el motor predictivo V63.0.0 de la plataforma V63.2.0.
   - Se verificaron concursos 2349, 2348 y 810 por API en modo offline determinista.

## Conservación obligatoria

`backend/core/model.py` permanece byte-identical a V63.0.0.

SHA-256:
`69eb8427d0896e61a6971fb8b5091cbd37f94a22ecb6330e754df3dfc34826ed`
