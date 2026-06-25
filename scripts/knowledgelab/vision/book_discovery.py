from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import urllib.request
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import urlencode

from knowledgelab.config import (
    BOOK_IMAGE_TERMS,
    BOOK_LOOKUP_MIN_SCORE,
    BOOK_PAGE_TERMS,
    BOOKSHELF_TERMS,
    GOOGLE_BOOKS_SEARCH_URL,
    LAYER_ACTIVE,
    LAYER_FINISHED_PROJECTS,
    OPEN_LIBRARY_SEARCH_URL,
    VAULT_DIR,
)
from knowledgelab.models import (
    BookDiscoveryReport,
    KnowledgeRoute,
    ManualBookEntry,
    MaterialRoutingReport,
)
from knowledgelab.utils.text import (
    clean_filename,
    compact_whitespace,
    contains_any,
    extract_json_object,
    now_iso,
    slugify,
    yaml_quote,
)
from knowledgelab.utils.urls import URL_RE
from knowledgelab.vault.capture import unique_path
from knowledgelab.vault.frontmatter import parse_basic_frontmatter
from knowledgelab.routing.topics import ensure_topic_exists


def infer_image_capture_kind(path: Path, caption: str) -> str:
    seed = f"{caption} {path.stem} {path.name}".lower()
    if contains_any(seed, BOOKSHELF_TERMS):
        return "bookshelf_photo"
    if contains_any(seed, BOOK_IMAGE_TERMS):
        return "book_page_photo" if contains_any(seed, BOOK_PAGE_TERMS) else "book_photo"
    return "image_capture"


def infer_book_title_from_hint(caption: str, path: Path) -> str:
    cleaned = caption.strip()
    if cleaned:
        cleaned = re.sub(r"\b(?:book|books|cover|page|chapter|isbn|книга|книги|обложка|страница|глава)\b", "", cleaned, flags=re.IGNORECASE)
        cleaned = compact_whitespace(cleaned)
    return clean_filename(cleaned or path.stem or "Unsorted Book")


def infer_page_number_guess(caption: str, path: Path) -> str:
    seed = f"{caption} {path.stem}"
    match = re.search(r"(?:page|p\.?|стр(?:аница)?\.?)\s*([0-9]{1,5})", seed, flags=re.IGNORECASE)
    if match:
        return match.group(1)
    match = re.search(r"\b([0-9]{1,5})\b", path.stem)
    return match.group(1) if match else ""


def image_mime_type(path: Path) -> str:
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".gif": "image/gif",
        ".bmp": "image/bmp",
        ".tif": "image/tiff",
        ".tiff": "image/tiff",
    }.get(path.suffix.lower(), "application/octet-stream")


def image_data_url(path: Path, max_bytes: int = 8_000_000) -> str:
    raw = path.read_bytes()
    if len(raw) > max_bytes:
        raise RuntimeError(f"image is too large for inline vision request: {len(raw)} bytes")
    encoded = base64.b64encode(raw).decode("ascii")
    return f"data:{image_mime_type(path)};base64,{encoded}"


def normalize_detected_book(item: object) -> dict[str, object]:
    if not isinstance(item, dict):
        return {}
    title = compact_whitespace(str(item.get("title") or item.get("book_title") or item.get("visual_guess") or ""))
    author = compact_whitespace(str(item.get("author") or item.get("authors") or item.get("visual_author_guess") or ""))
    isbn = re.sub(r"[^0-9Xx]", "", str(item.get("isbn") or ""))
    visible_text = compact_whitespace(str(item.get("visible_text") or item.get("spine_text") or ""))
    visual_guess = compact_whitespace(str(item.get("visual_guess") or item.get("guess") or ""))
    evidence = compact_whitespace(str(item.get("evidence") or visible_text or visual_guess or ""))
    status = str(item.get("status") or "found").strip().lower()
    if status not in {"found", "uncertain", "unreadable", "inferred", "user_confirmed"}:
        status = "found" if title else "unreadable"
    try:
        confidence = float(item.get("confidence", 0.0) or 0.0)
    except (TypeError, ValueError):
        confidence = 0.0
    confidence = max(0.0, min(confidence, 1.0))
    if not title and status != "unreadable":
        status = "unreadable"
    return {
        "title": title,
        "author": author,
        "isbn": isbn,
        "evidence": evidence,
        "status": status,
        "confidence": confidence,
        "region": compact_whitespace(str(item.get("region") or item.get("position") or "")),
        "visible_text": visible_text,
        "visual_guess": visual_guess,
        "guess_reason": compact_whitespace(str(item.get("reason") or item.get("guess_reason") or "")),
    }


def parse_manual_book_entries(text: str) -> list[ManualBookEntry]:
    entries: list[ManualBookEntry] = []
    current_section = ""
    seen: set[tuple[str, str]] = set()
    header_terms = {"№", "#", "название", "title", "автор", "author", "книга", "book"}
    for raw_line in text.splitlines():
        line = compact_whitespace(raw_line.strip().strip("|"))
        if not line:
            continue
        if re.fullmatch(r"[-:|_\s]+", line):
            continue
        lowered = line.lower()
        if lowered.endswith(":") and len(line) <= 80:
            current_section = line.rstrip(":").strip()
            continue
        if lowered in {"добавлено", "нужно уточнить", "не найдено", "не прочитано"}:
            continue
        if set(book_text_tokens(line)) <= header_terms:
            continue

        number = ""
        match = re.match(r"^\s*(?:[-*]\s*)?(?:(\d{1,3})[.)]\s+)?(.+?)\s*$", line)
        if match:
            number = match.group(1) or ""
            line = match.group(2).strip()

        title = ""
        author = ""
        cells = [compact_whitespace(part) for part in re.split(r"\s*\|\s*|\t+", line) if compact_whitespace(part)]
        if len(cells) >= 2:
            if re.fullmatch(r"\d{1,3}", cells[0]):
                number = number or cells[0]
                cells = cells[1:]
            if len(cells) >= 2:
                title, author = cells[0], cells[1]
            else:
                title = cells[0]
        if not title:
            split_match = re.match(r"(.+?)\s+(?:—|–|-|::| by | автор[:：]?)\s+(.+)", line, flags=re.IGNORECASE)
            if split_match:
                title = compact_whitespace(split_match.group(1))
                author = compact_whitespace(split_match.group(2))
            else:
                title = line
        title = re.sub(r"^\d{1,3}\s+", "", title).strip()
        author = re.sub(r"^(автор|author)[:：]\s*", "", author, flags=re.IGNORECASE).strip()
        if not title or len(title) < 3:
            continue
        if URL_RE.search(title):
            continue
        if title.lower() in {"да", "нет", "ок", "спасибо", "привет"}:
            continue
        key = (title.lower(), author.lower())
        if key in seen:
            continue
        seen.add(key)
        entries.append(ManualBookEntry(title=title, author=author, section=current_section, position=number, user_evidence=raw_line.strip()))
    return entries


