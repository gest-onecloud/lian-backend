@echo off
setlocal
cd /d "%~dp0"
set PY=%LocalAppData%\Programs\Python\Python314\python.exe
if not exist "%PY%" set PY=python
sc query LiAnBackground >nul 2>&1
if %errorlevel%==0 (
  echo LiAnBackground ya existe. Use uninstall_lian_service.bat para reemplazarlo.
  exit /b 1
)
sc create LiAnBackground binPath= "\"%PY%\" \"%CD%\run_background.py\"" start= auto DisplayName= "LiAn Background Engine"
sc description LiAnBackground "LiAn V62.4 background collector, catch-up, data fusion and learning service"
sc failure LiAnBackground reset= 86400 actions= restart/5000/restart/10000/restart/30000
sc start LiAnBackground
if %errorlevel% neq 0 echo No se pudo iniciar. Revise permisos de administrador.
endlocal
