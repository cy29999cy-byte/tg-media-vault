@echo off
setlocal
cd /d "%~dp0"

if not exist .venv\Scripts\python.exe (
  echo [ERROR] TG Media Vault is not set up yet.
  echo Run setup_vault_windows.bat first.
  pause
  exit /b 1
)

call .venv\Scripts\activate.bat
if errorlevel 1 (
  echo [ERROR] Could not activate the TG Media Vault virtual environment.
  pause
  exit /b 1
)

python vault_ui.py

if errorlevel 1 (
  echo.
  echo TG Media Vault exited with an error.
  pause
  exit /b 1
)

exit /b 0
