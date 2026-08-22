[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$RepositoryRoot = Split-Path -Parent $PSScriptRoot
$VirtualEnvironment = Join-Path $RepositoryRoot ".venv"
$VirtualPython = Join-Path $VirtualEnvironment "Scripts\python.exe"

if (-not (Test-Path $VirtualPython)) {
    Write-Host "Creating Windows virtual environment in .venv..." -ForegroundColor Cyan

    $PythonLauncher = Get-Command py -ErrorAction SilentlyContinue
    if ($PythonLauncher) {
        & $PythonLauncher.Source -3 -m venv $VirtualEnvironment
    }
    else {
        $PythonCommand = Get-Command python -ErrorAction SilentlyContinue
        if (-not $PythonCommand) {
            throw "Python 3 was not found. Install it or add python.exe to PATH."
        }

        & $PythonCommand.Source -m venv $VirtualEnvironment
    }

    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $VirtualPython)) {
        throw "Creating .venv failed."
    }
}

Write-Host "Upgrading pip and test dependencies..." -ForegroundColor Cyan
& $VirtualPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) {
    throw "Upgrading pip failed with exit code $LASTEXITCODE."
}

& $VirtualPython -m pip install --upgrade pytest pytest-cov pyyaml yamllint
if ($LASTEXITCODE -ne 0) {
    throw "Installing test dependencies failed with exit code $LASTEXITCODE."
}

Write-Host "`nTest environment is ready." -ForegroundColor Green
Write-Host "Run .\scripts\run-tests.ps1 to execute the suite."
