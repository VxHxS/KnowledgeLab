param(
    [switch] $SmokeTest
)

$ErrorActionPreference = "Continue"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$AppName = "LightRAG Control"
$ScriptHome = Split-Path -Parent $MyInvocation.MyCommand.Path
$DesktopLauncherDir = Join-Path (Join-Path ([Environment]::GetFolderPath("Desktop")) "LightRag") "LightRAG-Control"
$LauncherCandidates = @($ScriptHome, $DesktopLauncherDir, (Split-Path -Parent $ScriptHome))
$LauncherDir = $LauncherCandidates |
    Where-Object { $_ -and (Test-Path -LiteralPath (Join-Path $_ "01 Check LightRAG.cmd")) } |
    Select-Object -First 1
if (-not $LauncherDir) {
    $LauncherDir = $ScriptHome
}

$PathHelper = Join-Path $ScriptHome "Resolve-LightRAG-Paths.ps1"
$LabDir = $null
$VaultDir = $null
if (Test-Path -LiteralPath $PathHelper) {
    . $PathHelper
    try {
        $ResolvedPaths = Get-LightRAGPaths -StartDir $ScriptHome
        $LabDir = $ResolvedPaths.Root
        $VaultDir = $ResolvedPaths.Vault
    }
    catch {
        $LabDir = $null
        $VaultDir = $null
    }
}
$LmsPath = Join-Path $env:USERPROFILE ".lmstudio\bin\lms.exe"

function Get-ScriptDescription {
    param([System.IO.FileInfo] $Script)

    switch -Regex ($Script.Name) {
        "^01 Check LightRAG\.cmd$|^Check-LightRAG\.ps1$" {
            return "Полный тест: проверяет Obsidian vault, запускает LightRAG через LM Studio, строит граф и показывает ответ с references."
        }
        "^02 Ask Obsidian Vault\.cmd$|^Ask-Obsidian-Vault\.ps1$" {
            return "Открывает консоль, просит вопрос и отправляет его локальной RAG-системе по заметкам Obsidian."
        }
        "^03 Stop AI\.cmd$|^Stop-AI\.ps1$" {
            return "Выгружает модели qwen/qwen3-14b и nomic-embed, затем останавливает LM Studio server."
        }
        "^04 Open Obsidian Vault\.cmd$|^Open-Obsidian-Vault\.ps1$" {
            return "Открывает правильную папку Obsidian-Test-Vault и показывает краткую подсказку."
        }
        "^05 Import Telegram Export\.cmd$|^Import-Telegram-Export\.ps1$" {
            return "Импортирует Telegram Desktop result.json в Obsidian Markdown с source=telegram и scope=general/game."
        }
        "^06 Ask General Knowledge\.cmd$|^Ask-General-Knowledge\.ps1$" {
            return "Задает вопрос только по общей базе знаний: Unity-ресурсы, статьи, видео, Telegram-заметки."
        }
        "^07 Ask My Game\.cmd$|^Ask-My-Game\.ps1$" {
            return "Задает вопрос только по проектному контексту твоей игры: scope=game, project=my-game."
        }
        "^08 Reindex LightRAG Scope\.cmd$|^Reindex-LightRAG-Scope\.ps1$" {
            return "Строит отдельный LightRAG-индекс для выбранного scope: all, general или game."
        }
default {
            return "Запускает файл $($Script.Name) из папки LightRag."
        }
    }
}

function Start-LightRagScript {
    param([System.IO.FileInfo] $Script)

    try {
        if ($Script.Extension -ieq ".cmd") {
            Start-Process -FilePath $Script.FullName -WorkingDirectory $LauncherDir
        }
        elseif ($Script.Extension -ieq ".ps1") {
            Start-Process -FilePath "powershell.exe" -ArgumentList @(
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                $Script.FullName
            ) -WorkingDirectory $LauncherDir
        }
        $script:LastRunLabel.Text = "Последний запуск: $($Script.Name)"
        $script:LastRunLabel.ForeColor = [System.Drawing.Color]::FromArgb(45, 75, 105)
    }
    catch {
        [System.Windows.Forms.MessageBox]::Show(
            "Не получилось запустить $($Script.Name).`n`n$($_.Exception.Message)",
            $AppName,
            [System.Windows.Forms.MessageBoxButtons]::OK,
            [System.Windows.Forms.MessageBoxIcon]::Error
        ) | Out-Null
    }
}

function Set-StatusLabel {
    param(
        [System.Windows.Forms.Label] $Label,
        [string] $Text,
        [System.Drawing.Color] $BackColor
    )

    $Label.Text = $Text
    $Label.BackColor = $BackColor
}

