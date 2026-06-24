from __future__ import annotations

from knowledgelab.material.web import (
    ArticleTextExtractor,
    VisiblePageTextExtractor,
    classify_reference_link_role,
    dedupe_markdown_lines,
    extract_article_markdown_from_html,
    extract_human_strings_from_js,
    is_human_js_text,
)


def test_article_text_extractor_title():
    html = "<html><head><title>Test Title</title></head><body><p>Hello</p></body></html>"
    ext = ArticleTextExtractor()
    ext.feed(html)
    assert ext.title == "Test Title"


def test_article_text_extractor_paragraph():
    html = "<html><body><p>Hello world</p></body></html>"
    ext = ArticleTextExtractor()
    ext.feed(html)
    assert "Hello world" in ext.markdown()


def test_article_text_extractor_skips_script():
    html = "<html><body><script>var x = 1;</script><p>Visible</p></body></html>"
    ext = ArticleTextExtractor()
    ext.feed(html)
    assert "var x" not in ext.markdown()
    assert "Visible" in ext.markdown()


def test_visible_page_text_extractor():
    html = "<html><body><p>Some text</p></body></html>"
    ext = VisiblePageTextExtractor()
    ext.feed(html)
    assert "Some text" in ext.markdown()


def test_visible_page_text_extractor_headings():
    html = "<html><body><h1>Title</h1><p>Body</p></body></html>"
    ext = VisiblePageTextExtractor()
    ext.feed(html)
    md = ext.markdown()
    assert "## Title" in md or "Title" in md


def test_visible_page_text_extractor_meta():
    html = '<html><head><meta name="description" content="Page description"></head><body><p>Content</p></body></html>'
    ext = VisiblePageTextExtractor()
    ext.feed(html)
    md = ext.markdown()
    assert "Page description" in md


def test_extract_article_markdown_from_html():
    html = "<html><head><title>Article</title></head><body><p>Main content paragraph.</p></body></html>"
    title, md = extract_article_markdown_from_html(html, "https://example.com")
    assert title == "Article"
    assert "Main content" in md


def test_extract_article_markdown_fallback():
    html = "<html><body><p>Short</p></body></html>"
    title, md = extract_article_markdown_from_html(html, "https://example.com")
    assert isinstance(title, str)
    assert isinstance(md, str)


def test_dedupe_markdown_lines():
    md = "This is a long line that exceeds the threshold\nShort\nThis is a long line that exceeds the threshold\nAnother"
    result = dedupe_markdown_lines(md)
    assert result.count("This is a long line that exceeds the threshold") == 1


def test_dedupe_markdown_lines_blank():
    md = "Line one\n\n\nLine two"
    result = dedupe_markdown_lines(md)
    assert "\n\n\n" not in result


def test_is_human_js_text_normal():
    assert is_human_js_text("Hello World") is True


def test_is_human_js_text_too_short():
    assert is_human_js_text("ab") is False


def test_is_human_js_text_code():
    assert is_human_js_text("function() { return true; }") is False


def test_is_human_js_text_css():
    assert is_human_js_text("10px solid #000000") is False


def test_is_human_js_text_empty():
    assert is_human_js_text("") is False


def test_is_human_js_text_no_letters():
    assert is_human_js_text("123456789") is False


def test_extract_human_strings_from_js():
    js = 'var msg = "Hello World"; var bad = "function() {}";'
    result = extract_human_strings_from_js(js)
    assert any("Hello World" in s for s in result)


def test_extract_human_strings_from_js_empty():
    result = extract_human_strings_from_js("")
    assert result == []


def test_classify_reference_link_role_codepen():
    role = classify_reference_link_role(
        "https://codepen.io/user/pen/abc123", "example pen", "",
    )
    assert role == "codepen_pen"


def test_classify_reference_link_role_github():
    role = classify_reference_link_role(
        "https://github.com/user/repo", "source code", "",
    )
    assert role == "github_repository"


def test_classify_reference_link_role_example():
    role = classify_reference_link_role(
        "https://example.com/demo", "check this demo", "https://parent.com",
    )
    assert role == "example_reference"


def test_classify_reference_link_role_empty():
    role = classify_reference_link_role(
        "https://random.com/page", "just text", "https://random.com",
    )
    assert role == ""
