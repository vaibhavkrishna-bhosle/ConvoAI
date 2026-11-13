@echo off
setlocal EnableExtensions
title ConvoAI
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo ConvoAI is not set up yet. Run setup.bat first.
  pause
  exit /b 1
)

rem ---------------------------------------------------------------- make sure Ollama is running
curl.exe -s -o nul http://127.0.0.1:11434/api/version
if errorlevel 1 (
  echo Starting Ollama...
  start "Ollama" /min ollama serve
  for /l %%i in (1,1,30) do (
    timeout /t 1 /nobreak >nul
    curl.exe -s -o nul http://127.0.0.1:11434/api/version && goto :ollama_ok
  )
  echo Ollama did not start. Small talk still works, but document answers need Ollama.
)
:ollama_ok

rem ---------------------------------------------------------------- pick a free port (5000, else 5050)
if not defined PORT set "PORT=5000"
netstat -ano | findstr /r /c:":%PORT% .*LISTENING" >nul && set "PORT=5050"

rem ---------------------------------------------------------------- open the browser once the server is up (set CONVOAI_NO_BROWSER=1 to skip)
if not defined CONVOAI_NO_BROWSER start "" /min cmd /c "for /l %%i in (1,1,30) do (timeout /t 1 /nobreak >nul & curl.exe -s -o nul http://127.0.0.1:%PORT%/api/health && (start "" http://127.0.0.1:%PORT%/ & exit))"

".venv\Scripts\python.exe" app.py
