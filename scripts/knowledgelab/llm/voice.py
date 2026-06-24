"""Voice input — PowerShell speech recognition and error handling."""

from __future__ import annotations

import os
import subprocess
import webbrowser

from knowledgelab.config import VOICE_INPUT_SECONDS


def build_voice_recognition_script(timeout_seconds: int = VOICE_INPUT_SECONDS) -> str:
    return f"""
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
Add-Type -AssemblyName System.Speech
$recognizer = New-Object System.Speech.Recognition.SpeechRecognitionEngine
try {{
  $recognizer.SetInputToDefaultAudioDevice()
  $grammar = New-Object System.Speech.Recognition.DictationGrammar
  $recognizer.LoadGrammar($grammar)
  $result = $recognizer.Recognize([System.TimeSpan]::FromSeconds({timeout_seconds}))
  if ($null -ne $result -and $result.Text) {{
    Write-Output $result.Text
  }}
}} finally {{
  if ($recognizer) {{
    $recognizer.Dispose()
  }}
}}
"""


def friendly_voice_error(output: str) -> tuple[str, bool]:
    lowered = output.strip().lower()
    if "system.speech" in lowered or "add-type" in lowered:
        return "Windows Speech Recognition недоступен в этой системе. Проверьте системные настройки речи и микрофона Windows.", True
    if "no recognizer" in lowered or "default audio device" in lowered or "input" in lowered:
        return "Не удалось получить звук с микрофона или найти установленный recognizer. Проверьте устройство ввода в Windows.", True
    return "Не услышал речь. Попробуйте еще раз или вставьте текст вручную.", False


def open_windows_microphone_settings() -> str | None:
    """Open Windows sound settings. Returns error message on failure, None on success."""
    try:
        startfile = getattr(os, "startfile", None)
        if startfile:
            startfile("ms-settings:sound")
            return None
        webbrowser.open("ms-settings:sound")
        return None
    except Exception:
        try:
            subprocess.Popen(
                ["control", "mmsys.cpl,,1"],
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            return None
        except Exception:
            return "Не удалось открыть настройки Windows автоматически. Откройте Settings -> System -> Sound -> Input."
