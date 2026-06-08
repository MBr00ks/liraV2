@echo off
echo ============================================
echo   Lira V2.5 — Starting All Services
echo ============================================
echo.

cd /d "%~dp0"

REM --- Kokoro TTS (:19008) ---
echo [1/6] Starting Kokoro TTS...
start "Kokoro" /min cmd /c "services\kokoro-tts\.venv\Scripts\python.exe services\kokoro-tts\server.py"
timeout /t 3 >nul

REM --- Voice Proxy (:19011) ---
echo [2/6] Starting Voice Proxy...
start "Proxy" /min cmd /c "set PYTHONPATH=services\lira-v3&& apps\voice-runtime\.venv\Scripts\python.exe -X utf8 -m uvicorn src.main:app --host 127.0.0.1 --port 19011"
timeout /t 3 >nul

REM --- Whisper STT (:19002) ---
echo [3/6] Starting Whisper STT...
start "Whisper" /min cmd /c "apps\voice-runtime\.venv\Scripts\python.exe services\whisper-stt\server.py"
timeout /t 3 >nul

REM --- Lira V2.5 Orchestrator (:8100) ---
echo [4/6] Starting Lira Orchestrator...
start "Orchestrator" /min cmd /c "set PYTHONPATH=services\lira-v3&& apps\voice-runtime\.venv\Scripts\python.exe -X utf8 -m uvicorn orchestrator.main:app --host 0.0.0.0 --port 8100"
timeout /t 3 >nul

REM --- ComfyUI (:8188) ---
echo [5/6] Starting ComfyUI...
start "ComfyUI" /min cmd /c "services\comfyui\venv\Scripts\python.exe -s main.py --highvram --port 8188"
timeout /t 3 >nul

REM --- Frontend (:3000) ---
echo [6/6] Starting Frontend...
start "Frontend" /min cmd /c "cd /d apps\lira-chat && npx vite"
timeout /t 5 >nul

REM --- Open Browser ---
echo.
echo Opening browser...
start http://localhost:3000

echo.
echo ============================================
echo   All services launched!
echo   Chat:  http://localhost:3000
echo   API:   http://localhost:8100
echo ============================================
echo.
echo Close this window or press any key to exit.
pause >nul
