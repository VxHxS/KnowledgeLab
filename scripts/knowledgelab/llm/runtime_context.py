"""Runtime context prompt generation — injects app state into LLM prompts."""

from __future__ import annotations

import re

from knowledgelab.config import ROOT, VAULT_DIR, LAYER_FINISHED_PROJECTS
from knowledgelab.i18n.messages import msg, msg_list
from knowledgelab.models import KnowledgeRoute


NOISY_HISTORY_MARKERS = (
    "nativecommanderror",
    "context size has been exceeded",
    "openai api call failed",
    "starting lm studio server",
    "knowledge lab is ready",
    "lightrag storage was not found",
    "fullyqualifiederrorid",
    "categoryinfo",
    "success! server is now running",
)

RUNTIME_CONTEXT_TERMS = msg_list("runtime.context_terms")
ORDINARY_SHORT_CHAT_TERMS = msg_list("runtime.ordinary_short_chat_terms")


def should_include_runtime_context(question: str) -> bool:
    lowered = re.sub(r"\s+", " ", str(question or "").strip().lower())
    if not lowered:
        return False
    if len(lowered) <= 80 and any(term in lowered for term in ORDINARY_SHORT_CHAT_TERMS):
        return False
    return any(term in lowered for term in RUNTIME_CONTEXT_TERMS)


def is_safe_history_message(text: str) -> bool:
    lowered = text.lower()
    return bool(text.strip()) and not any(marker in lowered for marker in NOISY_HISTORY_MARKERS)


def build_topic_context(route: KnowledgeRoute, recent_topics: list[str] | None = None) -> str:
    """Build a topic-aware context block for the system prompt."""
    scope = str(route.scope or "general").lower()
    topic_descriptions = {
        "web": "фронтенд/бэкенд веб-разработка: HTML, CSS, JavaScript, TypeScript, React, Vue, Next.js, Node.js, API, базы данных, деплой",
        "game": "геймдев: Unity, Unreal Engine, C#, шейдеры, геймдизайн, физика, анимация, оптимизация",
        "general": "общие знания, программирование, референсы, инструменты, документация",
    }
    desc = topic_descriptions.get(scope, topic_descriptions["general"])
    lines = [f"Текущая специализация: {desc}"]
    if recent_topics:
        lines.append(f"Активные темы пользователя: {', '.join(recent_topics[:5])}")
    return "\n".join(lines)


def build_prompt_with_history(
    question: str,
    runtime_context: str,
    prior_messages: list[dict],
) -> str:
    lines = [
        msg("prompts.plain_base_instruction"),
        msg("prompts.no_hidden_context_echo"),
    ]
    runtime_context = str(runtime_context or "").strip()
    if runtime_context:
        lines.extend([
            "",
            msg("prompts.hidden_state_intro"),
            runtime_context,
        ])
    if not prior_messages:
        lines.extend(["", msg("prompts.current_user_message"), question])
        return "\n".join(lines)
    lines.extend(["", msg("prompts.chat_context_header")])
    total_chars = 0
    for message in prior_messages[-4:]:
        if message.get("role") not in {"user", "assistant"}:
            continue
        text = re.sub(r"\s+", " ", str(message.get("text", "")).strip())[:360]
        if not text:
            continue
        role = "User" if message.get("role") == "user" else "Assistant"
        line = f"{role}: {text}"
        total_chars += len(line)
        if total_chars > 1600:
            break
        lines.append(line)
    lines.extend(["", f"{msg('prompts.current_user_message')} {question}"])
    return "\n".join(lines)


def lightrag_help_message(lightrag_enabled: bool = False) -> str:
    state = msg("lightrag.state_on") if lightrag_enabled else msg("lightrag.state_off")
    return msg("lightrag.help", state=state)


def _short_storage_token(value: str, max_length: int = 48) -> str:
    import hashlib
    import re
    token = re.sub(r"[^a-zA-Z0-9_-]+", "-", str(value or "")).strip("-") or "default"
    if len(token) <= max_length:
        return token
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()[:12]
    prefix_length = max(8, max_length - 13)
    return f"{token[:prefix_length]}-{digest}"


