from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from knowledgelab.config import ROOT, VAULT_DIR
from vault_sources import ACTIVE_LAYER, infer_layer, infer_project, infer_scope, parse_frontmatter
MATERIAL_QUEUE_PATH = Path(os.getenv("KNOWLEDGELAB_MATERIAL_QUEUE_PATH", str(ROOT / "tmp" / "material-processing-queue.jsonl")))
YOUTUBE_URL_RE = re.compile(
    r"https?://(?:www\.)?(?:youtube\.com/watch\?[^\s<>)\]]+|youtu\.be/[^\s<>)\]]+)",
    re.IGNORECASE,
)
PROGRAMMING_TOPICS = {
    "architecture",
    "coding",
    "dependency-injection",
    "di",
    "frontend",
    "html",
    "javascript",
    "programming",
    "react",
    "typescript",
    "unity",
    "web",
    "zenject",
}
MUSIC_TOPICS = {"audio", "mastering", "mixing", "music", "sound"}


def normalize_url(url: str) -> str:
    return url.rstrip(".,;)]}>\"'")


def youtube_video_id(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if host.endswith("youtu.be"):
        return parsed.path.strip("/").split("/", 1)[0]
    if "youtube.com" in host:
        return parse_qs(parsed.query).get("v", [""])[0]
    return ""


def clean_path_segment(value: str, fallback: str = "Imported") -> str:
    value = value.strip()
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "-", value)
    value = re.sub(r"\s+", " ", value).strip(" .-")
    return value or fallback


def tag_values(meta: dict[str, object]) -> list[str]:
    tags = meta.get("tags", [])
    if isinstance(tags, str):
        return [tags]
    if isinstance(tags, list):
        return [str(tag) for tag in tags]
    return []


def topic_tags(meta: dict[str, object]) -> list[str]:
    topics: list[str] = []
    for tag in tag_values(meta):
        tag = tag.strip().lower()
        if tag.startswith("topic/"):
            topics.append(tag.split("/", 1)[1])
    return topics


def humanize_topic(value: str) -> str:
    value = value.strip().strip("#")
    if "/" in value:
        value = value.rsplit("/", 1)[1]
    value = value.replace("_", " ").replace("-", " ")
    words = [word for word in value.split() if word]
    if not words:
        return "Imported"
    known = {"di": "DI", "ui": "UI", "ux": "UX"}
    return " ".join(known.get(word.lower(), word[:1].upper() + word[1:]) for word in words)


def infer_topic(meta: dict[str, object], rel_path: str) -> str:
    raw_topic = str(meta.get("topic", "")).strip()
    if raw_topic:
        return clean_path_segment(humanize_topic(raw_topic))

    for tag_topic in topic_tags(meta):
        if tag_topic not in {"unity", "programming", "youtube"}:
            return clean_path_segment(humanize_topic(tag_topic))
    for tag_topic in topic_tags(meta):
        return clean_path_segment(humanize_topic(tag_topic))

    parts = rel_path.replace("\\", "/").split("/")
    for part in reversed(parts[:-1]):
        if part and not re.match(r"^\d+\s+", part) and part.lower() not in {"sources", "youtube links"}:
            return clean_path_segment(part)
    return "Imported"


def infer_area(meta: dict[str, object], rel_path: str) -> str:
    raw_area = str(meta.get("area", "")).strip().lower()
    if raw_area in {"programming", "code", "coding", "unity"}:
        return "10 Programming"
    if raw_area in {"music", "audio"}:
        return "20 Music"
    if raw_area in {"general", "knowledge"}:
        return "10 General Knowledge"

    normalized = rel_path.replace("\\", "/").lower()
    if normalized.startswith("10 programming/"):
        return "10 Programming"
    if normalized.startswith("20 music/"):
        return "20 Music"
    if normalized.startswith("10 general knowledge/"):
        return "10 General Knowledge"

    tag_set = set(topic_tags(meta))
    if tag_set & PROGRAMMING_TOPICS:
        return "10 Programming"
    if tag_set & MUSIC_TOPICS:
        return "20 Music"
    return "10 General Knowledge"


