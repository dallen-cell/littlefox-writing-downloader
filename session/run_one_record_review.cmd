@echo off
setlocal EnableExtensions
cd /d "%~dp0"

if not exist ".venv\Scripts\littlefox-one-record-review.exe" (
    echo.
    echo Run setup_session.cmd first in this session computer folder.
    echo.
    pause
    exit /b 2
)
echo.
echo Little Fox Writing - ONE RECORD local human review
echo ================================================
echo.
echo Keep the authenticated main browser window and ONE Writing popup open.
echo No new browser, navigation, or automatic class search will be started.
echo Writer/timestamp fields and correction text may be shown on THIS PC only.
echo Do not share the private review display or redirect it to a log file.
echo Type YES only after comparing each field to the normal Little Fox pages.
echo The script cannot export unknown markup or unverified work.
echo.
pause

".\.venv\Scripts\littlefox-one-record-review.exe" --cdp-endpoint http://127.0.0.1:9222 %*
set "REVIEW_EXIT=%ERRORLEVEL%"
echo.
echo Review ended (exit %REVIEW_EXIT%). 3 means no file was created.
echo Share only the final SANITIZED SUMMARY, not the private preview.
echo.
pause
exit /b %REVIEW_EXIT%
