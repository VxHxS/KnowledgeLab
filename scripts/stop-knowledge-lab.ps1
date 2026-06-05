$ErrorActionPreference = "Continue"

$Lms = Join-Path $env:USERPROFILE ".lmstudio\bin\lms.exe"
if (-not (Test-Path -LiteralPath $Lms)) {
    Write-Host "LM Studio CLI was not found at $Lms"
    exit 1
}

Write-Host "Unloading Knowledge Lab models..."
& $Lms unload qwen3-14b
& $Lms unload qwen/qwen3-14b
& $Lms unload qwen-local
& $Lms unload nomic-embed

Write-Host "Stopping LM Studio server..."
& $Lms server stop

Write-Host "Knowledge Lab stopped."
