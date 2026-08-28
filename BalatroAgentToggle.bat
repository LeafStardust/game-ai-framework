@echo off
setlocal
cd /d "%~dp0"

if /I "%~1"=="--one" goto one
if /I "%~1"=="--three" goto three
if /I "%~1"=="--five" goto five

py -m games.balatro.live.runtime.balatro_agent_toggle %*
goto end

:one
py -m games.balatro.live.runtime.balatro_agent_toggle
goto end

:three
shift
py -m games.balatro.live.runtime.balatro_agent_three_attempts_toggle %*
goto end

:five
shift
py -m games.balatro.live.runtime.balatro_agent_five_attempts_toggle %*

:end
endlocal