def route_out_dir(meta: dict[str, object], rel_path: str, scope: str, project: str) -> str:
    if scope == "game":
        project_name = clean_path_segment(project or "my-game", "my-game")
        return f"20 Projects/{project_name}/Sources/YouTube"
    if scope == "web":
        project_name = clean_path_segment(project or "Web Development", "Web Development")
        if project_name.lower() in {"web", "web-dev", "web-development", "frontend"}:
            project_name = "Web Development"
        return f"20 Projects/{project_name}/Sources/YouTube"

    area = infer_area(meta, rel_path)
    topic = infer_topic(meta, rel_path)
    return f"{area}/{topic}/Sources/YouTube"


def should_skip_note(meta: dict[str, object], rel_path: str) -> bool:
    source = str(meta.get("source", "")).strip().lower()
    note_type = str(meta.get("type", "")).strip().lower()
    normalized = rel_path.replace("\\", "/").lower()
    return (
        source == "youtube"
        or note_type == "youtube_transcript"
        or normalized.startswith("30 sources/youtube transcripts/")
    )


def is_marked_youtube_link_note(meta: dict[str, object], rel_path: str) -> bool:
    source = str(meta.get("source", "")).strip().lower()
    note_type = str(meta.get("type", "")).strip().lower()
    normalized = rel_path.replace("\\", "/").lower()

    return (
        source == "youtube_link"
        or note_type == "youtube_link"
        or normalized.startswith("30 sources/youtube links/")
        or "source/youtube" in {tag.strip().lower() for tag in tag_values(meta)}
    )


def iter_markdown_notes(vault_dir: Path) -> list[Path]:
    paths: list[Path] = []
    for path in sorted(vault_dir.rglob("*.md")):
        parts = {part.lower() for part in path.relative_to(vault_dir).parts}
        if ".obsidian" in parts or "_templates" in parts:
            continue
        paths.append(path)
    return paths


def collect_youtube_links(
    vault_dir: Path,
    scope_filter: str,
    project_filter: str,
    all_notes: bool,
) -> list[dict[str, str]]:
    found: dict[str, dict[str, str]] = {}
    for path in iter_markdown_notes(vault_dir):
        rel = path.relative_to(vault_dir).as_posix()
        text = path.read_text(encoding="utf-8-sig")
        meta, body = parse_frontmatter(text)
        if should_skip_note(meta, rel):
            continue
        if infer_layer(rel, meta) != ACTIVE_LAYER:
            continue
        if not all_notes and not is_marked_youtube_link_note(meta, rel):
            continue

        scope = infer_scope(rel, meta)
        project = infer_project(rel, meta)
        if scope_filter not in ("", "all", "*") and scope != scope_filter:
            continue
        if project_filter and project != project_filter:
            continue

        for raw_url in YOUTUBE_URL_RE.findall(body):
            url = normalize_url(raw_url)
            found.setdefault(
                url,
                {
                    "url": url,
                    "scope": scope if scope in ("general", "game", "web") else "general",
                    "project": project,
                    "source_note": rel,
                    "out_dir": route_out_dir(meta, rel, scope, project),
                    "video_id": youtube_video_id(url),
                },
            )
    return list(found.values())


def transcript_exists(vault_dir: Path, out_dir: str, video_id: str, url: str) -> bool:
    if not video_id and not url:
        return False
    root = vault_dir / out_dir
    if not root.exists():
        return False
    for path in root.rglob("*.md"):
        text = path.read_text(encoding="utf-8-sig")
        meta, _ = parse_frontmatter(text)
        if str(meta.get("source", "")).strip().lower() != "youtube":
            continue
        if video_id and str(meta.get("video_id", "")).strip() == video_id:
            return True
        if url and str(meta.get("source_url", "")).strip().startswith(url.split("&", 1)[0]):
            return True
    return False


