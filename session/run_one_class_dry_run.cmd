@echo off
setlocal EnableExtensions
cd /d "%~dp0"

if not exist ".venv\Scripts\littlefox-one-class-dry-run.exe" (
    echo Run setup_session.cmd first on this session computer.
    pause
    exit /b 2
)

set "CLASS_CODE="
set /p "CLASS_CODE=Enter the exact class code shown by Little Fox: "
if not defined CLASS_CODE (
    echo No class code entered. No site access attempted.
    pause
    exit /b 2
)

echo.
echo ONE CLASS read-only discovery dry-run
echo Keep the authenticated Chrome session opened by the one-record launcher running.
echo This follows only links supplied by current pages and creates no files.
pause

".\.venv\Scripts\littlefox-one-class-dry-run.exe" --class-code "%CLASS_CODE%" --cdp-endpoint http://127.0.0.1:9222
set "DISCOVERY_EXIT=%ERRORLEVEL%"
echo.
echo Dry-run finished (exit %DISCOVERY_EXIT%).
echo Status 3 is expected while pagination and live mappings remain unverified.
echo Share only the sanitized count-and-blocker report.
pause
exit /b %DISCOVERY_EXIT%
