$ErrorActionPreference = "Continue"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

$ControlDir = Join-Path $PSScriptRoot "LightRAG-Control"
. (Join-Path $ControlDir "Resolve-LightRAG-Paths.ps1")
$paths = Get-LightRAGPaths -StartDir $PSScriptRoot
$Lab = $paths.Root
$Python = $paths.Python
if (-not (Test-Path -LiteralPath $Python)) { $Python = "python" }

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Импорт Telegram export в Obsidian" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "В Telegram Desktop: канал/группа -> меню -> Export chat history -> Machine-readable JSON." -ForegroundColor DarkGray
Write-Host "Потом укажи путь к result.json." -ForegroundColor DarkGray
Write-Host ""

$InputPath = Read-Host "Путь к result.json"
if ([string]::IsNullOrWhiteSpace($InputPath) -or -not (Test-Path -LiteralPath $InputPath)) {
    Write-Host "Файл не найден." -ForegroundColor Red
    Read-Host "Нажмите Enter, чтобы закрыть окно"
    exit 1
}

$ChatName = Read-Host "Название источника [Unity ресурсы]"
if ([string]::IsNullOrWhiteSpace($ChatName)) { $ChatName = "Unity ресурсы" }

$Scope = Read-Host "Scope: general/game/web [general]"
if ([string]::IsNullOrWhiteSpace($Scope)) { $Scope = "general" }
if ($Scope -notin @("general", "game", "web")) { $Scope = "general" }

$Project = ""
if ($Scope -eq "game") {
    $Project = Read-Host "Project id [my-game]"
    if ([string]::IsNullOrWhiteSpace($Project)) { $Project = "my-game" }
} elseif ($Scope -eq "web") {
    $Project = Read-Host "Project id [web-development]"
    if ([string]::IsNullOrWhiteSpace($Project)) { $Project = "web-development" }
}

$DefaultAdFilter = if ($Scope -eq "web") { "separate" } else { "mark" }
$AdFilter = Read-Host "Фильтр рекламы: off/mark/separate/skip [$DefaultAdFilter]"
if ([string]::IsNullOrWhiteSpace($AdFilter)) { $AdFilter = $DefaultAdFilter }
if ($AdFilter -notin @("off", "mark", "separate", "skip")) { $AdFilter = $DefaultAdFilter }

Set-Location -LiteralPath $Lab
$ImportArgs = @(
    "--input", $InputPath,
    "--chat-name", $ChatName,
    "--scope", $Scope,
    "--project", $Project,
    "--ad-filter", $AdFilter
)
if ($Scope -eq "web") {
    $ImportArgs += @("--out-dir", "20 Projects/Web Development/Sources/Telegram")
}
& $Python (Join-Path $Lab "scripts\import-telegram-export.py") @ImportArgs

Write-Host ""
Write-Host "Импорт завершен. После импорта можно задать вопрос или переиндексировать scope." -ForegroundColor Green
Read-Host "Нажмите Enter, чтобы закрыть окно"
