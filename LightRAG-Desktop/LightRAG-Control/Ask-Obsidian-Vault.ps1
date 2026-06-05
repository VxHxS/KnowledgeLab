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
Write-Host "Вопрос к Obsidian Vault через локальную LLM" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Этот запуск читает Markdown-заметки из Obsidian-Test-Vault и задает вопрос локальной модели."
Write-Host "Для Qwen3 автоматически добавляется /no_think." -ForegroundColor DarkGray
Write-Host ""

$Question = Read-Host "Введите вопрос"
if ([string]::IsNullOrWhiteSpace($Question)) {
    $Question = "Какой Unity workflow описан в этом vault?"
    Write-Host "Вопрос не введен. Использую тестовый вопрос: $Question" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Запускаю локальный RAG-запрос..." -ForegroundColor Cyan
Set-Location -LiteralPath $Lab
& (Join-Path $Paths.Scripts "ask-vault-lmstudio.ps1") $Question

Write-Host ""
Write-Host "Запрос завершен." -ForegroundColor Cyan
Read-Host "Нажмите Enter, чтобы закрыть окно"