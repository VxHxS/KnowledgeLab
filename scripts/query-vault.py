import asyncio
import os
import sys
from pathlib import Path

import numpy as np
from lightrag import LightRAG, QueryParam
from lightrag.kg.shared_storage import initialize_pipeline_status
from lightrag.llm.ollama import ollama_embed, ollama_model_complete
from lightrag.utils import wrap_embedding_func_with_attrs

from local_tokenizer import LOCAL_TOKENIZER


ROOT = Path(__file__).resolve().parents[1]
WORKING_DIR = ROOT / "LightRAG" / "rag_storage_core"
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen3:14b")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "bge-m3")
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "1024"))


@wrap_embedding_func_with_attrs(embedding_dim=EMBEDDING_DIM, max_token_size=8192)
async def embedding_func(texts: list[str]) -> np.ndarray:
    return await ollama_embed.func(
        texts,
        embed_model=EMBEDDING_MODEL,
        host=OLLAMA_HOST,
    )


async def main() -> None:
    question = " ".join(sys.argv[1:]).strip()
    if not question:
        question = "What does this vault say about Unity and mastering workflows?"

    rag = LightRAG(
        working_dir=str(WORKING_DIR),
        llm_model_func=ollama_model_complete,
        llm_model_name=LLM_MODEL,
        llm_model_kwargs={
            "host": OLLAMA_HOST,
            "options": {"num_ctx": 32768, "temperature": 0.2},
        },
        embedding_func=embedding_func,
        tokenizer=LOCAL_TOKENIZER,
    )

    await rag.initialize_storages()
    await initialize_pipeline_status()
    try:
        response = await rag.aquery(question, param=QueryParam(mode="hybrid"))
        print(response)
    finally:
        await rag.finalize_storages()


if __name__ == "__main__":
    asyncio.run(main())
