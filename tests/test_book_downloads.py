from __future__ import annotations

from knowledgelab.models import BookDownloadResult
from knowledgelab.vision import book_downloads


def test_choose_gutendex_file_prefers_allowed_epub():
    item = {
        "copyright": False,
        "formats": {
            "text/html": "https://example.test/book.html",
            "application/epub+zip": "https://example.test/book.epub",
        },
    }
    url, suffix, reason = book_downloads.choose_gutendex_file(item, ["epub", "txt"])
    assert url == "https://example.test/book.epub"
    assert suffix == ".epub"
    assert reason == ""


def test_choose_gutendex_file_rejects_copyrighted_item():
    item = {"copyright": True, "formats": {"application/epub+zip": "https://example.test/book.epub"}}
    url, _suffix, reason = book_downloads.choose_gutendex_file(item, ["epub"])
    assert url == ""
    assert "copyrighted" in reason


def test_apply_download_result_updates_book_dict():
    book = {"title": "Clean Code"}
    result = BookDownloadResult(
        status="downloaded",
        reason="ok",
        source_name="gutenberg",
        url="https://example.test/book.epub",
        local_file_rel_path="50 Library/clean-code/Files/book.epub",
        file_name="book.epub",
        file_format="epub",
        size_bytes=123,
    )
    book_downloads.apply_download_result(book, result)
    assert book["download_status"] == "downloaded"
    assert book["local_file_rel_path"].endswith("book.epub")


def test_resolve_legal_book_download_uses_gutenberg(monkeypatch, tmp_path):
    def fake_search(_book, timeout=8.0):
        return [{"copyright": False, "formats": {"application/epub+zip": "https://example.test/book.epub"}}], "query"

    def fake_download(url, destination_dir, file_name, **kwargs):
        return BookDownloadResult(
            status="downloaded",
            reason="Downloaded from a legal open source.",
            url=url,
            local_file_rel_path=f"50 Library/Clean Code/Files/{file_name}",
            file_name=file_name,
            file_format="epub",
            size_bytes=10,
        )

    monkeypatch.setattr(book_downloads, "search_gutendex", fake_search)
    monkeypatch.setattr(book_downloads, "download_to_vault", fake_download)
    result = book_downloads.resolve_legal_book_download(
        {"title": "Clean Code", "author": "Robert C. Martin"},
        vault_dir=tmp_path,
        legal_sources=["gutenberg"],
        formats=["epub"],
    )
    assert result.status == "downloaded"
    assert result.source_name == "gutenberg"


def test_resolve_legal_book_download_rejects_unclear_archive_rights(monkeypatch, tmp_path):
    monkeypatch.setattr(book_downloads, "search_gutendex", lambda _book, timeout=8.0: ([], ""))
    monkeypatch.setattr(book_downloads, "search_internet_archive", lambda _book, timeout=8.0: ([{"identifier": "x"}], "query"))
    monkeypatch.setattr(book_downloads, "internet_archive_metadata", lambda identifier, timeout=8.0: {"metadata": {"title": "X"}, "files": []})
    result = book_downloads.resolve_legal_book_download(
        {"title": "Some Modern Book"},
        vault_dir=tmp_path,
        legal_sources=["internet_archive"],
    )
    assert result.status == "download_not_allowed"
    assert "not clearly public domain" in result.reason
