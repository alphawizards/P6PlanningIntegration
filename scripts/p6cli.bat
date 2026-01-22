@echo off
REM ============================================================================
REM P6 Planning Integration - CLI Wrapper
REM
REM Purpose: Quick access to P6 Planning Integration commands
REM Usage:   p6cli <command> [options]
REM
REM Commands:
REM   list          List all projects
REM   report        Generate PDF reports
REM   analyze       Run schedule analysis
REM   test          Test database connection
REM   help          Show help
REM ============================================================================

setlocal

REM Configuration
set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%..
set PYTHON_EXE=python

REM Change to project directory
cd /d "%PROJECT_ROOT%"

REM Parse command
set CMD=%~1

if "%CMD%"=="" goto :show_help
if /i "%CMD%"=="help" goto :show_help
if /i "%CMD%"=="list" goto :list_projects
if /i "%CMD%"=="report" goto :generate_report
if /i "%CMD%"=="analyze" goto :analyze
if /i "%CMD%"=="test" goto :test_connection

REM Unknown command - pass through to main.py
%PYTHON_EXE% main.py %*
goto :eof

:show_help
echo.
echo ============================================================================
echo P6 Planning Integration - Quick Commands
echo ============================================================================
echo.
echo Usage: p6cli ^<command^> [options]
echo.
echo Commands:
echo   list                      List all projects
echo   list -v                   List projects with details
echo   report ^<type^> -p ^<id^>     Generate PDF report
echo   analyze -p ^<id^>           Run schedule analysis
echo   test                      Test database connection
echo   help                      Show this help
echo.
echo Report Types:
echo   summary        Executive-level schedule overview
echo   critical       Critical path analysis
echo   health         Schedule quality validation
echo   comprehensive  Full multi-section report
echo.
echo Examples:
echo   p6cli list
echo   p6cli report summary -p 123
echo   p6cli report comprehensive -p 123 --landscape
echo   p6cli analyze -p 123 --export-json
echo.
echo For full options, run: python main.py --help
echo.
goto :eof

:list_projects
shift
%PYTHON_EXE% main.py --list-projects %1 %2 %3
goto :eof

:generate_report
shift
set REPORT_TYPE=%~1
shift
%PYTHON_EXE% main.py --report %REPORT_TYPE% %1 %2 %3 %4 %5 %6
goto :eof

:analyze
shift
%PYTHON_EXE% main.py --analyze %1 %2 %3 %4
goto :eof

:test_connection
%PYTHON_EXE% main.py --test
goto :eof

endlocal
