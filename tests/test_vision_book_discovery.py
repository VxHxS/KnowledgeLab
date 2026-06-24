from __future__ import annotations

from knowledgelab.models import BookDiscoveryReport, KnowledgeRoute, MaterialRoutingReport
from knowledgelab.vision.book_discovery import (
    book_note_slug,
    classify_book_topic,
    format_book_discovery_report,
    format_material_routing_report,
    merge_book_lookup,
    normalize_detected_book,
    parse_bookshelf_detection_response,
    score_book_lookup_candidate,
    select_best_book_lookup,
)


def test_normalize_detected_book_valid():
    item = {"title": "Clean Code", "author": "Robert Martin", "confidence": 0.9}
    result = normalize_detected_book(item)
    assert result["title"] == "Clean Code"
    assert result["author"] == "Robert Martin"
    assert result["status"] == "found"


def test_normalize_detected_book_no_title():
    result = normalize_detected_book({"evidence": "some text"})
    assert result["status"] == "unreadable"


def test_normalize_detected_book_not_dict():
    assert normalize_detected_book("not a dict") == {}


def test_normalize_detected_book_clamps_confidence():
    result = normalize_detected_book({"title": "Book", "confidence": 5.0})
    assert result["confidence"] == 1.0


def test_parse_bookshelf_detection_response_valid():
    text = '{"detected_books": [{"title": "Book1", "author": "Author1"}]}'
    result = parse_bookshelf_detection_response(text)
    assert len(result["detected_books"]) == 1
    assert result["detected_books"][0]["title"] == "Book1"


def test_parse_bookshelf_detection_response_empty():
    result = parse_bookshelf_detection_response("no json here")
    assert result["detected_books"] == []


def test_parse_bookshelf_detection_response_unreadable():
    text = '{"detected_books": [{"status": "unreadable", "evidence": "blur"}]}'
    result = parse_bookshelf_detection_response(text)
    assert len(result["unresolved"]) > 0


def test_classify_book_topic_web():
    book = {"title": "JavaScript Design Patterns", "author": "Addy Osmani"}
    assert classify_book_topic(book) == "Web Development"


def test_classify_book_topic_game():
    book = {"title": "Unity Game Development", "author": "Someone"}
    assert classify_book_topic(book) == "Game Development"


def test_classify_book_topic_programming():
    book = {"title": "Python Programming", "author": "Author"}
    assert classify_book_topic(book) == "Programming"


def test_classify_book_topic_library_fallback():
    book = {"title": "Mystery Novel", "author": "Writer"}
    assert classify_book_topic(book) == "Library"


def test_score_book_lookup_candidate_exact_title():
    book = {"title": "Clean Code", "author": "Robert Martin"}
    candidate = {"canonical_title": "Clean Code", "canonical_author": "Robert Martin", "isbn": ""}
    score = score_book_lookup_candidate(book, candidate)
    assert score > 0.7


def test_score_book_lookup_candidate_isbn_match():
    book = {"title": "Book", "author": "", "isbn": "9780132350884"}
    candidate = {"canonical_title": "Different", "canonical_author": "", "isbn": "9780132350884"}
    score = score_book_lookup_candidate(book, candidate)
    assert score >= 0.98


def test_select_best_book_lookup_found():
    book = {"title": "Clean Code", "author": "Robert Martin", "isbn": ""}
    candidates = [
        {"canonical_title": "Clean Code", "canonical_author": "Robert Martin", "source_catalog": "openlibrary", "isbn": ""},
    ]
    result = select_best_book_lookup(book, candidates)
    assert result["lookup_status"] == "found"


def test_select_best_book_lookup_empty():
    book = {"title": "Unknown", "author": "", "isbn": ""}
    result = select_best_book_lookup(book, [])
    assert result["lookup_status"] == "not_found"


def test_merge_book_lookup_with_data():
    book = {"title": "Visible Title", "author": "Visible Author"}
    lookup = {"canonical_title": "Canonical Title", "canonical_author": "Canonical Author", "isbn": "123"}
    merged = merge_book_lookup(book, lookup)
    assert merged["title"] == "Canonical Title"
    assert merged["visible_title"] == "Visible Title"


def test_merge_book_lookup_empty():
    book = {"title": "Book"}
    merged = merge_book_lookup(book, {})
    assert merged["title"] == "Book"
    assert merged.get("lookup_status") == "not_attempted"


def test_book_note_slug():
    book = {"title": "Clean Code", "author": "Robert Martin"}
    slug = book_note_slug(book)
    assert "clean" in slug
    assert "code" in slug


def test_book_note_slug_with_title_only():
    slug = book_note_slug({"title": "Some Book", "author": ""})
    assert "some" in slug
    assert "book" in slug


def test_format_material_routing_report_empty():
    assert format_material_routing_report([]) == ""


def test_format_material_routing_report_with_items():
    reports = [
        MaterialRoutingReport("file1.md", "article", "React", "path1"),
        MaterialRoutingReport("file2.md", "article", "React", "path2", created_topic=True),
    ]
    result = format_material_routing_report(reports)
    assert "React" in result
    assert "2 материал" in result


def test_format_book_discovery_report_empty():
    report = BookDiscoveryReport("note.md", added=[], needs_clarification=[], not_found=[])
    result = format_book_discovery_report(report)
    assert "Добавлено: 0" in result
    assert "Нужно уточнить: 0" in result
