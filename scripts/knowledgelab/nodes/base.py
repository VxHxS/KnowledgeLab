"""Base protocol and shared utilities for KnowledgeLab nodes."""
from __future__ import annotations

import logging
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class KnowledgeNode(Protocol):
    """Protocol that all KnowledgeLab nodes must satisfy."""

    id: str
    name: str
    purpose: str

    def run(self, payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]: ...


class BaseNode:
    """Base class providing common helpers for node implementations."""

    id: str = ""
    name: str = ""
    purpose: str = ""

    def __init__(self) -> None:
        self._logger = logging.getLogger(f"knowledgelab.nodes.{self.id}")

    def run(self, payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    def log(self, message: str) -> None:
        self._logger.info(message)

    def emit_warning(self, payload: dict[str, Any], message: str) -> None:
        warnings: list[str] = payload.setdefault("warnings", [])
        warnings.append(message)

    def emit_result(self, payload: dict[str, Any], key: str, value: Any) -> None:
        results: dict[str, Any] = payload.setdefault("result", {})
        results[key] = value
