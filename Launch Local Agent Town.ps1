param(
    [switch]$SmokeTest
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonPath = Join-Path $projectRoot ".venv\Scripts\python.exe"
$setupPath = Join-Path $projectRoot "setup.ps1"

try {
    Set-Location $projectRoot

    if (!(Test-Path -LiteralPath $pythonPath -PathType Leaf)) {
        Write-Host "First run setup: creating local Python environment..."
        & $setupPath
    }

    if ($SmokeTest) {
        & $pythonPath -m agent_town --smoke-test
    }
    else {
        & $pythonPath -m agent_town
    }
}
catch {
    Write-Host ""
    Write-Host "Local Agent Town failed to launch:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host ""
    Read-Host "Press Enter to close"
    exit 1
}
