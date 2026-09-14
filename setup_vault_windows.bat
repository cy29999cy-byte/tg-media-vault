@echo off
setlocal

where py >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python launcher not found. Install Python 3.10+ and try again.
  pause
  exit /b 1
)

if not exist .venv (
  echo Creating virtual environment...
  py -m venv .venv
)

call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-webui.txt

echo.
echo TG Media Vault setup complete.
echo Run run_vault_windows.bat to start the app.
pause
