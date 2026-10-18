@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Run MahjongSoulSetup.bat first.
    exit /b 1
)
".venv\Scripts\python.exe" -u -m agents.mahjong_soul.launch --stop-capture %*
exit /b %errorlevel%
