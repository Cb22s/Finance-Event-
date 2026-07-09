@echo off
REM ===== Money Master - serve the frontend on http://localhost:5500 =====
cd /d "%~dp0frontend"

echo.
echo ============================================================
echo   Frontend running at http://localhost:5500
echo   Open that address in your browser.
echo   Leave this window open. Press Ctrl+C to stop.
echo ============================================================
echo.
py -m http.server 5500 || python -m http.server 5500

pause
