@echo off
echo Setting up Geospatial Data Downloader...

REM Check if virtual environment exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
echo Installing dependencies...
pip install -e .

REM Check if we should run API or Streamlit
echo.
echo Choose how to run the application:
echo 1. REST API Server (localhost:8000)
echo 2. Streamlit Web Interface (localhost:8501)
echo 3. Exit
echo.
set /p choice="Enter your choice (1-3): "

if "%choice%"=="1" (
    echo Starting FastAPI server...
    python api/main.py
) else if "%choice%"=="2" (
    echo Starting Streamlit web interface...
    streamlit run streamlit_app.py
) else if "%choice%"=="3" (
    echo Exiting...
    exit /b 0
) else (
    echo Invalid choice. Starting Streamlit by default...
    streamlit run streamlit_app.py
)

pause