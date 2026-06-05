param(
    [ValidateSet("all", "general", "game", "web")]
    [string] $Scope = "all",
    [string] $Project = ""
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Root "LightRAG\.venv\Scripts\python.exe"
$SafeProject = $Project.Trim().ToLower() -replace "[^a-z0-9_-]+", "-"
if (-not $SafeProject) { $SafeProject = "default" }
$StorageName = if ($Scope -eq "all") { "all" } elseif ($Scope -eq "game") { "game_$SafeProject" } else { $Scope }

$env:PYTHONUTF8 = "1"
$env:LMSTUDIO_SCOPE = $Scope
$env:LMSTUDIO_PROJECT = if ($Scope -in @("game", "web")) { $Project } else { "" }
$env:LMSTUDIO_RAG_DIR = "LightRAG\rag_storage_$StorageName"

if ($env:LIGHTRAG_SYNC_YOUTUBE_LINKS -ne "0") {
    $SyncArgs = @("--scope", $Scope)
    if ($Scope -in @("game", "web") -and $Project) {
        $SyncArgs += @("--project", $Project)
    }
    & $Python (Join-Path $PSScriptRoot "sync-youtube-links.py") @SyncArgs
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}
& (Join-Path $PSScriptRoot "start-knowledge-lab.ps1")
& $Python (Join-Path $PSScriptRoot "ingest-vault-lmstudio.py")
