@echo off
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":8010" ^| findstr "LISTENING"') do taskkill /PID %%p /F >nul 2>&1
 echo [OK] LiAn V54 detenido si estaba activo.
