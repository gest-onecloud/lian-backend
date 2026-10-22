@echo off
setlocal
cd /d "%~dp0"
echo ============================================================
echo LiAn V54.1 - SINCRONIZADOR HISTORICO
echo ============================================================
echo.
python -m backend.data.historical
if errorlevel 1 (
  echo [ERROR] La sincronizacion fallo.
  echo [INFO] No se borro ni se recreo la base de datos.
  pause
  exit /b 1
)
python -m backend.validate
if errorlevel 1 (
  echo [ERROR] La validacion posterior fallo.
  pause
  exit /b 1
)
echo [OK] Sincronizacion y validacion completadas.
pause
