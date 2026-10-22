@echo off
cd /d "%~dp0"
set /p LIAN_VERSION=<VERSION.txt
set LIAN_PORT=8010
start "LiAn %LIAN_VERSION% API" cmd /c "python -m backend.server"
timeout /t 2 /nobreak >nul
python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8010/api/health',timeout=10).read().decode())"
python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8010/api/venue?match_id=cal-2026-08-25-concacaf-leagues-cf-monterrey-chicago-fire-fc',timeout=10).read().decode())"
python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8010/api/combinations?date=2026-08-25',timeout=20).read().decode()[:2000])"
echo [OK] Smoke test terminado.
pause
