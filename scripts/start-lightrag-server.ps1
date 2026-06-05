$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$LightRagDir = Join-Path $Root "LightRAG"
$VenvScripts = Join-Path $LightRagDir ".venv\Scripts"
$ServerExe = Join-Path $VenvScripts "lightrag-server.exe"

if (-not (Test-Path $ServerExe)) {
    throw "lightrag-server.exe was not found. Install LightRAG first with the local venv."
}

$env:OLLAMA_MODELS = Join-Path $Root "Ollama\models"
$env:PYTHONUTF8 = "1"
$env:PATH = (Join-Path $Root "Ollama") + ";" + $env:PATH

Set-Location $LightRagDir
Write-Host "Starting LightRAG Server at http://127.0.0.1:9621"
& $ServerExe
