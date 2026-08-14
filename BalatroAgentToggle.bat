@echo off
setlocal
cd /d "%~dp0"
py -m games.balatro.live.external.balatro_agent_toggle %*
endlocal
