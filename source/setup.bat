if "%2"=="--debug" (
    echo Debug mode: show echo.
    pause
) else (
    @echo off
)
chcp 65001 >nul
set PYTHONUTF8=1

echo.
echo ========================================
echo  VRCSol - Virtual Environment Setup
echo ========================================
echo.

if exist "%~dp0\.venv" (
    if "%1"=="--force" (
        echo Removing existing virtual environment...
        rmdir /s /q "%~dp0\.venv"
    ) else (
        echo Virtual environment already exists.
        echo To recreate, run: setup.bat --force
        pause
        exit /b 0
    )
)

echo Creating virtual environment...
python -m venv "%~dp0\.venv"
if errorlevel 1 goto error_venv

echo.
echo Upgrading pip...
"%~dp0\.venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 (
    echo Warning: pip upgrade failed, continuing...
)

echo.
echo Installing dependencies...
"%~dp0\.venv\Scripts\python.exe" -m pip install -r "%~dp0..\requirements.txt"
if errorlevel 1 goto error_deps

echo.
echo ========================================
echo  Setup completed successfully!
echo  Press any key to start up gui.
echo ========================================
echo.
pause
exit /b 0

:error_venv
echo Error: Failed to create virtual environment.
echo Make sure Python 3 is installed.
pause
exit /b 1

:error_deps
echo Error: Failed to install dependencies.
pause
exit /b 1
