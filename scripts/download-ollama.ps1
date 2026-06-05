$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$OllamaDir = Join-Path $Root "Ollama"
$ZipPath = Join-Path $OllamaDir "ollama-windows-amd64.zip"
$OllamaExe = Join-Path $OllamaDir "ollama.exe"
$Url = "https://github.com/ollama/ollama/releases/latest/download/ollama-windows-amd64.zip"

New-Item -ItemType Directory -Force -Path $OllamaDir | Out-Null

if (Test-Path $OllamaExe) {
    Write-Host "Portable Ollama already exists: $OllamaExe"
    & $OllamaExe --version
    exit 0
}

Write-Host "Downloading portable Ollama with resume support."
Write-Host "Target: $ZipPath"
curl.exe --fail --location --retry 50 --retry-all-errors --retry-delay 5 --continue-at - --output $ZipPath $Url

Write-Host "Extracting Ollama..."
Expand-Archive -Path $ZipPath -DestinationPath $OllamaDir -Force

if (-not (Test-Path $OllamaExe)) {
    throw "Download/extract completed, but ollama.exe was not found in $OllamaDir"
}

& $OllamaExe --version
Write-Host "Portable Ollama is ready."
