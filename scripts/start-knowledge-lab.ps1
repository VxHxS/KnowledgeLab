$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

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

function Invoke-LmsRaw {
    param(
        [string[]] $Arguments
    )

    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $Lms
    $psi.WorkingDirectory = $Root
    $psi.UseShellExecute = $false
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.CreateNoWindow = $true
    $psi.StandardOutputEncoding = [System.Text.Encoding]::UTF8
    $psi.StandardErrorEncoding = [System.Text.Encoding]::UTF8
    $psi.Arguments = ($Arguments | ForEach-Object {
        $arg = [string] $_
        if ($arg -match '[\s"]') {
            '"' + ($arg -replace '"', '\"') + '"'
        } else {
            $arg
        }
    }) -join " "

    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $psi
    [void] $process.Start()
    $stdoutText = $process.StandardOutput.ReadToEnd()
    $stderrText = $process.StandardError.ReadToEnd()
    $process.WaitForExit()

    return [pscustomobject]@{
        ExitCode = $process.ExitCode
        Stdout = @($stdoutText -split "\r?\n" | Where-Object { $_ -ne "" })
        Stderr = $stderrText
    }
}

function Invoke-Lms {
    param(
        [string[]] $Arguments
    )

    $result = Invoke-LmsRaw -Arguments $Arguments
    if ($result.Stdout) {
        $result.Stdout | ForEach-Object { Write-Host $_ }
    }
    if ($result.ExitCode -ne 0) {
        if ($result.Stderr) {
            Write-Error $result.Stderr.Trim()
        }
        throw "lms $($Arguments -join ' ') failed with exit code $($result.ExitCode)"
    }
    if ($result.Stderr) {
        Write-Host $result.Stderr.Trim()
    }
}

function Get-LoadedModels {
    try {
        $result = Invoke-LmsRaw -Arguments @("ps", "--json")
        if ($result.ExitCode -ne 0 -or -not $result.Stdout) { return @() }
        $json = ($result.Stdout -join [Environment]::NewLine)
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

if (($env:KNOWLEDGELAB_STARTUP_GAME_GUARD -match "^(1|true|yes|on)$") -and (Test-Path -LiteralPath $GameGuard)) {
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
