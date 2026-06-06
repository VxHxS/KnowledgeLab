param(
    [switch] $InstallPythonPackages,
    [switch] $InstallCorePackages,
    [switch] $InstallYoutubePackages,
    [switch] $InstallTelegramPackages,
    [switch] $SkipPythonPackages,
    [switch] $DryRun,
    [switch] $NoDesktopLaunchers
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

$Root = Split-Path -Parent $PSScriptRoot
$VenvDir = Join-Path $Root "LightRAG\.venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
$Requirements = Join-Path $Root "requirements-all.txt"
$RequirementsCore = Join-Path $Root "requirements-core.txt"
$RequirementsYoutube = Join-Path $Root "requirements-youtube.txt"
$RequirementsTelegram = Join-Path $Root "requirements-telegram.txt"
$DesktopDir = Join-Path $env:USERPROFILE "Desktop\LightRag"
$DesktopLogicDir = Join-Path $Root "LightRAG-Desktop"
$IconDir = Join-Path $Root "assets\icons"
$ReportPath = Join-Path $Root "INSTALL_REPORT.md"

$Checks = New-Object System.Collections.Generic.List[object]
$ManualSteps = New-Object System.Collections.Generic.List[string]

function Add-Check {
    param(
        [string] $Name,
        [string] $Status,
        [string] $Details = ""
    )
    $Checks.Add([pscustomobject]@{
        Name = $Name
        Status = $Status
        Details = $Details
    }) | Out-Null
}

function Add-ManualStep {
    param([string] $Text)
    $ManualSteps.Add($Text) | Out-Null
}

function Invoke-Capture {
    param(
        [string] $FilePath,
        [string[]] $Arguments,
        [int] $TimeoutSeconds = 30
    )

    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $FilePath
    $psi.Arguments = Join-ProcessArguments $Arguments
    $psi.WorkingDirectory = $Root
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true

    $process = [System.Diagnostics.Process]::Start($psi)
    if (-not $process.WaitForExit($TimeoutSeconds * 1000)) {
        try { $process.Kill() } catch {}
        throw "Command timed out: $FilePath $($Arguments -join ' ')"
    }

    return [pscustomobject]@{
        ExitCode = $process.ExitCode
        StdOut = $process.StandardOutput.ReadToEnd().Trim()
        StdErr = $process.StandardError.ReadToEnd().Trim()
    }
}

function ConvertTo-ProcessArgument {
    param([string] $Argument)
    if ($null -eq $Argument) { return '""' }
    if ($Argument.Length -eq 0) { return '""' }
    if ($Argument -notmatch '[\s"]') { return $Argument }

    $builder = New-Object System.Text.StringBuilder
    [void] $builder.Append('"')
    $backslashes = 0
    foreach ($char in $Argument.ToCharArray()) {
        if ($char -eq '\') {
            $backslashes += 1
            continue
        }
        if ($char -eq '"') {
            [void] $builder.Append(('\' * (($backslashes * 2) + 1)))
            [void] $builder.Append('"')
            $backslashes = 0
            continue
        }
        if ($backslashes -gt 0) {
            [void] $builder.Append(('\' * $backslashes))
            $backslashes = 0
        }
        [void] $builder.Append($char)
    }
    if ($backslashes -gt 0) {
        [void] $builder.Append(('\' * ($backslashes * 2)))
    }
    [void] $builder.Append('"')
    return $builder.ToString()
}

function Join-ProcessArguments {
    param([string[]] $Arguments)
    return (@($Arguments | ForEach-Object { ConvertTo-ProcessArgument $_ }) -join " ")
}

function New-DesktopShortcut {
    param(
        [string] $ShortcutPath,
        [string] $TargetPath,
        [string[]] $Arguments,
        [string] $WorkingDirectory,
        [string] $IconPath
    )

    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($ShortcutPath)
    $shortcut.TargetPath = $TargetPath
    $shortcut.Arguments = Join-ProcessArguments $Arguments
    $shortcut.WorkingDirectory = $WorkingDirectory
    if ($IconPath -and (Test-Path -LiteralPath $IconPath)) {
        $shortcut.IconLocation = "$IconPath,0"
    }
    $shortcut.Save()
}

function Get-CommandPath {
    param([string] $CommandName)
    $command = Get-Command $CommandName -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }
    return ""
}

function Test-Exe {
    param([string] $Path)
    return ($Path -and (Test-Path -LiteralPath $Path))
}

function Get-PythonVersion {
    param([string] $PythonExe)
    try {
        $result = Invoke-Capture $PythonExe @("-c", "import sys; print('.'.join(map(str, sys.version_info[:3])))") 15
        if ($result.ExitCode -eq 0) { return $result.StdOut.Trim() }
    }
    catch {}
    return ""
}

function Version-AtLeast {
    param(
        [string] $Actual,
        [int] $Major,
        [int] $Minor
    )
    if (-not $Actual) { return $false }
    $parts = $Actual.Split(".")
    if ($parts.Count -lt 2) { return $false }
    $actualMajor = [int] $parts[0]
    $actualMinor = [int] $parts[1]
    return ($actualMajor -gt $Major -or ($actualMajor -eq $Major -and $actualMinor -ge $Minor))
}

function Resolve-SystemPython {
    $python = Get-CommandPath "python"
    if ($python) {
        $version = Get-PythonVersion $python
        if (Version-AtLeast $version 3 10) {
            return [pscustomobject]@{ Path = $python; Version = $version; Source = "python" }
        }
    }

    $py = Get-CommandPath "py"
    if ($py) {
        foreach ($selector in @("-3.12", "-3.11", "-3.10", "-3")) {
            try {
                $result = Invoke-Capture $py @($selector, "-c", "import sys; print(sys.executable); print('.'.join(map(str, sys.version_info[:3])))") 15
                if ($result.ExitCode -eq 0) {
                    $lines = @($result.StdOut -split "`r?`n")
                    if ($lines.Count -ge 2 -and (Version-AtLeast $lines[1] 3 10)) {
                        return [pscustomobject]@{ Path = $lines[0]; Version = $lines[1]; Source = "py $selector" }
                    }
                }
            }
            catch {}
        }
    }

    return $null
}

function Get-SystemProfile {
    try { $os = Get-CimInstance Win32_OperatingSystem } catch { $os = $null }
    try { $cpu = Get-CimInstance Win32_Processor | Select-Object -First 1 } catch { $cpu = $null }
    try { $computer = Get-CimInstance Win32_ComputerSystem } catch { $computer = $null }
    try { $gpus = @(Get-CimInstance Win32_VideoController | Where-Object { $_.Name }) } catch { $gpus = @() }
    try { $disk = Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='C:'" } catch { $disk = $null }

    $gpuLines = foreach ($gpu in $gpus) {
        $ramGb = 0
        if ($gpu.AdapterRAM) { $ramGb = [math]::Round($gpu.AdapterRAM / 1GB, 1) }
        if ($ramGb -gt 0) { "$($gpu.Name) ($ramGb GB VRAM reported)" } else { "$($gpu.Name)" }
    }

    if ($os) { $osText = "$($os.Caption) $($os.Version) build $($os.BuildNumber)" } else { $osText = [System.Environment]::OSVersion.VersionString }
    if ($cpu) { $cpuText = "$($cpu.Name) ($($cpu.NumberOfCores) cores / $($cpu.NumberOfLogicalProcessors) threads)" } else { $cpuText = $env:PROCESSOR_IDENTIFIER }
    if ($computer -and $computer.TotalPhysicalMemory) { $ramText = "{0:N1} GB" -f ($computer.TotalPhysicalMemory / 1GB) } else { $ramText = "Unknown" }
    if ($disk) {
        $diskText = "{0:N1} GB free / {1:N1} GB total" -f ($disk.FreeSpace / 1GB), ($disk.Size / 1GB)
    } else {
        try {
            $drive = Get-PSDrive -Name C -ErrorAction Stop
            if ($drive.Free -gt 0) {
                $diskText = "{0:N1} GB free" -f ($drive.Free / 1GB)
            } else {
                $diskText = "Unknown"
            }
        }
        catch {
            $diskText = "Unknown"
        }
    }

    return [pscustomobject]@{
        ComputerName = $env:COMPUTERNAME
        UserName = $env:USERNAME
        OS = $osText
        CPU = $cpuText
        RAM = $ramText
        GPU = if ($gpuLines) { $gpuLines -join "; " } else { "Not detected" }
        DiskC = $diskText
        PowerShell = $PSVersionTable.PSVersion.ToString()
        Date = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    }
}

function Ensure-Venv {
    param([object] $SystemPython)
    if (Test-Path -LiteralPath $VenvPython) {
        $version = Get-PythonVersion $VenvPython
        Add-Check "Python venv" "OK" "$VenvPython ($version)"
        return
    }

    if (-not $SystemPython) {
        Add-Check "Python venv" "MISSING" "Cannot create venv because Python 3.10+ was not found."
        Add-ManualStep "Install Python 3.12 from https://www.python.org/downloads/ and enable Add python.exe to PATH."
        return
    }

    Add-Check "Python venv" "CREATE" "Creating $VenvDir from $($SystemPython.Path)"
    if (-not $DryRun) {
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $VenvDir) | Out-Null
        & $SystemPython.Path -m venv $VenvDir
        if ($LASTEXITCODE -ne 0) { throw "Failed to create Python venv." }
    }
}

function Install-PythonPackages {
    if (-not (Test-Path -LiteralPath $VenvPython)) {
        Add-Check "Python packages" "SKIPPED" "venv python not found."
        return
    }
    if (-not (Test-Path -LiteralPath $Requirements)) {
        Add-Check "Python packages" "MISSING" "requirements-all.txt not found."
        return
    }

    $selectedRequirements = New-Object System.Collections.Generic.List[string]
    if ($InstallPythonPackages) {
        $selectedRequirements.Add($Requirements) | Out-Null
    } else {
        if ($InstallCorePackages) { $selectedRequirements.Add($RequirementsCore) | Out-Null }
        if ($InstallYoutubePackages) { $selectedRequirements.Add($RequirementsYoutube) | Out-Null }
        if ($InstallTelegramPackages) { $selectedRequirements.Add($RequirementsTelegram) | Out-Null }
    }

    $shouldInstall = ($selectedRequirements.Count -gt 0)
    if (-not $shouldInstall -and -not $SkipPythonPackages.IsPresent) {
        $answer = Read-Host "Install/upgrade Python packages from the internet now? [y/N]"
        $shouldInstall = $answer -in @("y", "Y", "yes", "YES")
        if ($shouldInstall) {
            $selectedRequirements.Add($Requirements) | Out-Null
        }
    }

    if (-not $shouldInstall) {
        Add-Check "Python packages" "SKIPPED" "Run with -InstallPythonPackages or install manually with pip."
        return
    }

    $requirementNames = @($selectedRequirements | ForEach-Object { Split-Path -Leaf $_ }) -join ", "
    Add-Check "Python packages" "INSTALL" "Installing from $requirementNames"
    if (-not $DryRun) {
        & $VenvPython -m pip install --upgrade pip
        if ($LASTEXITCODE -ne 0) { throw "pip upgrade failed." }
        foreach ($requirementsFile in $selectedRequirements) {
            if (-not (Test-Path -LiteralPath $requirementsFile)) {
                throw "Requirements file was not found: $requirementsFile"
            }
            & $VenvPython -m pip install -r $requirementsFile
            if ($LASTEXITCODE -ne 0) { throw "pip install failed: $requirementsFile" }
        }
    }
}

function Test-LightRAGPackage {
    if (-not (Test-Path -LiteralPath $VenvPython)) { return }
    try {
        $result = Invoke-Capture $VenvPython @("-m", "pip", "show", "lightrag-hku") 30
        if ($result.ExitCode -eq 0 -and $result.StdOut) {
            $version = (($result.StdOut -split "`r?`n") | Where-Object { $_ -like "Version:*" } | Select-Object -First 1)
            Add-Check "LightRAG package" "OK" "$version; GitHub: https://github.com/HKUDS/LightRAG; PyPI: https://pypi.org/project/lightrag-hku/"
        } else {
            Add-Check "LightRAG package" "MISSING" "Install lightrag-hku via requirements-core.txt."
            Add-ManualStep "Install LightRAG: .\LightRAG\.venv\Scripts\python.exe -m pip install -r requirements-core.txt"
            Add-ManualStep "LightRAG GitHub: https://github.com/HKUDS/LightRAG"
        }
    }
    catch {
        Add-Check "LightRAG package" "ERROR" $_.Exception.Message
    }
}

function Test-PythonImports {
    if (-not (Test-Path -LiteralPath $VenvPython)) { return }
    $code = @"
import importlib.util
modules = ['tkinter', 'lightrag', 'openai', 'numpy', 'tiktoken', 'yt_dlp', 'telethon']
missing = [name for name in modules if importlib.util.find_spec(name) is None]
print('missing=' + ','.join(missing))
"@
    try {
        $result = Invoke-Capture $VenvPython @("-c", $code) 30
        if ($result.ExitCode -eq 0 -and $result.StdOut -match "missing=$") {
            Add-Check "Python imports" "OK" "tkinter, LightRAG, OpenAI, numpy, tiktoken, yt-dlp, Telethon"
        } else {
            Add-Check "Python imports" "INCOMPLETE" $result.StdOut
            Add-ManualStep "Install missing Python packages: .\LightRAG\.venv\Scripts\python.exe -m pip install -r requirements-all.txt"
        }
    }
    catch {
        Add-Check "Python imports" "ERROR" $_.Exception.Message
    }
}

function Ensure-EnvFile {
    $envFile = Join-Path $Root "LightRAG\.env"
    $example = Join-Path $Root "LightRAG\.env.lmstudio.example"
    if (Test-Path -LiteralPath $envFile) {
        $content = Get-Content -LiteralPath $envFile -Raw -ErrorAction SilentlyContinue
        if ($content -match "LLM_BINDING=openai" -and $content -match "LLM_MODEL=qwen/qwen3-14b" -and $content -match "EMBEDDING_MODEL=text-embedding-nomic-embed-text-v1.5") {
            Add-Check "LightRAG .env" "OK" $envFile
            return
        }
        if (Test-Path -LiteralPath $example) {
            $backup = "$envFile.backup-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
            Add-Check "LightRAG .env" "UPDATE" "Replacing non-LM Studio .env; backup: $backup"
            if (-not $DryRun) {
                Copy-Item -LiteralPath $envFile -Destination $backup -Force
                Copy-Item -LiteralPath $example -Destination $envFile -Force
            }
        } else {
            Add-Check "LightRAG .env" "CHECK" "Existing .env is not LM Studio format and no example file was found."
        }
        return
    }
    if (Test-Path -LiteralPath $example) {
        Add-Check "LightRAG .env" "CREATE" "Copying .env.lmstudio.example"
        if (-not $DryRun) {
            Copy-Item -LiteralPath $example -Destination $envFile -Force
        }
    } else {
        Add-Check "LightRAG .env" "MISSING" "No example env file found."
    }
}

function Test-ExternalTools {
    $lms = Join-Path $env:USERPROFILE ".lmstudio\bin\lms.exe"
    if (Test-Path -LiteralPath $lms) {
        Add-Check "LM Studio CLI" "OK" $lms
    } else {
        Add-Check "LM Studio CLI" "MISSING" $lms
        Add-ManualStep "Install LM Studio, enable the local server, and make sure lms.exe exists at %USERPROFILE%\.lmstudio\bin\lms.exe."
    }

    try {
        $models = Invoke-RestMethod -Uri "http://127.0.0.1:1234/v1/models" -TimeoutSec 2
        $ids = @($models.data | ForEach-Object { $_.id }) -join ", "
        Add-Check "LM Studio API" "OK" "http://127.0.0.1:1234/v1/models -> $ids"
    }
    catch {
        Add-Check "LM Studio API" "OFFLINE" "Start LM Studio server when you want to query/index."
        Add-ManualStep "Open LM Studio and start the local server on http://127.0.0.1:1234/v1."
    }

    $obsidianCandidates = @(
        (Join-Path $env:LOCALAPPDATA "Obsidian\Obsidian.exe"),
        (Join-Path $env:LOCALAPPDATA "Programs\Obsidian\Obsidian.exe"),
        (Get-CommandPath "obsidian")
    ) | Where-Object { $_ }
    if (@($obsidianCandidates | Where-Object { Test-Path -LiteralPath $_ }).Count -gt 0) {
        Add-Check "Obsidian" "OK" ($obsidianCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1)
    } else {
        Add-Check "Obsidian" "MISSING" "Not found in LocalAppData or PATH."
        Add-ManualStep "Install Obsidian and open this vault: $($Root)\Obsidian-Test-Vault"
    }

    $telegramCandidates = @(
        (Join-Path $env:APPDATA "Telegram Desktop\Telegram.exe"),
        (Join-Path $env:LOCALAPPDATA "Telegram Desktop\Telegram.exe"),
        (Join-Path $env:LOCALAPPDATA "Programs\Telegram Desktop\Telegram.exe")
    )
    if (@($telegramCandidates | Where-Object { Test-Path -LiteralPath $_ }).Count -gt 0) {
        Add-Check "Telegram Desktop" "OK" ($telegramCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1)
    } else {
        Add-Check "Telegram Desktop" "OPTIONAL" "Needed only for Telegram JSON exports."
        Add-ManualStep "Install Telegram Desktop if you want to export channels/groups into Obsidian."
    }

    $git = Get-CommandPath "git"
    if ($git) { Add-Check "Git" "OK" $git } else { Add-Check "Git" "OPTIONAL" "Install Git if you want version control." }

    $ffmpeg = Get-CommandPath "ffmpeg"
    if ($ffmpeg) {
        Add-Check "FFmpeg" "OK" $ffmpeg
    } else {
        Add-Check "FFmpeg" "OPTIONAL" "Needed later for audio transcription fallback when YouTube captions are absent."
    }
}

function Remove-LegacyStartupEntries {
    $startup = [Environment]::GetFolderPath("Startup")
    $removed = New-Object System.Collections.Generic.List[string]
    if ($startup) {
        foreach ($name in @("KnowledgeLab Game Guard.lnk", "LightRAG Game Guard.lnk")) {
            $path = Join-Path $startup $name
            if (Test-Path -LiteralPath $path) {
                if (-not $DryRun) {
                    Remove-Item -LiteralPath $path -Force -ErrorAction SilentlyContinue
                }
                $removed.Add($path) | Out-Null
            }
        }
    }

    $guardPidPath = Join-Path $Root "tmp\game-guard.pid"
    if (Test-Path -LiteralPath $guardPidPath) {
        try {
            $pidText = (Get-Content -LiteralPath $guardPidPath -ErrorAction Stop | Select-Object -First 1).Trim()
            if ($pidText) {
                $process = Get-Process -Id ([int] $pidText) -ErrorAction SilentlyContinue
                if ($process -and -not $DryRun) {
                    Stop-Process -Id ([int] $pidText) -Force -ErrorAction SilentlyContinue
                }
            }
            if (-not $DryRun) {
                Remove-Item -LiteralPath $guardPidPath -Force -ErrorAction SilentlyContinue
            }
            $removed.Add($guardPidPath) | Out-Null
        }
        catch {}
    }

    if ($removed.Count -gt 0) {
        $status = if ($DryRun) { "WOULD_REMOVE" } else { "REMOVED" }
        Add-Check "Legacy Game Guard startup" $status ($removed -join "; ")
    } else {
        Add-Check "Legacy Game Guard startup" "OK" "No Windows startup item detected."
    }
}

function Ensure-ChatSettings {
    $settingsPath = Join-Path $Root "tmp\knowledge-chat-settings.json"
    $vaultPath = Join-Path $Root "Obsidian-Test-Vault"
    $settings = [ordered]@{
        send_on_enter = $true
        use_lightrag = $false
        button_color = "#3d5f88"
        game_guard_enabled = $true
        game_guard_delay_seconds = 5
        auto_process_links = $true
        web_search_enabled = $false
        obsidian_path = ""
        vault_path = $vaultPath
        lmstudio_base_url = "http://127.0.0.1:1234/v1"
        llm_model = "qwen/qwen3-14b"
        embedding_model = "text-embedding-nomic-embed-text-v1.5"
        response_language = "ru"
        default_llm_mode_applied = $true
        main_toolbar_lightrag_removed = $true
        plain_chat_adapter_version = 1
    }

    if (Test-Path -LiteralPath $settingsPath) {
        try {
            $existing = Get-Content -LiteralPath $settingsPath -Raw -ErrorAction Stop | ConvertFrom-Json -ErrorAction Stop
            foreach ($property in $existing.PSObject.Properties) {
                if ($settings.Contains($property.Name)) {
                    $settings[$property.Name] = $property.Value
                }
            }
            $settings["use_lightrag"] = $false
            $settings["vault_path"] = $vaultPath
            $settings["lmstudio_base_url"] = "http://127.0.0.1:1234/v1"
            $settings["llm_model"] = "qwen/qwen3-14b"
            $settings["embedding_model"] = "text-embedding-nomic-embed-text-v1.5"
            $settings["response_language"] = "ru"
            $settings["auto_process_links"] = $true
            if (-not $settings.Contains("web_search_enabled")) {
                $settings["web_search_enabled"] = $false
            }
            $settings["main_toolbar_lightrag_removed"] = $true
            $settings["plain_chat_adapter_version"] = 1
        }
        catch {}
    }

    Add-Check "Chat settings" "WRITE" "$settingsPath (plain LM Studio by default, LightRAG off)"
    if (-not $DryRun) {
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $settingsPath) | Out-Null
        $settings | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $settingsPath -Encoding UTF8
    }
}

function Install-DesktopLaunchers {
    if ($NoDesktopLaunchers) {
        Add-Check "Desktop launchers" "SKIPPED" "-NoDesktopLaunchers was used."
        return
    }

    $chatTarget = Join-Path $DesktopLogicDir "LightRAG-Desktop-Chat.ps1"
    if (-not (Test-Path -LiteralPath $chatTarget)) {
        $chatTarget = Join-Path $Root "desktop-launchers\LightRAG-Desktop-Chat.ps1"
    }

    $controlTarget = Join-Path $DesktopLogicDir "LightRAG-Control\LightRAG-Control.ps1"
    if (-not (Test-Path -LiteralPath $controlTarget)) {
        $controlTarget = Join-Path $Root "LightRAG-Control.ps1"
    }

    $chatIcon = Join-Path $IconDir "LightRAG-Chat.ico"
    $controlIcon = Join-Path $IconDir "LightRAG-Control.ico"
    $missingIcons = @($chatIcon, $controlIcon) | Where-Object { -not (Test-Path -LiteralPath $_) }
    if ($missingIcons.Count -gt 0) {
        Add-Check "Desktop icons" "MISSING" ($missingIcons -join "; ")
    } else {
        Add-Check "Desktop icons" "OK" "$chatIcon; $controlIcon"
    }

    Add-Check "Desktop launchers" "WRITE" "$DesktopDir (LightRAG-Chat.lnk, LightRAG-Control.lnk only)"
    if (-not $DryRun) {
        New-Item -ItemType Directory -Force -Path $DesktopDir | Out-Null

        $keep = @("LightRAG-Chat.lnk", "LightRAG-Control.lnk")
        $extraFiles = @(Get-ChildItem -LiteralPath $DesktopDir -Force | Where-Object { $_.Name -notin $keep })
        if ($extraFiles.Count -gt 0) {
            $archiveDir = Join-Path $DesktopLogicDir ("Desktop-archive-" + (Get-Date -Format "yyyyMMdd-HHmmss"))
            New-Item -ItemType Directory -Force -Path $archiveDir | Out-Null
            foreach ($item in $extraFiles) {
                Move-Item -LiteralPath $item.FullName -Destination $archiveDir
            }
            Add-Check "Desktop cleanup" "MOVED" "$($extraFiles.Count) old items -> $archiveDir"
        }

        $powershellExe = Get-CommandPath "powershell.exe"
        if (-not $powershellExe) { $powershellExe = "powershell" }

        New-DesktopShortcut `
            -ShortcutPath (Join-Path $DesktopDir "LightRAG-Chat.lnk") `
            -TargetPath $powershellExe `
            -Arguments @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $chatTarget) `
            -WorkingDirectory $Root `
            -IconPath $chatIcon

        New-DesktopShortcut `
            -ShortcutPath (Join-Path $DesktopDir "LightRAG-Control.lnk") `
            -TargetPath $powershellExe `
            -Arguments @("-STA", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $controlTarget) `
            -WorkingDirectory $Root `
            -IconPath $controlIcon
    }
}

function Write-InstallReport {
    param([object] $Profile)

    $lines = New-Object System.Collections.Generic.List[string]
    $lines.Add("# AI Knowledge Lab install report") | Out-Null
    $lines.Add("") | Out-Null
    $lines.Add("Generated: $($Profile.Date)") | Out-Null
    $lines.Add("") | Out-Null
    $lines.Add("## System") | Out-Null
    $lines.Add("") | Out-Null
    $lines.Add("- Computer: $($Profile.ComputerName)") | Out-Null
    $lines.Add("- User: $($Profile.UserName)") | Out-Null
    $lines.Add("- OS: $($Profile.OS)") | Out-Null
    $lines.Add("- CPU: $($Profile.CPU)") | Out-Null
    $lines.Add("- RAM: $($Profile.RAM)") | Out-Null
    $lines.Add("- GPU: $($Profile.GPU)") | Out-Null
    $lines.Add("- Disk C: $($Profile.DiskC)") | Out-Null
    $lines.Add("- PowerShell: $($Profile.PowerShell)") | Out-Null
    $lines.Add("") | Out-Null
    $lines.Add("## Checks") | Out-Null
    $lines.Add("") | Out-Null
    foreach ($check in $Checks) {
        $line = "- [$($check.Status)] $($check.Name)"
        if ($check.Details) { $line += ": $($check.Details)" }
        $lines.Add($line) | Out-Null
    }
    $lines.Add("") | Out-Null
    $lines.Add("## Manual steps") | Out-Null
    $lines.Add("") | Out-Null
    if ($ManualSteps.Count -eq 0) {
        $lines.Add("- None detected as missing by the installer.") | Out-Null
    } else {
        foreach ($step in $ManualSteps) {
            $lines.Add("- $step") | Out-Null
        }
    }
    $lines.Add("") | Out-Null
    $lines.Add("## After install") | Out-Null
    $lines.Add("") | Out-Null
    $lines.Add("- LightRAG-Chat starts as a normal LM Studio chat. LightRAG retrieval is optional and can be enabled from Settings.") | Out-Null
    $lines.Add("- If LightRAG is enabled but an index is missing, the chat keeps answering through plain LM Studio and suggests LightRAG-Control for maintenance.") | Out-Null
    $lines.Add("- Install LM Studio manually if it is missing, then download/load the configured LLM and embedding models.") | Out-Null
    $lines.Add("- Install Obsidian manually if you want the Obsidian icon to open the app directly. If it is not detected, the chat can ask for Obsidian.exe.") | Out-Null
    $lines.Add("- Use LightRAG-Control when LM Studio, models, indexes, imports, or GPU/Game Guard diagnostics need attention.") | Out-Null
    $lines.Add("- Game Guard is not installed into Windows startup. LightRAG-Chat runs the delayed GPU-load check only while the chat is open.") | Out-Null
    $lines.Add("") | Out-Null
    $lines.Add("## Main launchers") | Out-Null
    $lines.Add("") | Out-Null
    $lines.Add("- Desktop chat: $DesktopDir\LightRAG-Chat.lnk") | Out-Null
    $lines.Add("- Desktop control: $DesktopDir\LightRAG-Control.lnk") | Out-Null
    $lines.Add("- Desktop logic: $DesktopLogicDir") | Out-Null
    $lines.Add("- Web vault: $Root\Obsidian-Test-Vault\20 Projects\Web Development") | Out-Null
    $lines.Add("- Manual maintenance indexing: powershell -NoProfile -ExecutionPolicy Bypass -File scripts\ingest-vault-scope-lmstudio.ps1 -Scope web -Project web-development") | Out-Null

    if (-not $DryRun) {
        $lines | Set-Content -LiteralPath $ReportPath -Encoding UTF8
    }
    return ($lines -join [Environment]::NewLine)
}

Write-Host "AI Knowledge Lab installer" -ForegroundColor Cyan
Write-Host "Root: $Root"
if ($DryRun) { Write-Host "Dry run: no filesystem changes will be made." -ForegroundColor Yellow }
Write-Host ""

$profile = Get-SystemProfile
Write-Host "System summary:"
Write-Host "OS:  $($profile.OS)"
Write-Host "CPU: $($profile.CPU)"
Write-Host "RAM: $($profile.RAM)"
Write-Host "GPU: $($profile.GPU)"
Write-Host "Disk C: $($profile.DiskC)"
Write-Host ""

$systemPython = Resolve-SystemPython
if ($systemPython) {
    Add-Check "System Python" "OK" "$($systemPython.Path) ($($systemPython.Version), $($systemPython.Source))"
} else {
    Add-Check "System Python" "MISSING" "Python 3.10+ was not found."
}

Ensure-Venv $systemPython
Install-PythonPackages
Test-PythonImports
Test-LightRAGPackage
Ensure-EnvFile
Test-ExternalTools
Remove-LegacyStartupEntries
Ensure-ChatSettings
Install-DesktopLaunchers

$report = Write-InstallReport $profile
Write-Host ""
Write-Host $report
Write-Host ""
if (-not $DryRun) {
    Write-Host "Report saved: $ReportPath" -ForegroundColor Green
}
