from __future__ import annotations

from knowledgelab.utils.text import (
    clean_filename,
    compact_text,
    compact_whitespace,
    contains_any,
    extract_json_object,
    markdown_fence_text,
    now_iso,
    slugify,
    yaml_quote,
)


def test_now_iso_returns_string():
    result = now_iso()
    assert isinstance(result, str)


def test_now_iso_contains_T():
    result = now_iso()
    assert "T" in result


def test_compact_text_lowercase():
    assert compact_text("Hello World") == "hello world"


def test_compact_text_collapses_whitespace():
    assert compact_text("  a   b   c  ") == "a b c"


def test_compact_text_strips():
    assert compact_text("  test  ") == "test"


def test_contains_any_true():
    assert contains_any("I love React hooks", {"react", "vue"}) is True


def test_contains_any_false():
    assert contains_any("I love React hooks", {"angular", "vue"}) is False


def test_contains_any_cyrillic():
    assert contains_any("добавь в obsidian эту заметку", {"добавь в obsidian"}) is True


def test_clean_filename_removes_special_chars():
    result = clean_filename('file<>:"/\\|?*name')
    assert "<" not in result
    assert ">" not in result
    assert ":" not in result


def test_clean_filename_truncates():
    long_name = "a" * 200
    result = clean_filename(long_name)
    assert len(result) <= 120


def test_clean_filename_empty_fallback():
    result = clean_filename("")
    assert result == "note"


def test_slugify_lowercase():
    assert slugify("Hello World") == "hello-world"


def test_slugify_removes_special():
    result = slugify("hello! @world#")
    assert "!" not in result
    assert "@" not in result


def test_slugify_cyrillic():
    result = slugify("Привет Мир")
    assert "привет" in result


def test_slugify_empty_fallback():
    assert slugify("") == "note"


def test_slugify_collapses_dashes():
    result = slugify("a---b")
    assert "--" not in result


def test_compact_whitespace():
    assert compact_whitespace("  hello   world  ") == "hello world"


def test_compact_whitespace_empty():
    assert compact_whitespace("") == ""


def test_compact_whitespace_none_like():
    assert compact_whitespace(None) == ""


def test_yaml_quote_wraps_in_quotes():
    result = yaml_quote("hello")
    assert result.startswith('"')
    assert result.endswith('"')


def test_yaml_quote_escapes_backslash():
    result = yaml_quote("path\\to")
    assert "\\\\" in result


def test_yaml_quote_escapes_quotes():
    result = yaml_quote('say "hi"')
    assert '\\"' in result


def test_markdown_fence_text():
    result = markdown_fence_text("```code```")
    assert "```" not in result
    assert "'''" in result


def test_markdown_fence_text_strips():
    result = markdown_fence_text("  text  ")
    assert result == "text"


def test_extract_json_object_valid():
    result = extract_json_object('{"key": "value"}')
    assert result == {"key": "value"}


def test_extract_json_object_embedded():
    result = extract_json_object('some text {"key": 123} more text')
    assert result == {"key": 123}


def test_extract_json_object_empty():
    assert extract_json_object("") == {}


def test_extract_json_object_no_dict():
    result = extract_json_object("[1, 2, 3]")
    assert result == {}


def test_extract_json_object_malformed():
    result = extract_json_object("{not valid json}")
    assert result == {}
