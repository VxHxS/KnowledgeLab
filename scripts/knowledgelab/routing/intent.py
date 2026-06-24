from __future__ import annotations

import re

from knowledgelab.config import (
    CONTEXTS,
    WEB_TERMS,
    GAME_TERMS,
    FINISHED_PROJECT_TERMS,
    KNOWLEDGE_LOOKUP_TERMS,
    KNOWLEDGE_HELP_TERMS,
    RUSSIAN_LANGUAGE_TERMS,
    SAVE_PHRASES,
    QUESTION_HINTS,
    TOPICS,
    LAYER_FINISHED_PROJECTS,
)
from knowledgelab.models import KnowledgeRoute
from knowledgelab.utils.text import compact_text, contains_any, slugify
from knowledgelab.utils.urls import (
    first_url,
    first_github_url,
    first_codepen_url,
    first_youtube_url,
    first_telegram_url,
)


def is_finished_project_lookup_text(text: str) -> bool:
    return contains_any(text, FINISHED_PROJECT_TERMS)


def subject_route_from_text(text: str) -> KnowledgeRoute:
    if contains_any(text, WEB_TERMS):
        return KnowledgeRoute("Web Development", "web", "web-development")
    if contains_any(text, GAME_TERMS):
        return KnowledgeRoute("My Game", "game", "my-game")
    return KnowledgeRoute("General", "general", "")


def route_context(text: str, selected: str) -> KnowledgeRoute:
    if selected == "Finished Projects":
        return KnowledgeRoute("Finished Projects", "all", "", LAYER_FINISHED_PROJECTS)
    if selected != "Auto":
        scope, project = CONTEXTS[selected]
        return KnowledgeRoute(selected, scope, project)
    if is_finished_project_lookup_text(text):
        return KnowledgeRoute("Finished Projects", "all", "", LAYER_FINISHED_PROJECTS)
    return subject_route_from_text(text)


def normalize_subject_scope(value: str, fallback: str = "general") -> str:
    normalized = slugify(value)
    if normalized in {"web", "frontend", "front-end", "web-development", "site", "website"}:
        return "web"
    if normalized in {"game", "games", "my-game", "gamedev"}:
        return "game"
    normalized_parts = {part for part in normalized.split("-") if part}
    if normalized_parts & {"web", "frontend", "front", "website", "site"}:
        return "web"
    if normalized_parts & {"game", "games", "gamedev"}:
        return "game"
    if normalized in {"general", "common", "other", "misc"}:
        return "general"
    if contains_any(value, WEB_TERMS):
        return "web"
    if contains_any(value, GAME_TERMS):
        return "game"
    return fallback if fallback in {"general", "web", "game"} else "general"


def default_finished_project_section(scope: str, title: str = "") -> str:
    title_lower = title.lower()
    if scope == "web" or contains_any(title_lower, WEB_TERMS):
        return "web"
    if scope == "game" or contains_any(title_lower, GAME_TERMS):
        return "game"
    return "general"


def is_knowledge_lookup_text(text: str) -> bool:
    compact = compact_text(text)
    return any(term in compact for term in KNOWLEDGE_LOOKUP_TERMS)


def is_lightrag_help_text(text: str) -> bool:
    compact = compact_text(text)
    if "lightrag" not in compact and "light rag" not in compact and "баз" not in compact:
        return False
    return any(term in compact for term in KNOWLEDGE_HELP_TERMS) or ("как" in compact and "lightrag" in compact)


def is_russian_language_request(text: str) -> bool:
    compact = compact_text(text)
    return any(term in compact for term in RUSSIAN_LANGUAGE_TERMS)


def is_save_intent_text(text: str) -> bool:
    compact = compact_text(text)
    if any(phrase in compact for phrase in SAVE_PHRASES):
        return True
    if first_github_url(text):
        words = set(re.findall(r"[a-zа-яё]+", compact, flags=re.IGNORECASE))
        return len(words & QUESTION_HINTS) == 0
    if first_url(text):
        words = set(re.findall(r"[a-zа-яё]+", compact, flags=re.IGNORECASE))
        return len(words & QUESTION_HINTS) == 0
    return False


def infer_topic(text: str, scope: str) -> str:
    lowered = f" {text.lower()} "
    for topic, terms in TOPICS:
        if any(term in lowered for term in terms):
            return topic
    if scope == "web":
        return "Web"
    if scope == "game":
        return "Project Notes"
    return "General"


def infer_kind(text: str) -> str:
    if first_github_url(text):
        return "github_repository"
    if first_codepen_url(text):
        return "codepen_pen"
    if first_youtube_url(text):
        return "youtube_link"
    if first_telegram_url(text):
        return "telegram_source"
    if first_url(text):
        return "article"
    lowered = text.lower()
    if any(term in lowered for term in ("решение", "solution", "snippet", "компонент", "pattern", "паттерн")):
        return "solution"
    return "capture"
