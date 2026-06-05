$ErrorActionPreference = "Continue"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

$PathHelperCandidates = @(
    (Join-Path $PSScriptRoot "LightRAG-Control\Resolve-LightRAG-Paths.ps1"),
    (Join-Path $PSScriptRoot "Resolve-LightRAG-Paths.ps1")
)

$PathHelper = $PathHelperCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if ($PathHelper) {
    . $PathHelper
    try {
        $Paths = Get-LightRAGPaths -StartDir $PSScriptRoot
        $Lab = $Paths.Root
        $Scripts = $Paths.Scripts
    }
    catch {
        Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
        Read-Host "Press Enter to close"
        exit 1
    }
} else {
    $Lab = "C:\MyFiles\KnowledgeLab"
    $Scripts = Join-Path $Lab "scripts"
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "LightRAG Web Chat" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Context: Obsidian Web Development -> LightRAG -> LM Studio"
Write-Host ""

Set-Location -LiteralPath $Lab
& (Join-Path $Scripts "chat-vault-lmstudio.ps1") -Scope web -Project web-development

Write-Host ""
Read-Host "Press Enter to close"

