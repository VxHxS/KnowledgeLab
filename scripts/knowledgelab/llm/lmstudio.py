"""Direct LM Studio API adapter — HTTP client and model operations."""

from __future__ import annotations

import json
import os
import re
import urllib.request

from knowledgelab.config import DEFAULT_VISION_MODEL, VISION_MODEL_MARKERS, LOCAL_RUNTIME_SYSTEM_PROMPT
from knowledgelab.i18n.messages import msg
from knowledgelab.llm.port_detector import normalize_lmstudio_base_url, rest_models_url


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
    normalized = normalize_lmstudio_base_url(base_url)
    url = f"{normalized}/{path.lstrip('/')}"
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
    response = lmstudio_request_json(normalize_lmstudio_base_url(base_url), "models", timeout=3.0)
    data = response.get("data") if isinstance(response, dict) else []
    ids = []
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and item.get("id"):
                ids.append(str(item["id"]))
    return ids


def _request_json_url(url: str, timeout: float = 4.0):
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read(200_000).decode("utf-8", errors="replace")
    return json.loads(raw) if raw.strip() else {}


def available_lmstudio_models(base_url: str) -> list[str]:
    """Return local model IDs from LM Studio, with OpenAI-compatible fallback."""
    ids: set[str] = set()
    try:
        response = _request_json_url(rest_models_url(base_url), timeout=4.0)
    except Exception:
        response = {}
    models = []
    if isinstance(response, list):
        models = response
    elif isinstance(response, dict):
        raw_models = response.get("models", response.get("data", []))
        models = raw_models if isinstance(raw_models, list) else []
    if isinstance(models, list):
        for model in models:
            if not isinstance(model, dict):
                continue
            for key in ("id", "key", "path", "displayName", "name"):
                value = str(model.get(key) or "").strip()
                if value:
                    ids.add(value)
            selected = model.get("selected_variant")
            if isinstance(selected, dict):
                for key in ("id", "key", "path"):
                    value = str(selected.get(key) or "").strip()
                    if value:
                        ids.add(value)
            loaded = model.get("loaded_instances")
            if isinstance(loaded, list):
                for item in loaded:
                    if isinstance(item, dict):
                        value = str(item.get("model_key") or item.get("id") or "").strip()
                        if value:
                            ids.add(value)
    if not ids:
        ids.update(loaded_lmstudio_models(base_url))
    return sorted(ids)


EMBEDDING_MODEL_MARKERS = ("embedding", "embed", "nomic", "bge", "e5", "gte", "minilm")


def is_embedding_model_name(model: str) -> bool:
    lowered = model.lower()
    return any(marker in lowered for marker in EMBEDDING_MODEL_MARKERS)


def _model_size_score(model: str) -> float:
    matches = re.findall(r"(\d+(?:\.\d+)?)\s*b\b", model.lower())
    if not matches:
        return 0.0
    try:
        return max(float(value) for value in matches)
    except ValueError:
        return 0.0


def model_role_score(model: str, role: str) -> float:
    lowered = model.lower()
    score = _model_size_score(lowered) * 10.0
    vision = is_vision_model_name(model)
    embedding = is_embedding_model_name(model)

    if role == "embedding":
        score += 1000 if embedding else -700
        if "nomic" in lowered:
            score += 120
        if "text-embedding" in lowered:
            score += 120
        if vision:
            score -= 800
        return score

    if role == "vision":
        score += 1000 if vision else -600
        if "qwen2.5-vl" in lowered:
            score += 180
        if "instruct" in lowered:
            score += 60
        if embedding:
            score -= 900
        return score

    score += 1000 if not vision and not embedding else -700
    if "qwen3" in lowered:
        score += 120
    if "coder" in lowered:
        score += 80
    if "instruct" in lowered or "chat" in lowered:
        score += 50
    return score


def ranked_lmstudio_models(models: list[str], role: str) -> list[str]:
    unique = sorted({str(model).strip() for model in models if str(model).strip()})
    return sorted(unique, key=lambda model: (-model_role_score(model, role), model.lower()))


def recommended_lmstudio_model(models: list[str], role: str) -> str:
    ranked = ranked_lmstudio_models(models, role)
    return ranked[0] if ranked else ""


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
