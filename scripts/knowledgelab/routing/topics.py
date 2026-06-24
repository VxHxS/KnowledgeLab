from __future__ import annotations

import re
from pathlib import Path

from knowledgelab.config import TOPICS, LAYER_ACTIVE, LAYER_FINISHED_PROJECTS, VAULT_DIR
from knowledgelab.utils.text import yaml_quote, clean_filename, slugify, now_iso, compact_whitespace
from knowledgelab.vault.frontmatter import parse_basic_frontmatter


def builtin_topic_names() -> set[str]:
    names = {name for name, _terms in TOPICS}
    names.update({"General", "Web", "Project Notes", "Library", "Programming", "Game Development", "Problem Solving", "Design"})
    return names


def collect_topic_registry(vault_dir: Path) -> set[str]:
    topics = set(builtin_topic_names())
    if not vault_dir.exists():
        return topics
    for topic_dir in vault_dir.rglob("Topics"):
        if topic_dir.is_dir():
            try:
                topics.update(child.name for child in topic_dir.iterdir() if child.is_dir())
            except OSError:
                pass
    for path in vault_dir.rglob("*.md"):
        try:
            meta = parse_basic_frontmatter(path.read_text(encoding="utf-8-sig", errors="replace"))
        except (OSError, UnicodeError, ValueError):
            continue
        topic = str(meta.get("topic") or meta.get("book_topic") or "").strip()
        if topic:
            topics.add(topic)
    return topics


def topic_note_path(scope: str, topic: str, project: str = "") -> Path:
    safe_topic = clean_filename(topic or "Unsorted")
    safe_project = slugify(project) if project else ""
    if safe_project and safe_project not in {"web-development", "my-game"}:
        return VAULT_DIR / "20 Projects" / clean_filename(safe_project) / "Topics" / safe_topic / "_Topic.md"
    if scope == "web":
        return VAULT_DIR / "20 Projects" / "Web Development" / "Topics" / safe_topic / "_Topic.md"
    if scope == "game":
        return VAULT_DIR / "20 Projects" / "My Game" / "Topics" / safe_topic / "_Topic.md"
    if scope == "library":
        return VAULT_DIR / "50 Library" / "Topics" / safe_topic / "_Topic.md"
    return VAULT_DIR / "10 General Knowledge" / "Topics" / safe_topic / "_Topic.md"


def render_topic_note_markdown(topic: str, scope: str, project: str = "") -> str:
    return "\n".join([
        "---",
        "type: topic",
        f"topic: {yaml_quote(topic)}",
        f"scope: {yaml_quote(scope)}",
        f"project: {yaml_quote(project)}",
        f"created_at: {yaml_quote(now_iso())}",
        "created_by: KnowledgeLab auto-topic",
        "---",
        "",
        f"# {topic}",
        "",
        "Auto-created topic registry note. Materials can link here through frontmatter and folder placement.",
        "",
    ])


def infer_note_layer_from_path(rel_path: str, meta: dict[str, str]) -> str:
    layer = meta.get("layer", "").strip().lower()
    if layer:
        return layer
    return LAYER_FINISHED_PROJECTS if rel_path.lower().startswith("40 finished projects/") else LAYER_ACTIVE


def infer_note_scope_from_path(rel_path: str, meta: dict[str, str]) -> str:
    scope = meta.get("scope", "").strip().lower()
    if scope:
        return scope
    normalized = rel_path.lower()
    if normalized.startswith("20 projects/web development/"):
        return "web"
    if normalized.startswith("20 projects/"):
        return "game"
    return "general"


def classify_material_topic(
    text: str,
    scope: str,
    kind: str,
    fallback_topic: str = "",
    preferred_topic: str = "",
    project: str = "",
    auto_route: bool = True,
    auto_create: bool = True,
    vault_dir: Path = VAULT_DIR,
) -> str:
    if not auto_route:
        return fallback_topic
    if kind in {"book_photo", "book_page_photo", "bookshelf_photo"} and preferred_topic:
        topic = preferred_topic
    else:
        from knowledgelab.routing.intent import infer_topic
        inferred = infer_topic(text, scope)
        topic = inferred if inferred and inferred != "General" else (preferred_topic or fallback_topic or ("Web" if scope == "web" else "Project Notes" if scope == "game" else "General"))
    if auto_create:
        ensure_topic_exists(topic, scope, project, vault_dir)
    return topic


def ensure_topic_exists(topic: str, scope: str = "general", project: str = "", vault_dir: Path = VAULT_DIR) -> bool:
    topic = compact_whitespace(topic)
    if not topic or topic in {"General", "Web", "Project Notes"}:
        return False
    if topic in collect_topic_registry(vault_dir):
        return False
    path = topic_note_path(scope, topic, project)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return False
    path.write_text(render_topic_note_markdown(topic, scope, project), encoding="utf-8-sig")
    return True
