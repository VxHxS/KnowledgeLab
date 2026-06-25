from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from knowledgelab.config import DEFAULT_SETTINGS, VAULT_DIR
from knowledgelab.models import BookDiscoveryReport, BookDownloadResult, BookPipelineResult, KnowledgeRoute
from knowledgelab.vision.book_discovery import (
    call_bookshelf_vision,
    enrich_detected_books,
    save_detected_book_notes,
    update_bookshelf_note_result,
)
from knowledgelab.vision.book_downloads import apply_download_result, resolve_legal_book_download


StatusCallback = Callable[[str], None]


def setting_bool(settings: dict[str, object], key: str) -> bool:
    return bool(settings.get(key, DEFAULT_SETTINGS.get(key)))


def setting_int(settings: dict[str, object], key: str) -> int:
    try:
        return int(settings.get(key, DEFAULT_SETTINGS.get(key)) or DEFAULT_SETTINGS.get(key) or 0)
    except (TypeError, ValueError):
        return int(DEFAULT_SETTINGS.get(key) or 0)


def dedupe_detected_books(books: list[dict[str, object]]) -> list[dict[str, object]]:
    seen: set[tuple[str, str, str, str]] = set()
    result: list[dict[str, object]] = []
    for book in books:
        key = (
            str(book.get("isbn") or "").strip().lower(),
            str(book.get("title") or "").strip().lower(),
            str(book.get("author") or "").strip().lower(),
            str(book.get("evidence") or "").strip().lower()[:80],
        )
        if key in seen:
            continue
        seen.add(key)
        result.append(book)
    return result


def should_try_download(book: dict[str, object]) -> bool:
    lookup_status = str(book.get("lookup_status") or "not_attempted").strip()
    return lookup_status not in {"needs_clarification", "not_found", "lookup_error"}


def assign_pipeline_status(book: dict[str, object]) -> None:
    lookup_status = str(book.get("lookup_status") or "not_attempted").strip()
    if book.get("vault_note"):
        book["pipeline_status"] = "added"
    elif str(book.get("status") or "") == "unreadable":
        book["pipeline_status"] = "unreadable"
    elif lookup_status == "not_found":
        book["pipeline_status"] = "catalog_not_found"
    elif lookup_status == "lookup_error":
        book["pipeline_status"] = "source_error"
    else:
        book["pipeline_status"] = "needs_clarification"


def failed_pipeline_result(
    rel_path: str,
    reason: str,
    *,
    update_parent: bool,
    vault_dir: Path,
) -> BookPipelineResult:
    detection_result = {
        "detected_books": [],
        "unresolved": [{"region": "", "reason": "vision processing failed", "evidence": reason}],
    }
    parent_note_updated = False
    if update_parent:
        update_bookshelf_note_result(rel_path, detection_result, [], vault_dir=vault_dir, error=reason)
        parent_note_updated = True
    report = BookDiscoveryReport(rel_path, [], [], detection_result["unresolved"])
    return BookPipelineResult(
        status="failed",
        detection_result=detection_result,
        created_notes=[],
        report=report,
        parent_note_updated=parent_note_updated,
        error=reason,
    )


def process_book_image(
    *,
    image_path: Path,
    rel_path: str,
    kind: str,
    caption: str,
    route: KnowledgeRoute,
    settings: dict[str, object] | None,
    vault_dir: Path = VAULT_DIR,
    vision_model: str,
    vision_ready: bool,
    loaded_models: list[str],
    base_url: str,
    timeout: int,
    update_parent: bool = True,
    on_status: StatusCallback | None = None,
) -> BookPipelineResult:
    settings = dict(DEFAULT_SETTINGS if settings is None else settings)
    del route  # Kept in the interface for future routing-aware pipeline decisions.

    def status(message: str) -> None:
        if on_status:
            on_status(message)

    if not vision_ready:
        loaded = ", ".join(loaded_models) if loaded_models else "нет загруженных моделей"
        return failed_pipeline_result(
            rel_path,
            f"Для распознавания книг нужна vision-модель. Сейчас загружено: {loaded}. Загрузите qwen2.5-vl-7b или llava в LM Studio.",
            update_parent=update_parent,
            vault_dir=vault_dir,
        )

    try:
        status("vision model is reading visible book text")
        detection_result = call_bookshelf_vision(
            image_path,
            kind,
            caption,
            vision_model,
            vision_ready,
            loaded_models,
            base_url,
            timeout,
        )
        detection_result["detected_books"] = dedupe_detected_books(detection_result.get("detected_books", []))

        status("catalog lookup is matching detected books")
        enriched_books, lookup_unresolved = enrich_detected_books(
            detection_result.get("detected_books", []),
            book_lookup_enabled=setting_bool(settings, "book_lookup_enabled"),
        )
        detection_result["detected_books"] = enriched_books
        detection_result.setdefault("unresolved", []).extend(lookup_unresolved)

        status("legal download resolver is checking open sources")
        for book in enriched_books:
            if should_try_download(book):
                download = resolve_legal_book_download(
                    book,
                    vault_dir=vault_dir,
                    enabled=setting_bool(settings, "book_download_enabled"),
                    max_mb=setting_int(settings, "book_download_max_mb"),
                    formats=settings.get("book_download_formats", DEFAULT_SETTINGS["book_download_formats"]),
                    legal_sources=settings.get("book_legal_sources", DEFAULT_SETTINGS["book_legal_sources"]),
                    timeout=min(max(5, timeout), 30),
                )
            else:
                download = BookDownloadResult(
                    status="download_not_available",
                    reason="Catalog match is not reliable enough for automatic download.",
                )
            apply_download_result(book, download)

        status("saving book notes")
        created_notes = save_detected_book_notes(
            detection_result.get("detected_books", []),
            rel_path,
            str(image_path),
            vault_dir=vault_dir,
        )
        should_update_parent = update_parent or bool(detection_result.get("detected_books")) or bool(detection_result.get("unresolved"))
        parent_note_updated = False
        if should_update_parent:
            update_bookshelf_note_result(rel_path, detection_result, created_notes, vault_dir=vault_dir)
            parent_note_updated = True

        for book in detection_result.get("detected_books", []):
            assign_pipeline_status(book)

        added = [book for book in detection_result.get("detected_books", []) if book.get("vault_note")]
        needs = [book for book in detection_result.get("detected_books", []) if not book.get("vault_note")]
        report = BookDiscoveryReport(rel_path, added, needs, detection_result.get("unresolved", []))
        return BookPipelineResult(
            status="done",
            detection_result=detection_result,
            created_notes=created_notes,
            report=report,
            parent_note_updated=parent_note_updated,
        )
    except Exception as exc:
        return failed_pipeline_result(rel_path, str(exc), update_parent=update_parent, vault_dir=vault_dir)
