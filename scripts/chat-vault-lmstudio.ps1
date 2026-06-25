param(
    [ValidateSet("all", "general", "game", "web")]
    [string] $Scope = "general",
    [string] $Project = ""
)

$ErrorActionPreference = "Stop"

function Get-KnowledgeLabShortName {
    param(
        [string] $Value,
        [int] $MaxLength = 48
    )

    $name = ($Value -replace "[^A-Za-z0-9_-]+", "-").Trim("-")
    if (-not $name) { $name = "default" }
    if ($name.Length -le $MaxLength) { return $name }

    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $bytes = [System.Text.Encoding]::UTF8.GetBytes($name)
        $hashBytes = $sha.ComputeHash($bytes)
    }
    finally {
        if ($sha) { $sha.Dispose() }
    }
    $hash = -join ($hashBytes[0..5] | ForEach-Object { $_.ToString("x2") })
    $prefixLength = [Math]::Max(8, $MaxLength - 13)
    return ("{0}-{1}" -f $name.Substring(0, [Math]::Min($prefixLength, $name.Length)), $hash)
}

$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Root "LightRAG\.venv\Scripts\python.exe"
$SafeProject = $Project.Trim().ToLower() -replace "[^a-z0-9_-]+", "-"
if (-not $SafeProject) { $SafeProject = "default" }
$SafeProject = Get-KnowledgeLabShortName $SafeProject 48
$StorageName = if ($Scope -eq "all") { "all" } elseif ($Scope -eq "game") { "game_$SafeProject" } else { $Scope }
$StorageRel = "LightRAG\rag_storage_$StorageName"
$StoragePath = Join-Path $Root $StorageRel

$env:PYTHONUTF8 = "1"
$env:LMSTUDIO_SCOPE = $Scope
$env:LMSTUDIO_PROJECT = if ($Scope -in @("game", "web")) { $Project } else { "" }
$env:LMSTUDIO_RAG_DIR = $StorageRel

Write-Host "LightRAG chat over Obsidian vault" -ForegroundColor Cyan
Write-Host "Scope: $Scope"
if ($Scope -eq "game") {
    if (-not $Project) { $Project = "my-game" }
    Write-Host "Project: $Project"
} elseif ($Scope -eq "web" -and $Project) {
    Write-Host "Project: $Project"
}

if (-not (Test-Path -LiteralPath (Join-Path $StoragePath "vdb_chunks.json"))) {
    Write-Host ""
    Write-Host "LightRAG storage is not indexed yet. Building it now..." -ForegroundColor Yellow

    if ($Scope -eq "game") {
        & (Join-Path $PSScriptRoot "ingest-vault-scope-lmstudio.ps1") -Scope $Scope -Project $Project
    } elseif ($Scope -eq "web" -and $Project) {
        & (Join-Path $PSScriptRoot "ingest-vault-scope-lmstudio.ps1") -Scope $Scope -Project $Project
    } else {
        & (Join-Path $PSScriptRoot "ingest-vault-scope-lmstudio.ps1") -Scope $Scope
    }
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

& (Join-Path $PSScriptRoot "start-knowledge-lab.ps1")
& $Python (Join-Path $PSScriptRoot "chat-vault-lmstudio.py")
