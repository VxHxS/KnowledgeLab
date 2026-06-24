from __future__ import annotations

import os

from knowledgelab.utils.paths import explorer_dnd_enabled, normalize_attached_source_path


def test_normalize_attached_source_path_plain():
    assert normalize_attached_source_path("/tmp/file.txt") == "/tmp/file.txt"


def test_normalize_attached_source_path_strips_quotes():
    result = normalize_attached_source_path('"/tmp/file.txt"')
    assert result == "/tmp/file.txt"


def test_normalize_attached_source_path_strips_braces():
    result = normalize_attached_source_path("{/tmp/file.txt}")
    assert result == "/tmp/file.txt"


def test_normalize_attached_source_path_file_uri():
    result = normalize_attached_source_path("file:///C:/Users/test/file.txt")
    assert "C:" in result or result.startswith("/")


def test_normalize_attached_source_path_empty():
    assert normalize_attached_source_path("") == ""


def test_explorer_dnd_enabled_default(monkeypatch):
    monkeypatch.delenv("KNOWLEDGELAB_ENABLE_EXPLORER_DND", raising=False)
    monkeypatch.delenv("KNOWLEDGELAB_DISABLE_EXPLORER_DND", raising=False)
    assert explorer_dnd_enabled() is True


def test_explorer_dnd_enabled_disabled(monkeypatch):
    monkeypatch.setenv("KNOWLEDGELAB_DISABLE_EXPLORER_DND", "1")
    assert explorer_dnd_enabled() is False


def test_explorer_dnd_enabled_explicit_on(monkeypatch):
    monkeypatch.delenv("KNOWLEDGELAB_DISABLE_EXPLORER_DND", raising=False)
    monkeypatch.setenv("KNOWLEDGELAB_ENABLE_EXPLORER_DND", "true")
    assert explorer_dnd_enabled() is True


def test_explorer_dnd_enabled_explicit_off(monkeypatch):
    monkeypatch.delenv("KNOWLEDGELAB_DISABLE_EXPLORER_DND", raising=False)
    monkeypatch.setenv("KNOWLEDGELAB_ENABLE_EXPLORER_DND", "false")
    assert explorer_dnd_enabled() is False
