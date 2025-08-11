@echo off
echo Checking for Python...
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo Python is not installed or not in your PATH.
    echo Please install Python from https://www.python.org/downloads/ and make sure to check "Add Python to PATH" during installation.
    pause
    exit /b
)

echo Python found.
echo Installing dependencies from requirements.txt...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo Failed to install dependencies. Please check your internet connection and try again.
    pause
    exit /b
)

echo.
echo Setup complete!
echo You can now run the application by double-clicking on 'run_ui.bat'.
echo.
pause
