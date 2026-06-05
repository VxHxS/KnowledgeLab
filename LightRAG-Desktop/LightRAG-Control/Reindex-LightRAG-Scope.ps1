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
Write-Host "Переиндексация LightRAG по scope" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$Scope = Read-Host "Scope: all/general/game [general]"
if ([string]::IsNullOrWhiteSpace($Scope)) { $Scope = "general" }
if ($Scope -notin @("all", "general", "game")) { $Scope = "general" }

$Project = ""
if ($Scope -eq "game") {
    $Project = Read-Host "Project id [my-game]"
    if ([string]::IsNullOrWhiteSpace($Project)) { $Project = "my-game" }
}

Set-Location -LiteralPath $Lab
& (Join-Path $Paths.Scripts "ingest-vault-scope-lmstudio.ps1") -Scope $Scope -Project $Project

Write-Host ""
Write-Host "Переиндексация завершена." -ForegroundColor Green
Read-Host "Нажмите Enter, чтобы закрыть окно"