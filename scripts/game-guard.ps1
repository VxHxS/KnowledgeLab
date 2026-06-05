param(
    [switch] $Once,
    [switch] $Watch,
    [switch] $InstallStartup,
    [switch] $UninstallStartup,
    [switch] $StartNow,
    [switch] $StopNow,
    [string[]] $ProcessName,
    [int] $IntervalSeconds = 15
)

$ErrorActionPreference = "Continue"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

$Root = Split-Path -Parent $PSScriptRoot
$StopScript = Join-Path $PSScriptRoot "stop-knowledge-lab.ps1"
$LogPath = Join-Path $Root "tmp\game-guard.log"
$GuardPidPath = Join-Path $Root "tmp\game-guard.pid"
$SettingsPath = Join-Path $Root "tmp\knowledge-chat-settings.json"
$StartupShortcutName = "KnowledgeLab Game Guard.lnk"
$MutexName = "KnowledgeLabGameGuard"
$ScriptPath = if ($PSCommandPath) { $PSCommandPath } else { $MyInvocation.MyCommand.Path }

function Test-GuardEnabled {
    if ($env:KNOWLEDGELAB_GAME_GUARD -match "^(0|false|no|off)$") {
        return $false
    }

    try {
        if (Test-Path -LiteralPath $SettingsPath) {
            $settings = Get-Content -LiteralPath $SettingsPath -Raw -ErrorAction Stop | ConvertFrom-Json -ErrorAction Stop
            if ($null -ne $settings.game_guard_enabled -and -not [bool] $settings.game_guard_enabled) {
                return $false
            }
        }
    }
    catch {}

    return $true
}

function Get-GuardProcessNames {
    $names = New-Object System.Collections.Generic.List[string]
    if ($ProcessName -and $ProcessName.Count -gt 0) {
        foreach ($name in $ProcessName) { $names.Add($name) | Out-Null }
    }
    elseif ($env:KNOWLEDGELAB_GAME_GUARD_PROCESSES) {
        foreach ($name in ($env:KNOWLEDGELAB_GAME_GUARD_PROCESSES -split "[,;]")) {
            $names.Add($name) | Out-Null
        }
    }
    else {
        foreach ($name in @(
            "CrimsonDesert",
            "CrimsonDesertClient",
            "CrimsonDesertLauncher",
            "CrimsonDesert-Win64-Shipping",
            "*Crimson*Desert*"
        )) {
            $names.Add($name) | Out-Null
        }
    }

    return @($names |
        ForEach-Object { $_.Trim() } |
        Where-Object { $_ } |
        Sort-Object -Unique)
}

function Write-GuardLog {
    param([string] $Message)
    try {
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $LogPath) | Out-Null
        $line = "{0} {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
        Add-Content -LiteralPath $LogPath -Value $line -Encoding UTF8
    }
    catch {}
}

function Get-GuardPid {
    if (-not (Test-Path -LiteralPath $GuardPidPath)) {
        return $null
    }
    try {
        $pidText = (Get-Content -LiteralPath $GuardPidPath -ErrorAction Stop | Select-Object -First 1).Trim()
        if (-not $pidText) { return $null }
        return [int] $pidText
    }
    catch {
        return $null
    }
}

function Test-GameGuardPidRunning {
    $guardPid = Get-GuardPid
    if (-not $guardPid) {
        return $false
    }
    $process = Get-Process -Id $guardPid -ErrorAction SilentlyContinue
    return ($null -ne $process)
}

function Set-GameGuardPid {
    try {
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $GuardPidPath) | Out-Null
        Set-Content -LiteralPath $GuardPidPath -Value $PID -Encoding ASCII
    }
    catch {}
}

function Clear-GameGuardPid {
    try {
        $guardPid = Get-GuardPid
        if ($guardPid -eq $PID -and (Test-Path -LiteralPath $GuardPidPath)) {
            Remove-Item -LiteralPath $GuardPidPath -Force
        }
    }
    catch {}
}

function Stop-GameGuardNow {
    $guardPid = Get-GuardPid
    if (-not $guardPid) {
        Write-Host "Game Guard background watcher is not running."
        return
    }

    $process = Get-Process -Id $guardPid -ErrorAction SilentlyContinue
    if (-not $process) {
        Remove-Item -LiteralPath $GuardPidPath -Force -ErrorAction SilentlyContinue
        Write-Host "Game Guard background watcher is not running."
        return
    }

    Stop-Process -Id $guardPid -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $GuardPidPath -Force -ErrorAction SilentlyContinue
    Write-Host "Game Guard background watcher stopped."
    Write-GuardLog "stopped background watcher: $guardPid"
}

function Get-GuardedGameProcesses {
    $names = Get-GuardProcessNames
    $processes = @(Get-Process -ErrorAction SilentlyContinue)
    $matches = New-Object System.Collections.Generic.List[object]
    foreach ($process in $processes) {
        foreach ($name in $names) {
            if ($name.Contains("*")) {
                if ($process.ProcessName -like $name) {
                    $matches.Add($process) | Out-Null
                    break
                }
            }
            elseif ($process.ProcessName -ieq $name) {
                $matches.Add($process) | Out-Null
                break
            }
        }
    }
    return @($matches.ToArray())
}

function Stop-KnowledgeLabAi {
    if (-not (Test-Path -LiteralPath $StopScript)) {
        Write-GuardLog "stop script missing: $StopScript"
        return
    }

    Write-Host "Game Guard: stopping KnowledgeLab AI models..."
    Write-GuardLog "stopping KnowledgeLab AI models"
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $StopScript | Out-Host
}

function Get-StartupShortcutPath {
    $startup = [Environment]::GetFolderPath("Startup")
    if (-not $startup) {
        throw "Windows Startup folder was not found."
    }
    return (Join-Path $startup $StartupShortcutName)
}

