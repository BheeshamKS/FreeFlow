@echo off
setlocal
echo ==============================================================================
echo             FreeFlow for Windows — Setup & Deployment Installer               
echo ==============================================================================
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Setup encountered an issue. Please run setup.ps1 directly in PowerShell.
    pause
)
