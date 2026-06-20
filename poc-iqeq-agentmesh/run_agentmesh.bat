@echo off
title IQ-EQ Unified Agent Mesh - Startup Control
color 0B

echo =====================================================================
echo           IQ-EQ UNIFIED AGENT MESH - STARTUP CONTROL
echo =====================================================================
echo.
echo Current Directory: %CD%
echo Target Directory:  c:\Projects\algoleap-poc-projects\poc-iqeq-agentmesh
echo.

REM Change directory to the workspace directory
cd /d "c:\Projects\algoleap-poc-projects\poc-iqeq-agentmesh"

REM Check if virtual environment exists and activate it
set "VENV_PATH="
if exist ".venv\Scripts\activate.bat" (
    set "VENV_PATH=.venv\Scripts\activate.bat"
)
if exist "venv\Scripts\activate.bat" (
    set "VENV_PATH=venv\Scripts\activate.bat"
)

if defined VENV_PATH (
    echo [INFO] Found virtual environment at %VENV_PATH%. Activating...
    call %VENV_PATH%
) else (
    echo [WARNING] No virtual environment found [.venv or venv]. Using global Python.
)

REM Validate python installation
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in system PATH.
    echo Please install Python and try again.
    pause
    exit /b 1
)

REM Check dependencies
echo [INFO] Verifying/installing dependencies from requirements.txt...
python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [WARNING] Could not install/verify all requirements. Attempting to start anyway...
)

REM Start browser in background
echo [INFO] Opening dashboard in your default browser...
start http://127.0.0.1:8010/

REM Start the application
echo [INFO] Starting FastAPI Uvicorn Server on http://127.0.0.1:8010 ...
echo.
echo Press Ctrl+C in this window to stop the server at any time.
echo =====================================================================
echo.

python -m uvicorn app.main:app --host 127.0.0.1 --port 8010 --reload

pause
