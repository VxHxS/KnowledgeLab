$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Root "LightRAG\.venv\Scripts\python.exe"
$env:PYTHONUTF8 = "1"

& $Python (Join-Path $PSScriptRoot "smoke-test.py")
