@echo off
setlocal

echo [INFO] Running setup...
call "%~dp0setup.bat"
if %errorlevel% neq 0 (
    echo [ERROR] Setup failed. Aborting.
    goto End
)

echo [INFO] Activating virtual environment...
call "%~dp0v-env\Scripts\activate.bat"

echo [INFO] Starting the UI...
python "%~dp0run_ui.py"

:End
echo.
echo Press any key to exit.
pause > nul
endlocal