def manual_book_resolution_likely(text: str, entries: list[ManualBookEntry], last_report: BookDiscoveryReport | None) -> bool:
    if not entries:
        return False
    lowered = text.lower()
    book_intent = contains_any(lowered, {"книга", "книги", "автор", "полк", "кореш", "добав", "library", "book", "bookshelf"})
    list_shape = (
        len(entries) >= 2
        or bool(re.search(r"(?m)^\s*(?:\d{1,3}[.)]|[-*])\s+", text))
        or "|" in text
        or "\t" in text
        or "—" in text
        or "–" in text
        or " - " in text
    )
    if last_report and (last_report.needs_clarification or last_report.not_found):
        return list_shape or (book_intent and len(entries) >= 2)
    return book_intent and list_shape


def book_text_tokens(value: object) -> set[str]:
    text = compact_whitespace(str(value or "")).lower()
    tokens = set(re.findall(r"[a-zа-яё0-9]{3,}", text, flags=re.IGNORECASE))
    return {token for token in tokens if token not in {"the", "and", "for", "with", "book", "книга", "том"}}


def token_overlap_score(left: object, right: object) -> float:
    left_tokens = book_text_tokens(left)
    right_tokens = book_text_tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / max(1, len(left_tokens | right_tokens))


def normalize_openlibrary_candidate(doc: dict) -> dict[str, object]:
    title = compact_whitespace(str(doc.get("title") or ""))
    authors = doc.get("author_name") if isinstance(doc.get("author_name"), list) else []
    author = compact_whitespace(str(authors[0])) if authors else ""
    isbns = doc.get("isbn") if isinstance(doc.get("isbn"), list) else []
    key = str(doc.get("key") or "").strip()
    catalog_url = f"https://openlibrary.org{key}" if key.startswith("/") else ""
    cover_i = doc.get("cover_i")
    cover_url = f"https://covers.openlibrary.org/b/id/{cover_i}-L.jpg" if cover_i else ""
    return {
        "canonical_title": title,
        "canonical_author": author,
        "isbn": str(isbns[0]) if isbns else "",
        "openlibrary_key": key,
        "catalog_url": catalog_url,
        "cover_url": cover_url,
        "first_publish_year": doc.get("first_publish_year", ""),
        "edition_count": doc.get("edition_count", ""),
        "source_catalog": "openlibrary",
    }


def normalize_google_books_candidate(item: dict) -> dict[str, object]:
    volume = item.get("volumeInfo") if isinstance(item.get("volumeInfo"), dict) else {}
    title = compact_whitespace(str(volume.get("title") or ""))
    authors = volume.get("authors") if isinstance(volume.get("authors"), list) else []
    author = compact_whitespace(str(authors[0])) if authors else ""
    identifiers = volume.get("industryIdentifiers") if isinstance(volume.get("industryIdentifiers"), list) else []
    isbn = ""
    for identifier in identifiers:
        if not isinstance(identifier, dict):
            continue
        value = re.sub(r"[^0-9Xx]", "", str(identifier.get("identifier") or ""))
        if value and (not isbn or len(value) == 13):
            isbn = value
    image_links = volume.get("imageLinks") if isinstance(volume.get("imageLinks"), dict) else {}
    cover_url = str(image_links.get("thumbnail") or image_links.get("smallThumbnail") or "").strip()
    published_date = str(volume.get("publishedDate") or "").strip()
    info_link = str(volume.get("infoLink") or volume.get("canonicalVolumeLink") or "").strip()
    return {
        "canonical_title": title,
        "canonical_author": author,
        "isbn": isbn,
        "google_books_id": str(item.get("id") or "").strip(),
        "google_books_url": info_link,
        "catalog_url": info_link,
        "cover_url": cover_url,
        "published_date": published_date,
        "first_publish_year": published_date[:4] if re.match(r"^\d{4}", published_date) else "",
        "publisher": compact_whitespace(str(volume.get("publisher") or "")),
        "page_count": volume.get("pageCount", ""),
        "source_catalog": "google_books",
    }


def score_book_lookup_candidate(book: dict[str, object], candidate: dict[str, object]) -> float:
    visible_title = str(book.get("title") or "")
    visible_author = str(book.get("author") or "")
    visible_isbn = re.sub(r"[^0-9Xx]", "", str(book.get("isbn") or "")).lower()
    candidate_isbn = re.sub(r"[^0-9Xx]", "", str(candidate.get("isbn") or "")).lower()
    title_score = max(
        token_overlap_score(visible_title, candidate.get("canonical_title")),
        SequenceMatcher(None, visible_title.lower(), str(candidate.get("canonical_title") or "").lower()).ratio() if visible_title else 0.0,
    )
    author_score = token_overlap_score(visible_author, candidate.get("canonical_author"))
    evidence_score = token_overlap_score(book.get("evidence"), f"{candidate.get('canonical_title')} {candidate.get('canonical_author')}")
    score = (title_score * 0.62) + (author_score * 0.2) + (evidence_score * 0.18)
    if visible_isbn and candidate_isbn and visible_isbn == candidate_isbn:
        score = max(score, 0.98)
    if visible_title and str(candidate.get("canonical_title") or "").lower() == visible_title.lower():
        score = max(score, 0.78)
    return round(max(0.0, min(score, 1.0)), 3)


def compact_catalog_candidate(candidate: dict[str, object]) -> dict[str, object]:
    return {
        key: value
        for key, value in {
            "source_catalog": candidate.get("source_catalog"),
            "title": candidate.get("canonical_title"),
            "author": candidate.get("canonical_author"),
            "isbn": candidate.get("isbn"),
            "catalog_url": candidate.get("catalog_url"),
            "score": candidate.get("lookup_score"),
        }.items()
        if value not in (None, "")
    }


