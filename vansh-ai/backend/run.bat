@echo off
cd /d "%~dp0"

if not exist venv (
    echo Virtual environment not found. Run install.bat first.
    pause
    exit /b 1
)

if not exist .env (
    echo .env file not found. Run install.bat first, then add your API key.
    pause
    exit /b 1
)

call venv\Scripts\activate.bat
echo Starting Jarvish AI backend on http://localhost:8000 ...
echo Press CTRL+C to stop.
python -m uvicorn main:app --reload --port 8000
pause
