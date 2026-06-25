$ErrorActionPreference = "Continue"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

$ControlDir = Join-Path $PSScriptRoot "LightRAG-Control"
. (Join-Path $ControlDir "Resolve-LightRAG-Paths.ps1")
$paths = Get-LightRAGPaths -StartDir $PSScriptRoot
$Lab = $paths.Root

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Вопрос по моей игре" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$Project = Read-Host "Project id [my-game]"
if ([string]::IsNullOrWhiteSpace($Project)) { $Project = "my-game" }
$Question = Read-Host "Введите вопрос"
if ([string]::IsNullOrWhiteSpace($Question)) {
    $Question = "Что сейчас известно по моей игре?"
}

$env:LMSTUDIO_SCOPE = "game"
$env:LMSTUDIO_PROJECT = $Project
Set-Location -LiteralPath $Lab
& (Join-Path $Lab "scripts\ask-vault-lmstudio.ps1") $Question

Write-Host ""
Read-Host "Нажмите Enter, чтобы закрыть окно"
