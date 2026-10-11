@echo off
setlocal EnableExtensions
cd /d "%~dp0"

if not exist ".venv\Scripts\littlefox-one-record-probe.exe" (
    echo.
    echo Run setup_session.cmd first on this session computer.
    echo.
    pause
    exit /b 2
)

set "CHROME="
if exist "%ProgramFiles%\Google\Chrome\Application\chrome.exe" set "CHROME=%ProgramFiles%\Google\Chrome\Application\chrome.exe"
if not defined CHROME if exist "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe" set "CHROME=%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
if not defined CHROME if exist "%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe" set "CHROME=%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"

if not defined CHROME (
    echo.
    echo Google Chrome was not found. Stop here; no site access attempted.
    pause
    exit /b 2
)

set "PROFILE=%~dp0chrome-profile"
echo.
echo Little Fox Writing - ONE RECORD read-only probe
echo ===============================================
echo.
echo Close other Chrome windows that could interfere with debugging.
echo This launcher opens one dedicated Chrome tab, not a class downloader.
echo.

start "" "%CHROME%" --remote-debugging-port=9222 --user-data-dir="%PROFILE%" --no-first-run --no-default-browser-check "about:blank"

echo In the new Chrome window:
echo   1. Sign in to Little Fox yourself.
echo   2. Manually open ONE Writing detail page through the site.
echo   3. Leave only that page open in the dedicated debugging profile.
echo   4. Return here, then press any key once.
echo.
pause

".\.venv\Scripts\littlefox-one-record-probe.exe" --cdp-endpoint http://127.0.0.1:9222
set "PROBE_EXIT=%ERRORLEVEL%"
echo.
echo Probe finished (exit %PROBE_EXIT%).
echo Status 3 is expected while source interpretation and export stay blocked.
echo This probe creates no Writing export and makes no website changes.
echo.
pause
exit /b %PROBE_EXIT%
