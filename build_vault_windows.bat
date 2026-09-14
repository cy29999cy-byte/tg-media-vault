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

python -m pip install --upgrade pyinstaller
if errorlevel 1 goto :build_failed

echo.
echo Building TGMediaVault.exe...
nicegui-pack --onefile --name TGMediaVault --clean --noconfirm vault_ui.py
if errorlevel 1 goto :build_failed

if not exist dist\TGMediaVault.exe (
  echo [ERROR] Build completed without creating dist\TGMediaVault.exe.
  pause
  exit /b 1
)

echo.
echo Build complete:
echo %CD%\dist\TGMediaVault.exe
pause
exit /b 0

:build_failed
echo.
echo [ERROR] TG Media Vault executable build failed.
echo Review the messages above and try again.
pause
exit /b 1
