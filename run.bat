@echo off
setlocal
title Hand Gesture Popup System

echo.
echo ==============================================
echo       HAND GESTURE POPUP SYSTEM
echo ==============================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] The project has not been installed yet.
    echo.
    echo Please double-click install.bat first.
    echo The installer will check Python and install everything needed.
    echo.
    pause
    exit /b 1
)

echo Starting the webcam gesture system...
echo.
echo Press Q or ESC in the camera window to quit.
echo.

".venv\Scripts\python.exe" main.py

if errorlevel 1 (
    echo.
    echo ==============================================
    echo The program stopped because of an error.
    echo ==============================================
    echo.
    echo If the camera did not open:
    echo 1. Close Zoom, Discord, Teams, OBS, etc.
    echo 2. Check Windows Camera permissions.
    echo 3. Try running run.bat again.
    echo.
)

pause
