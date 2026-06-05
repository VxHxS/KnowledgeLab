param(
    [ValidateSet("all", "general", "game", "web")]
    [string] $Scope = "all",
    [string] $Project = "",
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]] $QuestionParts
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Root "LightRAG\.venv\Scripts\python.exe"
$SafeProject = $Project.Trim().ToLower() -replace "[^a-z0-9_-]+", "-"
if (-not $SafeProject) { $SafeProject = "default" }
$StorageName = if ($Scope -eq "all") { "all" } elseif ($Scope -eq "game") { "game_$SafeProject" } else { $Scope }
$StorageRel = "LightRAG\rag_storage_$StorageName"
$StoragePath = Join-Path $Root $StorageRel
$Question = ($QuestionParts -join " ").Trim()
if (-not $Question) { $Question = "Что важного есть в этом контексте?" }
$UseLightRag = $true
if ($env:LMSTUDIO_USE_LIGHTRAG -match "^(0|false|no|off)$") {
    $UseLightRag = $false
}

$env:PYTHONUTF8 = "1"
$env:LMSTUDIO_SCOPE = $Scope
$env:LMSTUDIO_PROJECT = if ($Scope -in @("game", "web")) { $Project } else { "" }
$env:LMSTUDIO_RAG_DIR = $StorageRel

if ($UseLightRag -and -not (Test-Path -LiteralPath (Join-Path $StoragePath "vdb_chunks.json"))) {
    Write-Host "LightRAG storage was not found for scope '$Scope'." -ForegroundColor Yellow
    if ($Scope -eq "game") {
        Write-Host "Run first: scripts\ingest-vault-scope-lmstudio.ps1 -Scope game -Project $Project" -ForegroundColor Yellow
    } elseif ($Scope -eq "web" -and $Project) {
        Write-Host "Run first: scripts\ingest-vault-scope-lmstudio.ps1 -Scope web -Project $Project" -ForegroundColor Yellow
    } else {
        Write-Host "Run first: scripts\ingest-vault-scope-lmstudio.ps1 -Scope $Scope" -ForegroundColor Yellow
    }
    exit 2
}

& (Join-Path $PSScriptRoot "start-knowledge-lab.ps1")
& $Python (Join-Path $PSScriptRoot "query-vault-lmstudio.py") $Question
