$ErrorActionPreference = "Stop"
$labRoot = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $labRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $venvPython)) {
    throw ".venv was not found. Follow the README setup steps first."
}

Push-Location $labRoot
try {
    & $venvPython -m pytest -q -p no:cacheprovider
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
} finally {
    Pop-Location
}
