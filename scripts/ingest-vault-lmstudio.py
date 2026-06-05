import asyncio
import os
from pathlib import Path

import numpy as np
from lightrag import LightRAG
from lightrag.kg.shared_storage import initialize_pipeline_status
from lightrag.llm.openai import openai_complete
from lightrag.utils import wrap_embedding_func_with_attrs
from openai import AsyncOpenAI

from local_tokenizer import LOCAL_TOKENIZER
from vault_sources import collect_markdown_documents


ROOT = Path(__file__).resolve().parents[1]
VAULT_DIR = ROOT / "Obsidian-Test-Vault"
DEFAULT_WORKING_DIR = ROOT / "LightRAG" / "rag_storage_lmstudio"
WORKING_DIR = Path(os.getenv("LMSTUDIO_RAG_DIR", str(DEFAULT_WORKING_DIR)))
if not WORKING_DIR.is_absolute():
    WORKING_DIR = ROOT / WORKING_DIR
BASE_URL = os.getenv("LMSTUDIO_BASE_URL", "http://127.0.0.1:1234/v1")
API_KEY = os.getenv("LMSTUDIO_API_KEY", "lm-studio")
LLM_MODEL = os.getenv("LMSTUDIO_LLM_MODEL", "qwen/qwen3-14b")
EMBEDDING_MODEL = os.getenv("LMSTUDIO_EMBEDDING_MODEL", "nomic-embed")
EMBEDDING_DIM = int(os.getenv("LMSTUDIO_EMBEDDING_DIM", "768"))
CHUNK_TOKEN_SIZE = int(os.getenv("LMSTUDIO_CHUNK_TOKEN_SIZE", "800"))
CHUNK_OVERLAP_TOKEN_SIZE = int(os.getenv("LMSTUDIO_CHUNK_OVERLAP_TOKEN_SIZE", "100"))
MAX_DOC_CHARS = int(os.getenv("LMSTUDIO_MAX_DOC_CHARS", "0"))
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


async def main() -> None:
    WORKING_DIR.mkdir(parents=True, exist_ok=True)
    docs = collect_markdown_documents(VAULT_DIR)
    if not docs:
        raise SystemExit(f"No Markdown files found in {VAULT_DIR}")
    if MAX_DOC_CHARS > 0:
        for doc in docs:
            text = doc["text"]
            if len(text) > MAX_DOC_CHARS:
                doc["text"] = (
                    text[:MAX_DOC_CHARS].rstrip()
                    + f"\n\n[Truncated for test ingest at {MAX_DOC_CHARS} characters]"
                )

    rag = LightRAG(
        working_dir=str(WORKING_DIR),
        llm_model_func=lmstudio_complete,
        llm_model_name=LLM_MODEL,
        llm_model_kwargs={
            "base_url": BASE_URL,
            "api_key": API_KEY,
            "temperature": 0.2,
            "max_tokens": 2048,
            "stream": False,
            "enable_cot": True,
        },
        embedding_func=embedding_func,
        tokenizer=LOCAL_TOKENIZER,
        chunk_token_size=CHUNK_TOKEN_SIZE,
        chunk_overlap_token_size=CHUNK_OVERLAP_TOKEN_SIZE,
        llm_model_max_async=1,
        embedding_func_max_async=1,
        max_parallel_insert=1,
        entity_extract_max_gleaning=0,
    )

    await rag.initialize_storages()
    await initialize_pipeline_status()
    try:
        file_paths = [doc["rel"] for doc in docs]
        print("Ingesting:")
        for doc in docs:
            suffix = f" [{doc['scope']}]"
            if doc["project"]:
                suffix += f" project={doc['project']}"
            print(f"- {doc['rel']}{suffix}")
        await rag.ainsert([doc["text"] for doc in docs], file_paths=file_paths)
    finally:
        await rag.finalize_storages()

    print(f"Done. Indexed {len(docs)} Markdown files with LM Studio.")


if __name__ == "__main__":
    asyncio.run(main())
