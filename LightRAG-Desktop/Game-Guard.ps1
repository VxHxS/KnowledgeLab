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
Write-Host "Game Guard watches for Crimson Desert and stops LM Studio models before they steal RAM/VRAM."
Write-Host ""
Write-Host "1 - Watch now in this window"
Write-Host "2 - Install to Windows startup and start hidden"
Write-Host "3 - Disable startup and stop background watcher"
Write-Host "4 - Check once"
Write-Host ""

$Choice = Read-Host "Choose action [1]"
if ([string]::IsNullOrWhiteSpace($Choice)) { $Choice = "1" }

Set-Location -LiteralPath $Lab
switch ($Choice) {
    "2" { & powershell -NoProfile -ExecutionPolicy Bypass -File $GuardScript -InstallStartup -StartNow }
    "3" { & powershell -NoProfile -ExecutionPolicy Bypass -File $GuardScript -UninstallStartup -StopNow }
    "4" { & powershell -NoProfile -ExecutionPolicy Bypass -File $GuardScript -Once }
    default { & powershell -NoProfile -ExecutionPolicy Bypass -File $GuardScript -Watch }
}

Write-Host ""
Read-Host "Press Enter to close"
