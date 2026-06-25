from __future__ import annotations

import argparse
import datetime as dt
import html
import re
import sys
import urllib.request
from pathlib import Path
from typing import Any

from knowledgelab.config import ROOT, VAULT_DIR
from knowledgelab.utils.text import clean_filename, compact_whitespace, yaml_quote
from vault_sources import slugify


def load_yt_dlp() -> Any:
    try:
        import yt_dlp  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError(
            "yt-dlp is not installed. Install it in LightRAG/.venv with: "
            "python -m pip install yt-dlp"
        ) from exc
    return yt_dlp


def fetch_video_info(url: str) -> dict[str, Any]:
    yt_dlp = load_yt_dlp()
    options = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
    }
    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=False)
    if not isinstance(info, dict):
        raise RuntimeError("yt-dlp returned an empty response.")
    return info


def language_candidates(language: str) -> list[str]:
    language = language.strip().lower()
    if language == "ru":
        return ["ru-orig", "ru"]
    if language and language != "auto":
        return [language]
    return ["ru-orig", "ru", "en"]


def track_candidates(
    info: dict[str, Any],
    language: str,
) -> list[tuple[str, str, dict[str, Any]]]:
    sources = [
        ("auto_captions", info.get("automatic_captions") or {}),
        ("captions", info.get("subtitles") or {}),
    ]
    preferred_langs = language_candidates(language)
    candidates: list[tuple[str, str, dict[str, Any]]] = []

    for method, tracks_by_lang in sources:
        if not isinstance(tracks_by_lang, dict):
            continue

        ordered_langs = [
            key
            for wanted in preferred_langs
            for key in tracks_by_lang
            if key.lower() == wanted or key.lower().startswith(f"{wanted}-")
        ]
        if not ordered_langs:
            ordered_langs = list(tracks_by_lang)

        for lang in ordered_langs:
            tracks = tracks_by_lang.get(lang)
            if not isinstance(tracks, list) or not tracks:
                continue
            vtt_tracks = [track for track in tracks if str(track.get("ext", "")).lower() == "vtt"]
            usable = vtt_tracks or tracks
            for track in usable:
                if isinstance(track, dict) and track.get("url"):
                    candidates.append((method, lang, track))
                    break

    return candidates


def pick_best_track(
    info: dict[str, Any],
    language: str,
) -> tuple[str, str, dict[str, Any], list[str]]:
    for method, lang, track in track_candidates(info, language):
        try:
            subtitle_text = download_text(str(track["url"]))
        except Exception as exc:
            print(f"Skipping subtitle track {lang}/{method}: {exc}", file=sys.stderr)
            continue
        lines = parse_vtt(subtitle_text)
        score = sum(len(line) for line in lines)
        if score > 0:
            return method, lang, track, lines

    raise RuntimeError(
        "No captions were found for this video. Next automation step: "
        "download audio and transcribe it with faster-whisper or whisper.cpp."
    )


def download_text(url: str) -> str:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def parse_vtt(text: str) -> list[str]:
    lines: list[str] = []
    previous = ""
    skip_note = False

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            skip_note = False
            continue
        if line.startswith("\ufeff"):
            line = line.lstrip("\ufeff").strip()
        if line == "WEBVTT" or line.startswith(("Kind:", "Language:", "STYLE")):
            continue
        if line.startswith("NOTE"):
            skip_note = True
            continue
        if skip_note:
            continue
        if "-->" in line:
            continue
        if re.fullmatch(r"\d+", line):
            continue

        line = re.sub(r"<[^>]+>", "", line)
        line = html.unescape(line)
        line = compact_whitespace(line)
        if not line or line == previous:
            continue
        previous = line
        lines.append(line)

    return lines


def paragraphs_from_lines(lines: list[str], max_chars: int = 900) -> list[str]:
    paragraphs: list[str] = []
    current: list[str] = []
    current_len = 0

    for line in lines:
        if current and current_len + len(line) + 1 > max_chars:
            paragraphs.append(compact_whitespace(" ".join(current)))
            current = []
            current_len = 0
        current.append(line)
        current_len += len(line) + 1

    if current:
        paragraphs.append(compact_whitespace(" ".join(current)))

    return paragraphs


