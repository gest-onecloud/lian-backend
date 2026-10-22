@echo off
setlocal
cd /d "%~dp0"
echo =================================================
set /p LIAN_VERSION=<VERSION.txt
echo LiAn %LIAN_VERSION% - VALIDACION ANTIERROR
echo =================================================
python -m backend.validate
if errorlevel 1 (echo [ERROR] Validacion estructural fallida.&pause&exit /b 1)
python RUN_REGRESSION.py
if errorlevel 1 (echo [ERROR] Regresion fallida.&pause&exit /b 1)
where node >nul 2>&1
if errorlevel 1 (
  echo [WARN] Node no esta instalado; se omite node --check.
) else (
  node --check frontend\app.js
  if errorlevel 1 (echo [ERROR] JavaScript invalido.&pause&exit /b 1)
  echo [PASS] JavaScript syntax validado con Node.
)
echo [PASS] LiAn %LIAN_VERSION% validado.
pause