def select_best_book_lookup(
    book: dict[str, object],
    candidates: list[dict[str, object]],
    source_errors: list[str] | None = None,
    checked_sources: list[str] | None = None,
) -> dict[str, object]:
    errors = [error for error in (source_errors or []) if error]
    sources_checked = sorted(
        {
            str(source).strip()
            for source in (checked_sources or [])
            if str(source).strip()
        }
        | {
            str(candidate.get("source_catalog") or "").strip()
            for candidate in candidates
            if candidate.get("source_catalog")
        }
    )
    unique: dict[tuple[str, str, str, str], dict[str, object]] = {}
    for candidate in candidates:
        if not candidate.get("canonical_title"):
            continue
        key = (
            str(candidate.get("source_catalog") or ""),
            compact_whitespace(str(candidate.get("canonical_title") or "")).lower(),
            compact_whitespace(str(candidate.get("canonical_author") or "")).lower(),
            re.sub(r"[^0-9Xx]", "", str(candidate.get("isbn") or "")).lower(),
        )
        unique.setdefault(key, candidate)
    scored = [(score_book_lookup_candidate(book, candidate), candidate) for candidate in unique.values()]
    scored.sort(key=lambda item: item[0], reverse=True)
    candidate_preview: list[dict[str, object]] = []
    for score, candidate in scored[:5]:
        candidate = dict(candidate)
        candidate["lookup_score"] = score
        candidate_preview.append(compact_catalog_candidate(candidate))
    if not scored:
        status = "lookup_error" if errors else "not_found"
        reason = "Book catalog lookup failed: " + "; ".join(errors) if errors else "No catalog match was found for the visible book text."
        return {
            "lookup_status": status,
            "lookup_reason": reason,
            "lookup_errors": "; ".join(errors),
            "catalog_sources": ", ".join(sources_checked or ["openlibrary", "google_books"]),
            "catalog_candidate_count": 0,
            "catalog_candidates": candidate_preview,
        }
    score, best = scored[0]
    best = dict(best)
    best["lookup_score"] = score
    best["catalog_sources"] = ", ".join(sources_checked)
    best["catalog_candidate_count"] = len(scored)
    best["catalog_candidates"] = candidate_preview
    best["lookup_errors"] = "; ".join(errors)
    close_second = len(scored) > 1 and scored[1][0] >= max(BOOK_LOOKUP_MIN_SCORE, score - 0.06)
    if score >= BOOK_LOOKUP_MIN_SCORE and not (close_second and score < 0.76):
        best["lookup_status"] = "found"
        best["lookup_reason"] = "Matched against multiple book catalogs from visible spine/cover metadata."
    elif close_second:
        best["lookup_status"] = "needs_clarification"
        best["lookup_reason"] = "Several catalog candidates are close; ask the user to confirm title or author."
    else:
        best["lookup_status"] = "needs_clarification"
        best["lookup_reason"] = "Catalog lookup returned a weak match; ask the user to confirm title or author."
    return best


def merge_book_lookup(book: dict[str, object], lookup: dict[str, object]) -> dict[str, object]:
    merged = dict(book)
    if not lookup:
        merged.setdefault("lookup_status", "not_attempted")
        return merged
    merged.update({key: value for key, value in lookup.items() if value not in (None, "")})
    if lookup.get("canonical_title"):
        merged["visible_title"] = book.get("title", "")
        merged["title"] = lookup["canonical_title"]
    if lookup.get("canonical_author"):
        merged["visible_author"] = book.get("author", "")
        merged["author"] = lookup["canonical_author"]
    return merged


def classify_book_topic(book: dict[str, object]) -> str:
    seed = " ".join(
        str(book.get(key) or "")
        for key in ("title", "author", "evidence", "visible_title", "visible_author")
    ).lower()
    if contains_any(seed, {"css", "html", "javascript", "typescript", "react", "frontend", "web"}):
        return "Web Development"
    if contains_any(seed, {"unity", "c#", "csharp", "game", "игр", "игра", "гейм"}):
        return "Game Development"
    if contains_any(seed, {"java", "python", "programming", "программ", "разработ"}):
        return "Programming"
    if contains_any(seed, {"триз", "triz", "problem", "проблем"}):
        return "Problem Solving"
    if contains_any(seed, {"design", "дизайн", "ux", "ui"}):
        return "Design"
    return "Library"


def parse_bookshelf_detection_response(text: str) -> dict[str, list[dict[str, object]]]:
    parsed = extract_json_object(text)
    raw_books = parsed.get("detected_books") or parsed.get("books") or []
    if isinstance(raw_books, dict):
        raw_books = [raw_books]
    books = [book for book in (normalize_detected_book(item) for item in raw_books if isinstance(raw_books, list)) if book]
    raw_unresolved = parsed.get("unresolved") or parsed.get("unrecognized") or parsed.get("failed") or []
    if isinstance(raw_unresolved, dict):
        raw_unresolved = [raw_unresolved]
    unresolved: list[dict[str, object]] = []
    if isinstance(raw_unresolved, list):
        for item in raw_unresolved:
            if isinstance(item, dict):
                unresolved.append({
                    "region": compact_whitespace(str(item.get("region") or item.get("position") or "")),
                    "reason": compact_whitespace(str(item.get("reason") or item.get("issue") or "unreadable")),
                    "evidence": compact_whitespace(str(item.get("evidence") or item.get("visible_text") or item.get("visual_guess") or "")),
                })
            elif str(item).strip():
                unresolved.append({"region": "", "reason": compact_whitespace(str(item)), "evidence": ""})
    for book in books:
        if book.get("status") == "unreadable":
            unresolved.append({
                "region": "",
                "reason": "title/author unreadable",
                "evidence": str(book.get("evidence") or ""),
            })
        elif book.get("status") == "inferred" and float(book.get("confidence") or 0.0) < 0.72:
            unresolved.append({
                "region": str(book.get("region") or ""),
                "reason": str(book.get("guess_reason") or "visual guess needs confirmation"),
                "evidence": str(book.get("evidence") or book.get("title") or ""),
            })
    return {
        "detected_books": [book for book in books if book.get("title")],
        "unresolved": unresolved,
    }


