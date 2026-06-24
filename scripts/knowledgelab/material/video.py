"""Video analysis — frame extraction, vision calls, note writing."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import urllib.request
from pathlib import Path

from knowledgelab.config import (
    MATERIAL_QUEUE_PATH,
    ROOT,
    VAULT_DIR,
    VIDEO_FRAME_INTERVAL_SECONDS,
    VIDEO_FRAME_LIMIT,
    VIDEO_PROCESSING_DIR,
)
from knowledgelab.models import KnowledgeRoute, VideoAnalysisReport
from knowledgelab.utils.text import yaml_quote, compact_whitespace, now_iso, extract_json_object, slugify
from knowledgelab.vault.capture import capture_destination, unique_path
from knowledgelab.vision.book_discovery import image_data_url


def video_source_id(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8", errors="ignore")).hexdigest()[:16]


def video_runtime_dir(source: str) -> Path:
    return VIDEO_PROCESSING_DIR / video_source_id(source)


def parse_video_frame_response(text: str) -> dict[str, object]:
    text = text.strip()
    if not text:
        return {}
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return {}
    try:
        parsed = json.loads(match.group(0))
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def format_video_analysis_report(report: VideoAnalysisReport) -> str:
    lines = [
        "Отчёт по видео:",
        f"- Родительская заметка: {report.parent_note}",
        f"- Analysis note: {report.analysis_note}",
        f"- Transcript: {report.transcript_status}",
        f"- Frames: {report.frame_analysis_status}",
        f"- Кадров обработано: {report.frame_count}",
        f"- Code/text snippets: {report.code_snippet_count}",
    ]
    if report.warning:
        lines.append(f"- Внимание: {report.warning}")
    return "\n".join(lines)


def render_video_analysis_markdown(
    source: str,
    kind: str,
    rel_path: str,
    route: KnowledgeRoute,
    transcript_status: str,
    frame_analysis_status: str,
    runtime_dir: Path,
    frame_results: list[dict[str, object]],
    warning: str = "",
) -> str:
    source_label = "YouTube" if kind == "youtube_link" else "video file"
    frontmatter = [
        "---",
        "type: video_analysis",
        f"source_kind: {kind}",
        f"source: {yaml_quote(source)}",
        f"source_label: {yaml_quote(source_label)}",
        f"scope: {route.scope}",
        f"project: {yaml_quote(route.project)}",
        f"layer: {route.layer}",
        f"parent_note: {yaml_quote(rel_path)}",
        f"transcript_status: {yaml_quote(transcript_status)}",
        f"frame_analysis_status: {yaml_quote(frame_analysis_status)}",
        f"frame_count: {len(frame_results)}",
        f"captured_at: {yaml_quote(now_iso())}",
        f"runtime_workspace: {yaml_quote(str(runtime_dir))}",
        "tags: [video/analysis]",
        "---",
        "",
        f"# Video Analysis",
        "",
        f"- Source: {source}",
        f"- Source kind: {source_label}",
        f"- Parent note: [[{rel_path}]]",
        f"- Transcript status: {transcript_status}",
        f"- Frame analysis status: {frame_analysis_status}",
        f"- Frames analyzed: {len(frame_results)}",
    ]
    if warning:
        frontmatter.append(f"- Warning: {warning}")
    frontmatter.append("")
    if frame_results:
        frontmatter.append("## Frame Analysis")
        frontmatter.append("")
        for frame in frame_results:
            frame_name = str(frame.get("frame") or "unknown")
            summary = str(frame.get("summary") or "").strip()
            visible_text = str(frame.get("visible_text") or "").strip()
            code = str(frame.get("code") or "").strip()
            importance = str(frame.get("importance") or "low").strip()
            frontmatter.append(f"### Frame: {frame_name}")
            frontmatter.append("")
            if summary:
                frontmatter.append(f"Summary: {summary}")
            if importance and importance != "low":
                frontmatter.append(f"Importance: {importance}")
            if visible_text:
                frontmatter.append("")
                frontmatter.append("Visible text:")
                frontmatter.append("")
                frontmatter.append(f"```text\n{visible_text}\n```")
            if code:
                frontmatter.append("")
                frontmatter.append("Code / commands:")
                frontmatter.append("")
                frontmatter.append(f"```\n{code}\n```")
            frontmatter.append("")
    elif warning:
        frontmatter.append(f"_Warning: {warning}_")
        frontmatter.append("")
    return "\n".join(frontmatter)


def extract_video_frames(source_path: Path, runtime_dir: Path) -> tuple[list[Path], str]:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return [], "pending_needs_ffmpeg"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    output_pattern = runtime_dir / "frame_%04d.jpg"
    command = [
        ffmpeg,
        "-y",
        "-i",
        str(source_path),
        "-vf",
        f"fps=1/{VIDEO_FRAME_INTERVAL_SECONDS},scale=1280:-1:force_original_aspect_ratio=decrease",
        "-frames:v",
        str(VIDEO_FRAME_LIMIT),
        str(output_pattern),
    ]
    try:
        result = subprocess.run(command, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
    except Exception as exc:
        return [], f"frame_extraction_failed: {exc}"
    if result.returncode != 0:
        return [], f"frame_extraction_failed: {(result.stderr or result.stdout).strip()[:500]}"
    return sorted(runtime_dir.glob("frame_*.jpg")), "frames_extracted"


def call_video_frame_vision(frame_path: Path, vision_model: str, vision_ready: bool, loaded_models: list[str], base_url: str, timeout: int) -> dict[str, object]:
    if not vision_ready:
        loaded = ", ".join(loaded_models) if loaded_models else "no loaded models"
        raise RuntimeError(f"no vision/VL model loaded in LM Studio; loaded={loaded}")
    prompt = (
        "Analyze this video frame for useful knowledge capture. Return strict JSON only.\n"
        "Focus on visible code, terminal text, UI labels, diagrams, slides, formulas, commands, and important screen text.\n"
        "If nothing useful is visible, return empty strings.\n\n"
        "{\n"
        "  \"summary\": \"short description\",\n"
        "  \"visible_text\": \"OCR-like visible text\",\n"
        "  \"code\": \"visible code or commands\",\n"
        "  \"importance\": \"low/medium/high\"\n"
        "}"
    )
    payload = {
        "model": vision_model,
        "messages": [
            {
                "role": "system",
                "content": "You extract useful screen text and code from video frames inside the local KnowledgeLab app. Return strict JSON only.",
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": image_data_url(frame_path)}},
                ],
            },
        ],
        "temperature": 0.0,
        "max_tokens": 1200,
        "stream": False,
    }
    url = f"{base_url}/chat/completions"
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json", "User-Agent": "KnowledgeLab/1.0"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=min(timeout, 180)) as response:
        raw_response = json.loads(response.read().decode("utf-8", errors="replace"))
    if raw_response.get("error"):
        raise RuntimeError(str(raw_response.get("error")))
    choice = (raw_response.get("choices") or [{}])[0]
    message = choice.get("message") if isinstance(choice, dict) else {}
    content = str((message.get("content") or "") if isinstance(message, dict) else "")
    reasoning = str((message.get("reasoning_content") or "") if isinstance(message, dict) else "")
    parsed = extract_json_object(content or reasoning)
    parsed["frame"] = frame_path.name
    return parsed


def write_video_analysis_note(
    source: str,
    rel_path: str,
    kind: str,
    route: KnowledgeRoute,
    runtime_dir: Path,
    transcript_status: str,
    frame_analysis_status: str,
    frame_results: list[dict[str, object]],
    vault_dir: Path = VAULT_DIR,
    warning: str = "",
) -> str:
    destination = capture_destination(route.scope, "Video Analysis", "video_file", route.layer, route.project, route.project_section)
    destination.mkdir(parents=True, exist_ok=True)
    path = unique_path(destination / f"Video Analysis {video_source_id(source)}.md")
    path.write_text(
        render_video_analysis_markdown(source, kind, rel_path, route, transcript_status, frame_analysis_status, runtime_dir, frame_results, warning),
        encoding="utf-8-sig",
    )
    analysis_rel_path = path.relative_to(vault_dir).as_posix()
    parent_path = vault_dir / rel_path.replace("/", os.sep)
    if parent_path.exists():
        parent_text = parent_path.read_text(encoding="utf-8-sig", errors="replace")
        parent_path.write_text(
            parent_text.rstrip()
            + "\n\n## Video Analysis\n\n"
            + f"- Analysis note: [[{analysis_rel_path}]]\n"
            + f"- Transcript status: {transcript_status}\n"
            + f"- Frame analysis status: {frame_analysis_status}\n",
            encoding="utf-8-sig",
        )
    return analysis_rel_path


def queue_video_analysis_item(source: str, rel_path: str, kind: str, route: KnowledgeRoute, runtime_dir: Path) -> None:
    MATERIAL_QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
    item = {
        "queued_at": now_iso(),
        "source_path": source if kind == "video_file" else "",
        "source_url": source if kind == "youtube_link" else "",
        "vault_note": rel_path,
        "kind": "video_analysis",
        "source_kind": kind,
        "scope": route.scope,
        "project": route.project,
        "layer": route.layer,
        "topic": "Video Analysis",
        "status": "queued",
        "transcript_status": "queued_youtube_caption_sync" if kind == "youtube_link" else "pending_asr",
        "frame_analysis_status": "queued",
        "runtime_workspace": str(runtime_dir),
        "planned_processing": "transcript plus sampled visual frame analysis for code/slides/important screen text",
    }
    with MATERIAL_QUEUE_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(item, ensure_ascii=False) + "\n")
