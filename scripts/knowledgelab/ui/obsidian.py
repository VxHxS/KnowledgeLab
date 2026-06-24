"""Obsidian integration — path discovery, launch, program utilities."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path


def find_obsidian_shortcuts(roaming_app: Path, program_data: Path) -> list[str]:
    roots = [
        roaming_app / "Microsoft" / "Windows" / "Start Menu" / "Programs",
        program_data / "Microsoft" / "Windows" / "Start Menu" / "Programs",
        Path.home() / "Desktop",
        Path(os.getenv("PUBLIC", "")) / "Desktop",
    ]
    shortcuts: list[str] = []
    for root in roots:
        if not root.exists():
            continue
        try:
            shortcuts.extend(str(path) for path in root.rglob("*Obsidian*.lnk"))
        except OSError:
            continue
    return shortcuts


def find_obsidian_registry_candidates() -> list[str]:
    from knowledgelab.config import ROOT
    command = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        r"""
$paths = @(
  'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*',
  'HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*',
  'HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*'
)
foreach ($path in $paths) {
  Get-ItemProperty $path -ErrorAction SilentlyContinue |
    Where-Object { $_.DisplayName -like '*Obsidian*' } |
    ForEach-Object {
      if ($_.InstallLocation) { Join-Path $_.InstallLocation 'Obsidian.exe' }
      if ($_.DisplayIcon) { $_.DisplayIcon }
    }
}
""",
    ]
    try:
        completed = subprocess.run(
            command,
            cwd=str(ROOT),
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=4,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except Exception:
        return []
    candidates: list[str] = []
    for line in (completed.stdout or "").splitlines():
        candidate = clean_windows_program_path(line)
        if candidate:
            candidates.append(candidate)
    return candidates


def clean_windows_program_path(value: str) -> str:
    value = str(value or "").strip().strip('"')
    if not value:
        return ""
    value = re.sub(r",\d+$", "", value).strip().strip('"')
    lowered = value.lower()
    for suffix in (".exe", ".lnk"):
        index = lowered.find(suffix)
        if index >= 0:
            return value[: index + len(suffix)].strip().strip('"')
    return value if Path(value).suffix.lower() in {".exe", ".lnk"} else ""


def find_obsidian_path(configured: str = "") -> str:
    local_app = Path(os.getenv("LOCALAPPDATA", ""))
    roaming_app = Path(os.getenv("APPDATA", ""))
    program_data = Path(os.getenv("PROGRAMDATA", ""))
    program_files = Path(os.getenv("PROGRAMFILES", ""))
    program_files_x86 = Path(os.getenv("PROGRAMFILES(X86)", ""))
    candidates = [
        configured,
        shutil.which("Obsidian.exe") or "",
        shutil.which("obsidian") or "",
        str(local_app / "Obsidian" / "Obsidian.exe"),
        str(local_app / "Programs" / "Obsidian" / "Obsidian.exe"),
        str(local_app / "Programs" / "obsidian" / "Obsidian.exe"),
        str(local_app / "Microsoft" / "WindowsApps" / "Obsidian.exe"),
        str(program_files / "Obsidian" / "Obsidian.exe"),
        str(program_files_x86 / "Obsidian" / "Obsidian.exe"),
    ]
    candidates.extend(find_obsidian_shortcuts(roaming_app, program_data))
    candidates.extend(find_obsidian_registry_candidates())
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    return ""


def launch_windows_program(path: str, cwd: str | None = None) -> None:
    target = Path(path)
    if target.suffix.lower() == ".lnk":
        startfile = getattr(os, "startfile", None)
        if startfile:
            startfile(str(target))
            return
    try:
        subprocess.Popen([str(target)], cwd=cwd)
    except OSError:
        startfile = getattr(os, "startfile", None)
        if startfile:
            startfile(str(target))
        else:
            raise