function Update-SystemStatus {
    if (-not (Test-Path -LiteralPath $LmsPath)) {
        Set-StatusLabel $script:ServerStatus "LM Studio CLI: нет" ([System.Drawing.Color]::FromArgb(160, 64, 64))
        Set-StatusLabel $script:ModelStatus "Модели: неизвестно" ([System.Drawing.Color]::FromArgb(114, 116, 122))
        return
    }

    $status = ""
    $models = ""
    try {
        $status = & $LmsPath status 2>&1 | Out-String
        $models = & $LmsPath ps 2>&1 | Out-String
    }
    catch {
        Set-StatusLabel $script:ServerStatus "LM Studio: ошибка" ([System.Drawing.Color]::FromArgb(160, 64, 64))
        Set-StatusLabel $script:ModelStatus "Модели: ошибка" ([System.Drawing.Color]::FromArgb(160, 64, 64))
        return
    }

    if ($status -match "Server:\s+ON") {
        Set-StatusLabel $script:ServerStatus "Server: ON :1234" ([System.Drawing.Color]::FromArgb(48, 130, 84))
    }
    else {
        Set-StatusLabel $script:ServerStatus "Server: OFF" ([System.Drawing.Color]::FromArgb(160, 64, 64))
    }

    $hasLlm = $models -match "qwen/qwen3-14b"
    $hasEmbedding = $models -match "nomic-embed"
    if ($hasLlm -and $hasEmbedding) {
        Set-StatusLabel $script:ModelStatus "Модели: loaded" ([System.Drawing.Color]::FromArgb(48, 130, 84))
    }
    elseif ($models -match "No models") {
        Set-StatusLabel $script:ModelStatus "Модели: не загружены" ([System.Drawing.Color]::FromArgb(183, 132, 47))
    }
    else {
        Set-StatusLabel $script:ModelStatus "Модели: частично" ([System.Drawing.Color]::FromArgb(183, 132, 47))
    }
}

function New-StatusPill {
    param([string] $Text)

    $label = New-Object System.Windows.Forms.Label
    $label.Text = $Text
    $label.AutoSize = $false
    $label.Width = 150
    $label.Height = 28
    $label.Margin = New-Object System.Windows.Forms.Padding(0, 0, 8, 0)
    $label.TextAlign = [System.Drawing.ContentAlignment]::MiddleCenter
    $label.ForeColor = [System.Drawing.Color]::White
    $label.BackColor = [System.Drawing.Color]::FromArgb(114, 116, 122)
    $label.Font = New-Object System.Drawing.Font("Segoe UI", 9, [System.Drawing.FontStyle]::Bold)
    return $label
}

function New-SectionLabel {
    param([string] $Text)

    $label = New-Object System.Windows.Forms.Label
    $label.Text = $Text
    $label.AutoSize = $false
    $label.Width = 640
    $label.Height = 26
    $label.Margin = New-Object System.Windows.Forms.Padding(0, 14, 0, 4)
    $label.Font = New-Object System.Drawing.Font("Segoe UI Semibold", 10)
    $label.ForeColor = [System.Drawing.Color]::FromArgb(36, 46, 56)
    return $label
}

function New-ScriptButton {
    param(
        [System.IO.FileInfo] $Script,
        [System.Windows.Forms.ToolTip] $ToolTip
    )

    $button = New-Object System.Windows.Forms.Button
    $button.Text = [System.IO.Path]::GetFileNameWithoutExtension($Script.Name)
    $button.Tag = $Script
    $button.Width = 300
    $button.Height = 48
    $button.Margin = New-Object System.Windows.Forms.Padding(0, 0, 12, 12)
    $button.FlatStyle = [System.Windows.Forms.FlatStyle]::Flat
    $button.FlatAppearance.BorderColor = [System.Drawing.Color]::FromArgb(194, 202, 210)
    $button.FlatAppearance.MouseOverBackColor = [System.Drawing.Color]::FromArgb(225, 235, 244)
    $button.BackColor = [System.Drawing.Color]::FromArgb(248, 250, 252)
    $button.ForeColor = [System.Drawing.Color]::FromArgb(26, 39, 52)
    $button.Font = New-Object System.Drawing.Font("Segoe UI", 10)
    $button.TextAlign = [System.Drawing.ContentAlignment]::MiddleLeft
    $button.Padding = New-Object System.Windows.Forms.Padding(12, 0, 8, 0)
    $ToolTip.SetToolTip($button, (Get-ScriptDescription $Script))
    $button.Add_Click({ Start-LightRagScript ([System.IO.FileInfo] $this.Tag) })
    return $button
}

