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
Write-Host "LightRAG Chat" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "This is not the built-in LM Studio chat."
Write-Host "It is a RAG chat: Obsidian -> LightRAG -> LM Studio."
Write-Host ""
Write-Host "1 - General knowledge"
Write-Host "2 - My Game"
Write-Host "3 - Web Development"
Write-Host ""

$Choice = Read-Host "Choose context [1]"
if ([string]::IsNullOrWhiteSpace($Choice)) { $Choice = "1" }

$Scope = "general"
$Project = ""
if ($Choice -eq "2") {
    $Scope = "game"
    $Project = Read-Host "Project id [my-game]"
    if ([string]::IsNullOrWhiteSpace($Project)) { $Project = "my-game" }
} elseif ($Choice -eq "3") {
    $Scope = "web"
    $Project = Read-Host "Project id [web-development]"
    if ([string]::IsNullOrWhiteSpace($Project)) { $Project = "web-development" }
}

Set-Location -LiteralPath $Lab
if ($Scope -in @("game", "web")) {
    & (Join-Path $Scripts "chat-vault-lmstudio.ps1") -Scope $Scope -Project $Project
} else {
    & (Join-Path $Scripts "chat-vault-lmstudio.ps1") -Scope $Scope
}

Write-Host ""
Read-Host "Press Enter to close"
