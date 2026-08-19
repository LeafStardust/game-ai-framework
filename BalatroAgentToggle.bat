@echo off
setlocal
cd /d "%~dp0"

if /I "%~1"=="--five" (
    shift
    py -m games.balatro.live.runtime.balatro_agent_five_attempts_toggle %*
) else (
    py -m games.balatro.live.runtime.balatro_agent_toggle %*
)

endlocal
