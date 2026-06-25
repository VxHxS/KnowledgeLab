from __future__ import annotations

import urllib.request
from pathlib import Path
from urllib.parse import quote

from knowledgelab.config import VAULT_DIR
from knowledgelab.models import BookDownloadResult
from knowledgelab.utils.text import clean_filename
from knowledgelab.vault.capture import unique_path
from knowledgelab.vision.book_discovery import book_note_slug
from knowledgelab.vision.book_sources import (
    internet_archive_metadata,
    search_gutendex,
    search_internet_archive,
)


FORMAT_MIME_HINTS = {
    "epub": ("application/epub", ".epub"),
    "pdf": ("application/pdf", ".pdf"),
    "txt": ("text/plain", ".txt"),
}


def normalize_names(value: object, fallback: list[str]) -> list[str]:
    if isinstance(value, str):
        raw = value.split(",")
    elif isinstance(value, (list, tuple, set)):
        raw = value
    else:
        raw = fallback
    names = [str(item).strip().lower() for item in raw]
    return [name for name in names if name]


def apply_download_result(book: dict[str, object], result: BookDownloadResult) -> dict[str, object]:
    book["download_status"] = result.status
    book["download_reason"] = result.reason
    book["download_source"] = result.source_name
    book["download_url"] = result.url
    book["local_file_rel_path"] = result.local_file_rel_path
    book["download_file_name"] = result.file_name
    book["download_format"] = result.file_format
    book["download_size_bytes"] = result.size_bytes
    return book


