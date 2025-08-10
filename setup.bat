@echo off
setlocal

echo [INFO] Starting project setup...
echo.

:: 1. Check for Python
echo [INFO] Checking for Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in your PATH.
    echo Please install Python 3 and ensure it's added to your system's PATH.
    goto End
)
echo [INFO] Python found.
echo.

:: 2. Create virtual environment if it doesn't exist
if exist "%~dp0v-env" (
    echo [INFO] Virtual environment 'v-env' already exists.
) else (
    echo [INFO] Creating Python virtual environment in 'v-env'...
    python -m venv v-env
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create the virtual environment.
        goto End
    )
    echo [INFO] Virtual environment created successfully.
)
echo.

:: 3. Activate virtual environment
echo [INFO] Activating virtual environment...
call "%~dp0v-env\Scripts\activate.bat"
echo.

:: 4. Install dependencies
if not exist "%~dp0requirements.txt" (
    echo [WARN] 'requirements.txt' not found. Skipping dependency installation.
    echo You should create a 'requirements.txt' file and list your project's dependencies in it.
) else (
    echo [INFO] Installing dependencies from requirements.txt...
    pip install -r "%~dp0requirements.txt"
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install dependencies from requirements.txt.
        goto End
    )
    echo [INFO] Dependencies installed successfully.
    echo.
    echo [INFO] Installing Playwright browsers...
    playwright install
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install Playwright browsers.
        goto End
    )
)
echo.

echo [SUCCESS] Setup complete!
echo You can now run the agent using 'run_agent.bat'.

:End
echo.
echo Press any key to exit.
pause > nul
endlocal