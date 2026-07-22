$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

Set-Location $ProjectRoot

if (-not (Test-Path $VenvPython)) {
    throw "Expected virtual environment Python was not found at $VenvPython. Run scripts/setup-dev.ps1 first."
}

function Invoke-PythonModule {
    & $VenvPython -m @args
    if ($LASTEXITCODE -ne 0) {
        throw "python -m $($args[0]) failed with exit code $LASTEXITCODE."
    }
}

Invoke-PythonModule ruff format .
Invoke-PythonModule ruff check .
Invoke-PythonModule pyright
Invoke-PythonModule pytest
