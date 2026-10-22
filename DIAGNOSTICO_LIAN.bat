@echo off
cd /d "%~dp0"
echo ================================================
echo LiAn - DIAGNOSTICO
echo ================================================
python -c "import sys; print('Python:',sys.version)"
python -m backend.validate
python -c "import urllib.request,json; x=json.load(urllib.request.urlopen('http://127.0.0.1:8010/api/health',timeout=3)); print('API:',x)" 2>nul
if errorlevel 1 echo [INFO] API no esta activa en 8010.
pause
