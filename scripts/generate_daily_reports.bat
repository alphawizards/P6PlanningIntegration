@echo off
REM ============================================================================
REM P6 Planning Integration - Daily Report Generation
REM
REM Purpose: Generate schedule summary reports for all active projects
REM Schedule: Run daily via Windows Task Scheduler (e.g., 6:00 AM)
REM
REM Usage:
REM   generate_daily_reports.bat
REM   generate_daily_reports.bat 123 456 789    (specific project IDs)
REM ============================================================================

setlocal enabledelayedexpansion

REM Configuration
set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%..
set PYTHON_EXE=python
set LOG_FILE=%PROJECT_ROOT%\logs\daily_reports_%date:~-4,4%%date:~-10,2%%date:~-7,2%.log

REM Change to project directory
cd /d "%PROJECT_ROOT%"

echo ============================================================================ >> "%LOG_FILE%"
echo P6 Daily Report Generation - %date% %time% >> "%LOG_FILE%"
echo ============================================================================ >> "%LOG_FILE%"

REM Check if specific project IDs were provided
if "%~1"=="" (
    echo Generating reports for all projects... >> "%LOG_FILE%"

    REM Get list of projects and generate reports
    for /f "tokens=1" %%p in ('%PYTHON_EXE% -c "from src.dao import SQLiteManager; m=SQLiteManager(); m.connect(); df=m.get_project_dao().get_active_projects(); print(' '.join(str(x) for x in df['ObjectId'].tolist())); m.disconnect()" 2^>^&1') do (
        echo Generating summary report for project %%p >> "%LOG_FILE%"
        %PYTHON_EXE% main.py --report summary --project %%p >> "%LOG_FILE%" 2>&1
    )
) else (
    REM Process specific project IDs provided as arguments
    for %%p in (%*) do (
        echo Generating summary report for project %%p >> "%LOG_FILE%"
        %PYTHON_EXE% main.py --report summary --project %%p >> "%LOG_FILE%" 2>&1
    )
)

echo. >> "%LOG_FILE%"
echo Report generation completed at %time% >> "%LOG_FILE%"
echo ============================================================================ >> "%LOG_FILE%"

endlocal
