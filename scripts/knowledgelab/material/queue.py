from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

from knowledgelab.config import MATERIAL_QUEUE_PATH, RLM_QUEUE_PATH, VIDEO_PROCESSING_DIR
from knowledgelab.utils.text import now_iso
from knowledgelab.vault.capture import extraction_label
from knowledgelab.material.video import video_source_id


def read_jsonl_queue(path: Path | str) -> list[dict[str, object]]:
    path = Path(path)
    if not path.exists():
        return []
    items: list[dict[str, object]] = []
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict):
            items.append(item)
    return items


def append_jsonl_queue(path: Path | str, item: dict[str, object]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(item, ensure_ascii=False) + "\n")


def remove_from_jsonl_queue(path: Path | str, predicate: Callable[[dict[str, object]], bool]) -> int:
    path = Path(path)
    if not path.exists():
        return 0
    items = read_jsonl_queue(path)
    remaining = [item for item in items if not predicate(item)]
    removed_count = len(items) - len(remaining)
    path.write_text(
        "\n".join(json.dumps(item, ensure_ascii=False) for item in remaining) + ("\n" if remaining else ""),
        encoding="utf-8",
    )
    return removed_count


def queue_file_item(
    file_path: Path,
    rel_path: str,
    kind: str,
    scope: str,
    project: str,
    topic: str,
    extraction_status: str,
    layer: str = "active",
    project_title: str = "",
    project_section: str = "",
    source_root: Path | None = None,
    source_relative_path: str = "",
    project_action_id: str = "",
    book_title: str = "",
    page_number_guess: str = "",
) -> None:
    item = {
        "queued_at": now_iso(),
        "source_path": str(file_path),
        "source_root": str(source_root) if source_root else "",
        "source_relative_path": source_relative_path,
        "vault_note": rel_path,
        "kind": kind,
        "scope": scope,
        "project": project,
        "layer": layer,
        "project_title": project_title,
        "project_section": project_section,
        "project_action_id": project_action_id,
        "book_title": book_title,
        "page_number_guess": page_number_guess,
        "ocr_status": "pending" if kind in {"book_photo", "book_page_photo", "bookshelf_photo"} else "",
        "bookshelf_detection_status": "pending" if kind == "bookshelf_photo" else "",
        "detected_books": [] if kind == "bookshelf_photo" else "",
        "transcript_status": "pending_asr" if kind == "video_file" else "",
        "frame_analysis_status": "queued" if kind == "video_file" else "",
        "video_processing_workspace": str(VIDEO_PROCESSING_DIR / video_source_id(str(file_path))) if kind == "video_file" else "",
        "topic": topic,
        "status": "queued",
        "extraction_status": extraction_status,
        "planned_processing": extraction_label(kind),
    }
    append_jsonl_queue(MATERIAL_QUEUE_PATH, item)


def queue_github_item(
    url: str,
    rel_path: str,
    scope: str,
    project: str,
    topic: str,
    metadata: dict[str, str],
    layer: str = "active",
    project_title: str = "",
    project_section: str = "",
    project_action_id: str = "",
) -> None:
    item = {
        "queued_at": now_iso(),
        "source_path": "",
        "source_url": url,
        "vault_note": rel_path,
        "kind": "github_repository",
        "scope": scope,
        "project": project,
        "layer": layer,
        "project_title": project_title,
        "project_section": project_section,
        "project_action_id": project_action_id,
        "topic": topic,
        "status": "queued",
        "extraction_status": "pending",
        "planned_processing": extraction_label("github_repository"),
    }
    item.update({key: value for key, value in metadata.items() if value})
    append_jsonl_queue(MATERIAL_QUEUE_PATH, item)


def queue_rlm_item(
    rel_path: str,
    source_url: str,
    scope: str,
    project: str,
    layer: str,
    profile: dict[str, object],
) -> None:
    item = {
        "queued_at": now_iso(),
        "vault_note": rel_path,
        "source_url": source_url,
        "scope": scope,
        "project": project,
        "layer": layer,
        "rlm_type": "recursive_language_model",
        "status": "queued",
        "profile": profile,
        "planned_processing": "RLM REPL-style decomposition over long context snippets",
    }
    append_jsonl_queue(RLM_QUEUE_PATH, item)


def build_rlm_context_profile(text: str, source_name: str) -> dict[str, object]:
    lines = text.splitlines()
    non_empty_lines = sum(1 for line in lines if line.strip())
    approx_tokens = max(1, len(text) // 4)
    needs_rlm = len(text) >= 12000
    return {
        "source_name": source_name,
        "approx_tokens": approx_tokens,
        "non_empty_lines": non_empty_lines,
        "char_count": len(text),
        "needs_rlm": needs_rlm,
    }


def material_queue_display_path() -> str:
    try:
        return MATERIAL_QUEUE_PATH.relative_to(Path(__file__).resolve().parents[3]).as_posix()
    except ValueError:
        return str(MATERIAL_QUEUE_PATH)


def material_queue_summary(path: Path | str = MATERIAL_QUEUE_PATH) -> str:
    items = read_jsonl_queue(path)
    if not items:
        return "empty"
    return f"{len(items)} items queued"


def run_background_material_command(command: list[str], log_name: str, cwd: Path | None = None) -> tuple[bool, str]:
    import re
    import subprocess
    from knowledgelab.config import ROOT
    log_dir = ROOT / "tmp"
    log_dir.mkdir(parents=True, exist_ok=True)
    safe_name = re.sub(r"[^a-z0-9_-]+", "-", log_name.lower()).strip("-") or "material"
    log_path = log_dir / f"{safe_name}.log"
    err_path = log_dir / f"{safe_name}.err.log"
    try:
        with log_path.open("a", encoding="utf-8") as stdout, err_path.open("a", encoding="utf-8") as stderr:
            process = subprocess.Popen(
                command,
                cwd=str(cwd or ROOT),
                stdout=stdout,
                stderr=stderr,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            code = process.wait(timeout=240)
        if code == 0:
            return True, str(log_path)
        return False, f"код {code}; лог: {err_path}"
    except Exception as exc:
        return False, str(exc)


def launch_reindex_command(route) -> list[str]:
    import subprocess
    from knowledgelab.config import SCRIPTS_DIR, ROOT
    index_route = route.for_finished_index()
    command = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(SCRIPTS_DIR / "ingest-vault-scope-lmstudio.ps1"),
        "-Scope",
        index_route.scope,
        "-Layer",
        index_route.layer,
    ]
    if index_route.project:
        command.extend(["-Project", index_route.project])
    return command


def launch_reindex(route) -> None:
    import subprocess
    from knowledgelab.config import ROOT
    command = launch_reindex_command(route)
    env = dict(os.environ)
    try:
        subprocess.Popen(
            command,
            cwd=str(ROOT),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            env=env,
        )
    except Exception:
        pass
