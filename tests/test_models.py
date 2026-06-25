from __future__ import annotations

import pytest

from knowledgelab.config import LAYER_ACTIVE, LAYER_FINISHED_PROJECTS
from knowledgelab.models import (
    BookCandidate,
    BookDiscoveryReport,
    BookDownloadResult,
    BookLookupResult,
    BookPipelineResult,
    CodePenSnapshot,
    BackgroundTaskRecord,
    KnowledgeRoute,
    ManualBookEntry,
    MaterialRoutingReport,
    ProjectGuess,
    ReferenceLink,
    VideoAnalysisReport,
)


def test_knowledge_route_construction():
    route = KnowledgeRoute("General", "general", "")
    assert route.context_name == "General"
    assert route.scope == "general"
    assert route.project == ""
    assert route.layer == LAYER_ACTIVE


def test_knowledge_route_defaults():
    route = KnowledgeRoute("Web Development", "web")
    assert route.project == ""
    assert route.layer == LAYER_ACTIVE
    assert route.project_title == ""
    assert route.project_section == ""


def test_knowledge_route_is_finished_projects_false():
    route = KnowledgeRoute("General", "general", layer=LAYER_ACTIVE)
    assert route.is_finished_projects is False


def test_knowledge_route_is_finished_projects_true():
    route = KnowledgeRoute("Finished Projects", "all", layer=LAYER_FINISHED_PROJECTS)
    assert route.is_finished_projects is True


def test_knowledge_route_for_finished_index_non_finished():
    route = KnowledgeRoute("General", "general", "my-project")
    same = route.for_finished_index()
    assert same is route


def test_knowledge_route_for_finished_index_finished():
    route = KnowledgeRoute(
        "Finished Projects", "all", "my-project", LAYER_FINISHED_PROJECTS,
        project_title="My Project", project_section="web",
    )
    index = route.for_finished_index()
    assert index is not route
    assert index.scope == "all"
    assert index.project == ""
    assert index.project_section == "web"


def test_project_guess_construction():
    guess = ProjectGuess("My Project", "web", "game", 0.85)
    assert guess.title == "My Project"
    assert guess.confidence == 0.85


def test_project_guess_frozen():
    guess = ProjectGuess("Title", "section", "scope", 0.5)
    with pytest.raises(AttributeError):
        guess.title = "Other"


def test_material_routing_report_construction():
    report = MaterialRoutingReport("article.md", "article", "React", "20 Projects/Web/Notes")
    assert report.source_name == "article.md"
    assert report.created_topic is False


def test_material_routing_report_created_topic():
    report = MaterialRoutingReport("src.py", "solution", "Python", "path", created_topic=True)
    assert report.created_topic is True


def test_book_discovery_report_construction():
    report = BookDiscoveryReport("note.md", added=[], needs_clarification=[], not_found=[])
    assert report.parent_note == "note.md"
    assert report.added == []


def test_book_candidate_roundtrip():
    candidate = BookCandidate.from_book_dict({"title": "Clean Code", "author": "Robert C. Martin", "confidence": 0.9})
    assert candidate.title == "Clean Code"
    assert candidate.to_book_dict()["author"] == "Robert C. Martin"


def test_book_lookup_result_defaults():
    result = BookLookupResult("found")
    assert result.status == "found"
    assert result.book == {}
    assert result.candidates == []


def test_book_download_result_defaults():
    result = BookDownloadResult("download_not_available", reason="no legal file")
    assert result.status == "download_not_available"
    assert result.local_file_rel_path == ""


def test_book_pipeline_result_construction():
    report = BookDiscoveryReport("note.md", added=[], needs_clarification=[], not_found=[])
    result = BookPipelineResult("done", {"detected_books": [], "unresolved": []}, [], report)
    assert result.status == "done"
    assert result.report is report


def test_manual_book_entry_construction():
    entry = ManualBookEntry("Clean Code", author="Robert C. Martin")
    assert entry.title == "Clean Code"
    assert entry.author == "Robert C. Martin"
    assert entry.section == ""


def test_manual_book_entry_defaults():
    entry = ManualBookEntry("Book")
    assert entry.position == ""
    assert entry.user_evidence == ""


def test_video_analysis_report_construction():
    report = VideoAnalysisReport(
        "parent.md", "analysis.md", "youtube.com/x", "completed", "completed",
    )
    assert report.frame_count == 0
    assert report.warning == ""


def test_background_task_record_mutable():
    record = BackgroundTaskRecord("t1", "import", "Importing", "running")
    record.status = "completed"
    record.result = "done"
    assert record.status == "completed"
    assert record.result == "done"


def test_reference_link_construction():
    link = ReferenceLink("https://example.com", "Example", "reference article", "example_reference")
    assert link.url == "https://example.com"
    assert link.role == "example_reference"


def test_reference_link_frozen():
    link = ReferenceLink("url", "title", "ctx", "role")
    with pytest.raises(AttributeError):
        link.url = "other"


def test_codepen_snapshot_construction():
    snap = CodePenSnapshot("ok", "My Pen", "user", "description")
    assert snap.status == "ok"
    assert snap.html_code == ""
    assert snap.css_code == ""
    assert snap.js_code == ""


def test_codepen_snapshot_frozen():
    snap = CodePenSnapshot("ok", "Pen", "u", "d")
    with pytest.raises(AttributeError):
        snap.status = "fail"
