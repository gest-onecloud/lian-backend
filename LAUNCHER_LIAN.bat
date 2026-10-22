@echo off
setlocal
cd /d "%~dp0"
set /p LIAN_VERSION=<VERSION.txt
if "%LIAN_VERSION%"=="" (echo [ERROR] VERSION.txt vacio. No se inicia.&pause&exit /b 1)
python -m backend.validate
if errorlevel 1 (echo [ERROR] Validacion fallida. LiAn NO se inicia.&pause&exit /b 1)
set LIAN_PORT=8010
start "LiAn %LIAN_VERSION% API" cmd /c "python -m backend.server"
timeout /t 2 /nobreak >nul
start "" http://127.0.0.1:8010/
echo [OK] LiAn %LIAN_VERSION% iniciado en http://127.0.0.1:8010/
