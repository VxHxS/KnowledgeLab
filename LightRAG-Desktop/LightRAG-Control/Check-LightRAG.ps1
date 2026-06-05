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
Write-Host "Проверка LightRAG + Obsidian + LM Studio" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "1/4 Проверяю папку проекта..."
Write-Host "Проект: $Lab"
if (-not (Test-Path -LiteralPath $Lab)) {
    Write-Host "ОШИБКА: папка проекта не найдена." -ForegroundColor Red
    Read-Host "Нажмите Enter, чтобы закрыть окно"
    exit 1
}

Write-Host "2/4 Проверяю, что Obsidian vault существует..."
$Vault = $Paths.Vault
if (Test-Path -LiteralPath $Vault) {
    Write-Host "Vault найден: $Vault" -ForegroundColor Green
}
else {
    Write-Host "ОШИБКА: vault не найден." -ForegroundColor Red
    Read-Host "Нажмите Enter, чтобы закрыть окно"
    exit 1
}

Write-Host "3/4 Запускаю полный тест LightRAG..."
Write-Host "Ожидаемый успешный вывод: extracted ... Ent + ... Rel, Writing graph, References." -ForegroundColor DarkGray
Write-Host ""
Set-Location -LiteralPath $Lab
& (Join-Path $Paths.Scripts "run-lmstudio-test.cmd")

Write-Host ""
Write-Host "4/4 Проверка завершена." -ForegroundColor Cyan
Write-Host "Если выше есть 'Writing graph with ... nodes' и 'References', LightRAG работает." -ForegroundColor Green
Read-Host "Нажмите Enter, чтобы закрыть окно"