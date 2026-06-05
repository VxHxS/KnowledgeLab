$ErrorActionPreference = "Stop"
$Lab = "C:\Users\Юрий\Documents\Freelance\AI-Knowledge-Lab"
$Python = Join-Path $Lab "LightRAG\.venv\Scripts\pythonw.exe"
if (-not (Test-Path -LiteralPath $Python)) {
    $Python = Join-Path $Lab "LightRAG\.venv\Scripts\python.exe"
}
Start-Process -FilePath $Python -ArgumentList @((Join-Path $Lab "scripts\telegram_sync_app.py")) -WorkingDirectory $Lab
