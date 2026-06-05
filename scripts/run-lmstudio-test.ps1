$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Root "LightRAG\.venv\Scripts\python.exe"
$env:PYTHONUTF8 = "1"
$env:LMSTUDIO_INCLUDE = "unity"
$env:LMSTUDIO_RAG_DIR = "LightRAG\rag_storage_lmstudio_test_$((Get-Date).ToString('yyyyMMdd_HHmmss'))"

Write-Host "Checking LM Studio server..."
& (Join-Path $PSScriptRoot "start-knowledge-lab.ps1")
Invoke-RestMethod -Uri "http://127.0.0.1:1234/v1/models" -Method Get -TimeoutSec 5 | Out-Null

& $Python (Join-Path $PSScriptRoot "ingest-vault-lmstudio.py")
& $Python (Join-Path $PSScriptRoot "query-vault-lmstudio.py") "What Unity workflow is described in this vault?"
