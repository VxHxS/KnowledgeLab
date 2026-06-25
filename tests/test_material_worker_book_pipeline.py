from __future__ import annotations

from pathlib import Path

from knowledgelab.config import DEFAULT_SETTINGS
from knowledgelab.material import workers
from knowledgelab.models import BookDiscoveryReport, BookPipelineResult, KnowledgeRoute


class _Root:
    def after(self, _delay, callback, *args):
        callback(*args)


class _FakeApp:
    def __init__(self, vault_dir: Path):
        self.root = _Root()
        self.settings = dict(DEFAULT_SETTINGS)
        self.query_timeout_seconds = 600
        self.task_updates: list[dict[str, str]] = []
        self.reports: list[BookDiscoveryReport] = []
        self._vault_dir = vault_dir

    def vision_model_state(self):
        return "qwen2.5-vl", True, ["qwen2.5-vl"]

    def lmstudio_base_url(self):
        return "http://127.0.0.1:1234/v1"

    def vault_dir(self):
        return self._vault_dir

    def update_background_task(self, task_id, **kwargs):
        self.task_updates.append({"task_id": task_id, **kwargs})

    def append_book_discovery_report(self, report):
        self.reports.append(report)

    def append_warning_message(self, *_args, **_kwargs):
        pass


def test_book_image_worker_delegates_to_pipeline(monkeypatch, tmp_path):
    captured: dict[str, object] = {}
    launch_calls: list[KnowledgeRoute] = []

    def fake_pipeline(**kwargs):
        captured.update(kwargs)
        report = BookDiscoveryReport(
            "00 Inbox/shelf.md",
            added=[{"title": "Clean Code", "vault_note": "50 Library/clean-code/Book.md"}],
            needs_clarification=[],
            not_found=[],
        )
        return BookPipelineResult(
            status="done",
            detection_result={"detected_books": report.added, "unresolved": []},
            created_notes=["50 Library/clean-code/Book.md"],
            report=report,
            parent_note_updated=True,
        )

    monkeypatch.setattr(workers, "process_book_image", fake_pipeline)
    monkeypatch.setattr(workers, "launch_reindex", lambda route: launch_calls.append(route))

    app = _FakeApp(tmp_path)
    manager = workers.MaterialWorkerManager(app)
    route = KnowledgeRoute("General", "general")
    manager.auto_process_book_image_worker(
        str(tmp_path / "shelf.jpg"),
        "00 Inbox/shelf.md",
        "bookshelf_photo",
        "",
        route,
        "task-1",
    )

    assert captured["vision_model"] == "qwen2.5-vl"
    assert captured["base_url"] == "http://127.0.0.1:1234/v1"
    assert captured["settings"] == app.settings
    assert captured["vault_dir"] == tmp_path
    assert app.reports[0].added[0]["title"] == "Clean Code"
    assert launch_calls == [route]
    assert app.task_updates[-1]["status"] == "done"
