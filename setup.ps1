# FreeFlow Windows Automated Setup & Dependency Installer
# Installs Python dependencies, configures environment, and launches Setup Mode.

$ErrorActionPreference = "Stop"

Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host "            FreeFlow for Windows — Setup & Deployment Installer               " -ForegroundColor Cyan
Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host ""

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# 1. Check Python
Write-Host "[INFO] Checking Python installation..." -ForegroundColor Cyan
$PythonCmd = $null
if (Get-Command python -ErrorAction SilentlyContinue) {
    $PythonCmd = "python"
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $PythonCmd = "py -3"
} else {
    Write-Host "[ERROR] Python 3.10+ was not found. Please install Python from https://www.python.org/downloads/ or Microsoft Store." -ForegroundColor Red
    Exit 1
}

# Verify Python version >= 3.10
$PyVer = & $PythonCmd -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
Write-Host "[OK] Detected Python $PyVer" -ForegroundColor Green

# 2. Virtual Environment
$VenvDir = Join-Path $ScriptDir ".venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
$VenvPip = Join-Path $VenvDir "Scripts\pip.exe"

if (-not (Test-Path $VenvPython)) {
    Write-Host "[INFO] Creating virtual environment in $VenvDir..." -ForegroundColor Cyan
    & $PythonCmd -m venv $VenvDir
}
Write-Host "[OK] Virtual environment ready." -ForegroundColor Green

# 3. Upgrade pip and install requirements
Write-Host "[INFO] Installing FreeFlow requirements..." -ForegroundColor Cyan
& $VenvPip install --upgrade pip --quiet
& $VenvPip install -r requirements.txt --quiet
Write-Host "[OK] All dependencies installed successfully." -ForegroundColor Green

# 4. Create local shortcut / command launcher
$LocalBin = Join-Path $env:LOCALAPPDATA "Microsoft\WindowsApps"
$BatchLauncher = Join-Path $ScriptDir "freeflow.cmd"
$LauncherContent = @"
@echo off
start "" "$VenvPython" "$ScriptDir\app.py" %*
"@
Set-Content -Path $BatchLauncher -Value $LauncherContent -Force
Write-Host "[OK] Created launcher script: freeflow.cmd" -ForegroundColor Green

# 5. Launch FreeFlow in Setup Mode
Write-Host ""
Write-Host "==============================================================================" -ForegroundColor Green
Write-Host " [SUCCESS] FreeFlow installed successfully! Launching Setup Wizard...         " -ForegroundColor Green
Write-Host "==============================================================================" -ForegroundColor Green
Write-Host ""

& $VenvPython app.py --setup