$form = New-Object System.Windows.Forms.Form
$form.Text = $AppName
$form.StartPosition = [System.Windows.Forms.FormStartPosition]::CenterScreen
$form.Size = New-Object System.Drawing.Size(720, 560)
$form.MinimumSize = New-Object System.Drawing.Size(680, 460)
$form.BackColor = [System.Drawing.Color]::FromArgb(241, 244, 247)
$form.Font = New-Object System.Drawing.Font("Segoe UI", 10)

$toolTip = New-Object System.Windows.Forms.ToolTip
$toolTip.InitialDelay = 500
$toolTip.ReshowDelay = 100
$toolTip.AutoPopDelay = 16000
$toolTip.ShowAlways = $true
$toolTip.UseAnimation = $true
$toolTip.UseFading = $true

$root = New-Object System.Windows.Forms.TableLayoutPanel
$root.Dock = [System.Windows.Forms.DockStyle]::Fill
$root.ColumnCount = 1
$root.RowCount = 3
$root.Padding = New-Object System.Windows.Forms.Padding(24, 20, 24, 18)
$root.RowStyles.Add((New-Object System.Windows.Forms.RowStyle([System.Windows.Forms.SizeType]::Absolute, 72))) | Out-Null
$root.RowStyles.Add((New-Object System.Windows.Forms.RowStyle([System.Windows.Forms.SizeType]::Percent, 100))) | Out-Null
$root.RowStyles.Add((New-Object System.Windows.Forms.RowStyle([System.Windows.Forms.SizeType]::Absolute, 36))) | Out-Null
$form.Controls.Add($root)

$header = New-Object System.Windows.Forms.TableLayoutPanel
$header.Dock = [System.Windows.Forms.DockStyle]::Fill
$header.ColumnCount = 2
$header.RowCount = 1
$header.ColumnStyles.Add((New-Object System.Windows.Forms.ColumnStyle([System.Windows.Forms.SizeType]::Percent, 100))) | Out-Null
$header.ColumnStyles.Add((New-Object System.Windows.Forms.ColumnStyle([System.Windows.Forms.SizeType]::Absolute, 330))) | Out-Null
$root.Controls.Add($header, 0, 0)

$titleBlock = New-Object System.Windows.Forms.FlowLayoutPanel
$titleBlock.Dock = [System.Windows.Forms.DockStyle]::Fill
$titleBlock.FlowDirection = [System.Windows.Forms.FlowDirection]::TopDown
$titleBlock.WrapContents = $false

$title = New-Object System.Windows.Forms.Label
$title.Text = "LightRAG Control"
$title.AutoSize = $true
$title.Margin = New-Object System.Windows.Forms.Padding(0, 0, 0, 2)
$title.Font = New-Object System.Drawing.Font("Segoe UI Semibold", 18)
$title.ForeColor = [System.Drawing.Color]::FromArgb(22, 32, 44)
$titleBlock.Controls.Add($title)

$pathLabel = New-Object System.Windows.Forms.Label
$pathLabel.Text = $LauncherDir
$pathLabel.AutoSize = $true
$pathLabel.Margin = New-Object System.Windows.Forms.Padding(1, 0, 0, 0)
$pathLabel.Font = New-Object System.Drawing.Font("Segoe UI", 8)
$pathLabel.ForeColor = [System.Drawing.Color]::FromArgb(82, 92, 104)
$titleBlock.Controls.Add($pathLabel)
$header.Controls.Add($titleBlock, 0, 0)

$statusBlock = New-Object System.Windows.Forms.FlowLayoutPanel
$statusBlock.Dock = [System.Windows.Forms.DockStyle]::Fill
$statusBlock.FlowDirection = [System.Windows.Forms.FlowDirection]::LeftToRight
$statusBlock.WrapContents = $false
$statusBlock.Padding = New-Object System.Windows.Forms.Padding(0, 13, 0, 0)
$script:ServerStatus = New-StatusPill "Server: ..."
$script:ModelStatus = New-StatusPill "Модели: ..."
$statusBlock.Controls.Add($script:ServerStatus)
$statusBlock.Controls.Add($script:ModelStatus)
$header.Controls.Add($statusBlock, 1, 0)

$scroll = New-Object System.Windows.Forms.Panel
$scroll.Dock = [System.Windows.Forms.DockStyle]::Fill
$scroll.AutoScroll = $true
$root.Controls.Add($scroll, 0, 1)

