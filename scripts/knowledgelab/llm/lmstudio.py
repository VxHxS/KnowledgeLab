"""Direct LM Studio API adapter — HTTP client and model operations."""

from __future__ import annotations

import json
import os
import urllib.request

from knowledgelab.config import DEFAULT_VISION_MODEL, VISION_MODEL_MARKERS, LOCAL_RUNTIME_SYSTEM_PROMPT
from knowledgelab.i18n.messages import msg


def is_vision_model_name(model: str) -> bool:
    lowered = model.lower()
    return any(marker in lowered for marker in VISION_MODEL_MARKERS)


def lmstudio_request_json(
    base_url: str,
    path: str,
    *,
    method: str = "GET",
    payload: dict | None = None,
    timeout: float = 8.0,
) -> dict:
    url = f"{base_url}/{path.lstrip('/')}"
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read().decode("utf-8", errors="replace")
    parsed = json.loads(raw) if raw.strip() else {}
    return parsed if isinstance(parsed, dict) else {}


def loaded_lmstudio_models(base_url: str) -> list[str]:
    response = lmstudio_request_json(base_url, "models", timeout=3.0)
    data = response.get("data") if isinstance(response, dict) else []
    ids = []
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and item.get("id"):
                ids.append(str(item["id"]))
    return ids


def check_lmstudio_ready(
    base_url: str,
    required_model: str,
    *,
    require_models: bool = True,
) -> tuple[bool, str, list[str]]:
    try:
        models = loaded_lmstudio_models(base_url)
    except Exception as exc:
        error_detail = str(exc)
        if "10061" in error_detail or "Connection refused" in error_detail:
            hint = msg("lmstudio.connection_refused", base_url=base_url, port=base_url.split(":")[-1].split("/")[0])
        elif "Timeout" in error_detail or "timed out" in error_detail:
            hint = msg("lmstudio.timeout", base_url=base_url)
        else:
            hint = msg("lmstudio.unavailable", base_url=base_url, error_detail=error_detail)
        return False, hint, []

    if not require_models:
        return True, msg("lmstudio.server_ok"), models

    missing = [model for model in [required_model] if model not in models]
    if missing:
        loaded = ", ".join(models) if models else msg("lmstudio.no_loaded_models")
        return (
            False,
            msg("lmstudio.required_model_missing", models=", ".join(missing), loaded=loaded),
            models,
        )
    return True, msg("lmstudio.ready"), models


def extract_chat_content(response: dict) -> tuple[str, str]:
    try:
        choice = (response.get("choices") or [])[0]
        message = choice.get("message") or {}
    except Exception:
        return "", ""
    content = message.get("content")
    reasoning = message.get("reasoning_content")
    return (
        content.strip() if isinstance(content, str) else "",
        reasoning.strip() if isinstance(reasoning, str) else "",
    )


def vision_model_state(
    settings: dict,
    base_url: str,
) -> tuple[str, bool, list[str]]:
    configured = str(settings.get("vision_model", DEFAULT_VISION_MODEL) or DEFAULT_VISION_MODEL).strip()
    try:
        models = loaded_lmstudio_models(base_url)
    except Exception:
        models = []
    if configured:
        return configured, True, models
    for model in models:
        if is_vision_model_name(model):
            return model, True, models
    llm_model = str(settings.get("llm_model", "") or "")
    return llm_model, False, models


def call_plain_lmstudio(
    question: str,
    base_url: str,
    model_id: str,
    timeout: int = 120,
    max_tokens: int = 1800,
    topic_context: str = "",
) -> tuple[str, str]:
    system_content = LOCAL_RUNTIME_SYSTEM_PROMPT
    if topic_context:
        system_content = f"{LOCAL_RUNTIME_SYSTEM_PROMPT}\n\n{topic_context}"
    body = {
        "model": model_id,
        "messages": [
            {"role": "system", "content": system_content},
            {"role": "user", "content": f"/no_think\n\n{question}"},
        ],
        "temperature": 0.2,
        "max_tokens": max_tokens,
        "stream": False,
    }
    response = lmstudio_request_json(base_url, "chat/completions", method="POST", payload=body, timeout=min(timeout, 120))
    content, reasoning = extract_chat_content(response)
    if content:
        return content, ""
    if reasoning:
        retry_body = dict(body)
        retry_body["max_tokens"] = max(max_tokens, 3200)
        retry_body["messages"] = [
            body["messages"][0],
            {
                "role": "user",
                "content": "/no_think\n\n" + msg("prompts.reasoning_retry_user", question=question),
            },
        ]
        retry = lmstudio_request_json(base_url, "chat/completions", method="POST", payload=retry_body, timeout=min(timeout, 180))
        retry_content, retry_reasoning = extract_chat_content(retry)
        if retry_content:
            return retry_content, msg("lmstudio.reasoning_retry_warning")
        if retry_reasoning:
            return "", msg("lmstudio.reasoning_no_final")
    return "", msg("lmstudio.empty_response")
