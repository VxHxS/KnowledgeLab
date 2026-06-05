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

$Python = $Paths.Python
if (-not (Test-Path -LiteralPath $Python)) { $Python = "python" }

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Импорт Telegram export в Obsidian" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "В Telegram Desktop: канал/группа -> меню -> Export chat history -> Machine-readable JSON." -ForegroundColor DarkGray
Write-Host "Потом укажи путь к result.json." -ForegroundColor DarkGray
Write-Host ""

$InputPath = Read-Host "Путь к result.json"
$InputPath = $InputPath.Trim('"')
if ([string]::IsNullOrWhiteSpace($InputPath) -or -not (Test-Path -LiteralPath $InputPath)) {
    Write-Host "Файл не найден." -ForegroundColor Red
    Read-Host "Нажмите Enter, чтобы закрыть окно"
    exit 1
}

$ChatName = Read-Host "Название источника [Unity ресурсы]"
if ([string]::IsNullOrWhiteSpace($ChatName)) { $ChatName = "Unity ресурсы" }

$Scope = Read-Host "Scope: general/game [general]"
if ([string]::IsNullOrWhiteSpace($Scope)) { $Scope = "general" }
if ($Scope -notin @("general", "game")) { $Scope = "general" }

$Project = ""
if ($Scope -eq "game") {
    $Project = Read-Host "Project id [my-game]"
    if ([string]::IsNullOrWhiteSpace($Project)) { $Project = "my-game" }
}

Set-Location -LiteralPath $Lab
& $Python (Join-Path $Paths.Scripts "import-telegram-export.py") --input $InputPath --chat-name $ChatName --scope $Scope --project $Project

Write-Host ""
Write-Host "Импорт завершен. После импорта можно задать вопрос или переиндексировать scope." -ForegroundColor Green
Read-Host "Нажмите Enter, чтобы закрыть окно"