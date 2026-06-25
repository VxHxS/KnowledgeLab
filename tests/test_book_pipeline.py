from __future__ import annotations

from knowledgelab.config import DEFAULT_SETTINGS
from knowledgelab.models import BookDownloadResult, KnowledgeRoute
from knowledgelab.vision import book_pipeline


def test_process_book_image_no_vision_model_returns_failed(tmp_path):
    result = book_pipeline.process_book_image(
        image_path=tmp_path / "shelf.jpg",
        rel_path="00 Inbox/shelf.md",
        kind="bookshelf_photo",
        caption="",
        route=KnowledgeRoute("General", "general"),
        settings=DEFAULT_SETTINGS,
        vault_dir=tmp_path,
        vision_model="",
        vision_ready=False,
        loaded_models=["qwen/qwen3-14b"],
        base_url="http://127.0.0.1:1234/v1",
        timeout=30,
        update_parent=False,
    )
    assert result.status == "failed"
    assert result.report.not_found
    assert "vision" in result.error.lower() or "vision-модель" in result.error.lower()


def test_process_book_image_success_creates_added_report(monkeypatch, tmp_path):
    statuses: list[str] = []

    def fake_vision(*_args, **_kwargs):
        return {
            "detected_books": [{"title": "Clean Code", "author": "Robert C. Martin", "confidence": 0.91}],
            "unresolved": [],
        }

    def fake_enrich(books, book_lookup_enabled=True):
        enriched = [dict(books[0], lookup_status="found", book_topic="Programming")]
        return enriched, []

    def fake_download(book, **_kwargs):
        return BookDownloadResult(
            status="downloaded",
            reason="ok",
            source_name="gutenberg",
            url="https://example.test/book.epub",
            local_file_rel_path="50 Library/clean-code/Files/book.epub",
            file_name="book.epub",
            file_format="epub",
            size_bytes=10,
        )

    def fake_save(books, *_args, **_kwargs):
        books[0]["vault_note"] = "50 Library/clean-code/Book.md"
        return [books[0]["vault_note"]]

    monkeypatch.setattr(book_pipeline, "call_bookshelf_vision", fake_vision)
    monkeypatch.setattr(book_pipeline, "enrich_detected_books", fake_enrich)
    monkeypatch.setattr(book_pipeline, "resolve_legal_book_download", fake_download)
    monkeypatch.setattr(book_pipeline, "save_detected_book_notes", fake_save)
    monkeypatch.setattr(book_pipeline, "update_bookshelf_note_result", lambda *args, **kwargs: None)

    result = book_pipeline.process_book_image(
        image_path=tmp_path / "shelf.jpg",
        rel_path="00 Inbox/shelf.md",
        kind="bookshelf_photo",
        caption="",
        route=KnowledgeRoute("General", "general"),
        settings=DEFAULT_SETTINGS,
        vault_dir=tmp_path,
        vision_model="qwen2.5-vl",
        vision_ready=True,
        loaded_models=["qwen2.5-vl"],
        base_url="http://127.0.0.1:1234/v1",
        timeout=30,
        update_parent=True,
        on_status=statuses.append,
    )
    assert result.status == "done"
    assert result.created_notes == ["50 Library/clean-code/Book.md"]
    assert result.report.added[0]["download_status"] == "downloaded"
    assert result.report.added[0]["pipeline_status"] == "added"
    assert "saving book notes" in statuses


def test_dedupe_detected_books_keeps_unique_titles():
    books = [
        {"title": "Clean Code", "author": "Robert C. Martin", "evidence": "Clean Code"},
        {"title": "Clean Code", "author": "Robert C. Martin", "evidence": "Clean Code"},
        {"title": "The Pragmatic Programmer", "author": "Andrew Hunt", "evidence": "Pragmatic"},
    ]
    assert len(book_pipeline.dedupe_detected_books(books)) == 2
