"""Settings persistence — load, save, normalize, validate."""
from __future__ import annotations

import json
from pathlib import Path

from knowledgelab.config import (
    SETTINGS_PATH,
    DEFAULT_SETTINGS,
    DEFAULT_VAULT_DIR,
    LMSTUDIO_API_URL,
    DEFAULT_LLM_MODEL,
    DEFAULT_EMBEDDING_MODEL,
    BUTTON_COLOR_PRESETS,
)
from knowledgelab.utils.colors import valid_hex_color


def load_settings(path: Path = SETTINGS_PATH) -> dict[str, object]:
    settings = dict(DEFAULT_SETTINGS)
    try:
        if path.exists():
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                settings.update(loaded)
                if "default_llm_mode_applied" not in loaded:
                    settings["use_lightrag"] = False
                    settings["default_llm_mode_applied"] = True
                if "main_toolbar_lightrag_removed" not in loaded:
                    settings["use_lightrag"] = False
                    settings["main_toolbar_lightrag_removed"] = True
                if "plain_chat_adapter_version" not in loaded:
                    settings["use_lightrag"] = False
                    settings["plain_chat_adapter_version"] = 1
    except (OSError, json.JSONDecodeError):
        pass
    settings["send_on_enter"] = bool(settings.get("send_on_enter", DEFAULT_SETTINGS["send_on_enter"]))
    settings["use_lightrag"] = bool(settings.get("use_lightrag", DEFAULT_SETTINGS["use_lightrag"]))
    settings["game_guard_enabled"] = bool(settings.get("game_guard_enabled", DEFAULT_SETTINGS["game_guard_enabled"]))
    settings["auto_process_links"] = bool(settings.get("auto_process_links", DEFAULT_SETTINGS["auto_process_links"]))
    settings["auto_route_topics"] = bool(settings.get("auto_route_topics", DEFAULT_SETTINGS["auto_route_topics"]))
    settings["auto_create_topics"] = bool(settings.get("auto_create_topics", DEFAULT_SETTINGS["auto_create_topics"]))
    settings["auto_detect_books_in_images"] = bool(settings.get("auto_detect_books_in_images", DEFAULT_SETTINGS["auto_detect_books_in_images"]))
    settings["book_lookup_enabled"] = bool(settings.get("book_lookup_enabled", DEFAULT_SETTINGS["book_lookup_enabled"]))
    settings["web_search_enabled"] = bool(settings.get("web_search_enabled", DEFAULT_SETTINGS["web_search_enabled"]))
    settings["game_guard_delay_seconds"] = max(1, int(settings.get("game_guard_delay_seconds", 5) or 5))
    settings["button_color"] = valid_hex_color(str(settings.get("button_color", "")), DEFAULT_SETTINGS["button_color"])
    settings["obsidian_path"] = str(settings.get("obsidian_path", "") or "")
    settings["vault_path"] = str(settings.get("vault_path", str(DEFAULT_VAULT_DIR)) or str(DEFAULT_VAULT_DIR))
    settings["lmstudio_base_url"] = str(settings.get("lmstudio_base_url", LMSTUDIO_API_URL) or LMSTUDIO_API_URL).rstrip("/")
    settings["llm_model"] = str(settings.get("llm_model", DEFAULT_LLM_MODEL) or DEFAULT_LLM_MODEL)
    settings["embedding_model"] = str(settings.get("embedding_model", DEFAULT_EMBEDDING_MODEL) or DEFAULT_EMBEDDING_MODEL)
    settings["response_language"] = str(settings.get("response_language", "ru") or "ru")
    settings["default_llm_mode_applied"] = True
    settings["main_toolbar_lightrag_removed"] = True
    settings["plain_chat_adapter_version"] = 1
    return settings


def normalize_settings(settings: dict[str, object]) -> dict[str, object]:
    settings["send_on_enter"] = bool(settings.get("send_on_enter", DEFAULT_SETTINGS["send_on_enter"]))
    settings["use_lightrag"] = bool(settings.get("use_lightrag", DEFAULT_SETTINGS["use_lightrag"]))
    settings["game_guard_enabled"] = bool(settings.get("game_guard_enabled", DEFAULT_SETTINGS["game_guard_enabled"]))
    settings["auto_process_links"] = bool(settings.get("auto_process_links", DEFAULT_SETTINGS["auto_process_links"]))
    settings["auto_route_topics"] = bool(settings.get("auto_route_topics", DEFAULT_SETTINGS["auto_route_topics"]))
    settings["auto_create_topics"] = bool(settings.get("auto_create_topics", DEFAULT_SETTINGS["auto_create_topics"]))
    settings["auto_detect_books_in_images"] = bool(settings.get("auto_detect_books_in_images", DEFAULT_SETTINGS["auto_detect_books_in_images"]))
    settings["book_lookup_enabled"] = bool(settings.get("book_lookup_enabled", DEFAULT_SETTINGS["book_lookup_enabled"]))
    settings["web_search_enabled"] = bool(settings.get("web_search_enabled", DEFAULT_SETTINGS["web_search_enabled"]))
    settings["game_guard_delay_seconds"] = max(1, int(settings.get("game_guard_delay_seconds", 5) or 5))
    settings["button_color"] = valid_hex_color(str(settings.get("button_color", "")), DEFAULT_SETTINGS["button_color"])
    settings["obsidian_path"] = str(settings.get("obsidian_path", "") or "")
    settings["vault_path"] = str(settings.get("vault_path", str(DEFAULT_VAULT_DIR)) or str(DEFAULT_VAULT_DIR))
    settings["lmstudio_base_url"] = str(settings.get("lmstudio_base_url", LMSTUDIO_API_URL) or LMSTUDIO_API_URL).rstrip("/")
    settings["llm_model"] = str(settings.get("llm_model", DEFAULT_LLM_MODEL) or DEFAULT_LLM_MODEL)
    settings["embedding_model"] = str(settings.get("embedding_model", DEFAULT_EMBEDDING_MODEL) or DEFAULT_EMBEDDING_MODEL)
    settings["response_language"] = str(settings.get("response_language", "ru") or "ru")
    settings["default_llm_mode_applied"] = True
    settings["main_toolbar_lightrag_removed"] = True
    settings["plain_chat_adapter_version"] = 1
    return settings


def save_settings(settings: dict[str, object], path: Path = SETTINGS_PATH) -> None:
    normalized = normalize_settings(dict(settings))
    settings.update(normalized)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(settings, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except OSError:
        pass


def color_preset_name(color: str) -> str:
    color = valid_hex_color(color, DEFAULT_SETTINGS["button_color"])
    for name, value in BUTTON_COLOR_PRESETS.items():
        if value.lower() == color.lower():
            return name
    return ""
