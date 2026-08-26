@echo off
rem Build launcher for FeishuCalendar (delegates to build_windows.ps1).
rem Keep this file ASCII-only: cmd mis-parses UTF-8 Chinese under GBK codepage.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build_windows.ps1"
set EC=%errorlevel%
echo.
if not "%EC%"=="0" echo [ERROR] Build failed. See log above.
pause
exit /b %EC%
