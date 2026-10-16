param([string]$PythonPath = "python")
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot
& $PythonPath "$PSScriptRoot\configure_codex.py"
if ($LASTEXITCODE -ne 0) { throw 'Codex bridge configuration failed.' }
try { $bridgeHealth = Invoke-RestMethod 'http://127.0.0.1:8866/health' -TimeoutSec 3 } catch { $bridgeHealth = $null }
if ($bridgeHealth -and $bridgeHealth.service -ne 'lastmile-codex-bridge') { throw 'Port 8866 is occupied by another service.' }
$bridgeScript = Join-Path $PSScriptRoot 'codex_bridge.py'
$bridgeBuild = (Get-FileHash -LiteralPath $bridgeScript -Algorithm SHA256).Hash.ToLowerInvariant()
if ($bridgeHealth -and $bridgeHealth.build -ne $bridgeBuild) {
    if ($bridgeHealth.busy) { throw 'A Codex cycle is running. Wait for it to finish before restarting the bridge.' }
    Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and $_.CommandLine.Contains($bridgeScript) } | ForEach-Object { Stop-Process -Id $_.ProcessId }
    $bridgeHealth = $null
}
if (-not $bridgeHealth) {
    Start-Process -FilePath $PythonPath -ArgumentList @('-u', "`"$PSScriptRoot\codex_bridge.py`"") -WorkingDirectory $projectRoot -WindowStyle Hidden -RedirectStandardOutput "$projectRoot\.private\codex-bridge.log" -RedirectStandardError "$projectRoot\.private\codex-bridge-error.log"
}
docker compose up -d --build --wait
if ($LASTEXITCODE -ne 0) { throw 'Docker startup failed. Check Docker Desktop.' }
$appHealth = Invoke-RestMethod 'http://127.0.0.1:8000/api/health' -TimeoutSec 10
if (-not $appHealth.codex_configured) { throw 'The local Codex bridge is not authenticated or reachable. Check .private/codex-bridge-error.log and codex login status.' }
Write-Output 'LastMile is available at http://localhost:5173. Select Codex · ChatGPT plan.'
