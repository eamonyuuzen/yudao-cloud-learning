param(
    [switch]$RequireLive
)

$ErrorActionPreference = "Stop"
$labRoot = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $labRoot ".venv\Scripts\python.exe"
$envFile = Join-Path $labRoot ".env"

function Write-Check {
    param(
        [string]$Name,
        [bool]$Passed,
        [string]$Detail
    )
    $mark = if ($Passed) { "OK" } else { "MISSING" }
    Write-Host ("[{0}] {1}: {2}" -f $mark, $Name, $Detail)
}

function Test-TcpPort {
    param([int]$Port)
    $client = [System.Net.Sockets.TcpClient]::new()
    try {
        $task = $client.ConnectAsync("127.0.0.1", $Port)
        return $task.Wait(700) -and $client.Connected
    } catch {
        return $false
    } finally {
        $client.Dispose()
    }
}

$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
$javaCommand = Get-Command java -ErrorAction SilentlyContinue
$mavenCommand = Get-Command mvn -ErrorAction SilentlyContinue

Write-Check "Python command" ($null -ne $pythonCommand) "Day 1-6"
Write-Check "Java command" ($null -ne $javaCommand) "Day 2 source/test"
Write-Check "Maven command" ($null -ne $mavenCommand) "Day 2 Java test"
Write-Check "Lab virtualenv" (Test-Path -LiteralPath $venvPython) ".venv"

$importsReady = $false
if (Test-Path -LiteralPath $venvPython) {
    & $venvPython -c "import agents, fastapi, httpx, openai, pydantic; print('SDK imports OK')"
    $importsReady = $LASTEXITCODE -eq 0
}
Write-Check "Python dependencies" $importsReady "no model call"

$modelConfigured = $false
if (Test-Path -LiteralPath $envFile) {
    $keys = @{}
    foreach ($line in Get-Content -LiteralPath $envFile -Encoding utf8) {
        if ($line -match "^\s*([A-Z0-9_]+)\s*=\s*(.*?)\s*$") {
            $keys[$matches[1]] = $matches[2]
        }
    }
    $modelConfigured =
        -not [string]::IsNullOrWhiteSpace($keys["MODEL_NAME"]) -and
        -not [string]::IsNullOrWhiteSpace($keys["MODEL_API_KEY"])
}
Write-Check "Model config" $modelConfigured "presence only; values are never printed"

$agentPort = Test-TcpPort -Port 8001
$gatewayPort = Test-TcpPort -Port 48080
Write-Check "Agent :8001" $agentPort "optional before Day 5"
Write-Check "Yudao Gateway :48080" $gatewayPort "required for live query"

$baseReady =
    ($null -ne $pythonCommand) -and
    ($null -ne $javaCommand) -and
    ($null -ne $mavenCommand) -and
    (Test-Path -LiteralPath $venvPython) -and
    $importsReady
$liveReady = $baseReady -and $modelConfigured -and $gatewayPort

Write-Host ""
Write-Host ("Day 1-4 ready: {0}" -f $baseReady)
Write-Host ("Day 5 live-query ready: {0}" -f $liveReady)

if (-not $baseReady -or ($RequireLive -and -not $liveReady)) {
    exit 1
}
