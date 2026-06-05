$ErrorActionPreference = "Continue"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

$PathHelper = Join-Path $PSScriptRoot "Resolve-LightRAG-Paths.ps1"
if (-not (Test-Path -LiteralPath $PathHelper)) {
    Write-Host "ОШИБКА: не найден Resolve-LightRAG-Paths.ps1 рядом с запускателем." -ForegroundColor Red
    Read-Host "Нажмите Enter, чтобы закрыть окно"
    exit 1
}

. $PathHelper
try {
    $Paths = Get-LightRAGPaths -StartDir $PSScriptRoot
    $Lab = $Paths.Root
}
catch {
    Write-Host "ОШИБКА: $($_.Exception.Message)" -ForegroundColor Red
    Read-Host "Нажмите Enter, чтобы закрыть окно"
    exit 1
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Остановка локальной AI-системы" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Выгружаю модели и останавливаю LM Studio server..."
Set-Location -LiteralPath $Lab
& (Join-Path $Paths.Scripts "stop-knowledge-lab.ps1")

Write-Host ""
Write-Host "Готово. Ресурсы должны быть освобождены." -ForegroundColor Green
Read-Host "Нажмите Enter, чтобы закрыть окно"