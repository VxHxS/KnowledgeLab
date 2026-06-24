from __future__ import annotations

from knowledgelab.utils.urls import (
    URL_RE,
    first_codepen_url,
    first_github_url,
    first_telegram_url,
    first_url,
    first_youtube_url,
    normalize_github_url,
    normalize_source_url_for_match,
    parse_codepen_url,
    parse_github_url,
    source_domain,
    stable_content_hash,
    video_source_id,
)


def test_url_re_matches_valid():
    assert URL_RE.search("visit https://example.com for info")


def test_url_re_rejects_non_url():
    assert URL_RE.search("no url here") is None


def test_first_url_extracts():
    assert first_url("see https://example.com ok") == "https://example.com"


def test_first_url_empty():
    assert first_url("no urls") == ""


def test_first_url_strips_trailing_punctuation():
    assert first_url("visit https://example.com.") == "https://example.com"


def test_first_youtube_url_extracts():
    url = "check https://www.youtube.com/watch?v=abc123"
    assert "youtube.com" in first_youtube_url(url)


def test_first_youtube_url_short():
    url = "https://youtu.be/abc123"
    assert "youtu.be" in first_youtube_url(url)


def test_first_youtube_url_empty():
    assert first_youtube_url("no youtube") == ""


def test_first_telegram_url_extracts():
    url = "https://t.me/channel/123"
    assert first_telegram_url(url) == "https://t.me/channel/123"


def test_first_telegram_url_empty():
    assert first_telegram_url("no telegram") == ""


def test_first_codepen_url_extracts():
    url = "https://codepen.io/user/pen/abc123"
    assert first_codepen_url(url) == "https://codepen.io/user/pen/abc123"


def test_first_codepen_url_empty():
    assert first_codepen_url("no codepen") == ""


def test_first_github_url_extracts():
    url = "https://github.com/user/repo"
    assert first_github_url(url) == "https://github.com/user/repo"


def test_first_github_url_short():
    text = "github.com/user/repo is cool"
    result = first_github_url(text)
    assert "github.com" in result


def test_first_github_url_empty():
    assert first_github_url("no github") == ""


def test_parse_codepen_url_valid():
    result = parse_codepen_url("https://codepen.io/user/pen/abc123")
    assert result["codepen_owner"] == "user"
    assert result["codepen_id"] == "abc123"
    assert "codepen.io" in result["codepen_url"]


def test_parse_codepen_url_invalid():
    assert parse_codepen_url("https://example.com") == {}


def test_parse_github_url_valid():
    result = parse_github_url("https://github.com/user/repo")
    assert result["github_owner"] == "user"
    assert result["github_repo"] == "repo"
    assert result["github_full_name"] == "user/repo"
    assert result["github_clone_url"] == "https://github.com/user/repo.git"


def test_parse_github_url_strips_git():
    result = parse_github_url("https://github.com/user/repo.git")
    assert result["github_repo"] == "repo"


def test_parse_github_url_invalid_host():
    assert parse_github_url("https://gitlab.com/user/repo") == {}


def test_parse_github_url_too_few_parts():
    assert parse_github_url("https://github.com") == {}


def test_normalize_github_url_adds_prefix():
    result = normalize_github_url("github.com/user/repo")
    assert result.startswith("https://")


def test_normalize_github_url_empty():
    assert normalize_github_url("") == ""


def test_source_domain():
    assert source_domain("https://www.example.com/path") == "example.com"


def test_source_domain_no_www():
    assert source_domain("https://example.com/path") == "example.com"


def test_stable_content_hash_consistent():
    h1 = stable_content_hash("hello")
    h2 = stable_content_hash("hello")
    assert h1 == h2


def test_stable_content_hash_hex():
    result = stable_content_hash("test")
    assert all(c in "0123456789abcdef" for c in result)


def test_normalize_source_url_for_match():
    result = normalize_source_url_for_match("https://www.example.com/path/")
    assert result == "example.com/path"


def test_normalize_source_url_for_match_strips_protocol():
    result = normalize_source_url_for_match("https://example.com")
    assert result == "example.com"


def test_video_source_id_returns_16_hex():
    result = video_source_id("https://youtube.com/watch?v=abc")
    assert len(result) == 16
    assert all(c in "0123456789abcdef" for c in result)


def test_video_source_id_consistent():
    assert video_source_id("test") == video_source_id("test")
