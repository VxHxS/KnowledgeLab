from __future__ import annotations

from knowledgelab.routing.topics import builtin_topic_names, render_topic_note_markdown


def test_builtin_topic_names_non_empty():
    names = builtin_topic_names()
    assert len(names) > 0
    assert isinstance(names, set)


def test_builtin_topic_names_contains_general():
    assert "General" in builtin_topic_names()


def test_builtin_topic_names_contains_web():
    names = builtin_topic_names()
    assert "Web" in names or "Web Development" in names


def test_render_topic_note_markdown_frontmatter():
    result = render_topic_note_markdown("React", "web")
    assert result.startswith("---\n")
    assert "type: topic" in result
    assert "topic:" in result
    assert "scope:" in result


def test_render_topic_note_markdown_has_heading():
    result = render_topic_note_markdown("React", "web")
    assert "# React" in result


def test_render_topic_note_markdown_has_project():
    result = render_topic_note_markdown("Unity", "game", "my-game")
    assert "project:" in result
    assert "my-game" in result


def test_render_topic_note_markdown_has_timestamp():
    result = render_topic_note_markdown("CSS", "web")
    assert "created_at:" in result