def render_book_note_markdown(book: dict[str, object], source_rel_path: str, source_image_path: str) -> str:
    title = str(book.get("title") or "Unknown Book").strip()
    author = str(book.get("author") or "").strip()
    isbn = str(book.get("isbn") or "").strip()
    status = str(book.get("status") or "found").strip()
    confidence = book.get("confidence", 0.0)
    evidence = str(book.get("evidence") or "").strip()
    discovery_source = str(book.get("discovery_source") or ("manual_user_resolution" if book.get("user_confirmed") else "bookshelf_photo")).strip()
    user_evidence = str(book.get("user_evidence") or "").strip()
    region = str(book.get("region") or "").strip()
    visual_guess = str(book.get("visual_guess") or "").strip()
    lookup_status = str(book.get("lookup_status") or "not_attempted").strip()
    lookup_score = book.get("lookup_score", "")
    visible_title = str(book.get("visible_title") or "").strip()
    visible_author = str(book.get("visible_author") or "").strip()
    catalog_url = str(book.get("catalog_url") or "").strip()
    source_catalog = str(book.get("source_catalog") or "").strip()
    catalog_sources = str(book.get("catalog_sources") or source_catalog).strip()
    catalog_candidate_count = str(book.get("catalog_candidate_count") or "").strip()
    catalog_candidates = book.get("catalog_candidates") if isinstance(book.get("catalog_candidates"), list) else []
    lookup_errors = str(book.get("lookup_errors") or "").strip()
    openlibrary_key = str(book.get("openlibrary_key") or "").strip()
    google_books_id = str(book.get("google_books_id") or "").strip()
    google_books_url = str(book.get("google_books_url") or "").strip()
    cover_url = str(book.get("cover_url") or "").strip()
    first_publish_year = str(book.get("first_publish_year") or "").strip()
    published_date = str(book.get("published_date") or "").strip()
    publisher = str(book.get("publisher") or "").strip()
    page_count = str(book.get("page_count") or "").strip()
    edition_count = str(book.get("edition_count") or "").strip()
    lookup_reason = str(book.get("lookup_reason") or "").strip()
    download_status = str(book.get("download_status") or "not_attempted").strip()
    download_reason = str(book.get("download_reason") or "").strip()
    download_source = str(book.get("download_source") or "").strip()
    download_url = str(book.get("download_url") or "").strip()
    local_file_rel_path = str(book.get("local_file_rel_path") or "").strip()
    download_file_name = str(book.get("download_file_name") or "").strip()
    download_format = str(book.get("download_format") or "").strip()
    download_size_bytes = str(book.get("download_size_bytes") or "").strip()
    book_topic = str(book.get("book_topic") or classify_book_topic(book)).strip()
    tags = [
        "library/book",
        f"topic/{slugify(book_topic)}",
        f"discovery/{slugify(status)}",
        f"lookup/{slugify(lookup_status)}",
        f"download/{slugify(download_status)}",
    ]
    frontmatter = [
        "---",
        "type: book",
        f"source: {discovery_source}",
        f"book_title: {yaml_quote(title)}",
        f"book_author: {yaml_quote(author)}",
        f"isbn: {yaml_quote(isbn)}",
        f"visible_title: {yaml_quote(visible_title)}",
        f"visible_author: {yaml_quote(visible_author)}",
        f"topic: {yaml_quote(book_topic)}",
        f"book_topic: {yaml_quote(book_topic)}",
        f"discovery_status: {yaml_quote(status)}",
        f"discovery_source: {yaml_quote(discovery_source)}",
        f"user_confirmed: {str(bool(book.get('user_confirmed'))).lower()}",
        f"user_evidence: {yaml_quote(user_evidence)}",
        f"shelf_region: {yaml_quote(region)}",
        f"visual_guess: {yaml_quote(visual_guess)}",
        f"confidence: {confidence}",
        f"lookup_status: {yaml_quote(lookup_status)}",
        f"lookup_score: {yaml_quote(str(lookup_score))}",
        f"lookup_reason: {yaml_quote(lookup_reason)}",
        f"source_catalog: {yaml_quote(source_catalog)}",
        f"catalog_sources: {yaml_quote(catalog_sources)}",
        f"catalog_candidate_count: {yaml_quote(catalog_candidate_count)}",
        f"lookup_errors: {yaml_quote(lookup_errors)}",
        f"catalog_url: {yaml_quote(catalog_url)}",
        f"openlibrary_key: {yaml_quote(openlibrary_key)}",
        f"google_books_id: {yaml_quote(google_books_id)}",
        f"google_books_url: {yaml_quote(google_books_url)}",
        f"cover_url: {yaml_quote(cover_url)}",
        f"first_publish_year: {yaml_quote(first_publish_year)}",
        f"published_date: {yaml_quote(published_date)}",
        f"publisher: {yaml_quote(publisher)}",
        f"page_count: {yaml_quote(page_count)}",
        f"edition_count: {yaml_quote(edition_count)}",
        f"download_status: {yaml_quote(download_status)}",
        f"download_reason: {yaml_quote(download_reason)}",
        f"download_source: {yaml_quote(download_source)}",
        f"download_url: {yaml_quote(download_url)}",
        f"local_file_rel_path: {yaml_quote(local_file_rel_path)}",
        f"download_file_name: {yaml_quote(download_file_name)}",
        f"download_format: {yaml_quote(download_format)}",
        f"download_size_bytes: {yaml_quote(download_size_bytes)}",
        f"source_image_path: {yaml_quote(source_image_path)}",
        f"parent_note: {yaml_quote(source_rel_path)}",
        f"captured_at: {yaml_quote(now_iso())}",
        f"tags: [{', '.join(tags)}]",
        "---",
        "",
        f"# {title}",
        "",
        "## Book Metadata",
        "",
        f"- Title: {title}",
        f"- Author: {author or 'unknown'}",
        f"- ISBN: {isbn or 'unknown'}",
        f"- Discovery status: {status}",
        f"- Discovery source: {discovery_source}",
        f"- User confirmed: {'yes' if book.get('user_confirmed') else 'no'}",
        f"- Confidence: {confidence}",
        f"- Lookup status: {lookup_status}",
        f"- Lookup score: {lookup_score or 'unknown'}",
        f"- Catalog sources checked: {catalog_sources or source_catalog or 'not recorded'}",
        f"- Best catalog record: {catalog_url or source_catalog or 'not linked'}",
        f"- First publish year: {first_publish_year or 'unknown'}",
        f"- Published date: {published_date or 'unknown'}",
        f"- Publisher: {publisher or 'unknown'}",
        f"- Page count: {page_count or 'unknown'}",
        f"- Topic: {book_topic}",
        f"- Download status: {download_status}",
        f"- Download source: {download_source or 'none'}",
        f"- Local file: {local_file_rel_path or 'not downloaded'}",
        f"- Visible title: {visible_title or title}",
        f"- Visible author: {visible_author or author or 'unknown'}",
        f"- Shelf region: {region or 'unknown'}",
        f"- Visual guess: {visual_guess or 'none'}",
    ]
    if cover_url:
        frontmatter.extend(["", "## Cover", "", f"![cover]({cover_url})"])
    frontmatter.extend([
        "",
        "## Shelf Evidence",
        "",
        evidence or "_No readable spine/cover evidence was returned._",
        "",
        "## User Evidence",
        "",
        user_evidence or "_No manual user evidence was provided._",
        "",
        "## Lookup Notes",
        "",
        lookup_reason or "_No lookup issue reported._",
        "",
    ])
    frontmatter.extend([
        "## Download",
        "",
        f"- Status: {download_status}",
        f"- Reason: {download_reason or 'No download issue reported.'}",
        f"- Source: {download_source or 'none'}",
        f"- URL: {download_url or 'none'}",
        f"- Local file: {local_file_rel_path or 'not downloaded'}",
        f"- Format: {download_format or 'unknown'}",
        f"- Size bytes: {download_size_bytes or 'unknown'}",
        "",
    ])
    if lookup_errors:
        frontmatter.extend(["## Lookup Errors", "", lookup_errors, ""])
    if catalog_candidates:
        frontmatter.extend(["## Catalog Candidates", ""])
        for candidate in catalog_candidates[:5]:
            candidate_title = str(candidate.get("title") or "Unknown").strip()
            candidate_author = str(candidate.get("author") or "").strip()
            candidate_source = str(candidate.get("source_catalog") or "").strip()
            candidate_score = str(candidate.get("score") or "").strip()
            candidate_url = str(candidate.get("catalog_url") or "").strip()
            line = f"- {candidate_title}" + (f" - {candidate_author}" if candidate_author else "")
            details = ", ".join(part for part in (candidate_source, f"score {candidate_score}" if candidate_score else "") if part)
            if details:
                line += f" ({details})"
            if candidate_url:
                line += f": {candidate_url}"
            frontmatter.append(line)
        frontmatter.append("")
    frontmatter.extend([
        "## Source",
        "",
        f"- Bookshelf note: `{source_rel_path}`",
        f"- Source image: `{source_image_path}`",
        "",
    ])
    return "\n".join(frontmatter)


