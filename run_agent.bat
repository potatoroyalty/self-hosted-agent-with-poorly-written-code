@echo off
setlocal

:: --- Configuration ---
set "DEFAULT_URL=https://www.google.com"
set "DEFAULT_MODEL=llava:7b"
set "DEFAULT_FAST_MODEL=phi3:mini"
:: ---------------------

echo [INFO] Starting the web agent...
echo.

:: 1. Check for virtual environment
if not exist "%~dp0v-env\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found.
    echo Please run 'setup.bat' first to set up the project.
    goto End
)

:: 2. Activate virtual environment
call "%~dp0v-env\Scripts\activate.bat"

:: 3. Get user input
set "OBJECTIVE="
set /p OBJECTIVE="Please enter the objective for the web agent and press Enter: "
if not defined OBJECTIVE (
    echo [ERROR] Objective cannot be empty. Aborting.
    goto End
)

set "START_URL="
set /p START_URL="Enter starting URL (press Enter for default: %DEFAULT_URL%): "
if not defined START_URL (
    set START_URL=%DEFAULT_URL%
)

set "MODEL_NAME="
set /p MODEL_NAME="Enter model name (press Enter for default: %DEFAULT_MODEL%): "
if not defined MODEL_NAME (
    set MODEL_NAME=%DEFAULT_MODEL%
)

:: 4. Run the agent
python "%~dp0main.py" --objective "%OBJECTIVE%" --url "%START_URL%" --model "%MODEL_NAME%" --fast-model "%DEFAULT_FAST_MODEL%"

:End
echo.
pause