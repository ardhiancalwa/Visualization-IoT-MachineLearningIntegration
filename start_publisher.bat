@echo off
echo ============================================================
echo   IoT MQTT Dashboard - Quick Start
echo ============================================================
echo.
echo Checking Python installation...
py --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH!
    echo Please install Python 3.11 or 3.12 from python.org
    pause
    exit /b 1
)

echo.
echo Checking virtual environment...
if not exist "venv\" (
    echo Creating virtual environment...
    py -3.11 -m venv venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment!
        echo Try: py -m venv venv
        pause
        exit /b 1
    )
)

echo.
echo Activating virtual environment...
call venv\Scripts\activate.bat

echo.
echo Installing dependencies...
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo ERROR: Failed to install dependencies!
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   Setup Complete!
echo ============================================================
echo.
echo IMPORTANT: You need TWO terminal windows to run this app:
echo.
echo Terminal 1 - Run Publisher:
echo    python mqtt_publisher.py
echo.
echo Terminal 2 - Run Dashboard:
echo    streamlit run mqtt_dashboard.py
echo.
echo ============================================================
echo.
echo Press any key to start the PUBLISHER in this terminal...
pause >nul

echo.
echo Starting MQTT Publisher...
python mqtt_publisher.py