def storage_name_for_scope(scope: str, project: str, layer: str = "active") -> str:
    import re
    if layer == "finished-projects":
        return "finished_projects"
    safe_project = re.sub(r"[^a-z0-9_-]+", "-", project.strip().lower()) or "default"
    safe_project = _short_storage_token(safe_project)
    if scope == "all":
        return "all"
    if scope == "web" and safe_project not in {"default", "web-development"}:
        return f"web_{safe_project}"
    if scope == "game":
        return f"game_{safe_project}"
    if scope == "general" and safe_project != "default":
        return f"general_{safe_project}"
    return scope


def lightrag_index_path(scope: str, project: str, layer: str = "active") -> str:
    from knowledgelab.config import ROOT
    storage = storage_name_for_scope(scope, project, layer)
    return str(ROOT / "LightRAG" / f"rag_storage_{storage}" / "vdb_chunks.json")


def is_lightrag_ready(scope: str, project: str, layer: str = "active") -> bool:
    from pathlib import Path
    return Path(lightrag_index_path(scope, project, layer)).exists()


def python_executable() -> str:
    import sys
    from pathlib import Path
    from knowledgelab.config import ROOT
    candidate = ROOT / "LightRAG" / ".venv" / "Scripts" / "python.exe"
    return str(candidate if candidate.exists() else sys.executable)


def capture_path_from_rel(rel_path: str) -> str:
    import os
    from knowledgelab.config import VAULT_DIR
    return str(VAULT_DIR / rel_path.replace("/", os.sep))


def build_runtime_context_prompt(
    *,
    route: KnowledgeRoute,
    lmstudio_base_url: str,
    llm_model_id: str,
    loaded_models: list[str],
    models_error: str,
    vision_model: str,
    vision_ready: bool,
    lightrag_enabled: bool,
    lightrag_ready_check: callable,
    context_routes: list[KnowledgeRoute],
    web_search_enabled: bool,
    dnd_backend: str,
    busy: bool,
    busy_status_base: str,
    background_tasks_summary: list[str],
    material_queue_summary: str,
    book_discovery_summary: str,
    project_server_summary: str,
) -> str:
    index_lines = [
        f"{item.context_name}:{'ready' if lightrag_ready_check(item.scope, item.project, item.layer) else 'missing'}"
        for item in context_routes
    ]
    task_lines = list(background_tasks_summary) or ["none"]
    return "\n".join([
        "KnowledgeLab runtime context (authoritative app state):",
        f"- app_root: {ROOT}",
        f"- vault_dir: {VAULT_DIR}",
        f"- lmstudio_base_url: {lmstudio_base_url}",
        f"- llm_model_setting: {llm_model_id}",
        f"- loaded_lmstudio_models: {', '.join(loaded_models) if loaded_models else ('unavailable: ' + models_error if models_error else 'none reported')}",
        f"- model_runtime: local LM Studio OpenAI-compatible server; not a hosted cloud API",
        f"- vision_model: {vision_model}; available_for_images: {vision_ready}",
        f"- lightrag_setting: {'on' if lightrag_enabled else 'off'}",
        f"- lightrag_indexes: {', '.join(index_lines)}",
        f"- current_route: context={route.context_name}; scope={route.scope}; project={route.project}; layer={route.layer}",
        f"- web_search_default: {'on' if web_search_enabled else 'off'}",
        f"- dnd_backend: {dnd_backend}",
        f"- foreground_operation: {'running: ' + busy_status_base if busy else 'none'}",
        "- background_tasks:",
        *[f"  - {line}" for line in task_lines],
        f"- material_processing_queue: {material_queue_summary}",
        f"- latest_book_discovery_report: {book_discovery_summary}",
        f"- project_local_servers: {project_server_summary}",
        "Instruction: If the user asks about app status, connection, LightRAG, book import, video analysis, queues, DnD, servers, or what is happening now, answer using this context. If a task is running, say it is still processing and the user can continue chatting while it runs.",
    ])
