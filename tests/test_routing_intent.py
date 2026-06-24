from __future__ import annotations

from knowledgelab.config import LAYER_ACTIVE, LAYER_FINISHED_PROJECTS
from knowledgelab.models import KnowledgeRoute
from knowledgelab.routing.intent import (
    default_finished_project_section,
    infer_kind,
    infer_topic,
    is_knowledge_lookup_text,
    is_lightrag_help_text,
    is_russian_language_request,
    is_save_intent_text,
    normalize_subject_scope,
    route_context,
    subject_route_from_text,
)


def test_is_save_intent_text_with_phrase():
    assert is_save_intent_text("сохрани эту ссылку") is True


def test_is_save_intent_text_with_url_no_question():
    assert is_save_intent_text("https://example.com") is True


def test_is_save_intent_text_with_question():
    assert is_save_intent_text("что это за https://example.com?") is False


def test_is_save_intent_text_empty():
    assert is_save_intent_text("") is False


def test_is_knowledge_lookup_text_true():
    assert is_knowledge_lookup_text("найди в базе знаний") is True


def test_is_knowledge_lookup_text_false():
    assert is_knowledge_lookup_text("привет") is False


def test_is_lightrag_help_text_true():
    assert is_lightrag_help_text("как узнать через lightrag") is True


def test_is_lightrag_help_text_false():
    assert is_lightrag_help_text("привет мир") is False


def test_is_lightrag_help_text_how_lightrag():
    assert is_lightrag_help_text("как пользоваться lightrag") is True


def test_is_russian_language_request_true():
    assert is_russian_language_request("отвечай на русском") is True


def test_is_russian_language_request_false():
    assert is_russian_language_request("hello world") is False


def test_subject_route_from_text_web():
    route = subject_route_from_text("React hooks tutorial")
    assert route.scope == "web"
    assert route.context_name == "Web Development"


def test_subject_route_from_text_game():
    route = subject_route_from_text("моя игра геймплей")
    assert route.scope == "game"
    assert route.context_name == "My Game"


def test_subject_route_from_text_general():
    route = subject_route_from_text("как приготовить борщ")
    assert route.scope == "general"
    assert route.context_name == "General"


def test_route_context_auto_web():
    route = route_context("React hooks", "Auto")
    assert route.scope == "web"


def test_route_context_auto_game():
    route = route_context("мой проект игры", "Auto")
    assert route.scope == "game"


def test_route_context_finished_projects():
    route = route_context("any text", "Finished Projects")
    assert route.layer == LAYER_FINISHED_PROJECTS


def test_route_context_auto_finished():
    route = route_context("готовые проекты", "Auto")
    assert route.layer == LAYER_FINISHED_PROJECTS


def test_route_context_explicit_web():
    route = route_context("any", "Web Development")
    assert route.scope == "web"


def test_normalize_subject_scope_web():
    assert normalize_subject_scope("web") == "web"


def test_normalize_subject_scope_game():
    assert normalize_subject_scope("game") == "game"


def test_normalize_subject_scope_general():
    assert normalize_subject_scope("кулинария") == "general"


def test_normalize_subject_scope_fallback():
    assert normalize_subject_scope("unknown", "web") == "web"


def test_default_finished_project_section_web():
    assert default_finished_project_section("web") == "web"


def test_default_finished_project_section_game():
    assert default_finished_project_section("game") == "game"


def test_default_finished_project_section_general():
    assert default_finished_project_section("general") == "general"


def test_infer_topic_react():
    assert infer_topic("React hooks useState", "web") == "React"


def test_infer_topic_css():
    assert infer_topic("CSS grid layout", "web") == "CSS Layout"


def test_infer_topic_general_fallback():
    assert infer_topic("random text", "general") == "General"


def test_infer_topic_web_fallback():
    assert infer_topic("random", "web") == "Web"


def test_infer_topic_game_fallback():
    assert infer_topic("random", "game") == "Project Notes"


def test_infer_kind_github():
    assert infer_kind("https://github.com/user/repo") == "github_repository"


def test_infer_kind_codepen():
    assert infer_kind("https://codepen.io/user/pen/abc123") == "codepen_pen"


def test_infer_kind_youtube():
    assert infer_kind("https://www.youtube.com/watch?v=abc") == "youtube_link"


def test_infer_kind_telegram():
    assert infer_kind("https://t.me/channel/123") == "telegram_source"


def test_infer_kind_article():
    assert infer_kind("https://example.com/article") == "article"


def test_infer_kind_solution():
    assert infer_kind("решение проблемы с React") == "solution"


def test_infer_kind_capture():
    assert infer_kind("some text") == "capture"
