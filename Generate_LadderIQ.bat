@echo off
setlocal

set "LADDERIQ_ROOT=C:\Users\mcdph\OneDrive\03 - LadderIQ Platform\04 - Development"

if not exist "%LADDERIQ_ROOT%\publish_ladderiq.ps1" (
    echo.
    echo ERROR: LadderIQ was not found at:
    echo %LADDERIQ_ROOT%
    echo.
    echo Make sure this package is stored in the correct root folder.
    pause
    exit /b 1
)

cd /d "%LADDERIQ_ROOT%"

PowerShell.exe -NoProfile -ExecutionPolicy Bypass -File "%LADDERIQ_ROOT%\publish_ladderiq.ps1"

if errorlevel 1 (
    echo.
    echo LadderIQ stopped because an error occurred.
    echo Review the message above.
    echo.
    pause
    exit /b 1
)

exit