from __future__ import annotations

import datetime as dt
import html
import json
import re
import zipfile
from pathlib import Path

from knowledgelab.config import TEXT_EXTRACTION_LIMIT


def now_iso() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def compact_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def contains_any(text: str, terms: set[str]) -> bool:
    lowered = f" {text.lower()} "
    return any(term in lowered for term in terms)


def clean_filename(value: str) -> str:
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "-", value).strip()
    value = re.sub(r"\s+", " ", value)
    return value[:120].strip(" .-") or "note"


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9а-яё_-]+", "-", value, flags=re.IGNORECASE)
    value = re.sub(r"-{2,}", "-", value).strip("-")
    return value or "note"


def compact_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def yaml_quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def markdown_fence_text(value: str) -> str:
    return value.replace("```", "'''").strip()


def extract_json_object(text: str) -> dict:
    text = text.strip()
    if not text:
        return {}
    try:
        parsed = __import__('json').loads(text)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        pass
    match = __import__('re').search(r"\{.*\}", text, __import__('re').DOTALL)
    if not match:
        return {}
    try:
        parsed = __import__('json').loads(match.group(0))
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


SERVICE_OUTPUT_PREFIXES = (
    "game guard:", "gpu:", "lm studio", "lightrag", "python environment",
    "obsidian", "starting", "checking", "health",
)


def is_service_output_line(line: str) -> bool:
    stripped = line.strip().lower()
    return any(stripped.startswith(prefix) for prefix in SERVICE_OUTPUT_PREFIXES)


def trim_output(text: str) -> str:
    return text.strip().lstrip("\n").rstrip("\n").strip()


SERVICE_WARNINGS = {
    "game guard:", "gpu:", "lm studio server", "lightrag storage",
    "python environment", "obsidian vault", "obsidian не найден",
}


def friendly_error(output: str) -> str:
    cleaned = trim_output(output)
    lowered = cleaned.lower()
    for marker in SERVICE_WARNINGS:
        if marker in lowered:
            return cleaned
    return cleaned[:500] + ("..." if len(cleaned) > 500 else "")


def read_text_source(path: Path) -> tuple[str, str]:
    """Read text content from a text file."""
    try:
        raw = path.read_bytes()[: TEXT_EXTRACTION_LIMIT + 4096]
    except OSError as exc:
        return "", f"read failed: {exc}"
    for encoding in ("utf-8-sig", "utf-8", "cp1251", "utf-16"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            text = ""
    if not text:
        text = raw.decode("utf-8", errors="replace")
    truncated = len(text) > TEXT_EXTRACTION_LIMIT
    text = text[:TEXT_EXTRACTION_LIMIT].strip()
    status = "extracted"
    if truncated:
        status = "partial"
        text += "\n\n_Extraction was truncated; use a dedicated importer for the full file._"
    return text, status


def read_docx_source(path: Path) -> tuple[str, str]:
    """Read text content from a .docx file."""
    try:
        with zipfile.ZipFile(path) as archive:
            raw = archive.read("word/document.xml").decode("utf-8", errors="replace")
    except Exception as exc:
        return "", f"docx extraction failed: {exc}"
    raw = re.sub(r"</w:p\s*>", "\n", raw)
    raw = re.sub(r"<[^>]+>", "", raw)
    text = html.unescape(raw)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text).strip()
    truncated = len(text) > TEXT_EXTRACTION_LIMIT
    text = text[:TEXT_EXTRACTION_LIMIT].strip()
    if truncated:
        text += "\n\n_Extraction was truncated; use a dedicated importer for the full document._"
        return text, "partial"
    return text, "extracted" if text else "pending"


def extract_lightweight_file_text(path: Path, kind: str) -> tuple[str, str]:
    """Extract text content from a file based on its kind."""
    if kind == "text_file":
        return read_text_source(path)
    if path.suffix.lower() == ".docx":
        return read_docx_source(path)
    return "", "pending"