def render_bookshelf_detection_section(result: dict[str, list[dict[str, object]]], created_notes: list[str], error: str = "") -> str:
    books = result.get("detected_books", [])
    unresolved = result.get("unresolved", [])
    lines = [
        "## Bookshelf Detection Result",
        "",
        f"Processed at: {now_iso()}",
        f"Detection status: {'failed' if error else 'processed'}",
        "",
    ]
    if error:
        lines.extend(["### Processing Error", "", error, ""])
    lines.extend(["### Detected Books", ""])
    if books:
        for index, book in enumerate(books, start=1):
            note = str(book.get("vault_note") or (created_notes[index - 1] if index - 1 < len(created_notes) else ""))
            title = str(book.get("title") or "Unknown Book")
            author = str(book.get("author") or "")
            status = str(book.get("status") or "")
            confidence = book.get("confidence", 0.0)
            lookup_status = str(book.get("lookup_status") or "not_attempted")
            download_status = str(book.get("download_status") or "not_attempted")
            local_file = str(book.get("local_file_rel_path") or "")
            catalog_url = str(book.get("catalog_url") or "")
            book_topic = str(book.get("book_topic") or classify_book_topic(book))
            suffix = f" -> [[{note}]]" if note else ""
            catalog_suffix = f", catalog: {catalog_url}" if catalog_url else ""
            download_suffix = f", file: {local_file}" if local_file else f", download: {download_status}"
            lines.append(f"- {title}" + (f" - {author}" if author else "") + f" ({book_topic}; {status}, confidence {confidence}, lookup {lookup_status}{catalog_suffix}{download_suffix}){suffix}")
    else:
        lines.append("- None")
    lines.extend(["", "### Unresolved / Not Found", ""])
    if unresolved:
        for item in unresolved:
            region = str(item.get("region") or "").strip()
            reason = str(item.get("reason") or "unreadable").strip()
            evidence = str(item.get("evidence") or "").strip()
            label = f"{region}: {reason}" if region else reason
            lines.append(f"- {label}" + (f" - visible text: {evidence}" if evidence else ""))
    else:
        lines.append("- None reported")
    lines.append("")
    return "\n".join(lines)


def render_manual_book_list_markdown(entries: list[ManualBookEntry], source_text: str, route: KnowledgeRoute) -> str:
    frontmatter = [
        "---",
        "type: manual_book_list",
        "source: chat",
        f"layer: {route.layer}",
        f"scope: {route.scope}",
        f"project: {yaml_quote(route.project)}",
        "storage_policy: reference_only",
        "copies_original: false",
        "topic: \"Library\"",
        f"captured_at: {yaml_quote(now_iso())}",
        "tags: [library/manual-book-list, captured/chat]",
        "---",
        "",
        "# Manual Book List",
        "",
        "## Entries",
        "",
    ]
    if entries:
        for entry in entries:
            label = entry.title + (f" - {entry.author}" if entry.author else "")
            details = []
            if entry.section:
                details.append(f"section: {entry.section}")
            if entry.position:
                details.append(f"position: {entry.position}")
            frontmatter.append(f"- {label}" + (f" ({', '.join(details)})" if details else ""))
    else:
        frontmatter.append("- None")
    frontmatter.extend([
        "",
        "## Original User Text",
        "",
        source_text.strip() or "_No source text._",
        "",
    ])
    return "\n".join(frontmatter)


