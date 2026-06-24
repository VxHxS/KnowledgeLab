from __future__ import annotations

import json
from pathlib import Path

from knowledgelab.models import BackgroundTaskRecord
from knowledgelab.utils.text import now_iso


class BackgroundTaskManager:
    def __init__(self) -> None:
        self._tasks: dict[str, BackgroundTaskRecord] = {}

    def start_task(self, task_id: str, kind: str, label: str) -> BackgroundTaskRecord:
        record = BackgroundTaskRecord(
            task_id=task_id,
            kind=kind,
            label=label,
            status="running",
            started_at=now_iso(),
            updated_at=now_iso(),
        )
        self._tasks[task_id] = record
        return record

    def update_task(self, task_id: str, **kwargs: object) -> None:
        record = self._tasks.get(task_id)
        if record is None:
            return
        for key, value in kwargs.items():
            if hasattr(record, key):
                setattr(record, key, value)
        record.updated_at = now_iso()

    def get_task(self, task_id: str) -> BackgroundTaskRecord | None:
        return self._tasks.get(task_id)

    def get_all_tasks(self) -> list[BackgroundTaskRecord]:
        return list(self._tasks.values())

    def get_running_tasks(self) -> list[BackgroundTaskRecord]:
        return [t for t in self._tasks.values() if t.status == "running"]

    def compact_tasks(self) -> list[BackgroundTaskRecord]:
        tasks = sorted(self._tasks.values(), key=lambda item: item.updated_at or item.started_at, reverse=True)
        running = [task for task in tasks if task.status == "running"]
        recent = [task for task in tasks if task.status != "running"][:5]
        return running + recent


def compact_background_tasks_from_dict(background_tasks: dict[str, BackgroundTaskRecord]) -> list[BackgroundTaskRecord]:
    tasks = sorted(background_tasks.values(), key=lambda item: item.updated_at or item.started_at, reverse=True)
    running = [task for task in tasks if task.status == "running"]
    recent = [task for task in tasks if task.status != "running"][:5]
    return running + recent


def material_queue_summary(path: Path | str | None = None) -> str:
    if path is None:
        from knowledgelab.config import MATERIAL_QUEUE_PATH
        path = MATERIAL_QUEUE_PATH
    path = Path(path)
    if not path.exists():
        return "empty"
    counts: dict[str, int] = {}
    status_counts: dict[str, int] = {}
    total = 0
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip():
                continue
            total += 1
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            kind = str(item.get("kind") or "unknown")
            status = str(item.get("status") or "queued")
            counts[kind] = counts.get(kind, 0) + 1
            status_counts[status] = status_counts.get(status, 0) + 1
    except OSError as exc:
        return f"unavailable: {exc}"
    kind_text = ", ".join(f"{key}:{value}" for key, value in sorted(counts.items())) or "none"
    status_text = ", ".join(f"{key}:{value}" for key, value in sorted(status_counts.items())) or "none"
    return f"total={total}; statuses={status_text}; kinds={kind_text}"


def project_server_summary(project_actions: dict) -> str:
    actions = project_actions.get("actions") if isinstance(project_actions, dict) else {}
    if not isinstance(actions, dict) or not actions:
        return "none"
    from knowledgelab.tasks.project_actions import is_process_running
    running: list[str] = []
    stopped = 0
    for action_id, action in actions.items():
        if not isinstance(action, dict):
            continue
        server = action.get("server") if isinstance(action.get("server"), dict) else {}
        pid = int(server.get("pid") or 0)
        url = str(server.get("url") or "")
        if pid and is_process_running(pid):
            running.append(f"{action_id} -> {url or 'local server'} pid={pid}")
        elif pid:
            stopped += 1
    if running:
        return "; ".join(running[:4])
    return f"none running; stopped_records={stopped}"


def latest_book_discovery_summary(last_report) -> str:
    if not last_report:
        return "none in this chat session"
    return (
        f"parent={last_report.parent_note}; added={len(last_report.added)}; "
        f"needs_clarification={len(last_report.needs_clarification)}; not_found={len(last_report.not_found)}"
    )
