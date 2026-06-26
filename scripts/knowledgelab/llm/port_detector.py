"""Auto-detect LM Studio server URL and remember working ports."""
from __future__ import annotations

import json
import os
import re
import subprocess
import csv
from pathlib import Path
from urllib.parse import urlparse


PORT_HISTORY_FILE = Path(os.getenv("KNOWLEDGELAB_DATA_DIR", str(Path.home() / ".knowledgelab"))) / "port_history.json"
DEFAULT_PORT = 1234
COMMON_PORTS = [5000, 1234]
DETECT_TIMEOUT = 0.35


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


def normalize_lmstudio_base_url(value: str | None, default_port: int = DEFAULT_PORT) -> str:
    raw = str(value or "").strip().rstrip("/")
    if not raw:
        raw = f"http://127.0.0.1:{default_port}"
    if not re.match(r"^https?://", raw, re.IGNORECASE):
        raw = "http://" + raw
    if raw.endswith("/api/v1"):
        return raw[:-7].rstrip("/") + "/v1"
    if raw.endswith("/v1"):
        return raw
    return raw + "/v1"


def lmstudio_server_root(base_url: str) -> str:
    normalized = normalize_lmstudio_base_url(base_url)
    return normalized[:-3] if normalized.endswith("/v1") else normalized.rstrip("/")


def port_from_base_url(base_url: str) -> int | None:
    try:
        parsed = urlparse(normalize_lmstudio_base_url(base_url))
        return parsed.port
    except Exception:
        return None


def openai_models_url(base_url: str) -> str:
    return normalize_lmstudio_base_url(base_url).rstrip("/") + "/models"


def rest_models_url(base_url: str) -> str:
    return lmstudio_server_root(base_url).rstrip("/") + "/api/v1/models"


def _request_json(url: str, timeout: float = 2.0):
    import urllib.request
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read(100_000).decode("utf-8", errors="replace")
    return json.loads(raw) if raw.strip() else {}


def is_lmstudio_base_url_available(base_url: str, timeout: float = 2.0) -> bool:
    for url in (rest_models_url(base_url), openai_models_url(base_url)):
        try:
            data = _request_json(url, timeout=timeout)
            if isinstance(data, list) or (
                isinstance(data, dict) and (data.get("models") is not None or data.get("data") is not None)
            ):
                port = port_from_base_url(base_url)
                if port is not None:
                    _save_port(port, "probe")
                return True
        except Exception:
            continue
    return False


def _try_port(port: int, timeout: float = 2) -> bool:
    try:
        return is_lmstudio_base_url_available(f"http://127.0.0.1:{port}/v1", timeout=timeout)
    except Exception:
        return False


def _lmstudio_process_ids() -> set[int]:
    pids: set[int] = set()
    try:
        result = subprocess.run(
            ["tasklist", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, timeout=5,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        for row in csv.reader(result.stdout.splitlines()):
            if len(row) < 2:
                continue
            name = row[0].strip().lower()
            if "lm studio" not in name and "lmstudio" not in name and name != "lms.exe":
                continue
            try:
                pids.add(int(row[1]))
            except ValueError:
                continue
    except Exception:
        pass
    return pids


def detect_port_from_processes() -> int | None:
    """Try to find LM Studio port from LM Studio-owned listening ports."""
    lmstudio_pids = _lmstudio_process_ids()
    if not lmstudio_pids:
        return None
    try:
        result = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True, text=True, timeout=5,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        ports: list[int] = []
        for line in result.stdout.split("\n"):
            if "LISTENING" in line and "127.0.0.1" in line:
                match = re.search(r":(\d+)\s+.*\s+(\d+)\s*$", line)
                if match:
                    port = int(match.group(1))
                    pid = int(match.group(2))
                    if pid in lmstudio_pids:
                        ports.append(port)
        for port in sorted(set(ports), key=lambda item: (item not in COMMON_PORTS, item)):
            if _try_port(port, timeout=0.5):
                return port
    except Exception:
        pass

    return None


def detect_lmstudio_port() -> int:
    """Auto-detect LM Studio port with fallback chain."""
    env_url = os.getenv("LMSTUDIO_BASE_URL", "")
    if env_url:
        port = port_from_base_url(env_url)
        if port is not None:
            if _try_port(port, timeout=DETECT_TIMEOUT):
                _save_port(port, "env")
                return port

    history = _read_port_history()
    for entry in reversed(history):
        port = entry.get("port")
        if isinstance(port, int) and _try_port(port, timeout=DETECT_TIMEOUT):
            _save_port(port, "history")
            return port

    for port in COMMON_PORTS:
        if _try_port(port, timeout=DETECT_TIMEOUT):
            _save_port(port, "common")
            return port

    detected = detect_port_from_processes()
    if detected:
        _save_port(detected, "process")
        return detected

    return DEFAULT_PORT


def detect_lmstudio_base_url(configured_url: str | None = None) -> tuple[str, str, bool]:
    configured = normalize_lmstudio_base_url(configured_url)
    if configured_url and is_lmstudio_base_url_available(configured, timeout=DETECT_TIMEOUT):
        port = port_from_base_url(configured)
        if port is not None:
            _save_port(port, "configured")
        return configured, "configured", True

    port = detect_lmstudio_port()
    detected = normalize_lmstudio_base_url(f"http://127.0.0.1:{port}/v1")
    found = is_lmstudio_base_url_available(detected, timeout=DETECT_TIMEOUT)
    return detected, "auto" if found else "default", found


def remember_port(port: int) -> None:
    """Save a port to history for future fallback."""
    _save_port(port, "user")
