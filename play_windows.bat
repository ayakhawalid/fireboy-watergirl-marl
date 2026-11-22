@echo off
setlocal
cd /d "%~dp0"
set "PY="
for %%V in (3.13 3.12 3.11 3.10 3.14) do if not defined PY (py -%%V --version >nul 2>nul && set "PY=py -%%V")
if not defined PY (python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul && set "PY=python")
if not defined PY goto nopython
if not exist .venv\Scripts\python.exe %PY% -m venv .venv
if not exist .venv\Scripts\python.exe goto venvfail
set "VPY=.venv\Scripts\python.exe"
"%VPY%" -m pip install -q pygame
if errorlevel 1 "%VPY%" -m pip install -q pygame-ce
if errorlevel 1 goto pipfail
"%VPY%" play.py %*
pause
exit /b
:nopython
echo No Python 3.10 or newer was found. Install it from python.org and run this file again.
pause
exit /b
:venvfail
echo Creating the Python environment failed.
pause
exit /b
:pipfail
echo Installing pygame failed.
pause
