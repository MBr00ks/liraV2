@echo off
echo Stopping Lira V2.5 services...

REM Kill by port
for %%p in (3000 8100 19011 19008 19002 8188) do (
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%%p.*LISTENING"') do (
        taskkill /F /PID %%a >nul 2>&1
    )
)

echo All services stopped.
pause
