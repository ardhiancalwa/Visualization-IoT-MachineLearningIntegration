@echo off
echo ============================================================
echo   IoT MQTT Dashboard - Starting Dashboard
echo ============================================================
echo.

if not exist "venv\" (
    echo ERROR: Virtual environment not found!
    echo Please run start_publisher.bat first to setup the environment.
    pause
    exit /b 1
)

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo.
echo Starting Streamlit Dashboard...
echo Dashboard will open automatically in your browser.
echo URL: http://localhost:8501
echo.
echo Press Ctrl+C to stop the dashboard.
echo ============================================================
echo.

streamlit run mqtt_dashboard.py