def render_manual_book_resolution_section(entries: list[dict[str, object]], created_notes: list[str], source_text: str) -> str:
    lines = [
        "## Resolved by user",
        "",
        f"Resolved at: {now_iso()}",
        "",
        "### Added / Updated Books",
        "",
    ]
    if entries:
        for index, book in enumerate(entries, start=1):
            note = str(book.get("vault_note") or (created_notes[index - 1] if index - 1 < len(created_notes) else ""))
            title = str(book.get("title") or "Unknown Book")
            author = str(book.get("author") or "")
            topic = str(book.get("book_topic") or classify_book_topic(book))
            lookup_status = str(book.get("lookup_status") or "not_attempted")
            lines.append(f"- {title}" + (f" - {author}" if author else "") + f" ({topic}; lookup {lookup_status})" + (f" -> [[{note}]]" if note else ""))
    else:
        lines.append("- None")
    lines.extend([
        "",
        "### User Text",
        "",
        source_text.strip() or "_No source text._",
        "",
    ])
    return "\n".join(lines)


def format_material_routing_report(reports: list[MaterialRoutingReport], detail: str = "full") -> str:
    if not reports:
        return ""
    grouped: dict[str, list[MaterialRoutingReport]] = {}
    for report in reports:
        grouped.setdefault(report.topic or "Unsorted", []).append(report)
    if detail == "compact":
        topic_parts = [f"{topic} ({len(items)})" for topic, items in sorted(grouped.items())]
        total = sum(len(items) for items in grouped.values())
        return f"Сохранено: {total} файл(ов) по темам: {', '.join(topic_parts)}."
    lines = ["Разложено по темам:"]
    for topic, items in sorted(grouped.items()):
        lines.append(f"- {topic}: {len(items)} файл(ов)")
        for item in items[:4]:
            lines.append(f"  - {item.source_name}")
        if len(items) > 4:
            lines.append(f"  - ...и ещё {len(items) - 4}")
    return "\n".join(lines)


def format_book_discovery_report(report: BookDiscoveryReport, detail: str = "full") -> str:
    added = report.added
    needs = report.needs_clarification
    not_found = report.not_found

    if not added and not needs and not not_found:
        return "Книги на изображении не обнаружены."

    lines: list[str] = []

    if added:
        in_vault: list[dict[str, object]] = []
        new_books: list[dict[str, object]] = []

        for book in added:
            existing = find_existing_book_note(book)
            if existing:
                book["_vault_note"] = existing
                in_vault.append(book)
            else:
                new_books.append(book)

        lines.append(f"Определено книг: {len(added)}")
        lines.append("")

        index = 1
        if new_books:
            for book in new_books[:20]:
                title = str(book.get("title") or "?")
                author = str(book.get("author") or "")
                author_str = f" — {author}" if author else ""
                lines.append(f"{index}. {title}{author_str}")
                index += 1

        if in_vault:
            lines.append("")
            lines.append(f"Уже в Obsidian ({len(in_vault)}):")
            for book in in_vault[:20]:
                title = str(book.get("title") or "?")
                author = str(book.get("author") or "")
                author_str = f" — {author}" if author else ""
                lines.append(f"  ✓ {title}{author_str}")

        if new_books:
            lines.append("")
            lines.append(f"Нужны файлы: {len(new_books)} книг. Отправьте .epub, .pdf или .fb2 файлы.")

    if needs:
        lines.append("")
        lines.append(f"Не удалось определить ({len(needs)}):")
        for item in needs[:5]:
            title = str(item.get("title") or item.get("visible_title") or item.get("evidence") or "?")
            lines.append(f"  - {title}")

    if not_found:
        has_vision_error = any("vision" in str(item.get("reason", "")).lower() or "lm studio" in str(item.get("evidence", "")).lower() for item in not_found)
        if has_vision_error:
            lines.append("")
            lines.append("Не распознано: нужна vision-модель в LM Studio (qwen2.5-vl или llava).")
        elif not added and not needs:
            lines.append("Не удалось распознать книги на изображении.")

    return "\n".join(lines)


def book_note_slug(book: dict[str, object]) -> str:
    title = compact_whitespace(str(book.get("title") or book.get("canonical_title") or "")).strip()
    author = compact_whitespace(str(book.get("author") or book.get("canonical_author") or "")).strip()
    parts = [title]
    if author:
        parts.append(author)
    return slugify(" ".join(parts)) or "unknown-book"


def find_existing_book_note(book: dict[str, object], vault_dir: Path = VAULT_DIR) -> str:
    library_dir = vault_dir / "50 Library"
    if not library_dir.exists():
        return ""
    target_isbn = str(book.get("isbn") or "").strip().lower()
    target_key = str(book.get("openlibrary_key") or "").strip().lower()
    target_catalog_url = str(book.get("catalog_url") or "").strip().lower()
    target_title = compact_whitespace(str(book.get("title") or "")).lower()
    target_author = compact_whitespace(str(book.get("author") or "")).lower()
    for path in library_dir.rglob("*.md"):
        try:
            rel_path = path.relative_to(vault_dir).as_posix()
            meta = parse_basic_frontmatter(path.read_text(encoding="utf-8-sig", errors="replace"))
        except (OSError, UnicodeError, ValueError):
            continue
        if meta.get("type") != "book":
            continue
        note_key = str(meta.get("openlibrary_key") or "").strip().lower()
        if target_key and note_key and target_key == note_key:
            return rel_path
        note_catalog_url = str(meta.get("catalog_url") or "").strip().lower()
        if target_catalog_url and note_catalog_url and target_catalog_url == note_catalog_url:
            return rel_path
        note_isbn = str(meta.get("isbn") or "").strip().lower()
        if target_isbn and note_isbn and target_isbn == note_isbn:
            return rel_path
        note_title = compact_whitespace(str(meta.get("book_title") or "")).lower()
        note_author = compact_whitespace(str(meta.get("book_author") or "")).lower()
        if target_title and note_title == target_title and (not target_author or not note_author or target_author == note_author):
            return rel_path
    return ""


def format_video_analysis_report(report) -> str:
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


