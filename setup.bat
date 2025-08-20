@echo off
echo Geospatial Data Downloader - Initial Setup
echo ==========================================
echo This will set up the virtual environment and install all dependencies.
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

REM Check if virtual environment already exists
if exist "venv" (
    echo Virtual environment already exists.
    set /p recreate="Do you want to recreate it? This will delete the existing environment. (y/N): "
    if /i "%recreate%"=="y" (
        echo Removing existing virtual environment...
        rmdir /s /q venv
    ) else (
        echo Using existing virtual environment.
        goto :activate
    )
)

REM Create virtual environment
echo Creating virtual environment...
python -m venv venv
if errorlevel 1 (
    echo ERROR: Failed to create virtual environment.
    echo Make sure you have Python 3.8 or higher installed.
    pause
    exit /b 1
)

:activate
REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip

REM Install the package and all dependencies
echo Installing dependencies...
echo This may take a few minutes on first setup...
pip install -e .

REM Verify installation
echo.
echo Verifying installation...
python -c "import streamlit, geopandas, matplotlib, ezdxf; print('All dependencies installed successfully!')" 2>nul
if errorlevel 1 (
    echo WARNING: Some dependencies may not have installed correctly.
    echo You may need to run 'pip install -e .' manually after setup.
) else (
    echo.
    echo ========================================
    echo Setup completed successfully!
    echo ========================================
    echo.
    echo To start the application:
    echo 1. Double-click 'start.bat' 
    echo 2. Or run: streamlit run streamlit_app.py
    echo.
    echo The app will open in your web browser at http://localhost:8501
)

echo.
pause