$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

$PathHelperCandidates = @(
    (Join-Path $PSScriptRoot "LightRAG-Control\Resolve-LightRAG-Paths.ps1"),
    (Join-Path $PSScriptRoot "Resolve-LightRAG-Paths.ps1")
)

$PathHelper = $PathHelperCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if ($PathHelper) {
    . $PathHelper
    $Paths = Get-LightRAGPaths -StartDir $PSScriptRoot
    $Lab = $Paths.Root
} else {
    $Lab = "C:\MyFiles\KnowledgeLab"
}

$Installer = Join-Path $Lab "scripts\install-knowledge-lab.ps1"
if (-not (Test-Path -LiteralPath $Installer)) {
    Write-Host "Installer was not found: $Installer" -ForegroundColor Red
    Read-Host "Press Enter to close"
    exit 1
}

$Gui = Join-Path $Lab "scripts\install_wizard_gui.py"
$PythonCandidates = @(
    (Join-Path $Lab "LightRAG\.venv\Scripts\pythonw.exe"),
    (Join-Path $Lab "LightRAG\.venv\Scripts\python.exe"),
    "pythonw",
    "python"
)
$Python = $PythonCandidates | Where-Object {
    if ($_ -like "*\*") { Test-Path -LiteralPath $_ } else { Get-Command $_ -ErrorAction SilentlyContinue }
} | Select-Object -First 1

Set-Location -LiteralPath $Lab
if ($Python -and (Test-Path -LiteralPath $Gui)) {
    Start-Process -FilePath $Python -ArgumentList @($Gui) -WorkingDirectory $Lab
    exit 0
} else {
    & $Installer
}

Write-Host ""
Read-Host "Press Enter to close"
