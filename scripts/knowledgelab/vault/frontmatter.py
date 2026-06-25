from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from knowledgelab.config import VAULT_DIR, LAYER_ACTIVE, LAYER_FINISHED_PROJECTS
from knowledgelab.utils.text import slugify
from knowledgelab.utils.urls import normalize_source_url_for_match


WEB_PROJECT_SLUGS = {"web", "web-dev", "web-development", "frontend", "front-end"}
ACTIVE_LAYER = "active"
FINISHED_PROJECTS_LAYER = "finished-projects"


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    match = re.match(r"\A---\s*\n(.*?)\n---\s*(?:\n|\Z)", text, re.DOTALL)
    if not match:
        return {}, text

    meta: dict[str, Any] = {}
    for raw_line in match.group(1).splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, raw_value = line.split(":", 1)
        key = key.strip().lower()
        raw_value = raw_value.strip()
        if raw_value.startswith("[") and raw_value.endswith("]"):
            value = [
                item.strip().strip("\"'")
                for item in raw_value[1:-1].split(",")
                if item.strip()
            ]
        else:
            value = raw_value.strip("\"'")
        meta[key] = value

    return meta, text[match.end():]


def parse_basic_frontmatter(text: str) -> dict[str, str]:
    match = re.match(r"\A---\s*\n(.*?)\n---\s*(?:\n|\Z)", text, re.DOTALL)
    if not match:
        return {}
    meta: dict[str, str] = {}
    for raw_line in match.group(1).splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, raw_value = line.split(":", 1)
        meta[key.strip().lower()] = raw_value.strip().strip("\"'")
    return meta


def infer_scope(rel_path: str, meta: dict[str, Any]) -> str:
    raw_scope = str(meta.get("scope", "")).strip().lower()
    if raw_scope:
        return raw_scope

    normalized = rel_path.replace("\\", "/").lower()
    parts = rel_path.replace("\\", "/").split("/")
    if len(parts) >= 2 and parts[0].lower() == "20 projects":
        if slugify(parts[1]) in WEB_PROJECT_SLUGS:
            return "web"
        return "game"
    if normalized.startswith("30 sources/telegram/"):
        return "general"
    if normalized.startswith("30 sources/articles/"):
        return "general"
    if normalized.startswith("30 sources/youtube/"):
        return "general"
    if normalized.startswith("10 general knowledge/"):
        return "general"
    if normalized.startswith("10 programming/"):
        return "general"
    return "general"


def infer_project(rel_path: str, meta: dict[str, Any]) -> str:
    raw_project = str(meta.get("project", "")).strip()
    if raw_project:
        return slugify(raw_project)

    parts = rel_path.replace("\\", "/").split("/")
    if len(parts) >= 3 and parts[0].lower() == "40 finished projects":
        return slugify(parts[2])
    if len(parts) >= 2 and parts[0].lower() == "20 projects":
        return slugify(parts[1])
    return ""


def infer_project_section(rel_path: str, meta: dict[str, Any]) -> str:
    raw_section = str(meta.get("project_section", "")).strip()
    if raw_section:
        return slugify(raw_section)
    parts = rel_path.replace("\\", "/").split("/")
    if len(parts) >= 3 and parts[0].lower() == "40 finished projects":
        return slugify(parts[1])
    return ""


def infer_layer(rel_path: str, meta: dict[str, Any]) -> str:
    raw_layer = str(meta.get("layer", "")).strip().lower()
    if raw_layer:
        return raw_layer
    normalized = rel_path.replace("\\", "/").lower()
    if normalized.startswith("40 finished projects/"):
        return FINISHED_PROJECTS_LAYER
    return ACTIVE_LAYER


def find_existing_source_note(url: str, layer: str, scope: str, project: str) -> str:
    target = normalize_source_url_for_match(url)
    if not target or not VAULT_DIR.exists():
        return ""
    wanted_project = slugify(project) if project else ""
    for path in VAULT_DIR.rglob("*.md"):
        if not path.is_file():
            continue
        try:
            rel_path = path.relative_to(VAULT_DIR).as_posix()
            meta = parse_basic_frontmatter(path.read_text(encoding="utf-8-sig", errors="replace"))
        except (OSError, UnicodeError, ValueError):
            continue
        meta_url = meta.get("normalized_source_url", "") or meta.get("source_url", "")
        if normalize_source_url_for_match(meta_url) != target:
            continue
        from knowledgelab.routing.topics import infer_note_layer_from_path, infer_note_scope_from_path

        if infer_note_layer_from_path(rel_path, meta) != layer:
            continue
        if layer != LAYER_FINISHED_PROJECTS:
            if scope not in {"", "all"} and infer_note_scope_from_path(rel_path, meta) != scope:
                continue
            note_project = slugify(meta.get("project", "")) if meta.get("project") else ""
            if wanted_project and note_project and note_project != wanted_project:
                continue
        return rel_path
    return ""


def note_metadata(rel_path: str, vault_dir: Path = VAULT_DIR) -> dict[str, str]:
    try:
        path = vault_dir / rel_path
        return parse_basic_frontmatter(path.read_text(encoding="utf-8-sig", errors="replace"))
    except Exception:
        return {}


def find_existing_file_capture(source_path: str, layer: str, scope: str, project: str) -> list[dict[str, str]]:
    """Find existing capture notes for a local file or folder by source_path.

    Returns a list of dicts with rel_path, title, captured_at for each match.
    """
    if not source_path or not VAULT_DIR.exists():
        return []
    normalized = source_path.replace("\\", "/").rstrip("/").lower()
    wanted_project = slugify(project) if project else ""
    results: list[dict[str, str]] = []
    for path in VAULT_DIR.rglob("*.md"):
        if not path.is_file():
            continue
        try:
            rel_path = path.relative_to(VAULT_DIR).as_posix()
            meta = parse_basic_frontmatter(path.read_text(encoding="utf-8-sig", errors="replace"))
        except (OSError, UnicodeError, ValueError):
            continue
        meta_source = (meta.get("source_path") or "").replace("\\", "/").rstrip("/").lower()
        if not meta_source:
            continue
        if meta_source != normalized:
            continue
        from knowledgelab.routing.topics import infer_note_layer_from_path, infer_note_scope_from_path

        if infer_note_layer_from_path(rel_path, meta) != layer:
            continue
        if layer != LAYER_FINISHED_PROJECTS:
            if scope not in {"", "all"} and infer_note_scope_from_path(rel_path, meta) != scope:
                continue
            note_project = slugify(meta.get("project", "")) if meta.get("project") else ""
            if wanted_project and note_project and note_project != wanted_project:
                continue
        results.append({
            "rel_path": rel_path,
            "title": meta.get("title", path.stem),
            "captured_at": meta.get("captured_at", ""),
        })
    return results
