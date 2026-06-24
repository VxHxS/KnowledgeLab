"""Process management — subprocess execution, timeout handling."""

from __future__ import annotations

import subprocess
from pathlib import Path

from knowledgelab.config import ROOT


def run_command(command: list[str], timeout_seconds: int, env: dict[str, str] | None = None) -> tuple[int, str]:
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    process = subprocess.Popen(
        command,
        cwd=str(ROOT),
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=creationflags,
        env=env,
    )
    try:
        stdout, stderr = process.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        terminate_process(process)
        raise TimeoutError(f"Command timed out after {timeout_seconds} seconds.")
    output = stdout or ""
    if stderr:
        output = f"{output}\n{stderr}".strip()
    return process.returncode or 0, output


def terminate_process(process: subprocess.Popen) -> bool:
    if process.poll() is not None:
        return False
    try:
        process.terminate()
        try:
            process.wait(timeout=4)
        except subprocess.TimeoutExpired:
            process.kill()
        return True
    except Exception:
        try:
            process.kill()
            return True
        except Exception:
            return False
