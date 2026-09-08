@echo off
setlocal
cd /d "%~dp0"
py -m games.balatro.live.runtime.v09g_diagnostic_report %*
endlocal
