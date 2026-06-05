$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
& (Join-Path $PSScriptRoot "start-ollama.ps1")

$PortableExe = Join-Path $Root "Ollama\ollama.exe"
if (Test-Path $PortableExe) {
    $OllamaExe = $PortableExe
}
else {
    $OllamaExe = (Get-Command ollama -ErrorAction Stop).Source
}

Write-Host "Pulling embedding model: bge-m3"
& $OllamaExe pull bge-m3

Write-Host "Pulling recommended chat model for RTX 5060 Ti 16GB: qwen3:14b"
& $OllamaExe pull qwen3:14b

Write-Host "Installed models:"
& $OllamaExe list
