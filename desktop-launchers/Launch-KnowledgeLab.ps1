$ErrorActionPreference = "Stop"

$freelance = Join-Path $env:USERPROFILE "Documents\Freelance"
$latest = Get-ChildItem -Path $freelance -Directory -Filter "KnowledgeLab-staging-*" -ErrorAction SilentlyContinue |
    Sort-Object Name -Descending | Select-Object -First 1

if (-not $latest) {
    $latest = Get-ChildItem -Path $freelance -Directory -Filter "KnowledgeLab*" -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -match "KnowledgeLab" } |
        Sort-Object Name -Descending | Select-Object -First 1
}

if ($latest) {
    $script = Join-Path $latest.FullName "LightRAG-Desktop\LightRAG-Desktop-Chat.ps1"
    if (Test-Path -LiteralPath $script) {
        & $script
    } else {
        Write-Host "Launcher not found: $script" -ForegroundColor Red
        Read-Host "Press Enter to close"
    }
} else {
    Write-Host "KnowledgeLab not found in $freelance" -ForegroundColor Red
    Read-Host "Press Enter to close"
}
