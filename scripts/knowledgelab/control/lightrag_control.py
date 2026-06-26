"""Runtime orchestration used by LightRAG-Chat and Control launchers."""

from __future__ import annotations

import os
from collections.abc import Callable, MutableMapping

from knowledgelab.config import DEFAULT_LLM_MODEL, DEFAULT_VISION_MODEL, LMSTUDIO_API_URL
from knowledgelab.llm.lmstudio import (
    available_lmstudio_models,
    call_plain_lmstudio as call_plain_lmstudio_adapter,
    check_lmstudio_ready as check_lmstudio_ready_adapter,
    extract_chat_content,
    is_vision_model_name,
    lmstudio_request_json,
    loaded_lmstudio_models,
    vision_model_state as vision_model_state_adapter,
)
from knowledgelab.llm.model_manager import ModelManager
from knowledgelab.llm.port_detector import (
    DETECT_TIMEOUT,
    detect_lmstudio_base_url,
    is_lmstudio_base_url_available,
    normalize_lmstudio_base_url,
)


SettingsMap = MutableMapping[str, object]


def _model_matches(expected: str, actual: str) -> bool:
    left = expected.strip().lower()
    right = actual.strip().lower()
    return bool(left and right and (left == right or left in right or right in left))


class LightRAGControl:
    """Small control-plane facade for LM Studio runtime orchestration."""

    def __init__(
        self,
        settings: SettingsMap,
        *,
        save_settings: Callable[[], None] | None = None,
        timeout_seconds: Callable[[], int] | None = None,
    ) -> None:
        self.settings = settings
        self._save_settings = save_settings or (lambda: None)
        self._timeout_seconds = timeout_seconds or (lambda: 120)
        self._model_manager = ModelManager(str(self.settings.get("lmstudio_base_url", LMSTUDIO_API_URL)))

    def lmstudio_base_url(self) -> str:
        configured = normalize_lmstudio_base_url(str(self.settings.get("lmstudio_base_url", "") or ""))
        if is_lmstudio_base_url_available(configured, timeout=DETECT_TIMEOUT):
            base_url = configured
        else:
            base_url, _source, found = detect_lmstudio_base_url(configured)
            if not found and configured:
                base_url = configured
        if self.settings.get("lmstudio_base_url") != base_url:
            self.settings["lmstudio_base_url"] = base_url
            self._save_settings()
        self._model_manager.base_url = base_url.rstrip("/")
        return base_url

    def llm_model_id(self) -> str:
        return str(self.settings.get("llm_model", DEFAULT_LLM_MODEL) or DEFAULT_LLM_MODEL)

    def vision_model_id(self) -> str:
        configured = str(self.settings.get("vision_model", DEFAULT_VISION_MODEL) or DEFAULT_VISION_MODEL).strip()
        if configured and is_vision_model_name(configured):
            return configured
        if configured:
            return ""
        try:
            loaded = self.loaded_lmstudio_models()
        except Exception:
            loaded = []
        for model in loaded:
            if is_vision_model_name(model):
                return model
        try:
            available = available_lmstudio_models(self.lmstudio_base_url())
        except Exception:
            available = []
        for model in available:
            if is_vision_model_name(model):
                return model
        return ""

    def auto_switch_models_enabled(self) -> bool:
        return bool(self.settings.get("auto_switch_models", True))

    def loaded_lmstudio_models(self) -> list[str]:
        return loaded_lmstudio_models(self.lmstudio_base_url())

    def lmstudio_request_json(
        self,
        path: str,
        *,
        method: str = "GET",
        payload: dict | None = None,
        timeout: float = 8.0,
    ) -> dict:
        return lmstudio_request_json(
            self.lmstudio_base_url(),
            path,
            method=method,
            payload=payload,
            timeout=timeout,
        )

    def check_lmstudio_ready(self, *, require_models: bool = True) -> tuple[bool, str, list[str]]:
        if self.auto_switch_models_enabled() and require_models:
            self.ensure_model_loaded(self.llm_model_id())
        return check_lmstudio_ready_adapter(
            self.lmstudio_base_url(),
            self.llm_model_id(),
            require_models=require_models,
        )

    def ensure_model_loaded(self, model_id: str) -> bool:
        model_id = str(model_id or "").strip()
        if not model_id:
            return False
        self._model_manager.base_url = self.lmstudio_base_url().rstrip("/")
        return self._model_manager.ensure_model(model_id)

    def ensure_vision_model(self) -> tuple[str, bool, list[str]]:
        model = self.vision_model_id()
        if self.auto_switch_models_enabled() and model:
            self.ensure_model_loaded(model)
        return self.vision_model_state()

    def vision_model_state(self) -> tuple[str, bool, list[str]]:
        model, ready, loaded = vision_model_state_adapter(self.settings, self.lmstudio_base_url())
        if ready:
            return model, ready, loaded
        configured = str(model or self.vision_model_id()).strip()
        if configured and is_vision_model_name(configured) and any(_model_matches(configured, item) for item in loaded):
            return configured, True, loaded
        return configured, False, loaded

    def call_plain_lmstudio(
        self,
        question: str,
        *,
        max_tokens: int | None = None,
        topic_context: str = "",
    ) -> tuple[str, str]:
        max_tokens = max_tokens or int(os.getenv("LMSTUDIO_GUI_MAX_RESPONSE_TOKENS", "1800"))
        if self.auto_switch_models_enabled():
            self.ensure_model_loaded(self.llm_model_id())
        return call_plain_lmstudio_adapter(
            question,
            self.lmstudio_base_url(),
            self.llm_model_id(),
            timeout=min(self._timeout_seconds(), 120),
            max_tokens=max_tokens,
            topic_context=topic_context,
        )

    def extract_chat_content(self, response: dict) -> tuple[str, str]:
        return extract_chat_content(response)
