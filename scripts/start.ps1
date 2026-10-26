param([switch]$Install)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
if ($Install) {
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the Python environment.' }
    & ./.venv/Scripts/python.exe -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw 'Python dependency installation failed.' }
    Push-Location frontend
    try { npm.cmd ci; if ($LASTEXITCODE -ne 0) { throw 'Frontend installation failed.' } } finally { Pop-Location }
}
if (!(Test-Path -LiteralPath '.venv/Scripts/python.exe')) { throw 'Run ./scripts/start.ps1 -Install first.' }
& ./.venv/Scripts/python.exe -m scripts.dev
