from __future__ import annotations

import importlib


def test_main_module_importable():
    mod = importlib.import_module("main")
    assert mod is not None


def test_main_has_knowledge_chat_app():
    mod = importlib.import_module("main")
    assert hasattr(mod, "KnowledgeChatApp")


def test_main_reexports_config_names():
    mod = importlib.import_module("main")
    assert hasattr(mod, "ROOT")
    assert hasattr(mod, "VAULT_DIR")
    assert hasattr(mod, "LAYER_ACTIVE")
    assert hasattr(mod, "LAYER_FINISHED_PROJECTS")
    assert hasattr(mod, "UI_THEME")
    assert hasattr(mod, "DEFAULT_SETTINGS")
    assert hasattr(mod, "TOPICS")
    assert hasattr(mod, "WEB_TERMS")


def test_main_reexports_model_names():
    mod = importlib.import_module("main")
    assert hasattr(mod, "KnowledgeRoute")
    assert hasattr(mod, "ProjectGuess")
    assert hasattr(mod, "MaterialRoutingReport")
    assert hasattr(mod, "BookDiscoveryReport")
    assert hasattr(mod, "ManualBookEntry")
    assert hasattr(mod, "VideoAnalysisReport")
    assert hasattr(mod, "BackgroundTaskRecord")
    assert hasattr(mod, "ReferenceLink")
    assert hasattr(mod, "CodePenSnapshot")


def test_main_reexports_utils_names():
    mod = importlib.import_module("main")
    assert hasattr(mod, "now_iso")
    assert hasattr(mod, "compact_text")
    assert hasattr(mod, "contains_any")
    assert hasattr(mod, "clean_filename")
    assert hasattr(mod, "slugify")
    assert hasattr(mod, "compact_whitespace")
    assert hasattr(mod, "yaml_quote")
    assert hasattr(mod, "markdown_fence_text")
    assert hasattr(mod, "extract_json_object")


def test_main_reexports_url_names():
    mod = importlib.import_module("main")
    assert hasattr(mod, "URL_RE")
    assert hasattr(mod, "first_url")
    assert hasattr(mod, "first_youtube_url")
    assert hasattr(mod, "first_github_url")
    assert hasattr(mod, "parse_codepen_url")
    assert hasattr(mod, "parse_github_url")
    assert hasattr(mod, "normalize_github_url")
    assert hasattr(mod, "source_domain")
    assert hasattr(mod, "stable_content_hash")


def test_main_reexports_color_names():
    mod = importlib.import_module("main")
    assert hasattr(mod, "valid_hex_color")
    assert hasattr(mod, "adjust_hex_color")
    assert hasattr(mod, "mix_hex_color")
    assert hasattr(mod, "readable_text_color")


def test_main_reexports_path_names():
    mod = importlib.import_module("main")
    assert hasattr(mod, "normalize_attached_source_path")
    assert hasattr(mod, "explorer_dnd_enabled")


def test_main_reexports_routing_names():
    mod = importlib.import_module("main")
    assert hasattr(mod, "is_save_intent_text")
    assert hasattr(mod, "is_knowledge_lookup_text")
    assert hasattr(mod, "subject_route_from_text")
    assert hasattr(mod, "route_context")
    assert hasattr(mod, "normalize_subject_scope")
    assert hasattr(mod, "infer_topic")
    assert hasattr(mod, "infer_kind")


def test_main_reexports_vault_names():
    mod = importlib.import_module("main")
    assert hasattr(mod, "parse_frontmatter")
    assert hasattr(mod, "parse_basic_frontmatter")
    assert hasattr(mod, "infer_scope")
    assert hasattr(mod, "infer_project")
    assert hasattr(mod, "infer_layer")
    assert hasattr(mod, "capture_destination")
    assert hasattr(mod, "classify_source_file")
    assert hasattr(mod, "extraction_label")
    assert hasattr(mod, "file_kind_label")


def test_main_reexports_llm_names():
    mod = importlib.import_module("main")
    assert hasattr(mod, "is_vision_model_name")
    assert hasattr(mod, "extract_chat_content_standalone")


def test_main_reexports_book_names():
    mod = importlib.import_module("main")
    assert hasattr(mod, "normalize_detected_book")
    assert hasattr(mod, "parse_bookshelf_detection_response")
    assert hasattr(mod, "classify_book_topic")
    assert hasattr(mod, "score_book_lookup_candidate")
    assert hasattr(mod, "select_best_book_lookup")
    assert hasattr(mod, "merge_book_lookup")
    assert hasattr(mod, "book_note_slug")
    assert hasattr(mod, "format_book_discovery_report")
    assert hasattr(mod, "format_material_routing_report")
