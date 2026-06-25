from __future__ import annotations

import json
import re
import urllib.request
from urllib.parse import urlencode

from knowledgelab.config import (
    GOOGLE_BOOKS_SEARCH_URL,
    GUTENDEX_SEARCH_URL,
    INTERNET_ARCHIVE_ADVANCEDSEARCH_URL,
    INTERNET_ARCHIVE_METADATA_URL,
    OPEN_LIBRARY_SEARCH_URL,
)
from knowledgelab.utils.text import compact_whitespace


USER_AGENT = "KnowledgeLab/1.0"


def fetch_json(url: str, timeout: float = 8.0) -> dict[str, object]:
    request = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8", errors="replace"))
    return payload if isinstance(payload, dict) else {}


def book_query(book: dict[str, object], limit: int = 160) -> str:
    title = compact_whitespace(str(book.get("title") or book.get("canonical_title") or ""))
    author = compact_whitespace(str(book.get("author") or book.get("canonical_author") or ""))
    isbn = re.sub(r"[^0-9Xx]", "", str(book.get("isbn") or ""))
    if isbn:
        return isbn
    return compact_whitespace(" ".join(part for part in (title, author) if part))[:limit]


def search_openlibrary(book: dict[str, object], timeout: float = 8.0) -> tuple[list[dict[str, object]], str]:
    isbn = re.sub(r"[^0-9Xx]", "", str(book.get("isbn") or ""))
    title = compact_whitespace(str(book.get("title") or ""))
    author = compact_whitespace(str(book.get("author") or ""))
    evidence = compact_whitespace(str(book.get("evidence") or ""))
    params: dict[str, str] = {
        "limit": "5",
        "fields": "key,title,author_name,first_publish_year,isbn,cover_i,edition_count",
    }
    if isbn:
        params["isbn"] = isbn
    elif title:
        params["title"] = title
        if author:
            params["author"] = author
    else:
        params["q"] = evidence[:160]
    url = f"{OPEN_LIBRARY_SEARCH_URL}?{urlencode(params)}"
    payload = fetch_json(url, timeout=timeout)
    docs = payload.get("docs") if isinstance(payload, dict) else []
    candidates: list[dict[str, object]] = []
    if isinstance(docs, list):
        for doc in docs:
            if not isinstance(doc, dict):
                continue
            title_value = compact_whitespace(str(doc.get("title") or ""))
            authors = doc.get("author_name") if isinstance(doc.get("author_name"), list) else []
            isbns = doc.get("isbn") if isinstance(doc.get("isbn"), list) else []
            key = str(doc.get("key") or "").strip()
            cover_i = doc.get("cover_i")
            candidates.append({
                "canonical_title": title_value,
                "canonical_author": compact_whitespace(str(authors[0])) if authors else "",
                "isbn": str(isbns[0]) if isbns else "",
                "openlibrary_key": key,
                "catalog_url": f"https://openlibrary.org{key}" if key.startswith("/") else "",
                "cover_url": f"https://covers.openlibrary.org/b/id/{cover_i}-L.jpg" if cover_i else "",
                "first_publish_year": doc.get("first_publish_year", ""),
                "edition_count": doc.get("edition_count", ""),
                "source_catalog": "openlibrary",
            })
    return candidates, url


def search_google_books(book: dict[str, object], timeout: float = 8.0) -> tuple[list[dict[str, object]], str]:
    isbn = re.sub(r"[^0-9Xx]", "", str(book.get("isbn") or ""))
    title = compact_whitespace(str(book.get("title") or ""))
    author = compact_whitespace(str(book.get("author") or ""))
    evidence = compact_whitespace(str(book.get("evidence") or ""))
    if isbn:
        query = f"isbn:{isbn}"
    elif title:
        query = f"intitle:{title}" + (f" inauthor:{author}" if author else "")
    else:
        query = evidence[:160]
    params = {"q": query, "maxResults": "5", "printType": "books", "projection": "lite"}
    url = f"{GOOGLE_BOOKS_SEARCH_URL}?{urlencode(params)}"
    payload = fetch_json(url, timeout=timeout)
    items = payload.get("items") if isinstance(payload, dict) else []
    candidates: list[dict[str, object]] = []
    if isinstance(items, list):
        for item in items:
            if not isinstance(item, dict):
                continue
            volume = item.get("volumeInfo") if isinstance(item.get("volumeInfo"), dict) else {}
            authors = volume.get("authors") if isinstance(volume.get("authors"), list) else []
            identifiers = volume.get("industryIdentifiers") if isinstance(volume.get("industryIdentifiers"), list) else []
            found_isbn = ""
            for identifier in identifiers:
                if not isinstance(identifier, dict):
                    continue
                value = re.sub(r"[^0-9Xx]", "", str(identifier.get("identifier") or ""))
                if value and (not found_isbn or len(value) == 13):
                    found_isbn = value
            image_links = volume.get("imageLinks") if isinstance(volume.get("imageLinks"), dict) else {}
            published_date = str(volume.get("publishedDate") or "").strip()
            info_link = str(volume.get("infoLink") or volume.get("canonicalVolumeLink") or "").strip()
            candidates.append({
                "canonical_title": compact_whitespace(str(volume.get("title") or "")),
                "canonical_author": compact_whitespace(str(authors[0])) if authors else "",
                "isbn": found_isbn,
                "google_books_id": str(item.get("id") or "").strip(),
                "google_books_url": info_link,
                "catalog_url": info_link,
                "cover_url": str(image_links.get("thumbnail") or image_links.get("smallThumbnail") or "").strip(),
                "published_date": published_date,
                "first_publish_year": published_date[:4] if re.match(r"^\d{4}", published_date) else "",
                "publisher": compact_whitespace(str(volume.get("publisher") or "")),
                "page_count": volume.get("pageCount", ""),
                "source_catalog": "google_books",
            })
    return candidates, url


def search_gutendex(book: dict[str, object], timeout: float = 8.0) -> tuple[list[dict[str, object]], str]:
    query = book_query(book)
    if not query:
        return [], ""
    url = f"{GUTENDEX_SEARCH_URL}?{urlencode({'search': query})}"
    payload = fetch_json(url, timeout=timeout)
    results = payload.get("results") if isinstance(payload, dict) else []
    return ([item for item in results if isinstance(item, dict)], url) if isinstance(results, list) else ([], url)


def search_internet_archive(book: dict[str, object], timeout: float = 8.0) -> tuple[list[dict[str, object]], str]:
    query = book_query(book)
    if not query:
        return [], ""
    params: list[tuple[str, str]] = [
        ("q", f'title:("{query}") AND mediatype:texts'),
        ("fl[]", "identifier"),
        ("fl[]", "title"),
        ("fl[]", "creator"),
        ("fl[]", "possible-copyright-status"),
        ("rows", "5"),
        ("output", "json"),
    ]
    url = f"{INTERNET_ARCHIVE_ADVANCEDSEARCH_URL}?{urlencode(params)}"
    payload = fetch_json(url, timeout=timeout)
    response = payload.get("response") if isinstance(payload, dict) else {}
    docs = response.get("docs") if isinstance(response, dict) else []
    return ([item for item in docs if isinstance(item, dict)], url) if isinstance(docs, list) else ([], url)


def internet_archive_metadata(identifier: str, timeout: float = 8.0) -> dict[str, object]:
    identifier = identifier.strip()
    if not identifier:
        return {}
    return fetch_json(f"{INTERNET_ARCHIVE_METADATA_URL}/{identifier}", timeout=timeout)
