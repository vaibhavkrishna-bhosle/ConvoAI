@echo off
setlocal EnableExtensions
title ConvoAI setup
cd /d "%~dp0"

echo ============================================================
echo  ConvoAI setup  (safe to run again: finished steps are skipped)
echo ============================================================
echo.

rem ---------------------------------------------------------------- 1. Find any Python 3
set "PY="
where py >nul 2>&1 && (
  py -3 --version >nul 2>&1 && set "PY=py -3"
)
if not defined PY (
  where python >nul 2>&1 && (
    python -c "import sys; raise SystemExit(0 if sys.version_info[0] >= 3 else 1)" >nul 2>&1 && set "PY=python"
  )
)
if not defined PY (
  where python3 >nul 2>&1 && (
    python3 -c "import sys; raise SystemExit(0 if sys.version_info[0] >= 3 else 1)" >nul 2>&1 && set "PY=python3"
  )
)
if not defined PY (
  echo [X] Python 3 was not found.
  echo     Install it from https://www.python.org/downloads/
  echo     ^(tick "Add python.exe to PATH"^), then run setup.bat again.
  goto :fail
)
for /f "tokens=*" %%v in ('%PY% --version 2^>^&1') do set "PYVER=%%v"
echo [1/8] %PYVER% found ^(%PY%^).

rem ---------------------------------------------------------------- 2. virtual environment
if not exist ".venv\Scripts\python.exe" (
  echo [2/8] Creating the virtual environment...
  %PY% -m venv .venv || goto :fail
) else (
  echo [2/8] Virtual environment already exists.
)

rem ---------------------------------------------------------------- 3. packages
echo [3/8] Installing Python packages (first time: several minutes)...
".venv\Scripts\python.exe" -m pip install --upgrade pip -q || goto :fail
".venv\Scripts\python.exe" -m pip install -r requirements.txt -q || goto :fail

rem ---------------------------------------------------------------- 4. NLTK data
echo [4/8] Downloading language data for the intent classifier...
".venv\Scripts\python.exe" -c "from nlp.preprocess import ensure_nltk_data; ensure_nltk_data()" || goto :fail

rem ---------------------------------------------------------------- 5. Ollama
where ollama >nul 2>&1
if errorlevel 1 (
  echo [X] Ollama is not installed. It runs the AI models on this computer.
  echo     Install it from https://ollama.com/download  or run:  winget install Ollama.Ollama
  echo     then run setup.bat again.
  goto :fail
)
call :ensure_ollama || goto :fail
echo [5/8] Ollama is running.

rem ---------------------------------------------------------------- 6. models (~6.5 GB the first time)
echo [6/8] Downloading AI models (first time: about 6.5 GB)...
ollama pull nomic-embed-text || goto :fail
ollama pull qwen2.5:7b-instruct || goto :fail
ollama pull llama3.2:3b || goto :fail

rem ---------------------------------------------------------------- 7. intent classifier + sample documents
if not exist "data\models\intent_model.joblib" (
  echo [7/8] Training the intent classifier...
  ".venv\Scripts\python.exe" -m nlp.train || goto :fail
) else (
  echo [7/8] Intent classifier already trained.
)
echo       Loading the sample company documents (already-loaded files are skipped)...
".venv\Scripts\python.exe" tools\load_sample_docs.py || goto :fail

rem ---------------------------------------------------------------- 8. speech model
echo [8/8] Downloading the speech-to-text model (about 460 MB the first time)...
".venv\Scripts\python.exe" -c "from faster_whisper import WhisperModel; WhisperModel('small', device='cpu', compute_type='int8', download_root='data/models/whisper')" || echo     (Voice input will download it on first use instead.)

echo.
echo ============================================================
echo  Setup complete.  Start ConvoAI with:  start.bat
echo ============================================================
pause
exit /b 0

:ensure_ollama
curl.exe -s -o nul http://127.0.0.1:11434/api/version && exit /b 0
echo       Starting Ollama...
start "Ollama" /min ollama serve
for /l %%i in (1,1,30) do (
  timeout /t 1 /nobreak >nul
  curl.exe -s -o nul http://127.0.0.1:11434/api/version && exit /b 0
)
echo [X] Ollama did not start. Open the Ollama app from the Start menu and try again.
exit /b 1

:fail
echo.
echo Setup stopped. Fix the problem above and run setup.bat again.
pause
exit /b 1