$buttonsPanel = New-Object System.Windows.Forms.FlowLayoutPanel
$buttonsPanel.Dock = [System.Windows.Forms.DockStyle]::Top
$buttonsPanel.AutoSize = $true
$buttonsPanel.FlowDirection = [System.Windows.Forms.FlowDirection]::LeftToRight
$buttonsPanel.WrapContents = $true
$buttonsPanel.Padding = New-Object System.Windows.Forms.Padding(0, 0, 0, 12)
$scroll.Controls.Add($buttonsPanel)

$scriptFiles = @()
if (Test-Path -LiteralPath $LauncherDir) {
    $scriptFiles = Get-ChildItem -LiteralPath $LauncherDir -File |
        Where-Object {
            $_.Name -in @(
                "01 Check LightRAG.cmd",
                "02 Ask Obsidian Vault.cmd",
                "03 Stop AI.cmd",
                "04 Open Obsidian Vault.cmd",
                "05 Import Telegram Export.cmd",
                "06 Ask General Knowledge.cmd",
                "07 Ask My Game.cmd",
                "08 Reindex LightRAG Scope.cmd"
            )
        } |
        Sort-Object Name
}

$cmdFiles = @($scriptFiles | Where-Object { $_.Extension -ieq ".cmd" })
$ps1Files = @($scriptFiles | Where-Object { $_.Extension -ieq ".ps1" })

if ($cmdFiles.Count -gt 0) {
    $buttonsPanel.Controls.Add((New-SectionLabel "Запускатели"))
    foreach ($script in $cmdFiles) {
        $buttonsPanel.Controls.Add((New-ScriptButton $script $toolTip))
    }
}

if ($scriptFiles.Count -eq 0) {
    $empty = New-Object System.Windows.Forms.Label
    $empty.Text = "Скрипты не найдены: $LauncherDir"
    $empty.AutoSize = $true
    $empty.ForeColor = [System.Drawing.Color]::FromArgb(160, 64, 64)
    $buttonsPanel.Controls.Add($empty)
}

if ($SmokeTest) {
    Write-Host "LauncherDir=$LauncherDir"
    Write-Host "ScriptCount=$($scriptFiles.Count)"
    Write-Host "CmdCount=$($cmdFiles.Count)"
    Write-Host "Ps1Count=$($ps1Files.Count)"
    Write-Host "TooltipInitialDelay=$($toolTip.InitialDelay)"
    exit 0
}

$footer = New-Object System.Windows.Forms.TableLayoutPanel
$footer.Dock = [System.Windows.Forms.DockStyle]::Fill
$footer.ColumnCount = 2
$footer.RowCount = 1
$footer.ColumnStyles.Add((New-Object System.Windows.Forms.ColumnStyle([System.Windows.Forms.SizeType]::Percent, 100))) | Out-Null
$footer.ColumnStyles.Add((New-Object System.Windows.Forms.ColumnStyle([System.Windows.Forms.SizeType]::Absolute, 136))) | Out-Null
$root.Controls.Add($footer, 0, 2)

$script:LastRunLabel = New-Object System.Windows.Forms.Label
$script:LastRunLabel.Text = "Готово"
$script:LastRunLabel.Dock = [System.Windows.Forms.DockStyle]::Fill
$script:LastRunLabel.TextAlign = [System.Drawing.ContentAlignment]::MiddleLeft
$script:LastRunLabel.ForeColor = [System.Drawing.Color]::FromArgb(82, 92, 104)
$footer.Controls.Add($script:LastRunLabel, 0, 0)

$refreshButton = New-Object System.Windows.Forms.Button
$refreshButton.Text = "Обновить"
$refreshButton.Dock = [System.Windows.Forms.DockStyle]::Fill
$refreshButton.FlatStyle = [System.Windows.Forms.FlatStyle]::Flat
$refreshButton.BackColor = [System.Drawing.Color]::FromArgb(232, 238, 244)
$refreshButton.FlatAppearance.BorderColor = [System.Drawing.Color]::FromArgb(194, 202, 210)
$refreshButton.ForeColor = [System.Drawing.Color]::FromArgb(26, 39, 52)
$refreshButton.Font = New-Object System.Drawing.Font("Segoe UI", 9)
$toolTip.SetToolTip($refreshButton, "Обновляет статус LM Studio server и загруженных моделей.")
$refreshButton.Add_Click({ Update-SystemStatus })
$footer.Controls.Add($refreshButton, 1, 0)

$form.Add_Shown({ Update-SystemStatus })
[void]$form.ShowDialog()
