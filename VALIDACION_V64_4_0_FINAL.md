# Validación final LiAn V64.4.0

Base: V64.3.0.

Objetivo: corregir la cadena de transporte/discovery sin modificar el motor predictivo V64.0.0.

Pruebas obligatorias:
- suite pytest completa
- compilación Python
- sintaxis JavaScript
- validación SQLite
- HTTP smoke
- regresión calendario
- Match Intelligence
- Universal Search
- transporte multi-ruta
- bloqueo de red externa accidental en tests
- inspección del ZIP descomprimido

Las pruebas live de proveedores se deben ejecutar con `PROBAR_FUENTES.bat` en una máquina Windows con Internet, porque el entorno de construcción no dispone de DNS externo.
