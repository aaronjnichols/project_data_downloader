@echo off
echo Starting Geospatial Data Downloader...
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH.
    echo Please install Python 3.8 or higher from https://python.org
    echo.
    pause
    exit /b 1
)

REM Change to app directory
if not exist "app" (
    echo ERROR: app folder not found. Make sure you're running this from the correct directory.
    echo.
    pause
    exit /b 1
)

cd app

REM Check if virtual environment exists
if not exist "venv" (
    echo Virtual environment not found. Please run setup.bat first.
    echo.
    pause
    exit /b 1
)

REM Check if virtual environment is corrupted (has old paths)
venv\Scripts\python.exe -c "import sys; print('Python path check OK')" 2>nul
if errorlevel 1 (
    echo Virtual environment appears to be corrupted or has old paths.
    echo This can happen after moving files. Recreating virtual environment...
    echo.
    rmdir /s /q venv
    echo Please run setup.bat to recreate the virtual environment.
    echo.
    pause
    exit /b 1
)

REM Use virtual environment Python directly
echo Checking dependencies...
venv\Scripts\python.exe -c "import streamlit, geopandas, matplotlib, ezdxf" 2>nul
if errorlevel 1 (
    echo Some dependencies are missing. Installing...
    venv\Scripts\pip.exe install -e .
    if errorlevel 1 (
        echo ERROR: Failed to install dependencies.
        echo Please check your internet connection and try again.
        echo.
        pause
        exit /b 1
    )
) else (
    echo Dependencies already installed.
)

REM Kill any existing API servers on port 8000
echo Checking for existing API servers...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING 2^>nul') do (
    echo Stopping existing server on port 8000 (PID: %%a)
    taskkill /PID %%a /F >nul 2>&1
    if errorlevel 1 (
        echo Warning: Could not stop process %%a
    ) else (
        echo Process %%a stopped successfully
    )
)

REM Wait a moment for cleanup
timeout /t 2 /nobreak >nul

REM Start API server in background from the app directory
echo Starting API server...
echo Working directory: %CD%
start "API Server" /min cmd /k "cd /d %CD% && venv\Scripts\python.exe -m uvicorn api.main:app --host 0.0.0.0 --port 8000"

REM Wait a moment for API server to start
echo Waiting for API server to start...
timeout /t 5 /nobreak >nul

REM Check if API server is running
echo Checking API server...
venv\Scripts\python.exe -c "import requests; requests.get('http://localhost:8000/health', timeout=5)" 2>nul
if errorlevel 1 (
    echo WARNING: API server may not be ready yet. Starting Streamlit anyway...
    echo If you get connection errors, please wait a moment and refresh the page.
    echo.
) else (
    echo API server is running successfully.
)

REM Start Streamlit web interface from the app directory
echo.
echo Starting Streamlit web interface...
echo.
echo The app will open in your default web browser at:
echo - Streamlit Interface: http://localhost:8501
echo - API Documentation: http://localhost:8000/docs
echo.
echo Press Ctrl+C to stop the Streamlit application.
echo To stop the API server, close the "API Server" window.
echo.

venv\Scripts\python.exe -m streamlit run streamlit_app.py
if errorlevel 1 (
    echo.
    echo ERROR: Failed to start Streamlit application.
    echo Please check the error messages above.
    echo.
    pause
    exit /b 1
)