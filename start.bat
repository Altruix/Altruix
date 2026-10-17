@echo off
title Altruix Userbot Launcher
cd /d "%~dp0"

echo ===================================================
echo             Altruix Userbot Launcher
echo ===================================================

:: Check for Python / Py launcher
where py >nul 2>nul
if %errorlevel% equ 0 (
    set "PY_CMD=py -3"
) else (
    where python >nul 2>nul
    if %errorlevel% equ 0 (
        set "PY_CMD=python"
    ) else (
        echo [ERROR] Python is not installed or not in PATH!
        echo Please install Python 3.10 or newer from https://www.python.org/
        pause
        exit /b 1
    )
)

:: Check if .env exists, offer wizard if missing
if not exist ".env" (
    echo [INFO] No .env configuration file found!
    echo Launching the interactive Setup Wizard now...
    echo.
    %PY_CMD% -m Main.scripts.wizard
    if not exist ".env" (
        echo [WARNING] Setup wizard exited without creating .env.
        pause
        exit /b 1
    )
)

:: Virtual environment setup (optional)
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
    set "RUN_CMD=python"
) else (
    set "RUN_CMD=%PY_CMD%"
)

:: Run Altruix
echo [INFO] Starting Altruix...
echo.
%RUN_CMD% -m Main

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Altruix stopped with an error code.
    pause
)