def output_dir_for(vault_dir: Path, scope: str, project: str, out_dir: str) -> Path:
    if out_dir:
        return vault_dir / out_dir
    if scope == "game":
        project_slug = slugify(project or "my-game")
        return vault_dir / "20 Projects" / project_slug / "YouTube"
    if scope == "web":
        return vault_dir / "20 Projects" / "Web Development" / "Sources" / "YouTube"
    return vault_dir / "30 Sources" / "YouTube"


def render_markdown(
    info: dict[str, Any],
    url: str,
    scope: str,
    project: str,
    language: str,
    method: str,
    paragraphs: list[str],
) -> str:
    title = str(info.get("title") or "YouTube video")
    video_id = str(info.get("id") or "")
    channel = str(info.get("channel") or info.get("uploader") or "")
    webpage_url = str(info.get("webpage_url") or url)
    upload_date = str(info.get("upload_date") or "")
    published_at = ""
    if re.fullmatch(r"\d{8}", upload_date):
        published_at = f"{upload_date[0:4]}-{upload_date[4:6]}-{upload_date[6:8]}"

    captured_at = dt.datetime.now().replace(microsecond=0).isoformat()
    frontmatter = [
        "---",
        "type: youtube_transcript",
        "source: youtube",
        f"source_url: {yaml_quote(webpage_url)}",
        f"video_id: {yaml_quote(video_id)}",
        f"title: {yaml_quote(title)}",
        f"channel: {yaml_quote(channel)}",
        f"published_at: {yaml_quote(published_at)}",
        f"captured_at: {yaml_quote(captured_at)}",
        f"language: {yaml_quote(language)}",
        f"scope: {scope}",
        f"project: {yaml_quote(project)}",
        f"transcript_method: {yaml_quote(method)}",
        "tags: [source/youtube, imported/youtube]",
        "---",
        "",
    ]
    body = [
        f"# {title}",
        "",
        f"Source: {webpage_url}",
    ]
    if channel:
        body.append(f"Channel: {channel}")
    if published_at:
        body.append(f"Published: {published_at}")
    body.extend(["", "## Transcript", ""])
    body.extend(paragraphs)
    return "\n".join(frontmatter + body).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import a YouTube caption transcript into the Obsidian vault."
    )
    parser.add_argument("--url", required=True, help="YouTube video URL")
    parser.add_argument("--scope", default="general", choices=["general", "game", "web"])
    parser.add_argument("--project", default="", help="Project id for project scopes")
    parser.add_argument("--language", default="auto", help="Caption language, e.g. auto, ru, en")
    parser.add_argument(
        "--vault-dir",
        default=str(VAULT_DIR),
        help="Obsidian vault folder. Defaults to the project test vault.",
    )
    parser.add_argument(
        "--out-dir",
        default="",
        help="Output folder inside the vault. Defaults by scope.",
    )
    parser.add_argument("--overwrite", action="store_true", help="Overwrite an existing note")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    url = args.url.strip()
    if not url:
        raise SystemExit("--url is required")

    vault_dir = Path(args.vault_dir).expanduser().resolve()
    if not vault_dir.exists():
        raise SystemExit(f"Vault folder was not found: {vault_dir}")

    info = fetch_video_info(url)
    method, detected_language, track, transcript_lines = pick_best_track(info, args.language)
    paragraphs = paragraphs_from_lines(transcript_lines)
    if not paragraphs:
        raise SystemExit("Transcript was downloaded, but no readable text was extracted.")

    title = str(info.get("title") or "YouTube video")
    video_id = str(info.get("id") or "video")
    output_root = output_dir_for(vault_dir, args.scope, args.project, args.out_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    file_path = output_root / f"{clean_filename(title)} [{video_id}].md"
    if file_path.exists() and not args.overwrite:
        print(f"Already exists: {file_path.relative_to(vault_dir).as_posix()}")
        print("Use --overwrite to refresh the transcript.")
        return

    markdown = render_markdown(
        info=info,
        url=url,
        scope=args.scope,
        project=args.project if args.scope in {"game", "web"} else "",
        language=detected_language,
        method=method,
        paragraphs=paragraphs,
    )
    file_path.write_text(markdown, encoding="utf-8-sig")

    print(f"Imported YouTube transcript: {title}")
    print(f"- {file_path.relative_to(vault_dir).as_posix()}")
    print(f"Language: {detected_language}")
    print(f"Method: {method}")
    print(f"Paragraphs: {len(paragraphs)}")


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
