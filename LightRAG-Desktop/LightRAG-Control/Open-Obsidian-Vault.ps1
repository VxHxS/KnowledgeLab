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
    $Vault = $Paths.Vault
}
catch {
    Write-Host "ОШИБКА: $($_.Exception.Message)" -ForegroundColor Red
    Read-Host "Нажмите Enter, чтобы закрыть окно"
    exit 1
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Открытие папки Obsidian vault" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Открываю папку vault в Проводнике:"
Write-Host $Vault -ForegroundColor Yellow
Write-Host ""
Write-Host "Важно: если в Obsidian не видны папки 00 Inbox / 10 Programming / 20 Music," -ForegroundColor Yellow
Write-Host "значит в Obsidian открыт другой vault или открыт Graph/быстрый переход, а не файловая панель." -ForegroundColor Yellow
Write-Host ""
Write-Host "В Obsidian открой: Manage vaults -> Open folder as vault -> эту папку." -ForegroundColor Cyan

if (-not (Test-Path -LiteralPath $Vault)) {
    Write-Host "ОШИБКА: vault не найден." -ForegroundColor Red
    Read-Host "Нажмите Enter, чтобы закрыть окно"
    exit 1
}

Start-Process explorer.exe -ArgumentList @($Vault)

Write-Host ""
Read-Host "Нажмите Enter, чтобы закрыть окно"