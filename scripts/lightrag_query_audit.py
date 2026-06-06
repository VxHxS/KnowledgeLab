from __future__ import annotations

import os
from typing import Any

from lightrag import QueryParam


TRUE_VALUES = {"1", "true", "yes", "y", "on"}
FALSE_VALUES = {"0", "false", "no", "n", "off"}


def env_flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in TRUE_VALUES:
        return True
    if normalized in FALSE_VALUES:
        return False
    return default


def env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    try:
        return int(value)
    except ValueError:
        return default


def build_query_param(
    *,
    top_k: int,
    chunk_top_k: int,
    max_total_tokens: int,
    only_need_context: bool = False,
) -> QueryParam:
    return QueryParam(
        mode="naive",
        only_need_context=only_need_context,
        top_k=top_k,
        chunk_top_k=chunk_top_k,
        max_total_tokens=max_total_tokens,
        include_references=True,
        enable_rerank=False,
    )


def build_bypass_param() -> QueryParam:
    return QueryParam(
        mode="bypass",
        stream=False,
        include_references=False,
    )


def retrieval_stats(result: dict[str, Any]) -> dict[str, Any]:
    data = result.get("data") or {}
    metadata = result.get("metadata") or {}
    processing_info = metadata.get("processing_info") or {}
    chunks = data.get("chunks") or []
    references = data.get("references") or []
    entities = data.get("entities") or []
    relationships = data.get("relationships") or []

    final_chunks = processing_info.get("final_chunks_count")
    if final_chunks is None:
        final_chunks = len(chunks)
    total_found = processing_info.get("total_chunks_found")
    if total_found is None:
        total_found = final_chunks

    return {
        "status": result.get("status", "unknown"),
        "message": result.get("message", ""),
        "mode": metadata.get("query_mode", metadata.get("mode", "unknown")),
        "total_chunks_found": int(total_found or 0),
        "final_chunks_count": int(final_chunks or 0),
        "chunks": chunks,
        "references": references,
        "entities": entities,
        "relationships": relationships,
    }


def has_usable_context(result: dict[str, Any]) -> bool:
    stats = retrieval_stats(result)
    if stats["status"] != "success":
        return False
    return bool(
        stats["final_chunks_count"] > 0
        or stats["chunks"]
        or stats["entities"]
        or stats["relationships"]
    )


def format_context_warning(result: dict[str, Any] | None = None, *, error: Exception | None = None) -> str:
    if error is not None:
        return (
            "LightRAG не смог получить контекст перед ответом; "
            f"ответ создан без контекста базы знаний. Детали: {error}"
        )

    stats = retrieval_stats(result or {})
    return (
        "LightRAG не нашёл подходящий контекст; "
        "ответ создан без контекста базы знаний. "
        f"Статус: {stats['status']}, chunks: {stats['final_chunks_count']}, "
        f"references: {len(stats['references'])}."
    )


def format_retrieval_audit(result: dict[str, Any], *, max_references: int = 8) -> str:
    stats = retrieval_stats(result)
    lines = [
        "LightRAG retrieval audit:",
        f"- status: {stats['status']}",
        f"- mode: {stats['mode']}",
        f"- chunks found: {stats['total_chunks_found']}",
        f"- final chunks sent to answer: {stats['final_chunks_count']}",
        f"- references: {len(stats['references'])}",
    ]
    if stats["message"]:
        lines.append(f"- message: {stats['message']}")

    if stats["references"]:
        lines.append("- source files:")
        for ref in stats["references"][:max_references]:
            ref_id = ref.get("reference_id", "?")
            path = ref.get("file_path", "unknown_source")
            lines.append(f"  [{ref_id}] {path}")
        remaining = len(stats["references"]) - max_references
        if remaining > 0:
            lines.append(f"  ...and {remaining} more")

    return "\n".join(lines)


def require_usable_context(result: dict[str, Any]) -> None:
    if has_usable_context(result):
        return
    audit = format_retrieval_audit(result)
    raise RuntimeError(
        "LightRAG did not retrieve usable context, so no answer was generated.\n"
        f"{audit}"
    )


def llm_content(result: dict[str, Any]) -> str:
    response = result.get("llm_response") or {}
    content = response.get("content")
    if isinstance(content, str) and content.strip():
        return content.strip()
    reasoning = response.get("reasoning_content")
    if isinstance(reasoning, str) and reasoning.strip():
        return ""
    return ""
