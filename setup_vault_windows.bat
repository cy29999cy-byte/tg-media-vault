@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python launcher not found.
  echo Install Python 3.10 or newer from python.org, enable the Python launcher, and try again.
  pause
  exit /b 1
)

py -3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)"
if errorlevel 1 (
  echo [ERROR] TG Media Vault requires Python 3.10 or newer.
  py -3 --version
  pause
  exit /b 1
)

if not exist .venv\Scripts\python.exe (
  echo Creating virtual environment...
  py -3 -m venv .venv
  if errorlevel 1 (
    echo [ERROR] Could not create the virtual environment.
    pause
    exit /b 1
  )
)

call .venv\Scripts\activate.bat
if errorlevel 1 (
  echo [ERROR] Could not activate the virtual environment.
  pause
  exit /b 1
)

python -m pip install --upgrade pip
if errorlevel 1 goto :install_failed
python -m pip install -r requirements.txt
if errorlevel 1 goto :install_failed
python -m pip install -r requirements-webui.txt
if errorlevel 1 goto :install_failed

echo.
echo TG Media Vault setup complete.
echo Run run_vault_windows.bat to start the app.
pause
exit /b 0

:install_failed
echo.
echo [ERROR] Dependency installation failed. Review the messages above and try again.
pause
exit /b 1
