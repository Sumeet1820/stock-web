@echo off
title StockPro - Starting...
color 0A

echo.
echo  ========================================
echo   StockPro - Stock Analyzer Pro
echo  ========================================
echo.
echo  Starting server...
echo.

:: Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo  ERROR: Python not found!
    echo  Please install Python from python.org
    pause
    exit /b 1
)

:: Install/check dependencies silently
echo  Checking dependencies...
pip install -r requirements.txt -q --no-warn-script-location 2>nul

:: Start Flask in background
echo  Launching StockPro...
start /B python app.py

:: Wait for server to start
timeout /t 3 /nobreak >nul

:: Open browser
echo  Opening browser...
start http://127.0.0.1:5000

echo.
echo  StockPro is running at http://127.0.0.1:5000
echo  Close this window to STOP the server.
echo.
echo  Press Ctrl+C to stop...
echo.

:: Keep window open (server runs here)
python app.py
