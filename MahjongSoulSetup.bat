@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    py -m venv .venv
    if errorlevel 1 exit /b 1
)
".venv\Scripts\python.exe" -m pip install -r games\mahjong_soul\setup\requirements.txt
if errorlevel 1 exit /b 1
".venv\Scripts\python.exe" -m games.mahjong_soul.live --check
exit /b %errorlevel%
