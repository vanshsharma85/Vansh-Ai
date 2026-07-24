@echo off
cd /d "%~dp0"
echo Starting Jarvish AI frontend on http://localhost:5500 ...
echo Open that address in Chrome or Edge. Press CTRL+C to stop.
start http://localhost:5500
python -m http.server 5500
pause
