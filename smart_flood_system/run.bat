@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\activate.bat (
  echo Run setup.bat first.
  pause
  exit /b 1
)
call .venv\Scripts\activate.bat
echo Starting the server... the browser will open in a few seconds.
echo Keep this window open. Press Ctrl+C to stop.
start "" cmd /c "timeout /t 6 /nobreak >nul & start http://127.0.0.1:8000/"
python -m uvicorn backend.main:app --reload
echo.
echo The server stopped. Read the messages above for the reason.
pause
