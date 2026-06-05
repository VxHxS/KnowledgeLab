$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$PortableExe = Join-Path $Root "Ollama\ollama.exe"
$ModelsDir = Join-Path $Root "Ollama\models"
New-Item -ItemType Directory -Force -Path $ModelsDir | Out-Null

$env:OLLAMA_MODELS = $ModelsDir

try {
    Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -Method Get -TimeoutSec 2 | Out-Null
    Write-Host "Ollama is already running at http://127.0.0.1:11434"
    exit 0
}
catch {
}

$OllamaExe = $PortableExe
if (-not (Test-Path $OllamaExe)) {
    $Command = Get-Command ollama -ErrorAction SilentlyContinue
    if ($null -eq $Command) {
        throw "Ollama was not found. Finish the portable download/extract step or install Ollama for Windows."
    }
    $OllamaExe = $Command.Source
}

Write-Host "Starting Ollama from $OllamaExe"
Start-Process -FilePath $OllamaExe -ArgumentList "serve" -WorkingDirectory (Split-Path -Parent $OllamaExe) -WindowStyle Hidden
Start-Sleep -Seconds 5
Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -Method Get -TimeoutSec 10 | Out-Null
Write-Host "Ollama started at http://127.0.0.1:11434"
