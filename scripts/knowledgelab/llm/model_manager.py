"""Model manager: auto-switch LLM/Vision/Embeddings via LM Studio API."""
from __future__ import annotations

import json
import urllib.request
from typing import Any

from knowledgelab.llm.port_detector import lmstudio_server_root, normalize_lmstudio_base_url


def _model_matches(expected: str, actual: str) -> bool:
    left = expected.strip().lower()
    right = actual.strip().lower()
    return bool(left and right and (left == right or left in right or right in left))


class ModelManager:
    """Manages model loading/unloading via LM Studio API."""

    def __init__(self, base_url: str = "http://127.0.0.1:1234/v1") -> None:
        self.base_url = normalize_lmstudio_base_url(base_url).rstrip("/")

    def _url(self, path: str, *, native: bool = False) -> str:
        base = lmstudio_server_root(self.base_url).rstrip() + "/api/v1" if native else normalize_lmstudio_base_url(self.base_url).rstrip("/")
        return f"{base}/{path.lstrip('/')}"

    def _request(self, path: str, method: str = "GET", timeout: int = 10, *, native: bool = False) -> dict[str, Any] | None:
        url = self._url(path, native=native)
        headers = {"Content-Type": "application/json"}
        request = urllib.request.Request(url, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read(100_000).decode("utf-8"))
        except Exception:
            return None

    def _post(self, path: str, data: dict | None = None, timeout: int = 30, *, native: bool = False) -> dict[str, Any] | None:
        url = self._url(path, native=native)
        headers = {"Content-Type": "application/json"}
        body = json.dumps(data or {}).encode("utf-8")
        request = urllib.request.Request(url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read(100_000).decode("utf-8", errors="replace")
                return json.loads(raw) if raw.strip() else {}
        except Exception:
            return None

    def get_loaded_models(self) -> list[str]:
        """Return list of currently loaded model IDs."""
        response = self._request("models")
        if not response:
            return []
        return [m.get("id", "") for m in response.get("data", []) if m.get("id")]

    def is_model_loaded(self, model_id: str) -> bool:
        """Check if a specific model is loaded."""
        loaded = self.get_loaded_models()
        return any(_model_matches(model_id, lid) for lid in loaded)

    def load_model(self, model_id: str) -> bool:
        """Load a model into LM Studio."""
        payloads = (
            {"model": model_id},
            {"modelKey": model_id},
            {"path": model_id},
        )
        for payload in payloads:
            response = self._post("models/load", payload, timeout=120, native=True)
            if response is not None:
                return True
        return False

    def unload_model(self, model_id: str) -> bool:
        """Unload a model from LM Studio."""
        payloads = (
            {"model": model_id},
            {"modelKey": model_id},
            {"path": model_id},
        )
        for payload in payloads:
            response = self._post("models/unload", payload, timeout=30, native=True)
            if response is not None:
                return True
        return False

    def ensure_model(self, model_id: str) -> bool:
        """Ensure a model is loaded. Load if not already loaded."""
        if self.is_model_loaded(model_id):
            return True
        return self.load_model(model_id)

    def switch_to_model(self, needed_model: str, current_models: list[str] | None = None) -> bool:
        """Switch to needed model, unloading others if needed."""
        if current_models is None:
            current_models = self.get_loaded_models()

        if any(needed_model in m for m in current_models):
            return True

        for loaded in current_models:
            if needed_model not in loaded:
                self.unload_model(loaded)

        return self.load_model(needed_model)

    def get_model_info(self) -> dict[str, Any]:
        """Get current model status."""
        loaded = self.get_loaded_models()
        return {
            "loaded": loaded,
            "count": len(loaded),
            "base_url": self.base_url,
        }
