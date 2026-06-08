@echo off
cd /d "%~dp0"
call "%CD%\..\..\..\apps\voice-runtime\.venv\Scripts\activate.bat"
set PYTHONPATH=%CD%
echo Starting Lira V2.5 Orchestrator on :8100...
uvicorn orchestrator.main:app --host 127.0.0.1 --port 8100 --reload
pause
