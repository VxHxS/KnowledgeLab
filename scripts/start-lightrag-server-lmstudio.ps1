$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$LightRagDir = Join-Path $Root "LightRAG"
$ServerExe = Join-Path $LightRagDir ".venv\Scripts\lightrag-server.exe"
$LmEnv = Join-Path $LightRagDir ".env.lmstudio.example"
$ActiveEnv = Join-Path $LightRagDir ".env"

if (-not (Test-Path $ServerExe)) {
    throw "lightrag-server.exe was not found."
}

Copy-Item -Path $LmEnv -Destination $ActiveEnv -Force
$env:PYTHONUTF8 = "1"

Set-Location $LightRagDir
Write-Host "Starting LightRAG Server via LM Studio at http://127.0.0.1:9621"
& $ServerExe
