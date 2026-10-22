@echo off
setlocal
cd /d "%~dp0"
set /p LIAN_VERSION=<VERSION.txt
echo LiAn %LIAN_VERSION% - VERIFICACION DE PAQUETE
if "%LIAN_VERSION%"=="" (echo [ERROR] VERSION.txt vacio&exit /b 1)
python -m backend.validate
if errorlevel 1 exit /b 1
python RUN_REGRESSION.py
if errorlevel 1 exit /b 1
where node >nul 2>&1
if not errorlevel 1 node --check frontend\app.js
if errorlevel 1 exit /b 1
echo [PASS] Paquete LiAn %LIAN_VERSION% verificado.
