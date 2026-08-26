@echo off
cd /d "%~dp0"
py -m games.balatro.live.runtime.balatro_agent_monitor_timed %*
echo.
echo Balatro Agent Monitor is no longer updating. Press any key to close this window.
pause >nul
