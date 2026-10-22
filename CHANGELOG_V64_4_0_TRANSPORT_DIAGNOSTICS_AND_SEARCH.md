# LiAn V64.4.0 — transporte resiliente y búsqueda verificable

## Causa raíz revisada
V64.3.0 separó perfiles HTTP por proveedor, pero seguía dependiendo exclusivamente de `urllib` para ejecutar esas solicitudes. En instalaciones Windows con diferencias de TLS, proxy, certificados o resolución DNS, los tres proveedores amplios podían fallar y LiAn quedaba con el fallback de TheSportsDB, que puede ser pequeño.

## Corrección
- Transporte compartido con tres rutas: `urllib` → `requests` → `curl`.
- Perfiles de cabeceras por proveedor.
- FotMob admite las dos representaciones de fecha usadas por su endpoint.
- La recuperación ESPN por competición sólo se ejecuta cuando al menos un proveedor amplio fue alcanzable pero devolvió cero eventos; no se dispara un abanico inútil durante una caída total de red.
- Match Intelligence consulta más identidades de equipo y usa calendario amplio como recuperación únicamente cuando el horario específico es vacío/sospechosamente corto.
- Se conserva la deduplicación canónica y la ventana de 30 días.
- Se agrega `PROBAR_FUENTES.bat` para validar desde Windows la conectividad real del equipo del usuario.
- Se añade bloqueo de red externa en la suite de tests para impedir falsos PASS causados por pruebas colgadas o dependientes de Internet.

## Motor predictivo
Sin cambios. Se conserva `backend/core/model.py` V64.0.0.
