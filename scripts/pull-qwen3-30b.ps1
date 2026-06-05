$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
& (Join-Path $PSScriptRoot "start-ollama.ps1")

$PortableExe = Join-Path $Root "Ollama\ollama.exe"
if (Test-Path $PortableExe) {
    $OllamaExe = $PortableExe
}
else {
    $Command = Get-Command ollama -ErrorAction SilentlyContinue
    if ($null -eq $Command) {
        throw "Ollama CLI was not found in PATH. If you downloaded qwen3:30b from Ollama Desktop, you can skip this script and run run-core-test.cmd."
    }
    $OllamaExe = $Command.Source
}

Write-Host "Pulling embedding model: bge-m3"
& $OllamaExe pull bge-m3

Write-Host "Pulling chat model: qwen3:30b"
& $OllamaExe pull qwen3:30b

Write-Host "Installed models:"
& $OllamaExe list
