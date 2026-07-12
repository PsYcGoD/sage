param(
    [string]$Package = "psycgod-sage",
    [switch]$ForceSetup
)

$ErrorActionPreference = "Stop"

Write-Host "Installing SAGE from PyPI..." -ForegroundColor Cyan
python -m pip install --upgrade $Package

if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "Starting SAGE setup..." -ForegroundColor Cyan
if ($ForceSetup) {
    python -m sage setup --force
} else {
    python -m sage
}
