$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Root "LightRAG\.venv\Scripts\python.exe"
$env:PYTHONUTF8 = "1"

Write-Host "Checking LM Studio server..."
Invoke-RestMethod -Uri "http://127.0.0.1:1234/v1/models" -Method Get -TimeoutSec 5 | Out-Null

& $Python (Join-Path $PSScriptRoot "simple-vault-rag-lmstudio.py") "Какой Unity workflow описан в этом vault?"
