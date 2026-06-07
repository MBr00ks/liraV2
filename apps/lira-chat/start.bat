@echo off
cd /d "%~dp0"
setlocal enabledelayedexpansion

:: Read CHAT_UI from .env
if exist "..\.env" (
    for /f "tokens=2 delims==" %%a in ('findstr /b "LIRA_CHAT_UI" "..\.env"') do set "CHAT_UI=%%a"
)
if "%CHAT_UI%"=="" set "CHAT_UI=lira-chat"
:: trim whitespace
set "CHAT_UI=%CHAT_UI: =%"

if /i "%CHAT_UI%"=="sillytavern" (
    echo Starting SillyTavern...
    start "" /b cmd /c "cd /d "C:\Users\Mike Brooks\Documents\SillyTavern" && Start.bat"
) else (
    echo Starting Lira Chat (backend + frontend)...
    start "Lira Backend" /b cmd /c "cd /d "%~dp0backend" && ..\..\..\apps\voice-runtime\.venv\Scripts\python.exe -X utf8 -m uvicorn main:app --host 127.0.0.1 --port 8001 --reload"
    echo Backend starting on :8001...
    timeout /t 3 >nul
    start "Lira Frontend" /b cmd /c "cd /d "%~dp0" && npx vite"
    echo Frontend starting on :3000...
)

echo Chat UI set to %CHAT_UI%
echo To switch, edit LIRA_CHAT_UI in .env (lira-chat | sillytavern)