def now_iso() -> str:
    import datetime as dt

    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def queue_youtube_asr_fallback(link: dict[str, str], vault_dir: Path, reason: str = "") -> None:
    MATERIAL_QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
    item = {
        "queued_at": now_iso(),
        "source_url": link["url"],
        "video_id": link.get("video_id", ""),
        "vault_note": link.get("source_note", ""),
        "kind": "youtube_asr_fallback",
        "scope": link.get("scope", "general"),
        "project": link.get("project", ""),
        "layer": ACTIVE_LAYER,
        "status": "queued",
        "transcript_status": "pending_asr",
        "frame_analysis_status": "queued_video_analysis",
        "out_dir": link.get("out_dir", ""),
        "vault_dir": str(vault_dir),
        "failure_reason": reason,
        "planned_processing": "download audio and transcribe with local ASR when a transcription worker is available",
    }
    with MATERIAL_QUEUE_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(item, ensure_ascii=False) + "\n")


def run_import(link: dict[str, str], vault_dir: Path, overwrite: bool) -> int:
    if not overwrite and transcript_exists(vault_dir, link["out_dir"], link["video_id"], link["url"]):
        print(f"Already synced YouTube transcript: {link['url']}")
        print(f"Destination: {link['out_dir']}")
        return 0

    command = [
        sys.executable,
        str(ROOT / "scripts" / "import-youtube-transcript.py"),
        "--url",
        link["url"],
        "--scope",
        link["scope"],
        "--vault-dir",
        str(vault_dir),
        "--out-dir",
        link["out_dir"],
    ]
    if link["project"]:
        command.extend(["--project", link["project"]])
    if overwrite:
        command.append("--overwrite")

    print(f"Sync YouTube: {link['url']}")
    print(f"Source note: {link['source_note']}")
    result = subprocess.run(command, cwd=str(ROOT), text=True, encoding="utf-8", errors="replace", capture_output=True)
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    if result.returncode != 0:
        queue_youtube_asr_fallback(link, vault_dir, (result.stderr or result.stdout).strip()[:600])
    return result.returncode


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scan Obsidian notes for YouTube links and import caption transcripts."
    )
    parser.add_argument("--vault-dir", default=str(VAULT_DIR), help="Obsidian vault folder")
    parser.add_argument("--scope", default="all", choices=["all", "general", "game", "web"])
    parser.add_argument("--project", default="", help="Project id filter for game scope")
    parser.add_argument("--overwrite", action="store_true", help="Refresh existing transcripts")
    parser.add_argument("--list-only", action="store_true", help="Print matching links and exit")
    parser.add_argument(
        "--all-notes",
        action="store_true",
        help="Scan every Markdown note, not only notes marked as YouTube links.",
    )
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Keep syncing other links if one video fails.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    vault_dir = Path(args.vault_dir).expanduser().resolve()
    if not vault_dir.exists():
        raise SystemExit(f"Vault folder was not found: {vault_dir}")

    project_filter = args.project.strip()
    if args.scope not in ("game", "web"):
        project_filter = ""

    links = collect_youtube_links(vault_dir, args.scope, project_filter, args.all_notes)
    if not links:
        print("No YouTube links found for this scope.")
        return

    if args.list_only:
        for link in links:
            print(f"{link['url']} [{link['scope']}] {link['source_note']} -> {link['out_dir']}")
        return

    failures = 0
    for link in links:
        code = run_import(link, vault_dir, args.overwrite)
        if code != 0:
            failures += 1
            if not args.continue_on_error:
                raise SystemExit(code)

    if failures and not args.continue_on_error:
        raise SystemExit(f"{failures} YouTube link(s) failed to sync.")
    if failures:
        print(f"WARNING: {failures} YouTube link(s) failed to sync.")


if __name__ == "__main__":
    os.environ.setdefault("PYTHONUTF8", "1")
    main()
