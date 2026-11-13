@echo off
cd /d "%~dp0"
echo === Smart Flood System - first-time setup ===
where python >nul 2>nul
if errorlevel 1 (
  echo Python was not found. Install Python from python.org and tick "Add Python to PATH".
  pause
  exit /b 1
)
if not exist .venv (
  echo Creating virtual environment...
  python -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
  echo Package install failed. See the messages above.
  pause
  exit /b 1
)
echo.
echo === Creating database and tables (MySQL must be running in XAMPP) ===
python scripts\setup_database.py
if errorlevel 1 (
  pause
  exit /b 1
)
echo.
echo === Loading saved weather data ===
python scripts\import_weather_csv.py
echo.
echo === Loading flood history labels ===
python scripts\import_flood_labels.py
echo.
echo Setup finished. Now double-click run.bat to start the app.
pause
