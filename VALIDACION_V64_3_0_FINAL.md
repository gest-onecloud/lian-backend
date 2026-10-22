# VALIDACIÓN FINAL — LiAn V64.3.0

## 1. Autopsia previa obligatoria

La V64.2.0 corrigió los hosts de SofaScore, pero conservó un transporte HTTP uniforme con un User-Agent `LiAn/...` para ESPN, SofaScore y FotMob. Esto era incorrecto: los proveedores tienen políticas de borde diferentes. En particular, la evidencia técnica revisada indica que ESPN puede rechazar User-Agents falsificados, mientras que SofaScore puede requerir cabeceras de navegador.

El síntoma observado en la instalación era:

`ESPN 0 · SofaScore 0 · FotMob 0 · TheSportsDB 3`

Eso dejaba a TheSportsDB como única fuente no vacía, y su respuesta pequeña terminaba dominando la pantalla.

Match Intelligence tenía una segunda dependencia: la identificación del equipo estaba concentrada en TheSportsDB/SofaScore. Si esas dos rutas fallaban, la búsqueda no podía reconstruir el calendario futuro del club.

## 2. Corrección V64.3.0

- ESPN: transporte sin User-Agent falso.
- SofaScore: perfil de navegador.
- FotMob: perfil de navegador.
- TheSportsDB: secundario, nunca autoridad de cobertura.
- Recuperación de calendario por ligas ESPN cuando los tres feeds amplios están vacíos.
- Descubrimiento de equipos mediante directorio ESPN + schedule como ruta independiente.
- Ventana de equipo exactamente de hoy a hoy+29.
- Máximo de 30 candidatos futuros.
- Deduplicación canónica conservada.
- Fechas en México conservadas.
- Motor predictivo V64.0.0 no modificado.

## 3. Pruebas

54 módulos / 227 pruebas recolectadas.

Las 227 pruebas fueron ejecutadas individualmente y aprobaron.

Nuevas pruebas V64.3.0: 5/5.

Regresión V64.2.0: 4/4.

Regresión de calendario/fuentes V64.1.0: 7/7.

Regresión de inteligencia/calendario V63.1.0: 6/6.

Auditoría profunda V64.0.0: 9/9.

Integridad predictiva V64.0.0: 5/5.

HTTP smoke: 8/8.

## 4. Validación estática

- `py_compile` backend: PASS.
- `node --check frontend/app.js`: PASS.
- `python backend/validate.py`: PASS.
- SQLite: PASS.
- Predictive core hash: `ab9af7a7a98240bbbd86a8e4a6d34d5f3767e0c3efd98f77a7d0458d4e8294f9`.

## 5. Transparencia de red

El entorno de desarrollo aislado no tiene DNS externo operativo. Por ello no se afirma que los proveedores live hayan sido llamados desde este entorno. Se validaron los adaptadores mediante payloads deterministas, perfiles HTTP, recuperación por liga, descubrimiento de equipo, deduplicación y regresión. En una instalación con Internet, los fallos de fuente quedan visibles en diagnostics en lugar de ocultarse detrás de TheSportsDB.
