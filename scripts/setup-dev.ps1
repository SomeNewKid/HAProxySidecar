$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$HostPython = "C:\Users\somen\AppData\Local\Programs\Python\Python311\python.exe"
$VenvWindowsPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$VenvUnixPython = Join-Path $ProjectRoot ".venv\bin\python.exe"

Set-Location $ProjectRoot

if (-not (Test-Path $HostPython)) {
    throw "Expected Python 3.11 executable was not found at $HostPython."
}

if (-not ((Test-Path $VenvWindowsPython) -or (Test-Path $VenvUnixPython))) {
    & $HostPython -m venv .venv
    if ($LASTEXITCODE -ne 0) {
        throw "Virtual environment creation failed with exit code $LASTEXITCODE."
    }
}

if (Test-Path $VenvWindowsPython) {
    $VenvPython = $VenvWindowsPython
} elseif (Test-Path $VenvUnixPython) {
    $VenvPython = $VenvUnixPython
} else {
    throw "Could not find a Python executable in the virtual environment."
}

function Invoke-Pip {
    & $VenvPython -m pip @args
    if ($LASTEXITCODE -ne 0) {
        throw "pip command failed with exit code $LASTEXITCODE."
    }
}

Invoke-Pip install --index-url https://pypi.org/simple --upgrade pip
Invoke-Pip install --index-url https://pypi.org/simple keyring artifacts-keyring
Invoke-Pip install --editable ".[dev]"
