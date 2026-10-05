@echo off
setlocal EnableExtensions EnableDelayedExpansion
title Hand Gesture Popup System - Installation

echo.
echo ==============================================
echo    HAND GESTURE POPUP SYSTEM - INSTALLER
echo ==============================================
echo.

set "PYTHON_CMD="
set "PYTHON_EXE="

REM ============================================================
REM IMPORTANT:
REM Do NOT trust "where python" by itself because Windows may
REM return the Microsoft Store python.exe alias/stub.
REM We test whether Python can actually execute a command.
REM ============================================================

echo Searching for a working Python installation...
echo.

REM ---- First try the Python Launcher (usually the most reliable) ----
where py >nul 2>nul
if not errorlevel 1 (
    py -3 -c "import sys; print(sys.executable)" > "%TEMP%\hand_gesture_python_path.txt" 2>nul
    if not errorlevel 1 (
        set /p PYTHON_EXE=<"%TEMP%\hand_gesture_python_path.txt"
        if defined PYTHON_EXE (
            set "PYTHON_CMD=py -3"
            goto :PYTHON_FOUND
        )
    )
)

REM ---- Then try python.exe ----
where python >nul 2>nul
if not errorlevel 1 (
    python -c "import sys; print(sys.executable)" > "%TEMP%\hand_gesture_python_path.txt" 2>nul
    if not errorlevel 1 (
        set /p PYTHON_EXE=<"%TEMP%\hand_gesture_python_path.txt"
        if defined PYTHON_EXE (
            set "PYTHON_CMD=python"
            goto :PYTHON_FOUND
        )
    )
)

REM ---- No working Python was found ----
echo.
echo ==============================================
echo [ERROR] A working Python installation was NOT found.
echo ==============================================
echo.
echo Your screenshot shows that Windows can see a "python"
echo command, but that command is only the Microsoft Store
echo shortcut/alias and is NOT a real Python installation.
echo.
echo PLEASE DO THIS:
echo.
echo 1. Download Python 3.11 for Windows from:
echo    https://www.python.org/downloads/windows/
echo.
echo 2. Run the Python installer.
echo.
echo 3. On the FIRST installer screen, VERY IMPORTANT:
echo    [X] Add python.exe to PATH
echo.
echo 4. Click "Install Now".
echo.
echo 5. When installation finishes, CLOSE this window.
echo.
echo 6. Open a NEW Command Prompt and type:
echo.
echo    py --version
echo.
echo    and/or:
echo    python --version
echo.
echo    You should see something like:
echo    Python 3.11.x
echo.
echo 7. Run this install.bat again.
echo.
echo ------------------------------------------------
echo IF PYTHON IS ALREADY INSTALLED:
echo ------------------------------------------------
echo.
echo Windows may have the Microsoft Store aliases enabled.
echo Go to:
echo.
echo Settings
echo   ^> Apps
echo   ^> Advanced app settings
echo   ^> App execution aliases
echo.
echo Turn OFF:
echo    python.exe
echo    python3.exe
echo.
echo Then open a NEW Command Prompt and test:
echo    py --version
echo    python --version
echo.
echo Then run install.bat again.
echo.
echo ==============================================
pause
exit /b 1

:PYTHON_FOUND
if exist "%TEMP%\hand_gesture_python_path.txt" del "%TEMP%\hand_gesture_python_path.txt" >nul 2>nul

echo [OK] Working Python found.
echo.
echo Python executable:
echo %PYTHON_EXE%
echo.
echo Checking Python version...
%PYTHON_CMD% --version
if errorlevel 1 (
    echo.
    echo [ERROR] Python was detected but could not report its version.
    echo Please reinstall Python 3.10 or 3.11.
    pause
    exit /b 1
)

echo.
echo Python is ready.
echo.

REM ============================================================
REM Create virtual environment
REM ============================================================
if exist ".venv\Scripts\python.exe" (
    echo [OK] Existing virtual environment found.
) else (
    echo Creating virtual environment...
    %PYTHON_CMD% -m venv .venv

    if errorlevel 1 (
        echo.
        echo [ERROR] Failed to create the virtual environment.
        echo.
        echo Make sure you installed Python from python.org
        echo and enabled the Python installation/venv components.
        echo.
        pause
        exit /b 1
    )
)

if not exist ".venv\Scripts\python.exe" (
    echo.
    echo [ERROR] The virtual environment was not created correctly.
    echo.
    pause
    exit /b 1
)

echo.
echo [OK] Virtual environment is ready.
echo.

REM ============================================================
REM Upgrade pip
REM ============================================================
echo Upgrading pip...
".venv\Scripts\python.exe" -m pip install --upgrade pip

if errorlevel 1 (
    echo.
    echo [WARNING] pip could not be upgraded.
    echo Continuing with package installation...
)

REM ============================================================
REM Install dependencies
REM ============================================================
echo.
echo Installing required packages (MediaPipe 0.10.21 for compatibility)...
echo This may take a few minutes.
echo.

".venv\Scripts\python.exe" -m pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo ==============================================
    echo [ERROR] Package installation failed.
    echo ==============================================
    echo.
    echo Possible causes:
    echo - No internet connection
    echo - Firewall/antivirus blocked pip
    echo - Unsupported Python version
    echo.
    echo Recommended:
    echo Use Python 3.10 or 3.11 and run install.bat again.
    echo.
    pause
    exit /b 1
)

echo.
echo ==============================================
echo       INSTALLATION COMPLETED SUCCESSFULLY
echo ==============================================
echo.
echo Your hand gesture system is ready!
echo.
echo Double-click:
echo    run.bat
echo.
echo Then show your gestures to the webcam.
echo.
echo Supported gestures:
echo    Open Palm  = hand
echo    Fist       = fist
echo    Thumbs Up  = thumbs up
echo    Peace      = peace sign
echo    One Finger = one finger
echo    Heart      = two-hand heart
echo.
pause
exit /b 0
