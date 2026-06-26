"""Auto-detect LM Studio port from running processes or config."""
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path


PORT_HISTORY_FILE = Path(os.getenv("KNOWLEDGELAB_DATA_DIR", str(Path.home() / ".knowledgelab"))) / "port_history.json"
DEFAULT_PORT = 1234
COMMON_PORTS = [5000, 1234, 11434, 8080, 8000, 3000, 9090]


def _read_port_history() -> list[dict]:
    try:
        if PORT_HISTORY_FILE.exists():
            data = json.loads(PORT_HISTORY_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
    except Exception:
        pass
    return []


def _write_port_history(history: list[dict]) -> None:
    try:
        PORT_HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        PORT_HISTORY_FILE.write_text(json.dumps(history[-20:], ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def _save_port(port: int, source: str) -> None:
    history = _read_port_history()
    history = [h for h in history if h.get("port") != port]
    history.append({"port": port, "source": source})
    _write_port_history(history)


def _try_port(port: int, timeout: int = 2) -> bool:
    import urllib.request
    try:
        url = f"http://127.0.0.1:{port}/v1/models"
        request = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read(10_000).decode("utf-8"))
            return bool(data.get("data"))
    except Exception:
        return False


def detect_port_from_processes() -> int | None:
    """Try to find LM Studio port from running processes by scanning all listening ports."""
    try:
        result = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True, text=True, timeout=5,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        for line in result.stdout.split("\n"):
            if "LISTENING" in line and "127.0.0.1" in line:
                match = re.search(r":(\d+)\s", line)
                if match:
                    port = int(match.group(1))
                    if _try_port(port):
                        return port
    except Exception:
        pass

    return None


def detect_lmstudio_port() -> int:
    """Auto-detect LM Studio port with fallback chain.

    Priority:
    1. Environment variable LMSTUDIO_BASE_URL
    2. Common ports (1234, 11434, etc.)
    3. Running process detection
    4. Port history file
    5. Default port (1234)
    """
    env_url = os.getenv("LMSTUDIO_BASE_URL", "")
    if env_url:
        match = re.search(r":(\d+)", env_url)
        if match:
            port = int(match.group(1))
            if _try_port(port):
                _save_port(port, "env")
                return port

    for port in COMMON_PORTS:
        if _try_port(port):
            _save_port(port, "common")
            return port

    detected = detect_port_from_processes()
    if detected:
        _save_port(detected, "process")
        return detected

    history = _read_port_history()
    for entry in reversed(history):
        port = entry.get("port")
        if isinstance(port, int) and _try_port(port):
            return port

    return DEFAULT_PORT


def remember_port(port: int) -> None:
    """Save a port to history for future fallback."""
    _save_port(port, "user")
