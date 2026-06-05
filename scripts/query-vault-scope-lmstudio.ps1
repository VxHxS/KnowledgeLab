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
$AutoIndexMissing = $true
if ($env:LMSTUDIO_AUTO_INDEX_MISSING -match "^(0|false|no|off)$") {
    $AutoIndexMissing = $false
}

function Write-KnowledgeWarning {
    param([string] $Message)
    if ($env:LMSTUDIO_GUI_OUTPUT -match "^(1|true|yes|on)$") {
        Write-Host "::knowledge-warning $Message"
    } else {
        Write-Warning $Message
    }
}

function Test-AutoIndexRunning {
    param([string] $PidPath)
    if (-not (Test-Path -LiteralPath $PidPath)) {
        return $false
    }
    try {
        $pidText = (Get-Content -LiteralPath $PidPath -ErrorAction Stop | Select-Object -First 1).Trim()
        if (-not $pidText) { return $false }
        $process = Get-Process -Id ([int] $pidText) -ErrorAction SilentlyContinue
        return ($null -ne $process)
    }
    catch {
        return $false
    }
}

function Start-AutoIndex {
    param(
        [string] $StorageName,
        [string] $Scope,
        [string] $Project
    )

    $tmpDir = Join-Path $Root "tmp"
    $pidPath = Join-Path $tmpDir "auto-index-$StorageName.pid"
    $logPath = Join-Path $tmpDir "auto-index-$StorageName.log"
    $errPath = Join-Path $tmpDir "auto-index-$StorageName.err.log"
    New-Item -ItemType Directory -Force -Path $tmpDir | Out-Null

    if (Test-AutoIndexRunning $pidPath) {
        return "already-running"
    }

    $ingestScript = Join-Path $PSScriptRoot "ingest-vault-scope-lmstudio.ps1"
    $args = @(
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        $ingestScript,
        "-Scope",
        $Scope
    )
    if ($Scope -in @("game", "web") -and $Project) {
        $args += @("-Project", $Project)
    }

    $process = Start-Process -FilePath "powershell.exe" `
        -ArgumentList $args `
        -WorkingDirectory $Root `
        -WindowStyle Hidden `
        -RedirectStandardOutput $logPath `
        -RedirectStandardError $errPath `
        -PassThru
    Set-Content -LiteralPath $pidPath -Value $process.Id -Encoding ASCII
    return "started"
}

$env:PYTHONUTF8 = "1"
$env:LMSTUDIO_SCOPE = $Scope
$env:LMSTUDIO_PROJECT = if ($Scope -in @("game", "web")) { $Project } else { "" }
$env:LMSTUDIO_RAG_DIR = $StorageRel

if ($UseLightRag -and -not (Test-Path -LiteralPath (Join-Path $StoragePath "vdb_chunks.json"))) {
    if ($AutoIndexMissing) {
        $autoIndexState = Start-AutoIndex -StorageName $StorageName -Scope $Scope -Project $Project
        if ($autoIndexState -eq "started") {
            Write-KnowledgeWarning "LightRAG индекс для '$Scope' еще не готов; я запустил сборку в фоне. Этот ответ будет создан без базы знаний, следующие ответы подключат LightRAG после завершения."
        } else {
            Write-KnowledgeWarning "LightRAG индекс для '$Scope' еще собирается в фоне. Этот ответ будет создан без базы знаний."
        }
    } else {
        Write-KnowledgeWarning "LightRAG индекс для '$Scope' пока отсутствует; ответ будет создан без базы знаний."
    }
    $env:LMSTUDIO_USE_LIGHTRAG = "0"
    $env:LMSTUDIO_LIGHTRAG_OFF_REASON = "LightRAG индекс для '$Scope' пока не готов; этот ответ создан без контекста базы знаний."
    $UseLightRag = $false
}

& (Join-Path $PSScriptRoot "start-knowledge-lab.ps1")
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
& $Python (Join-Path $PSScriptRoot "query-vault-lmstudio.py") $Question
exit $LASTEXITCODE
