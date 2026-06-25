$ErrorActionPreference = "Continue"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

$ControlDir = Join-Path $PSScriptRoot "LightRAG-Control"
. (Join-Path $ControlDir "Resolve-LightRAG-Paths.ps1")
$paths = Get-LightRAGPaths -StartDir $PSScriptRoot
$Lab = $paths.Root

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Вопрос к web-базе знаний" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$Question = Read-Host "Введите вопрос"
if ([string]::IsNullOrWhiteSpace($Question)) {
    $Question = "Какие полезные web-решения есть в базе?"
}

$env:LMSTUDIO_SCOPE = "web"
$env:LMSTUDIO_PROJECT = "web-development"
Set-Location -LiteralPath $Lab
& (Join-Path $Lab "scripts\ask-vault-lmstudio.ps1") $Question

Write-Host ""
Read-Host "Нажмите Enter, чтобы закрыть окно"

