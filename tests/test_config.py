from __future__ import annotations

from pathlib import Path

from knowledgelab import config


def test_root_is_path_exists():
    assert isinstance(config.ROOT, Path)
    assert config.ROOT.exists()


def test_vault_dir_is_path():
    assert isinstance(config.VAULT_DIR, Path)


def test_lmstudio_default_url_matches_lm_studio_local_server():
    assert config.LMSTUDIO_API_URL == "http://127.0.0.1:1234/v1"


def test_default_settings_keys():
    assert isinstance(config.DEFAULT_SETTINGS, dict)
    expected = {
        "send_on_enter",
        "use_lightrag",
        "button_color",
        "game_guard_enabled",
        "llm_model",
        "vision_model",
        "book_lookup_enabled",
        "book_download_enabled",
        "book_download_max_mb",
        "book_download_formats",
        "book_legal_sources",
        "auto_route_topics",
        "auto_create_topics",
        "response_language",
    }
    assert expected.issubset(config.DEFAULT_SETTINGS.keys())


def test_ui_theme_keys():
    assert isinstance(config.UI_THEME, dict)
    expected = {"app_bg", "accent", "text", "muted", "warning", "success", "danger"}
    assert expected.issubset(config.UI_THEME.keys())


def test_topics_non_empty_list_of_tuples():
    assert isinstance(config.TOPICS, list)
    assert len(config.TOPICS) > 0
    for name, terms in config.TOPICS:
        assert isinstance(name, str)
        assert isinstance(terms, set)
        assert len(terms) > 0


def test_web_terms_non_empty():
    assert isinstance(config.WEB_TERMS, set)
    assert len(config.WEB_TERMS) > 0


def test_game_terms_non_empty():
    assert isinstance(config.GAME_TERMS, set)
    assert len(config.GAME_TERMS) > 0


def test_finished_project_terms_non_empty():
    assert isinstance(config.FINISHED_PROJECT_TERMS, set)
    assert len(config.FINISHED_PROJECT_TERMS) > 0


def test_book_image_terms_non_empty():
    assert isinstance(config.BOOK_IMAGE_TERMS, set)
    assert len(config.BOOK_IMAGE_TERMS) > 0


def test_book_page_terms_non_empty():
    assert isinstance(config.BOOK_PAGE_TERMS, set)
    assert len(config.BOOK_PAGE_TERMS) > 0


def test_bookshelf_terms_non_empty():
    assert isinstance(config.BOOKSHELF_TERMS, set)
    assert len(config.BOOKSHELF_TERMS) > 0


def test_reference_link_hints_non_empty():
    assert isinstance(config.REFERENCE_LINK_HINTS, set)
    assert len(config.REFERENCE_LINK_HINTS) > 0


def test_save_phrases_non_empty():
    assert isinstance(config.SAVE_PHRASES, set)
    assert len(config.SAVE_PHRASES) > 0


def test_question_hints_non_empty():
    assert isinstance(config.QUESTION_HINTS, set)
    assert len(config.QUESTION_HINTS) > 0


def test_knowledge_lookup_terms_non_empty():
    assert isinstance(config.KNOWLEDGE_LOOKUP_TERMS, set)
    assert len(config.KNOWLEDGE_LOOKUP_TERMS) > 0


def test_layer_constants_are_strings():
    assert isinstance(config.LAYER_ACTIVE, str)
    assert isinstance(config.LAYER_FINISHED_PROJECTS, str)


def test_path_constants_are_paths_or_strings():
    path_attrs = [
        "ROOT", "VAULT_DIR", "SCRIPTS_DIR", "QUERY_SCRIPT", "GAME_GUARD_SCRIPT",
        "CONTROL_SCRIPT", "LEGACY_HISTORY_PATH", "CHAT_STORE_PATH", "SETTINGS_PATH",
        "MATERIAL_QUEUE_PATH", "RLM_QUEUE_PATH", "PROJECT_ACTIONS_PATH",
        "PROJECT_RUNTIME_DIR", "VIDEO_PROCESSING_DIR",
    ]
    for attr in path_attrs:
        value = getattr(config, attr)
        assert isinstance(value, (Path, str)), f"{attr} is {type(value)}, expected Path or str"


def test_vision_model_markers_non_empty():
    assert isinstance(config.VISION_MODEL_MARKERS, tuple)
    assert len(config.VISION_MODEL_MARKERS) > 0


def test_button_color_presets():
    assert isinstance(config.BUTTON_COLOR_PRESETS, dict)
    assert len(config.BUTTON_COLOR_PRESETS) > 0
    for name, color in config.BUTTON_COLOR_PRESETS.items():
        assert isinstance(color, str)
        assert color.startswith("#")
