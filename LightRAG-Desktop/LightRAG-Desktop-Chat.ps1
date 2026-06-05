$ErrorActionPreference = "Stop"

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

$Python = Join-Path $Lab "LightRAG\.venv\Scripts\pythonw.exe"
if (-not (Test-Path -LiteralPath $Python)) {
    $Python = Join-Path $Lab "LightRAG\.venv\Scripts\python.exe"
}
if (-not (Test-Path -LiteralPath $Python)) {
    $Python = "python"
}

$App = Join-Path $Lab "scripts\knowledge_chat_gui.py"
Start-Process -FilePath $Python -ArgumentList @($App) -WorkingDirectory $Lab