def download_to_vault(url: str, destination_dir: Path, file_name: str, vault_dir: Path = VAULT_DIR, max_mb: int = 50, timeout: float = 20.0) -> BookDownloadResult:
    destination_dir.mkdir(parents=True, exist_ok=True)
    safe_name = clean_filename(file_name) or "book-download"
    path = unique_path(destination_dir / safe_name)
    max_bytes = max(1, int(max_mb)) * 1024 * 1024
    request = urllib.request.Request(url, headers={"User-Agent": "KnowledgeLab/1.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        content_length = response.headers.get("Content-Length")
        if content_length and int(content_length) > max_bytes:
            return BookDownloadResult(
                status="download_not_available",
                reason=f"File is larger than configured limit ({int(content_length)} bytes > {max_bytes} bytes).",
                url=url,
                file_name=safe_name,
            )
        total = 0
        with path.open("wb") as handle:
            while True:
                chunk = response.read(1024 * 256)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_bytes:
                    try:
                        path.unlink()
                    except OSError:
                        pass
                    return BookDownloadResult(
                        status="download_not_available",
                        reason=f"File exceeded configured limit ({max_bytes} bytes).",
                        url=url,
                        file_name=safe_name,
                    )
                handle.write(chunk)
    return BookDownloadResult(
        status="downloaded",
        reason="Downloaded from a legal open source.",
        url=url,
        local_file_rel_path=path.relative_to(vault_dir).as_posix(),
        file_name=path.name,
        file_format=path.suffix.lstrip(".").lower(),
        size_bytes=path.stat().st_size,
    )


def choose_gutendex_file(item: dict[str, object], formats: list[str]) -> tuple[str, str, str]:
    if bool(item.get("copyright")):
        return "", "", "Project Gutenberg candidate is marked as copyrighted."
    source_formats = item.get("formats") if isinstance(item.get("formats"), dict) else {}
    for preferred in formats:
        mime_hint, suffix = FORMAT_MIME_HINTS.get(preferred, ("", ""))
        if not mime_hint:
            continue
        for mime, url in source_formats.items():
            if not isinstance(url, str) or not url.startswith("http"):
                continue
            lowered_mime = str(mime).lower()
            if mime_hint in lowered_mime:
                return url, suffix, ""
    return "", "", "Project Gutenberg has no allowed EPUB/PDF/TXT file for this match."


def internet_archive_allowed(metadata: dict[str, object]) -> tuple[bool, str]:
    item = metadata.get("metadata") if isinstance(metadata.get("metadata"), dict) else {}
    status = str(item.get("possible-copyright-status") or item.get("copyrightstatus") or "").lower()
    collections = item.get("collection")
    if isinstance(collections, str):
        collections = [collections]
    collections = [str(value).lower() for value in collections] if isinstance(collections, list) else []
    if "not_in_copyright" in status or "public domain" in status or "publicdomain" in status:
        return True, ""
    if "gutenberg" in collections:
        return True, ""
    return False, "Internet Archive item is not clearly public domain/open access, so KnowledgeLab will not download it automatically."


def choose_internet_archive_file(identifier: str, metadata: dict[str, object], formats: list[str]) -> tuple[str, str, str]:
    files = metadata.get("files") if isinstance(metadata.get("files"), list) else []
    for preferred in formats:
        _mime_hint, suffix = FORMAT_MIME_HINTS.get(preferred, ("", ""))
        if not suffix:
            continue
        for item in files:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").strip()
            lowered = name.lower()
            if not name or lowered.endswith(("_meta.xml", "_files.xml", "_reviews.xml", ".torrent")):
                continue
            if preferred == "txt" and not lowered.endswith(".txt"):
                continue
            if preferred != "txt" and not lowered.endswith(suffix):
                continue
            return f"https://archive.org/download/{quote(identifier)}/{quote(name, safe='/')}", suffix, ""
    return "", "", "Internet Archive item has no allowed EPUB/PDF/TXT file."


def resolve_legal_book_download(
    book: dict[str, object],
    *,
    vault_dir: Path = VAULT_DIR,
    enabled: bool = True,
    max_mb: int = 50,
    formats: object = None,
    legal_sources: object = None,
    timeout: float = 10.0,
) -> BookDownloadResult:
    if not enabled:
        return BookDownloadResult(status="disabled", reason="Book download is disabled.")
    preferred_formats = normalize_names(formats, ["epub", "pdf", "txt"])
    sources = normalize_names(legal_sources, ["gutenberg", "internet_archive"])
    destination = vault_dir / "50 Library" / book_note_slug(book) / "Files"
    reasons: list[str] = []
    source_errors: list[str] = []

    if "gutenberg" in sources:
        try:
            items, _query_url = search_gutendex(book, timeout=timeout)
            for item in items:
                url, suffix, reason = choose_gutendex_file(item, preferred_formats)
                if url:
                    file_name = f"{book_note_slug(book)}{suffix}"
                    result = download_to_vault(url, destination, file_name, vault_dir=vault_dir, max_mb=max_mb, timeout=timeout)
                    return BookDownloadResult(**{**result.__dict__, "source_name": "gutenberg"})
                if reason:
                    reasons.append(reason)
        except Exception as exc:
            source_errors.append(f"gutenberg: {exc}")

    if "internet_archive" in sources:
        try:
            items, _query_url = search_internet_archive(book, timeout=timeout)
            for item in items:
                identifier = str(item.get("identifier") or "").strip()
                if not identifier:
                    continue
                metadata = internet_archive_metadata(identifier, timeout=timeout)
                allowed, reason = internet_archive_allowed(metadata)
                if not allowed:
                    reasons.append(reason)
                    continue
                url, suffix, reason = choose_internet_archive_file(identifier, metadata, preferred_formats)
                if url:
                    file_name = f"{book_note_slug(book)}{suffix}"
                    result = download_to_vault(url, destination, file_name, vault_dir=vault_dir, max_mb=max_mb, timeout=timeout)
                    return BookDownloadResult(**{**result.__dict__, "source_name": "internet_archive"})
                if reason:
                    reasons.append(reason)
        except Exception as exc:
            source_errors.append(f"internet_archive: {exc}")

    if source_errors and not reasons:
        return BookDownloadResult(status="source_error", reason="; ".join(source_errors))
    if reasons:
        if any("not clearly public domain" in reason for reason in reasons):
            return BookDownloadResult(status="download_not_allowed", reason="; ".join(sorted(set(reasons))))
        return BookDownloadResult(status="download_not_available", reason="; ".join(sorted(set(reasons))))
    return BookDownloadResult(status="download_not_available", reason="No legal download candidate was found in the configured sources.")
