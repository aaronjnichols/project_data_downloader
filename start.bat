@echo off
echo Starting Geospatial Data Downloader...

REM Check if virtual environment exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Check if dependencies are installed (quick check for key packages)
echo Checking dependencies...
python -c "import streamlit, geopandas, matplotlib, ezdxf" 2>nul
if errorlevel 1 (
    echo Installing dependencies...
    pip install -e .
) else (
    echo Dependencies already installed.
)

REM Start Streamlit web interface automatically
echo.
echo Opening Streamlit web interface...
echo The app will open in your default web browser at http://localhost:8501
echo.
echo Press Ctrl+C to stop the application when you're done.
echo.

streamlit run streamlit_app.py