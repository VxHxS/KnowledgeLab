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
    }
    catch {
        Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
        Read-Host "Press Enter to close"
        exit 1
    }
} else {
    $Lab = "C:\MyFiles\KnowledgeLab"
}

$GuardScript = Join-Path $Lab "scripts\game-guard.ps1"
if (-not (Test-Path -LiteralPath $GuardScript)) {
    Write-Host "ERROR: Game Guard script was not found:" -ForegroundColor Red
    Write-Host $GuardScript
    Read-Host "Press Enter to close"
    exit 1
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "KnowledgeLab Game Guard" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Game Guard helps diagnose GPU conflicts between heavy apps and local AI processes."
Write-Host "The chat also runs a delayed GPU warning after the window opens."
Write-Host "Game Guard is not installed into Windows startup."
Write-Host ""
Write-Host "1 - Watch now in this window"
Write-Host "2 - Check once"
Write-Host ""

$Choice = Read-Host "Choose action [1]"
if ([string]::IsNullOrWhiteSpace($Choice)) { $Choice = "1" }

Set-Location -LiteralPath $Lab
switch ($Choice) {
    "2" { & powershell -NoProfile -ExecutionPolicy Bypass -File $GuardScript -Once }
    default { & powershell -NoProfile -ExecutionPolicy Bypass -File $GuardScript -Watch }
}

Write-Host ""
Read-Host "Press Enter to close"