def lookup_book_catalog(book: dict[str, object], book_lookup_enabled: bool = True) -> dict[str, object]:
    if not book_lookup_enabled:
        return {"lookup_status": "disabled", "lookup_reason": "Book catalog lookup is disabled."}
    isbn = re.sub(r"[^0-9Xx]", "", str(book.get("isbn") or ""))
    title = compact_whitespace(str(book.get("title") or ""))
    author = compact_whitespace(str(book.get("author") or ""))
    evidence = compact_whitespace(str(book.get("evidence") or ""))
    if not any((isbn, title, evidence)):
        return {
            "lookup_status": "needs_clarification",
            "lookup_reason": "No readable title, author, ISBN, or spine evidence was available.",
        }
    candidates: list[dict[str, object]] = []
    errors: list[str] = []
    lookup_queries: list[str] = []
    checked_sources = ["openlibrary", "google_books"]

    openlibrary_params: dict[str, str] = {
        "limit": "5",
        "fields": "key,title,author_name,first_publish_year,isbn,cover_i,edition_count",
    }
    if isbn:
        openlibrary_params["isbn"] = isbn
    elif title:
        openlibrary_params["title"] = title
        if author:
            openlibrary_params["author"] = author
    else:
        openlibrary_params["q"] = evidence[:160]
    openlibrary_url = f"{OPEN_LIBRARY_SEARCH_URL}?{urlencode(openlibrary_params)}"
    lookup_queries.append(openlibrary_url)
    try:
        request = urllib.request.Request(openlibrary_url, headers={"Accept": "application/json", "User-Agent": "KnowledgeLab/1.0"})
        with urllib.request.urlopen(request, timeout=8.0) as response:
            payload = json.loads(response.read().decode("utf-8", errors="replace"))
        docs = payload.get("docs") if isinstance(payload, dict) else []
        if isinstance(docs, list):
            candidates.extend(normalize_openlibrary_candidate(doc) for doc in docs if isinstance(doc, dict))
    except Exception as exc:
        errors.append(f"openlibrary: {exc}")

    google_query = ""
    if isbn:
        google_query = f"isbn:{isbn}"
    elif title:
        google_query = f"intitle:{title}"
        if author:
            google_query += f" inauthor:{author}"
    else:
        google_query = evidence[:160]
    google_params: dict[str, str] = {
        "q": google_query,
        "maxResults": "5",
        "printType": "books",
        "projection": "lite",
    }
    google_url = f"{GOOGLE_BOOKS_SEARCH_URL}?{urlencode(google_params)}"
    lookup_queries.append(google_url)
    try:
        request = urllib.request.Request(google_url, headers={"Accept": "application/json", "User-Agent": "KnowledgeLab/1.0"})
        with urllib.request.urlopen(request, timeout=8.0) as response:
            payload = json.loads(response.read().decode("utf-8", errors="replace"))
        items = payload.get("items") if isinstance(payload, dict) else []
        if isinstance(items, list):
            candidates.extend(normalize_google_books_candidate(item) for item in items if isinstance(item, dict))
    except Exception as exc:
        errors.append(f"google_books: {exc}")

    result = select_best_book_lookup(book, candidates, errors, checked_sources)
    result["lookup_query"] = " | ".join(lookup_queries)
    return result


def enrich_detected_books(books: list[dict[str, object]], book_lookup_enabled: bool = True) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    enriched_books: list[dict[str, object]] = []
    unresolved: list[dict[str, object]] = []
    for book in books:
        lookup: dict[str, object] = {}
        try:
            lookup = lookup_book_catalog(book, book_lookup_enabled=book_lookup_enabled)
        except Exception as exc:
            lookup = {
                "lookup_status": "lookup_error",
                "lookup_reason": f"Book catalog lookup failed: {exc}",
            }
        enriched = merge_book_lookup(book, lookup)
        enriched["book_topic"] = str(enriched.get("book_topic") or classify_book_topic(enriched))
        enriched_books.append(enriched)
        lookup_status = str(enriched.get("lookup_status") or "")
        if lookup_status in {"needs_clarification", "not_found", "lookup_error"}:
            unresolved.append({
                "region": "",
                "reason": f"book lookup {lookup_status}",
                "evidence": (
                    str(enriched.get("lookup_reason") or "")
                    or f"{book.get('title', '')} {book.get('author', '')}".strip()
                ),
            })
    return enriched_books, unresolved


def web_enrich_books(books: list[dict[str, object]]) -> list[dict[str, object]]:
    """Search DuckDuckGo for books without confirmed author/title."""
    from knowledgelab.llm.web_search import fetch_web_search_results

    for book in books:
        title = str(book.get("title") or "").strip()
        author = str(book.get("author") or "").strip()
        if not title:
            continue
        if author and len(author) > 2:
            continue

        query = f"{title} книга автор"
        try:
            results = fetch_web_search_results(query, max_results=3, timeout=8)
        except Exception:
            continue

        if not results:
            continue

        combined_text = " ".join(
            f"{r.get('title', '')} {r.get('snippet', '')}"
            for r in results
        ).lower()

        if not author or len(author) <= 2:
            import re
            author_patterns = [
                rf"(?:автор[:\s]+)([А-ЯЁа-яё][а-яё]+ [А-ЯЁа-яё][а-яё]+(?:\s*,\s*[А-ЯЁа-яё][а-яё]+ [А-ЯЁа-яё][а-яё]+)*)",
                rf"{re.escape(title.lower())}[^.]*?([А-ЯЁ][а-яё]+ [А-ЯЁ][а-яё]+(?:\s+и\s+[А-ЯЁ][а-яё]+ [А-ЯЁ][а-яё]+)*)",
                r"(?:by|от)\s+([A-Z][a-z]+ [A-Z][a-z]+(?:\s+and\s+[A-Z][a-z]+ [A-Z][a-z]+)*)",
            ]
            for pattern in author_patterns:
                match = re.search(pattern, combined_text, re.IGNORECASE)
                if match:
                    found_author = match.group(1).strip()
                    if len(found_author) > 3 and found_author.lower() not in title.lower():
                        book["author"] = found_author
                        book["author_source"] = "web_search"
                        break

        if not str(book.get("isbn") or ""):
            import re
            isbn_match = re.search(r"(?:isbn[:\s-]*)?(\d[\d-]{9,16}\d)", combined_text)
            if isbn_match:
                book["isbn"] = isbn_match.group(1).replace("-", "")

    return books


