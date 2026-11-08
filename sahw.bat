@echo off
rem SAHW launcher: finds the SAH tree (smol-agentic-harness) and starts the server on it.
rem Point SAH_INSTALL_DIR at the tree if it is not on PATH; extra arguments pass straight through:
rem   sahw.bat --port 8391
set "SAH_INSTALL_DIR=C:\Work\SAH"
if not exist "%SAH_INSTALL_DIR%" (
  for /f "delims=" %%i in ('where sah 2^>nul') do if not defined SAH_FOUND (
    set "SAH_INSTALL_DIR=%%~dpi"
    set "SAH_FOUND=1"
  )
)
if defined SAH_FOUND if "%SAH_INSTALL_DIR:~-1%"=="\" set "SAH_INSTALL_DIR=%SAH_INSTALL_DIR:~0,-1%"
if not exist "%SAH_INSTALL_DIR%" (
  echo hey user - this needs https://github.com/FrischCode/smol-agentic-harness installed:
  echo point SAH_INSTALL_DIR above to its location by editing this file, or add it to PATH - otherwise this won't start.
  exit /b 1
)
cd /d "%~dp0"
".venv\Scripts\python.exe" -m sahw --runs-root "%SAH_INSTALL_DIR%\runs" --sah-tree "%SAH_INSTALL_DIR%" %*
