@echo off
setlocal
cd /d "%~dp0"

if /I "%~1"=="--attempts" goto attempts

py -m games.balatro.live.runtime.balatro_agent_toggle %*
goto end

:attempts
py -m games.balatro.live.runtime.balatro_agent_attempts_toggle %*

:end
endlocal
