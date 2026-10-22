@echo off
sc stop LiAnBackground >nul 2>&1
sc delete LiAnBackground
pause
