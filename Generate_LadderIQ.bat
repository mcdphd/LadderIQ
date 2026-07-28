@echo off
setlocal

rem Run LadderIQ from the folder that contains this BAT file.
rem This remains portable after moving Development out of OneDrive.
set "LADDERIQ_ROOT=%~dp0"
cd /d "%LADDERIQ_ROOT%"

if not exist "%LADDERIQ_ROOT%publish_ladderiq.ps1" (
    echo.
    echo ERROR: publish_ladderiq.ps1 was not found in:
    echo %LADDERIQ_ROOT%
    pause
    exit /b 1
)

PowerShell.exe -NoProfile -ExecutionPolicy Bypass -File "%LADDERIQ_ROOT%publish_ladderiq.ps1"

if errorlevel 1 (
    echo.
    echo LadderIQ stopped because an error occurred.
    echo Review the message above.
    echo.
    pause
    exit /b 1
)

exit /b 0