function Install-GameGuardStartup {
    $shortcutPath = Get-StartupShortcutPath
    $powershell = (Get-Command "powershell.exe" -ErrorAction SilentlyContinue).Source
    if (-not $powershell) { $powershell = "powershell.exe" }

    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($shortcutPath)
    $shortcut.TargetPath = $powershell
    $shortcut.Arguments = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$ScriptPath`" -Watch -IntervalSeconds $IntervalSeconds"
    $shortcut.WorkingDirectory = $Root
    $icon = Join-Path $Root "assets\icons\LightRAG-Control.ico"
    if (Test-Path -LiteralPath $icon) {
        $shortcut.IconLocation = "$icon,0"
    }
    $shortcut.Save()

    Write-Host "Game Guard startup shortcut installed:"
    Write-Host $shortcutPath
    Write-GuardLog "startup installed: $shortcutPath"
}

function Uninstall-GameGuardStartup {
    $shortcutPath = Get-StartupShortcutPath
    if (Test-Path -LiteralPath $shortcutPath) {
        Remove-Item -LiteralPath $shortcutPath -Force
        Write-Host "Game Guard startup shortcut removed:"
        Write-Host $shortcutPath
        Write-GuardLog "startup removed: $shortcutPath"
    }
    else {
        Write-Host "Game Guard startup shortcut was not installed."
    }
}

function Start-GameGuardHidden {
    if (Test-GameGuardPidRunning) {
        Write-Host "Game Guard is already running in the background."
        return
    }

    $powershell = (Get-Command "powershell.exe" -ErrorAction SilentlyContinue).Source
    if (-not $powershell) { $powershell = "powershell.exe" }
    Start-Process -FilePath $powershell -ArgumentList @(
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-WindowStyle",
        "Hidden",
        "-File",
        $ScriptPath,
        "-Watch",
        "-IntervalSeconds",
        $IntervalSeconds
    ) -WorkingDirectory $Root -WindowStyle Hidden
    Write-Host "Game Guard started in the background."
    Write-GuardLog "started in background"
}

function Invoke-GameGuardOnce {
    if (-not (Test-GuardEnabled)) {
        Write-Host "Game Guard is disabled by KNOWLEDGELAB_GAME_GUARD=0."
        return 0
    }

    $matches = @(Get-GuardedGameProcesses)
    if ($matches.Count -eq 0) {
        Write-Host "Game Guard: no watched game process is running."
        return 0
    }

    $names = ($matches | ForEach-Object { "$($_.ProcessName)#$($_.Id)" }) -join ", "
    Write-Host "Game Guard: detected game process: $names" -ForegroundColor Yellow
    Write-Host "KnowledgeLab AI startup is blocked to avoid stealing RAM/VRAM from the game." -ForegroundColor Yellow
    Write-GuardLog "detected: $names"
    Stop-KnowledgeLabAi
    return 3
}

function Watch-GameGuard {
    if (-not (Test-GuardEnabled)) {
        Write-Host "Game Guard is disabled by KNOWLEDGELAB_GAME_GUARD=0."
        return
    }

    $created = $false
    $mutex = New-Object System.Threading.Mutex($true, $MutexName, [ref] $created)
    if (-not $created) {
        Write-Host "Game Guard is already running."
        return
    }

    try {
        Set-GameGuardPid
        $watched = (Get-GuardProcessNames) -join ", "
        Write-Host "KnowledgeLab Game Guard is watching: $watched"
        Write-Host "If one of these games starts, LM Studio models are unloaded automatically."
        Write-Host "Close this window to stop this visible watcher."
        Write-GuardLog "watch started: $watched"

        $gameWasRunning = $false
        while ($true) {
            $matches = @(Get-GuardedGameProcesses)
            if ($matches.Count -gt 0 -and -not $gameWasRunning) {
                $names = ($matches | ForEach-Object { "$($_.ProcessName)#$($_.Id)" }) -join ", "
                Write-Host "Game detected: $names" -ForegroundColor Yellow
                Write-GuardLog "watch detected: $names"
                Stop-KnowledgeLabAi
                $gameWasRunning = $true
            }
            elseif ($matches.Count -eq 0 -and $gameWasRunning) {
                Write-Host "Watched game process closed. Game Guard is still active."
                Write-GuardLog "game cleared"
                $gameWasRunning = $false
            }

            Start-Sleep -Seconds ([Math]::Max(3, $IntervalSeconds))
        }
    }
    finally {
        Clear-GameGuardPid
        try { $mutex.ReleaseMutex() } catch {}
        try { $mutex.Dispose() } catch {}
    }
}

if ($InstallStartup) {
    Install-GameGuardStartup
}

if ($UninstallStartup) {
    Uninstall-GameGuardStartup
}

if ($StopNow) {
    Stop-GameGuardNow
}

if ($StartNow) {
    Start-GameGuardHidden
}

if (($InstallStartup -or $UninstallStartup -or $StartNow -or $StopNow) -and -not $Once -and -not $Watch) {
    exit 0
}

if ($Once) {
    exit (Invoke-GameGuardOnce)
}

if ($Watch) {
    Watch-GameGuard
    exit 0
}

Write-Host "KnowledgeLab Game Guard"
Write-Host ""
Write-Host "Watched processes: $((Get-GuardProcessNames) -join ', ')"
Write-Host ""
Write-Host "Usage:"
Write-Host "  scripts\game-guard.ps1 -Once"
Write-Host "  scripts\game-guard.ps1 -Watch"
Write-Host "  scripts\game-guard.ps1 -InstallStartup -StartNow"
Write-Host "  scripts\game-guard.ps1 -UninstallStartup -StopNow"
