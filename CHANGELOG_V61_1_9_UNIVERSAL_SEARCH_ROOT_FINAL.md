# LiAn V61.1.9 — Universal Search Root Final

## Causa raíz confirmada
V61.1.8 todavía podía devolver resultados históricos de agosto cuando el flujo de descubrimiento en vivo lanzaba una excepción. El `except` del servidor registraba el error pero conservaba `result=canonical(...)`, por lo que el frontend recibía nuevamente los candidatos locales antiguos. Esto explica exactamente el síntoma: `Barcelona` → Elche/Barcelona y Barcelona/Athletic; `Valencia vs Barcelona` → sin encuentro actual.

## Corrección de raíz
- La búsqueda universal ahora es **fail-closed**: si el descubrimiento en vivo falla, nunca se devuelve el resultado local histórico como si fuera la respuesta solicitada.
- Los históricos se conservan únicamente bajo `historical_candidates` y quedan explícitamente marcados como diagnóstico.
- Se añadió descubrimiento ESPN por **rango de fechas** como primera ruta de adquisición, evitando una petición por cada día.
- Se mantiene el fallback diario ESPN + SofaScore y el descubrimiento por equipo/pareja.
- Se agregan diagnósticos de fuente para diferenciar `sin coincidencia` de `fallo de proveedor/DNS`.
- Se mantiene la deduplicación y la validación de ambos lados del partido.
- Se sincronizaron todas las referencias de runtime a V61.1.9; no se modificó el modelo predictivo salvo su versión de runtime.

## Regresión
- 113/113 pruebas PASS.
- 90 archivos productivos/tests auditados por AST/sintaxis.
- 4,965 líneas analizadas.
- 49,165 palabras léxicas contadas.
- 68,619 tokens Python no triviales.
- 4,878 sentencias Python AST.
- 266 sentencias/constructos JS estimados por análisis léxico.
- `node --check frontend/app.js` PASS.
- Sin referencias runtime a V61.1.8.
- Pruebas E2E nuevas: una excepción de fuente nunca promueve agosto; una pareja sin descubrimiento nunca cae a un partido ajeno.
