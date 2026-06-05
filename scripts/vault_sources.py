from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any


FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*(?:\n|\Z)", re.DOTALL)
WEB_PROJECT_SLUGS = {"web", "web-dev", "web-development", "frontend", "front-end"}


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9а-яё_-]+", "-", value, flags=re.IGNORECASE)
    value = re.sub(r"-{2,}", "-", value).strip("-")
    return value or "default"


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    match = FRONTMATTER_RE.match(text)
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

    return meta, text[match.end() :]


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
    if len(parts) >= 2 and parts[0].lower() == "20 projects":
        return slugify(parts[1])
    return ""


def value_matches(value: str, expected: str) -> bool:
    if not expected:
        return True
    return slugify(value) == slugify(expected)


def should_include_document(rel_path: str, text: str) -> bool:
    meta, body = parse_frontmatter(text)
    include_filter = os.getenv("LMSTUDIO_INCLUDE", "").strip().lower()
    scope_filter = os.getenv("LMSTUDIO_SCOPE", "all").strip().lower()
    project_filter = os.getenv("LMSTUDIO_PROJECT", "").strip()

    exclude_flag = str(meta.get("lightrag_exclude", "")).strip().lower()
    index_flag = str(meta.get("index", "")).strip().lower()
    if exclude_flag in {"1", "true", "yes"} or index_flag in {"0", "false", "no"}:
        return False

    searchable = f"{rel_path}\n{body}".lower()
    if include_filter and include_filter not in searchable:
        return False

    scope = infer_scope(rel_path, meta)
    if scope_filter not in ("", "all", "*") and scope != scope_filter:
        return False

    if project_filter and not value_matches(infer_project(rel_path, meta), project_filter):
        return False

    return True


def collect_markdown_documents(vault_dir: Path) -> list[dict[str, str]]:
    docs: list[dict[str, str]] = []
    for path in sorted(vault_dir.rglob("*.md")):
        rel = path.relative_to(vault_dir).as_posix()
        lowered_parts = {part.lower() for part in path.relative_to(vault_dir).parts}
        if ".obsidian" in lowered_parts or "_templates" in lowered_parts:
            continue

        text = path.read_text(encoding="utf-8-sig")
        if not should_include_document(rel, text):
            continue

        meta, _ = parse_frontmatter(text)
        scope = infer_scope(rel, meta)
        project = infer_project(rel, meta)
        header = [
            f"# Source: {rel}",
            f"Source scope: {scope}",
        ]
        if project:
            header.append(f"Source project: {project}")

        docs.append(
            {
                "path": str(path),
                "rel": rel,
                "text": "\n".join(header) + "\n\n" + text,
                "scope": scope,
                "project": project,
            }
        )

    return docs
