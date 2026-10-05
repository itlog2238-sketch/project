@echo off
setlocal
title Hand Gesture Popup System - Repair MediaPipe

echo.
echo ==============================================
echo     REPAIRING MEDIAPIPE FOR THIS PROJECT
echo ==============================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] The virtual environment does not exist.
    echo Please run install.bat first.
    pause
    exit /b 1
)

echo Uninstalling incompatible MediaPipe...
".venv\Scripts\python.exe" -m pip uninstall mediapipe -y

echo.
echo Installing compatible MediaPipe 0.10.21...
".venv\Scripts\python.exe" -m pip install "mediapipe==0.10.21"

if errorlevel 1 (
    echo.
    echo [ERROR] MediaPipe installation failed.
    echo Check your internet connection and try again.
    pause
    exit /b 1
)

echo.
echo Testing MediaPipe...
".venv\Scripts\python.exe" -c "import mediapipe as mp; print('MediaPipe version:', mp.__version__); print('Legacy solutions API:', hasattr(mp, 'solutions'))"

echo.
echo ==============================================
echo Repair complete.
echo Now run run.bat
echo ==============================================
pause
