@echo off
REM ===== Money Master - start the backend API on http://localhost:5000 =====
cd /d "%~dp0backend"

if not exist ".venv\" (
    echo Creating virtual environment...
    py -m venv .venv || python -m venv .venv
)

call .venv\Scripts\activate.bat

echo Installing / updating dependencies...
pip install -r requirements.txt

echo.
echo ============================================================
echo   Backend running at http://localhost:5000
echo   Leave this window open. Press Ctrl+C to stop.
echo ============================================================
echo.
python app.py

pause
