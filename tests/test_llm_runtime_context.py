from __future__ import annotations

from knowledgelab.config import LAYER_ACTIVE
from knowledgelab.i18n.messages import msg, msg_list
from knowledgelab.llm.runtime_context import build_runtime_context_prompt, storage_name_for_scope
from knowledgelab.models import KnowledgeRoute


def _noop_ready(scope: str, project: str, layer: str) -> bool:
    return True


def test_build_runtime_context_prompt_returns_string():
    route = KnowledgeRoute("General", "general", "", LAYER_ACTIVE)
    result = build_runtime_context_prompt(
        route=route,
        lmstudio_base_url="http://127.0.0.1:5000/v1",
        llm_model_id="test-model",
        loaded_models=["test-model"],
        models_error="",
        vision_model="",
        vision_ready=False,
        lightrag_enabled=False,
        lightrag_ready_check=_noop_ready,
        context_routes=[route],
        web_search_enabled=False,
        dnd_backend="explorer",
        busy=False,
        busy_status_base="",
        background_tasks_summary=[],
        material_queue_summary="empty",
        book_discovery_summary="none",
        project_server_summary="none",
    )
    assert isinstance(result, str)


def test_build_runtime_context_prompt_contains_model():
    route = KnowledgeRoute("General", "general", "", LAYER_ACTIVE)
    result = build_runtime_context_prompt(
        route=route,
        lmstudio_base_url="http://127.0.0.1:5000/v1",
        llm_model_id="qwen3-14b",
        loaded_models=["qwen3-14b"],
        models_error="",
        vision_model="",
        vision_ready=False,
        lightrag_enabled=False,
        lightrag_ready_check=_noop_ready,
        context_routes=[route],
        web_search_enabled=False,
        dnd_backend="explorer",
        busy=False,
        busy_status_base="",
        background_tasks_summary=[],
        material_queue_summary="empty",
        book_discovery_summary="none",
        project_server_summary="none",
    )
    assert "qwen3-14b" in result
    assert "lmstudio_base_url" in result


def test_build_runtime_context_prompt_busy():
    route = KnowledgeRoute("General", "general", "", LAYER_ACTIVE)
    result = build_runtime_context_prompt(
        route=route,
        lmstudio_base_url="http://127.0.0.1:5000/v1",
        llm_model_id="model",
        loaded_models=[],
        models_error="",
        vision_model="",
        vision_ready=False,
        lightrag_enabled=False,
        lightrag_ready_check=_noop_ready,
        context_routes=[],
        web_search_enabled=False,
        dnd_backend="explorer",
        busy=True,
        busy_status_base="Importing files",
        background_tasks_summary=["task1"],
        material_queue_summary="empty",
        book_discovery_summary="none",
        project_server_summary="none",
    )
    assert "Importing files" in result
    assert "task1" in result


def test_storage_name_for_scope_shortens_long_project_names():
    project = "runs-user-pidString-" * 20
    first = storage_name_for_scope("game", project)
    second = storage_name_for_scope("game", project)
    assert first == second
    assert first.startswith("game_")
    assert len(first) <= 53


def test_message_catalog_loads_runtime_strings():
    assert "KnowledgeLab Chat" in msg("prompts.local_runtime_system")
    assert "привет" in msg_list("runtime.ordinary_short_chat_terms")
