@echo off
setlocal
chcp 65001 >nul
echo VRCSol を起動しています...
cd /d "%~dp0\source"
call start_gui.bat %*
if errorlevel 1 (
    echo.
    echo エラーが発生しました。
    pause
)
