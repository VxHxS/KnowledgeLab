function Test-LightRAGRoot {
    param([string] $Path)

    if ([string]::IsNullOrWhiteSpace($Path)) {
        return $false
    }

    foreach ($name in @("scripts", "LightRAG", "Obsidian-Test-Vault")) {
        if (-not (Test-Path -LiteralPath (Join-Path $Path $name))) {
            return $false
        }
    }

    return $true
}

function Add-LightRAGRootCandidate {
    param(
        [System.Collections.Generic.List[string]] $Candidates,
        [string] $Path
    )

    if ([string]::IsNullOrWhiteSpace($Path)) {
        return
    }

    try {
        $fullPath = [System.IO.Path]::GetFullPath($Path)
    }
    catch {
        return
    }

    if (-not $Candidates.Contains($fullPath)) {
        $Candidates.Add($fullPath) | Out-Null
    }
}

function Get-LightRAGRoot {
    param([string] $StartDir = $PSScriptRoot)

    $candidates = New-Object "System.Collections.Generic.List[string]"

    if ([string]::IsNullOrWhiteSpace($StartDir)) {
        $StartDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    }

    $resolvedStart = Resolve-Path -LiteralPath $StartDir -ErrorAction SilentlyContinue
    if ($resolvedStart) {
        $start = $resolvedStart.Path
    }
    else {
        $start = $StartDir
    }

    $dir = $start
    while (-not [string]::IsNullOrWhiteSpace($dir)) {
        Add-LightRAGRootCandidate $candidates $dir
        Add-LightRAGRootCandidate $candidates (Join-Path $dir "AI-Knowledge-Lab")
        Add-LightRAGRootCandidate $candidates (Join-Path $dir "KnowledgeLab")

        $parent = Split-Path -Parent $dir
        if ([string]::IsNullOrWhiteSpace($parent) -or $parent -eq $dir) {
            break
        }
        $dir = $parent
    }

    if ($env:USERPROFILE) {
        Add-LightRAGRootCandidate $candidates (Join-Path $env:USERPROFILE "Documents\Freelance\AI-Knowledge-Lab")
        Add-LightRAGRootCandidate $candidates (Join-Path $env:USERPROFILE "Documents\Freelance\KnowledgeLab")
        Add-LightRAGRootCandidate $candidates (Join-Path $env:USERPROFILE "MyFiles\KnowledgeLab")
    }

    $documents = [Environment]::GetFolderPath("MyDocuments")
    if ($documents) {
        Add-LightRAGRootCandidate $candidates (Join-Path $documents "Freelance\AI-Knowledge-Lab")
        Add-LightRAGRootCandidate $candidates (Join-Path $documents "Freelance\KnowledgeLab")
    }

    foreach ($candidate in $candidates) {
        if (Test-LightRAGRoot $candidate) {
            return $candidate
        }
    }

    $searched = $candidates -join "`n  - "
    throw "Не найден корень LightRAG-системы. Проверенные пути:`n  - $searched"
}

function Get-LightRAGPaths {
    param([string] $StartDir = $PSScriptRoot)

    $root = Get-LightRAGRoot -StartDir $StartDir
    return [pscustomobject]@{
        Root = $root
        Scripts = Join-Path $root "scripts"
        LightRAG = Join-Path $root "LightRAG"
        Vault = Join-Path $root "Obsidian-Test-Vault"
        Python = Join-Path $root "LightRAG\.venv\Scripts\python.exe"
    }
}