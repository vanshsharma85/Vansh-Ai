@echo off
echo ============================================
echo  Vansh AI - Backend Setup
echo ============================================

cd /d "%~dp0"

if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)

call venv\Scripts\activate.bat

echo Installing dependencies...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if not exist .env (
    echo Creating .env from template...
    copy .env.example .env
    echo.
    echo ============================================
    echo  IMPORTANT: Open backend\.env in Notepad and
    echo  paste your FREE Gemini API key before running.
    echo  Get one at https://aistudio.google.com/apikey
    echo ============================================
)

echo.
echo Setup complete. Run "run.bat" to start the server.
pause
