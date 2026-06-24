from __future__ import annotations

from pathlib import Path

from knowledgelab.config import LAYER_ACTIVE, LAYER_FINISHED_PROJECTS, VAULT_DIR
from knowledgelab.models import KnowledgeRoute, ReferenceLink
from knowledgelab.vault.capture import (
    classify_source_file,
    extraction_label,
    file_kind_label,
    render_capture_markdown,
    render_file_capture_markdown,
    capture_destination,
)


def test_capture_destination_general_article():
    dest = capture_destination("general", "React", "article")
    assert str(dest).startswith(str(VAULT_DIR))


def test_capture_destination_web_github():
    dest = capture_destination("web", "React", "github_repository")
    assert "Web Development" in str(dest)


def test_capture_destination_game_youtube():
    dest = capture_destination("game", "Unity", "youtube_link")
    assert "My Game" in str(dest)


def test_capture_destination_finished_projects():
    dest = capture_destination(
        "general", "Project", "article", LAYER_FINISHED_PROJECTS,
        project="my-project", project_section="web",
    )
    assert "40 Finished Projects" in str(dest)


def test_capture_destination_book_in_library():
    dest = capture_destination("general", "Clean Code", "book_photo")
    assert "50 Library" in str(dest)


def test_classify_source_file_text():
    assert classify_source_file(Path("file.txt")) == "text_file"


def test_classify_source_file_image():
    assert classify_source_file(Path("photo.jpg")) == "image_capture"


def test_classify_source_file_audio():
    assert classify_source_file(Path("sound.mp3")) == "audio_file"


def test_classify_source_file_video():
    assert classify_source_file(Path("clip.mp4")) == "video_file"


def test_classify_source_file_archive():
    assert classify_source_file(Path("archive.zip")) == "archive_file"


def test_classify_source_file_generic():
    assert classify_source_file(Path("file.xyz")) == "generic_file"


def test_extraction_label_known():
    assert extraction_label("article") == "custom extraction"


def test_extraction_label_image():
    assert "OCR" in extraction_label("image_capture")


def test_extraction_label_text_file():
    assert "text" in extraction_label("text_file").lower()


def test_file_kind_label_known():
    assert file_kind_label("image_capture") == "image"


def test_file_kind_label_github():
    assert file_kind_label("github_repository") == "GitHub"


def test_file_kind_label_unknown():
    assert file_kind_label("unknown_kind") == "file"


def test_render_capture_markdown_frontmatter(tmp_path):
    md = render_capture_markdown(
        "https://example.com/article",
        "Web Development", "web", "web-development", "React", "article",
    )
    assert md.startswith("---\n")
    assert "type: article" in md
    assert "scope: web" in md


def test_render_capture_markdown_has_title():
    md = render_capture_markdown(
        "Some text about React",
        "General", "general", "", "React", "capture",
    )
    assert "# " in md


def test_render_file_capture_markdown(tmp_path):
    fake_file = tmp_path / "test.txt"
    fake_file.write_text("hello")
    md = render_file_capture_markdown(
        fake_file, "Test caption", "General", "general", "", "React",
        "text_file", "extracted text", "extracted",
    )
    assert md.startswith("---\n")
    assert "type: text_file" in md
    assert "extracted text" in md
