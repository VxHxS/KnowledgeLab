"""Shared LM Studio configuration and utilities for KnowledgeLab scripts."""

import os
from pathlib import Path

import numpy as np
from knowledgelab.config import ROOT, VAULT_DIR, LOCAL_RUNTIME_SYSTEM_PROMPT, LMSTUDIO_API_URL
from lightrag.llm.openai import openai_complete
from lightrag.utils import wrap_embedding_func_with_attrs
from openai import AsyncOpenAI


DEFAULT_WORKING_DIR = ROOT / "LightRAG" / "rag_storage_lmstudio"
WORKING_DIR = Path(os.getenv("LMSTUDIO_RAG_DIR", str(DEFAULT_WORKING_DIR)))
if not WORKING_DIR.is_absolute():
    WORKING_DIR = ROOT / WORKING_DIR
BASE_URL = os.getenv("LMSTUDIO_BASE_URL", LMSTUDIO_API_URL)
API_KEY = os.getenv("LMSTUDIO_API_KEY", "lm-studio")
LLM_MODEL = os.getenv("LMSTUDIO_LLM_MODEL", "qwen/qwen3-14b")
EMBEDDING_MODEL = os.getenv("LMSTUDIO_EMBEDDING_MODEL", "text-embedding-nomic-embed-text-v1.5")
EMBEDDING_DIM = int(os.getenv("LMSTUDIO_EMBEDDING_DIM", "768"))
EMBEDDING_CLIENT = AsyncOpenAI(base_url=BASE_URL, api_key=API_KEY)


@wrap_embedding_func_with_attrs(embedding_dim=EMBEDDING_DIM, max_token_size=8192)
async def embedding_func(texts: list[str]) -> np.ndarray:
    response = await EMBEDDING_CLIENT.embeddings.create(
        model=EMBEDDING_MODEL,
        input=texts,
    )
    return np.array([item.embedding for item in response.data], dtype=np.float32)


async def lmstudio_complete(
    prompt: str,
    system_prompt: str | None = None,
    history_messages: list[dict] | None = None,
    keyword_extraction: bool = False,
    **kwargs,
) -> str:
    if "/no_think" not in prompt:
        prompt = f"{prompt}\n\n/no_think"
    return await openai_complete(
        prompt,
        system_prompt=system_prompt,
        history_messages=history_messages,
        keyword_extraction=keyword_extraction,
        **kwargs,
    )


def chat_message_content(response) -> tuple[str, str]:
    """Extract content and reasoning from response. Returns (content, reasoning)."""
    message = response.choices[0].message
    content = getattr(message, "content", None)
    if isinstance(content, str) and content.strip():
        return content.strip(), ""
    reasoning = getattr(message, "reasoning_content", None)
    if isinstance(reasoning, str) and reasoning.strip():
        return "", reasoning.strip()
    return "", ""
