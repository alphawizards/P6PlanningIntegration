@echo off
REM ============================================================================
REM P6 Planning Integration - Comprehensive Report Generation
REM
REM Purpose: Generate a full comprehensive report for a project
REM Usage:   generate_comprehensive_report.bat <project_id> [output_filename]
REM
REM Examples:
REM   generate_comprehensive_report.bat 123
REM   generate_comprehensive_report.bat 123 monthly_report.pdf
REM ============================================================================

setlocal

REM Configuration
set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%..
set PYTHON_EXE=python

REM Change to project directory
cd /d "%PROJECT_ROOT%"

REM Check for project ID argument
if "%~1"=="" (
    echo ============================================================================
    echo P6 Comprehensive Report Generator
    echo ============================================================================
    echo.
    echo Usage: generate_comprehensive_report.bat ^<project_id^> [output_filename]
    echo.
    echo Examples:
    echo   generate_comprehensive_report.bat 123
    echo   generate_comprehensive_report.bat 123 monthly_report.pdf
    echo.
    echo Available projects:
    echo.
    %PYTHON_EXE% main.py --list-projects
    exit /b 1
)

set PROJECT_ID=%~1

echo ============================================================================
echo P6 Comprehensive Report Generator
echo ============================================================================
echo.
echo Project ID: %PROJECT_ID%
echo Timestamp: %date% %time%
echo.

REM Build command based on whether output filename is provided
if "%~2"=="" (
    echo Generating comprehensive report...
    %PYTHON_EXE% main.py --report comprehensive --project %PROJECT_ID% --landscape
) else (
    echo Generating comprehensive report: %~2
    %PYTHON_EXE% main.py --report comprehensive --project %PROJECT_ID% --output "%~2" --landscape
)

set RESULT=%ERRORLEVEL%

echo.
if %RESULT%==0 (
    echo Report generated successfully.
    echo Check the reports\pdf folder for output.
) else (
    echo Report generation failed.
)

endlocal
exit /b %RESULT%
