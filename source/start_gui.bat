@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
set PYTHONUTF8=1

rem Check if venv needs to be created
if not exist "%~dp0\.venv\Scripts\python.exe" (
	echo.
	echo Virtual environment not found. Running setup...
	echo.
	call "%~dp0\setup.bat"
	if errorlevel 1 (
		echo.
		echo Setup failed. Cannot continue.
		pause
		exit /b 1
	)
)

rem Fix pyvenv.cfg to use current system Python (for portability)
if exist "%~dp0\fix_pyvenv.py" (
    py "%~dp0\fix_pyvenv.py" >nul 2>&1
)

rem Prefer venv python if present
if exist "%~dp0\.venv\Scripts\python.exe" (
	echo Start up GUI（Virtual enviroment）...
	"%~dp0\.venv\Scripts\python.exe" "%~dp0\gui.py" %*
	if errorlevel 1 (
		echo error has occurred.1
		pause
	)
	goto :EOF
)

rem Try system python
where python >nul 2>&1
if %errorlevel%==0 (
	echo Start up GUI（System Python）...
	python "%~dp0\gui.py" %*
	if errorlevel 1 (
		echo error has occurred.2
		pause
	)
	goto :EOF
)

rem Try py launcher
where py >nul 2>&1
if %errorlevel%==0 (
	echo start up GUI（Python Launcher）...
	py -3 "%~dp0\gui.py" %*
	if errorlevel 1 (
		echo error has occurred.3
		pause
	)
	goto :EOF
)

echo.
echo error: Python 3 has not been found.
echo install Python 3 and set PATH or install Virtual Environment.
echo you can run the GUI with one of the following commands after installation:
echo ".\.venv\Scripts\python.exe gui.py"
echo.
pause