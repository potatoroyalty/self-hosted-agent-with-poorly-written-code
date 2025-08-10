@echo off

REM Check if a commit message was provided
if "%~1"=="" (
  echo Error: Please provide a commit message.
  echo Usage: push_to_github.bat Your commit message
  exit /b 1
)

echo Adding all changes...
git add .

echo Committing with message: "%*"
git commit -m "%*"

echo Pushing to GitHub...
git push

echo Done!