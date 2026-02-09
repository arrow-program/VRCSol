@echo off
setlocal
rem Prefer venv python if present
if exist "%~dp0\.venv\Scripts\python.exe" (
	"%~dp0\.venv\Scripts\python.exe" "%~dp0\gui.py" %*
	goto :EOF
)

rem Try system python
where python >nul 2>&1
if %errorlevel%==0 (
	python "%~dp0\gui.py" %*
	goto :EOF
)

rem Try py launcher
where py >nul 2>&1
if %errorlevel%==0 (
	py -3 "%~dp0\gui.py" %*
	goto :EOF
)

echo ERROR: No Python interpreter found.
echo Install Python 3 or create a virtual environment in the project folder.
echo You can also run the GUI with: ".\.venv\Scripts\python.exe gui.py"
pause