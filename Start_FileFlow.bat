@echo off
title FileFlow Launcher
cd /d "%~dp0"

:: Check if Python is installed
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Python was not found in PATH. Please install Python 3.
    pause
    exit /b 1
)

:: Launch without background command prompt window
start "" pythonw main.py
if %ERRORLEVEL% NEQ 0 (
    echo Launching with standard python...
    python main.py
    pause
)
