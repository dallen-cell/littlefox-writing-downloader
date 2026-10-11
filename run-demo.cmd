@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Missing .venv. Follow docs\windows-session-pc.md first.
  exit /b 1
)
".venv\Scripts\python.exe" -m littlefox_writing.cli --demo --all-classes %*

