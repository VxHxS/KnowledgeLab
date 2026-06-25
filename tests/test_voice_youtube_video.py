"""Tests for voice, youtube, and video modules."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from knowledgelab.llm.voice import build_voice_recognition_script, friendly_voice_error
from knowledgelab.material.youtube import build_youtube_sync_command
from knowledgelab.material.queue import launch_reindex, launch_reindex_command
from knowledgelab.material.video import (
    video_source_id, video_runtime_dir, parse_video_frame_response,
    format_video_analysis_report,
)
from knowledgelab.models import KnowledgeRoute, VideoAnalysisReport


class TestVoiceModule:
    def test_build_script_contains_timeout(self):
        script = build_voice_recognition_script(10)
        assert "10" in script
        assert "System.Speech" in script

    def test_build_script_default_timeout(self):
        script = build_voice_recognition_script()
        assert "SpeechRecognitionEngine" in script

    def test_friendly_voice_error_speech(self):
        msg, offer = friendly_voice_error("system.speech not found")
        assert "недоступен" in msg
        assert offer is True

    def test_friendly_voice_error_recognizer(self):
        msg, offer = friendly_voice_error("no recognizer installed")
        assert "микрофон" in msg
        assert offer is True

    def test_friendly_voice_error_default(self):
        msg, offer = friendly_voice_error("some random error")
        assert "Попробуйте еще раз" in msg
        assert offer is False

    def test_friendly_voice_error_empty(self):
        msg, offer = friendly_voice_error("")
        assert "Попробуйте еще раз" in msg
        assert offer is False


class TestYoutubeModule:
    def test_build_command_basic(self):
        cmd = build_youtube_sync_command("/usr/bin/python", "general")
        assert "sync-youtube-links.py" in cmd[-1] or any("sync-youtube-links.py" in c for c in cmd)
        assert "--scope" in cmd
        assert "general" in cmd

    def test_build_command_with_project(self):
        cmd = build_youtube_sync_command("/usr/bin/python", "web", "web-dev")
        assert "--project" in cmd
        assert "web-dev" in cmd

    def test_build_command_game_no_project(self):
        cmd = build_youtube_sync_command("/usr/bin/python", "game")
        assert "--project" not in cmd

    def test_build_command_finished_no_project(self):
        cmd = build_youtube_sync_command("/usr/bin/python", "all")
        assert "--project" not in cmd


class TestMaterialQueueModule:
    def test_launch_reindex_command_includes_route(self):
        route = KnowledgeRoute("Web", "web", "web-development")
        cmd = launch_reindex_command(route)
        assert "ingest-vault-scope-lmstudio.ps1" in " ".join(cmd)
        assert "-Scope" in cmd
        assert "web" in cmd
        assert "-Project" in cmd
        assert "web-development" in cmd

    def test_launch_reindex_starts_process_with_environment(self, monkeypatch):
        route = KnowledgeRoute("General", "general", "")
        calls: dict[str, object] = {}

        def fake_popen(command, **kwargs):
            calls["command"] = command
            calls["kwargs"] = kwargs
            return object()

        import subprocess

        monkeypatch.setenv("KNOWLEDGELAB_TEST_ENV", "1")
        monkeypatch.setattr(subprocess, "Popen", fake_popen)

        launch_reindex(route)

        assert calls["command"]
        env = calls["kwargs"]["env"]
        assert env["KNOWLEDGELAB_TEST_ENV"] == "1"


class TestVideoModule:
    def test_video_source_id_deterministic(self):
        id1 = video_source_id("https://youtube.com/watch?v=abc")
        id2 = video_source_id("https://youtube.com/watch?v=abc")
        assert id1 == id2

    def test_video_source_id_length(self):
        id1 = video_source_id("test")
        assert len(id1) == 16

    def test_video_source_id_different(self):
        id1 = video_source_id("url1")
        id2 = video_source_id("url2")
        assert id1 != id2

    def test_video_runtime_dir(self):
        d = video_runtime_dir("https://youtube.com/watch?v=abc")
        assert d.name == video_source_id("https://youtube.com/watch?v=abc")

    def test_parse_frame_response_valid(self):
        result = parse_video_frame_response('{"summary": "test", "code": ""}')
        assert result.get("summary") == "test"

    def test_parse_frame_response_empty(self):
        result = parse_video_frame_response("")
        assert result == {}

    def test_parse_frame_response_no_json(self):
        result = parse_video_frame_response("no json here")
        assert result == {}

    def test_format_report(self):
        report = VideoAnalysisReport(
            parent_note="test.md",
            analysis_note="analysis.md",
            source="test.mp4",
            transcript_status="pending",
            frame_analysis_status="queued",
            frame_count=5,
            code_snippet_count=2,
            warning="test warning",
        )
        text = format_video_analysis_report(report)
        assert "5" in text
        assert "2" in text
        assert "analysis.md" in text

    def test_format_report_no_warning(self):
        report = VideoAnalysisReport(
            parent_note="test.md",
            analysis_note="analysis.md",
            source="test.mp4",
            transcript_status="done",
            frame_analysis_status="done",
        )
        text = format_video_analysis_report(report)
        assert "Внимание" not in text
