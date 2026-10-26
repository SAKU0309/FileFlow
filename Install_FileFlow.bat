@echo off
title FileFlow Setup Wizard
echo.
echo ========================================================
echo               Installing FileFlow...
echo ========================================================
echo.
echo Please wait while FileFlow is installed on your laptop...
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0installer.ps1"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Installation encountered an error.
    pause
)
