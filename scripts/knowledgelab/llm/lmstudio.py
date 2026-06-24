"""Direct LM Studio API adapter — HTTP client and model operations."""

from __future__ import annotations

import json
import os
import urllib.request

from knowledgelab.config import DEFAULT_VISION_MODEL, VISION_MODEL_MARKERS, LOCAL_RUNTIME_SYSTEM_PROMPT


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
            hint = (
                f"LM Studio server не отвечает на {base_url}.\n\n"
                "Как исправить:\n"
                "1. Откройте LM Studio\n"
                "2. Перейдите в Developer → Local Server\n"
                "3. Нажмите 'Start Server' или включите переключатель Status\n"
                f"4. Убедитесь, что порт совпадает: {base_url.split(':')[-1].split('/')[0]}\n\n"
                "Также можно открыть LightRAG-Control для проверки."
            )
        elif "Timeout" in error_detail or "timed out" in error_detail:
            hint = (
                f"LM Studio не отвечает вовремя на {base_url}.\n\n"
                "Возможные причины:\n"
                "- Сервер запускается, подождите 10-15 секунд\n"
                "- Модель загружается, проверьте LM Studio\n"
                "- Слишком большая нагрузка на GPU"
            )
        else:
            hint = (
                f"LM Studio server не отвечает на {base_url}.\n"
                f"Детали: {error_detail}\n\n"
                "Откройте LM Studio → Developer → Local Server и убедитесь, что сервер запущен."
            )
        return False, hint, []

    if not require_models:
        return True, "LM Studio server отвечает.", models

    missing = [model for model in [required_model] if model not in models]
    if missing:
        loaded = ", ".join(models) if models else "нет загруженных моделей"
        return (
            False,
            f"LM Studio server отвечает, но модель {', '.join(missing)} не загружена. Сейчас загружено: {loaded}. Откройте LightRAG-Control или LM Studio и загрузите модель.",
            models,
        )
    return True, "LM Studio готов.", models


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
) -> tuple[str, str]:
    body = {
        "model": model_id,
        "messages": [
            {"role": "system", "content": LOCAL_RUNTIME_SYSTEM_PROMPT},
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
                "content": (
                    "/no_think\n\n"
                    "Ответь финальным сообщением без рассуждений. "
                    "Если вопрос короткий или бытовой, ответь естественно и кратко на русском.\n\n"
                    f"{question}"
                ),
            },
        ]
        retry = lmstudio_request_json(base_url, "chat/completions", method="POST", payload=retry_body, timeout=min(timeout, 180))
        retry_content, retry_reasoning = extract_chat_content(retry)
        if retry_content:
            return retry_content, "Первый ответ модели ушел в reasoning-режим; я повторил запрос в plain-режиме."
        if retry_reasoning:
            return "", "Модель рассуждала, но не вернула финальный текст. В LM Studio отключите thinking/reasoning для этой модели или попробуйте другой instruct-моделью."
    return "", "Модель вернула пустой ответ."
