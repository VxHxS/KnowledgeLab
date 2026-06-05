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
Write-Host "Вопрос к общей базе знаний" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$Question = Read-Host "Введите вопрос"
if ([string]::IsNullOrWhiteSpace($Question)) {
    $Question = "Что полезного есть в общей Unity-базе?"
}

$env:LMSTUDIO_SCOPE = "general"
$env:LMSTUDIO_PROJECT = ""
Set-Location -LiteralPath $Lab
& (Join-Path $Paths.Scripts "ask-vault-lmstudio.ps1") $Question

Write-Host ""
Read-Host "Нажмите Enter, чтобы закрыть окно"