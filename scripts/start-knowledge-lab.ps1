$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$GameGuard = Join-Path $PSScriptRoot "game-guard.ps1"
$Lms = Join-Path $env:USERPROFILE ".lmstudio\bin\lms.exe"
$LlmModelKey = $env:LMSTUDIO_MODEL_KEY
if (-not $LlmModelKey) { $LlmModelKey = "qwen/qwen3-14b" }

$LlmIdentifier = $env:LMSTUDIO_LLM_MODEL
if (-not $LlmIdentifier) { $LlmIdentifier = "qwen/qwen3-14b" }

$EmbeddingModelKey = $env:LMSTUDIO_EMBEDDING_MODEL_KEY
if (-not $EmbeddingModelKey) { $EmbeddingModelKey = "text-embedding-nomic-embed-text-v1.5" }

$EmbeddingIdentifier = $env:LMSTUDIO_EMBEDDING_MODEL
if (-not $EmbeddingIdentifier) { $EmbeddingIdentifier = "nomic-embed" }

$LlmTtlSeconds = $env:LMSTUDIO_LLM_TTL_SECONDS
if (-not $LlmTtlSeconds) { $LlmTtlSeconds = "900" }

$EmbeddingTtlSeconds = $env:LMSTUDIO_EMBEDDING_TTL_SECONDS
if (-not $EmbeddingTtlSeconds) { $EmbeddingTtlSeconds = "1800" }

function Invoke-Lms {
    param(
        [string[]] $Arguments
    )

    & $Lms @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "lms $($Arguments -join ' ') failed with exit code $LASTEXITCODE"
    }
}

function Get-LoadedModels {
    try {
        $json = & $Lms ps --json
        if ($LASTEXITCODE -ne 0 -or -not $json) { return @() }
        return @($json | ConvertFrom-Json)
    }
    catch {
        return @()
    }
}

function Test-ModelLoaded {
    param([string] $Identifier)
    return (@(Get-LoadedModels | Where-Object { $_.identifier -eq $Identifier }).Count -gt 0)
}

if (-not (Test-Path -LiteralPath $Lms)) {
    throw "LM Studio CLI was not found at $Lms"
}

if (Test-Path -LiteralPath $GameGuard) {
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $GameGuard -Once
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Knowledge Lab AI startup was blocked by Game Guard." -ForegroundColor Yellow
        exit $LASTEXITCODE
    }
}

Write-Host "Starting LM Studio server..."
Invoke-Lms @("server", "start")

if (Test-ModelLoaded "qwen-local") {
    Write-Host "Unloading old qwen-local model to free VRAM..."
    Invoke-Lms @("unload", "qwen-local")
}

if (-not (Test-ModelLoaded $EmbeddingIdentifier)) {
    Write-Host "Loading embedding model: $EmbeddingModelKey as $EmbeddingIdentifier..."
    Invoke-Lms @("load", $EmbeddingModelKey, "--identifier", $EmbeddingIdentifier, "--ttl", $EmbeddingTtlSeconds, "-y")
}
else {
    Write-Host "Embedding model already loaded: $EmbeddingIdentifier"
}

if (-not (Test-ModelLoaded $LlmIdentifier)) {
    Write-Host "Loading LLM: $LlmModelKey as $LlmIdentifier..."
    Write-Host "If this fails, finish the qwen3-14b download in LM Studio and run this script again."
    Invoke-Lms @("load", $LlmModelKey, "--identifier", $LlmIdentifier, "--gpu", "max", "--context-length", "8192", "--parallel", "1", "--ttl", $LlmTtlSeconds, "-y")
}
else {
    Write-Host "LLM already loaded: $LlmIdentifier"
}

Write-Host ""
Write-Host "Knowledge Lab is ready."
Write-Host "API: http://127.0.0.1:1234/v1"
Write-Host "LLM identifier: $LlmIdentifier"
Write-Host "Embedding identifier: $EmbeddingIdentifier"
Write-Host "Idle unload: LLM ${LlmTtlSeconds}s, embeddings ${EmbeddingTtlSeconds}s"
