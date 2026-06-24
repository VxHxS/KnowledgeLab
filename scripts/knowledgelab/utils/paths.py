from __future__ import annotations

import os
import re
from pathlib import Path
from urllib.parse import unquote, urlparse

from knowledgelab.config import DND_DISABLE_ENV, DND_SAFE_MODE_ENV


def normalize_attached_source_path(value: str) -> str:
    value = str(value or "").strip()
    value = value.strip('"').strip("'")
    if value.startswith("{") and value.endswith("}") and len(value) >= 2:
        value = value[1:-1].strip()
    if value.lower().startswith("file:"):
        parsed = urlparse(value)
        path = unquote(parsed.path or "")
        if re.match(r"^/[a-zA-Z]:/", path):
            path = path[1:]
        value = path.replace("/", os.sep) if path else value
    return value


def explorer_dnd_enabled() -> bool:
    disabled = os.getenv(DND_DISABLE_ENV, "").strip().lower()
    if disabled in {"1", "true", "yes", "on"}:
        return False
    explicit = os.getenv(DND_SAFE_MODE_ENV, "").strip().lower()
    if explicit:
        return explicit in {"1", "true", "yes", "on"}
    return True


def first_existing_local_source(text: str) -> Path | None:
    candidates = [text.strip()]
    candidates.extend(line.strip() for line in text.splitlines())
    for candidate in candidates:
        if not candidate:
            continue
        normalized = normalize_attached_source_path(candidate)
        if not normalized:
            continue
        try:
            path = Path(normalized)
        except (OSError, ValueError):
            continue
        if path.exists() and (path.is_dir() or path.is_file()):
            return path
    return None
