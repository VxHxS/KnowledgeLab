param(
    [ValidateSet("all", "general", "game", "web")]
    [string] $Scope = "all",
    [ValidateSet("active", "finished-projects")]
    [string] $Layer = "active",
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
$StorageName = if ($Layer -eq "finished-projects") {
    "finished_projects"
} elseif ($Scope -eq "all") {
    "all"
} elseif ($Scope -eq "web" -and $SafeProject -notin @("default", "web-development")) {
    "web_$SafeProject"
} elseif ($Scope -eq "game") {
    "game_$SafeProject"
} elseif ($Scope -eq "general" -and $SafeProject -ne "default") {
    "general_$SafeProject"
} else {
    $Scope
}

$env:PYTHONUTF8 = "1"
$env:LMSTUDIO_SCOPE = $Scope
$env:LMSTUDIO_PROJECT = if ($Project) { $Project } else { "" }
$env:LMSTUDIO_LAYER = $Layer
$env:LMSTUDIO_RAG_DIR = "LightRAG\rag_storage_$StorageName"
$ConfiguredVaultDir = ""

$SettingsPath = Join-Path $Root "tmp\knowledge-chat-settings.json"
try {
    if (Test-Path -LiteralPath $SettingsPath) {
        $settings = Get-Content -LiteralPath $SettingsPath -Raw -ErrorAction Stop | ConvertFrom-Json -ErrorAction Stop
        if ($settings.vault_path) {
            $ConfiguredVaultDir = [string] $settings.vault_path
            $env:KNOWLEDGELAB_VAULT_DIR = $ConfiguredVaultDir
        }
    }
}
catch {
    Write-Warning "Failed to read settings from $SettingsPath`: $($_.Exception.Message). Using default vault path."
}

if ($Layer -eq "active" -and $env:LIGHTRAG_SYNC_YOUTUBE_LINKS -ne "0") {
    $SyncArgs = @("--scope", $Scope)
    if ($Scope -in @("game", "web") -and $Project) {
        $SyncArgs += @("--project", $Project)
    }
    if ($ConfiguredVaultDir) {
        $SyncArgs += @("--vault-dir", $ConfiguredVaultDir)
    }
    & $Python (Join-Path $PSScriptRoot "sync-youtube-links.py") @SyncArgs
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}
& (Join-Path $PSScriptRoot "start-knowledge-lab.ps1")
& $Python (Join-Path $PSScriptRoot "ingest-vault-lmstudio.py")
