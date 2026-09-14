@echo off
setlocal

if not exist .venv\Scripts\python.exe (
  echo [ERROR] TG Media Vault is not set up yet.
  echo Run setup_vault_windows.bat first.
  pause
  exit /b 1
)

call .venv\Scripts\activate.bat
python vault_ui.py

if errorlevel 1 (
  echo.
  echo TG Media Vault exited with an error.
  pause
)
