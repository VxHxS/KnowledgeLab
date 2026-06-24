"""Runtime context prompt generation — injects app state into LLM prompts."""

from __future__ import annotations

import re

from knowledgelab.config import ROOT, VAULT_DIR, LAYER_FINISHED_PROJECTS
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


def is_safe_history_message(text: str) -> bool:
    lowered = text.lower()
    return bool(text.strip()) and not any(marker in lowered for marker in NOISY_HISTORY_MARKERS)


def build_prompt_with_history(
    question: str,
    runtime_context: str,
    prior_messages: list[dict],
) -> str:
    if not prior_messages:
        return runtime_context + "\n\nТекущее сообщение пользователя:\n" + question
    lines = [runtime_context, "", "Краткий контекст текущего диалога:"]
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
    lines.extend(["", f"Текущее сообщение пользователя: {question}"])
    return "\n".join(lines)


def lightrag_help_message(lightrag_enabled: bool = False) -> str:
    state = "включен" if lightrag_enabled else "выключен"
    return (
        f"LightRAG сейчас {state}. Чтобы получить ответ из сохраненных материалов, "
        "включите LightRAG в Настройках или явно попросите поиск по базе: "
        "«найди в базе материалы про CSS», «что у меня сохранено про лендинги», "
        "«сделай инструкцию из сохраненных материалов». "
        "Если я напишу, что индекс не готов, откройте LightRAG-Control и запустите проверку или переиндексацию."
    )


def storage_name_for_scope(scope: str, project: str, layer: str = "active") -> str:
    import re
    if layer == "finished-projects":
        return "finished_projects"
    safe_project = re.sub(r"[^a-z0-9_-]+", "-", project.strip().lower()) or "default"
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