def save_detected_book_notes(books: list[dict[str, object]], source_rel_path: str, source_image_path: str, vault_dir: Path = VAULT_DIR, allow_unverified: bool = False) -> list[str]:
    saved: list[str] = []
    for book in books:
        if not book.get("title"):
            continue
        if not allow_unverified and str(book.get("lookup_status") or "").strip() in {"needs_clarification", "not_found", "lookup_error"}:
            continue
        book["book_topic"] = str(book.get("book_topic") or classify_book_topic(book))
        existing = find_existing_book_note(book, vault_dir=vault_dir)
        if existing:
            book["vault_note"] = existing
            saved.append(existing)
            continue
        destination = vault_dir / "50 Library" / book_note_slug(book)
        destination.mkdir(parents=True, exist_ok=True)
        path = unique_path(destination / "Book.md")
        path.write_text(render_book_note_markdown(book, source_rel_path, source_image_path), encoding="utf-8-sig")
        rel_path = path.relative_to(vault_dir).as_posix()
        book["vault_note"] = rel_path
        saved.append(rel_path)
    return saved


def update_bookshelf_note_result(rel_path: str, result: dict[str, list[dict[str, object]]], created_notes: list[str], vault_dir: Path = VAULT_DIR, error: str = "") -> None:
    path = vault_dir / rel_path.replace("/", os.sep)
    text = path.read_text(encoding="utf-8-sig", errors="replace") if path.exists() else ""
    status = "failed" if error else "processed"
    if "bookshelf_detection_status:" in text:
        text = re.sub(r'bookshelf_detection_status:\s*".*?"', f'bookshelf_detection_status: "{status}"', text, count=1)
        text = re.sub(r"bookshelf_detection_status:\s*[^\n]+", f'bookshelf_detection_status: "{status}"', text, count=1)
    elif text.startswith("---\n"):
        text = re.sub(r"\A---\n", f"---\nbookshelf_detection_status: \"{status}\"\n", text, count=1)
    section = render_bookshelf_detection_section(result, created_notes, error)
    if "## Bookshelf Detection Result" in text:
        text = re.sub(r"\n## Bookshelf Detection Result\n.*\Z", "\n" + section + "\n", text, flags=re.DOTALL)
    else:
        text = text.rstrip() + "\n\n" + section + "\n"
    path.write_text(text, encoding="utf-8-sig")


def call_bookshelf_vision(image_path: Path, kind: str, caption: str, vision_model: str, vision_ready: bool, loaded_models: list[str], base_url: str, timeout: int) -> dict[str, list[dict[str, object]]]:
    if not vision_ready:
        loaded = ", ".join(loaded_models) if loaded_models else "нет загруженных моделей"
        raise RuntimeError(
            "Не загружена vision/VL-модель в LM Studio. "
            "Чтобы KnowledgeLab сам находил книги по фото полки или корешкам, загрузите в LM Studio модель с поддержкой изображений "
            "(например Qwen2.5-VL, LLaVA, MiniCPM-V, Pixtral или другую vision-модель) "
            "или задайте KNOWLEDGELAB_VISION_MODEL. "
            f"Сейчас загружено: {loaded}. Текстовая модель не может надежно читать изображение."
        )
    prompt = (
        "Inspect this image for books. It may be a bookshelf, a single book cover/spine, "
        "a book page, or an unrelated image. Return only strict JSON, no markdown.\n\n"
        "If the image is unrelated to books, return {\"detected_books\": [], \"unresolved\": []}.\n"
        "If a book is visible but title/author cannot be read, put that item in unresolved.\n"
        "Create one detected_books item per readable or strongly inferable book. Work like a bookshelf inventory table: scan left-to-right and top-to-bottom, record region/position, readable text, and evidence.\n"
        "Use status \"found\" when the title/author is readable. Use status \"inferred\" only when visual context strongly suggests a known book but the spine text is partly hidden; include visual_guess and guess_reason. Use status \"uncertain\" for weak guesses and put the same item in unresolved if it needs user confirmation.\n"
        "Do not invent full metadata beyond visible evidence and cautious visual guesses.\n\n"
        "JSON schema:\n"
        "{\n"
        "  \"detected_books\": [\n"
        "    {\n"
        "      \"region\": \"top row item 1 / main row left / etc\",\n"
        "      \"title\": \"visible title\",\n"
        "      \"author\": \"visible author or empty string\",\n"
        "      \"isbn\": \"visible ISBN or empty string\",\n"
        "      \"visible_text\": \"raw readable spine/cover text\",\n"
        "      \"visual_guess\": \"cautious visual guess or empty string\",\n"
        "      \"guess_reason\": \"why the visual guess may be right\",\n"
        "      \"evidence\": \"short visible spine/cover text that supports the match\",\n"
        "      \"confidence\": 0.0,\n"
        "      \"status\": \"found, inferred, uncertain, or unreadable\"\n"
        "    }\n"
        "  ],\n"
        "  \"unresolved\": [\n"
        "    {\"region\": \"left/top/etc\", \"reason\": \"blurry/glare/too small/hidden\", \"evidence\": \"partial visible text\"}\n"
        "  ]\n"
        "}\n\n"
        f"Intake kind: {kind}\n"
        f"User caption or hint: {caption or '(none)'}"
    )
    payload = {
        "model": vision_model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You extract visible book metadata from images inside the local KnowledgeLab app. "
                    "The request is routed through the user's local LM Studio server, not a hosted cloud API. "
                    "Return strict JSON only."
                ),
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": image_data_url(image_path)}},
                ],
            },
        ],
        "temperature": 0.0,
        "max_tokens": 1800,
        "stream": False,
    }
    url = f"{base_url}/chat/completions"
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json", "User-Agent": "KnowledgeLab/1.0"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=min(timeout, 240)) as response:
        raw_response = json.loads(response.read().decode("utf-8", errors="replace"))
    if raw_response.get("error"):
        raise RuntimeError(str(raw_response.get("error")))
    choice = (raw_response.get("choices") or [{}])[0]
    message = choice.get("message") if isinstance(choice, dict) else {}
    content = str((message.get("content") or "") if isinstance(message, dict) else "")
    reasoning = str((message.get("reasoning_content") or "") if isinstance(message, dict) else "")
    raw_text = content or reasoning
    if not raw_text.strip():
        raise RuntimeError("vision model returned an empty response")
    result = parse_bookshelf_detection_response(raw_text)
    if not result["detected_books"] and not result["unresolved"] and raw_text.strip():
        result["unresolved"].append({
            "region": "",
            "reason": "vision model returned non-JSON or no structured books",
            "evidence": compact_whitespace(raw_text)[:500],
        })
    return result
