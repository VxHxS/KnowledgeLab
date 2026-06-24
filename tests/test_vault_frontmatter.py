from __future__ import annotations

from knowledgelab.vault.frontmatter import (
    infer_layer,
    infer_project,
    infer_scope,
    parse_basic_frontmatter,
    parse_frontmatter,
)


def test_parse_frontmatter_extracts_metadata():
    text = "---\ntitle: My Note\ntype: article\n---\n\n# Content"
    meta, body = parse_frontmatter(text)
    assert meta["title"] == "My Note"
    assert meta["type"] == "article"
    assert "# Content" in body


def test_parse_frontmatter_no_frontmatter():
    text = "# Just a heading\n\nContent here."
    meta, body = parse_frontmatter(text)
    assert meta == {}
    assert body == text


def test_parse_frontmatter_list_value():
    text = "---\ntags: [web, react, hooks]\n---\n\nBody"
    meta, _ = parse_frontmatter(text)
    assert meta["tags"] == ["web", "react", "hooks"]


def test_parse_frontmatter_skips_comments():
    text = "---\n# comment\ntitle: Test\n---\nBody"
    meta, _ = parse_frontmatter(text)
    assert "title" in meta


def test_parse_basic_frontmatter_extracts():
    text = "---\ntopic: React\nscope: web\n---\nBody"
    meta = parse_basic_frontmatter(text)
    assert meta["topic"] == "React"
    assert meta["scope"] == "web"


def test_parse_basic_frontmatter_empty():
    meta = parse_basic_frontmatter("No frontmatter here")
    assert meta == {}


def test_infer_scope_from_metadata():
    assert infer_scope("any/path.md", {"scope": "game"}) == "game"


def test_infer_scope_from_web_path():
    assert infer_scope("20 Projects/Web Development/file.md", {}) == "web"


def test_infer_scope_from_game_path():
    assert infer_scope("20 Projects/My Game/file.md", {}) == "game"


def test_infer_scope_general_default():
    assert infer_scope("10 General Knowledge/file.md", {}) == "general"


def test_infer_project_from_metadata():
    assert infer_project("any/path.md", {"project": "My Project"}) == "my-project"


def test_infer_project_from_finished_path():
    assert infer_project("40 Finished Projects/Web/My Site/file.md", {}) == "my-site"


def test_infer_project_from_projects_path():
    assert infer_project("20 Projects/Web Development/file.md", {}) == "web-development"


def test_infer_project_empty_default():
    assert infer_project("random/file.md", {}) == ""


def test_infer_layer_from_metadata():
    assert infer_layer("any/path.md", {"layer": "finished-projects"}) == "finished-projects"


def test_infer_layer_finished_path():
    assert infer_layer("40 Finished Projects/Web/file.md", {}) == "finished-projects"


def test_infer_layer_default():
    assert infer_layer("10 General/file.md", {}) == "active"
