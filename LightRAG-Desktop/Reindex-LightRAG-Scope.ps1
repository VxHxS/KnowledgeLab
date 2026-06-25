$ErrorActionPreference = "Continue"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

$ControlDir = Join-Path $PSScriptRoot "LightRAG-Control"
. (Join-Path $ControlDir "Resolve-LightRAG-Paths.ps1")
$paths = Get-LightRAGPaths -StartDir $PSScriptRoot
$Lab = $paths.Root

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Переиндексация LightRAG по scope" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$Scope = Read-Host "Scope: all/general/game/web [general]"
if ([string]::IsNullOrWhiteSpace($Scope)) { $Scope = "general" }
if ($Scope -notin @("all", "general", "game", "web")) { $Scope = "general" }

$Project = ""
if ($Scope -eq "game") {
    $Project = Read-Host "Project id [my-game]"
    if ([string]::IsNullOrWhiteSpace($Project)) { $Project = "my-game" }
} elseif ($Scope -eq "web") {
    $Project = Read-Host "Project id [web-development]"
    if ([string]::IsNullOrWhiteSpace($Project)) { $Project = "web-development" }
}

Set-Location -LiteralPath $Lab
& (Join-Path $Lab "scripts\ingest-vault-scope-lmstudio.ps1") -Scope $Scope -Project $Project

Write-Host ""
Write-Host "Переиндексация завершена." -ForegroundColor Green
Read-Host "Нажмите Enter, чтобы закрыть окно"
