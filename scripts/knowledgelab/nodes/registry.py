"""Node registry — central lookup for all registered KnowledgeLab nodes."""
from __future__ import annotations

from typing import Any

from knowledgelab.nodes.base import KnowledgeNode


class NodeRegistry:
    """Singleton registry mapping node IDs to their classes."""

    _instance: NodeRegistry | None = None
    _nodes: dict[str, type[KnowledgeNode]]

    def __new__(cls) -> NodeRegistry:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._nodes = {}
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        cls._instance = None

    def register(self, node_class: type[KnowledgeNode]) -> type[KnowledgeNode]:
        """Register a node class. Can be used as a decorator."""
        instance = node_class()
        self._nodes[instance.id] = node_class
        return node_class

    def get(self, node_id: str) -> type[KnowledgeNode] | None:
        return self._nodes.get(node_id)

    def list_nodes(self) -> list[dict[str, str]]:
        """Return metadata for all registered nodes."""
        result = []
        for node_id, cls in self._nodes.items():
            instance = cls()
            result.append({
                "id": node_id,
                "name": instance.name,
                "purpose": instance.purpose,
            })
        return result

    def run_node(self, node_id: str, payload: dict[str, Any], context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Run a node by ID with the given payload and context."""
        cls = self._nodes.get(node_id)
        if cls is None:
            return {"error": f"Node not found: {node_id}"}
        instance = cls()
        ctx = context or {}
        try:
            return instance.run(payload, ctx)
        except Exception as exc:
            return {"error": str(exc), "node_id": node_id}


_registry: NodeRegistry | None = None


def get_registry() -> NodeRegistry:
    global _registry
    if _registry is None:
        _registry = NodeRegistry()
    return _registry
