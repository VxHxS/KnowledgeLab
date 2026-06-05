$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Root "LightRAG\.venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    throw "Python venv was not found."
}

$env:PYTHONUTF8 = "1"
& (Join-Path $PSScriptRoot "start-ollama.ps1")
& $Python (Join-Path $PSScriptRoot "ingest-vault.py")
& $Python (Join-Path $PSScriptRoot "query-vault.py") "What Unity and music-production workflows are described in this vault?"
