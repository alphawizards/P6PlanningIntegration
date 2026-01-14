@echo off
REM ============================================================================
REM P6 Planning Integration - Schedule Health Check
REM
REM Purpose: Run schedule health analysis and export results
REM Schedule: Run weekly via Windows Task Scheduler (e.g., Monday 7:00 AM)
REM
REM Usage:
REM   run_health_check.bat <project_id>
REM   run_health_check.bat 123
REM ============================================================================

setlocal

REM Configuration
set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%..
set PYTHON_EXE=python
set TIMESTAMP=%date:~-4,4%%date:~-10,2%%date:~-7,2%_%time:~0,2%%time:~3,2%
set TIMESTAMP=%TIMESTAMP: =0%

REM Change to project directory
cd /d "%PROJECT_ROOT%"

REM Check for project ID argument
if "%~1"=="" (
    echo Usage: run_health_check.bat ^<project_id^>
    echo.
    echo Example: run_health_check.bat 123
    echo.
    echo Available projects:
    %PYTHON_EXE% main.py --list-projects
    exit /b 1
)

set PROJECT_ID=%~1
set LOG_FILE=%PROJECT_ROOT%\logs\health_check_%PROJECT_ID%_%TIMESTAMP%.log

echo ============================================================================
echo P6 Schedule Health Check
echo ============================================================================
echo.
echo Project ID: %PROJECT_ID%
echo Timestamp: %date% %time%
echo Log File: %LOG_FILE%
echo.

REM Run health check with JSON export
echo Running health check analysis...
%PYTHON_EXE% main.py --analyze --project %PROJECT_ID% --export-json > "%LOG_FILE%" 2>&1
set RESULT=%ERRORLEVEL%

REM Also generate a PDF health report
echo Generating PDF health report...
%PYTHON_EXE% main.py --report health --project %PROJECT_ID% >> "%LOG_FILE%" 2>&1

REM Display results
type "%LOG_FILE%"

echo.
if %RESULT%==0 (
    echo Health check completed successfully.
) else (
    echo Health check failed. See log for details.
)

endlocal
exit /b %RESULT%
