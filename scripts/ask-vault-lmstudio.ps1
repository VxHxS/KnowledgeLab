param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]] $QuestionParts
)

$ErrorActionPreference = "Stop"

$Question = ($QuestionParts -join " ").Trim()
if (-not $Question) {
    $Question = "What important context is available in this vault?"
}

$Scope = $env:LMSTUDIO_SCOPE
if (-not $Scope) {
    $Scope = "general"
}

$Project = $env:LMSTUDIO_PROJECT
if (-not $Project) {
    $Project = ""
}

if ($Scope -in @("game", "web") -and $Project) {
    & (Join-Path $PSScriptRoot "query-vault-scope-lmstudio.ps1") -Scope $Scope -Project $Project $Question
} else {
    & (Join-Path $PSScriptRoot "query-vault-scope-lmstudio.ps1") -Scope $Scope $Question
}
