@echo off
setlocal
cd /d "%~dp0"
echo ================================================
echo LiAn - DIAGNOSTICO REAL DE FUENTES
 echo Fecha MX: %date% %time%
echo ================================================
python tools\provider_smoke.py
if errorlevel 1 (
  echo.
  echo [FALLO] Una o mas fuentes no pudieron consultarse.
  echo Revisa el diagnostico anterior: DNS, TLS, proxy, HTTP o respuesta JSON.
) else (
  echo.
  echo [OK] Todas las fuentes principales respondieron.
)
pause
