import asyncio
import os
from pathlib import Path

from lightrag import LightRAG
from lightrag.kg.shared_storage import initialize_pipeline_status

from lmstudio_common import (
    API_KEY,
    BASE_URL,
    EMBEDDING_DIM,
    EMBEDDING_MODEL,
    LLM_MODEL,
    VAULT_DIR,
    WORKING_DIR,
    embedding_func,
    lmstudio_complete,
)
from local_tokenizer import LOCAL_TOKENIZER
from vault_sources import collect_markdown_documents
from knowledgelab.config import ROOT



CHUNK_TOKEN_SIZE = int(os.getenv("LMSTUDIO_CHUNK_TOKEN_SIZE", "800"))
CHUNK_OVERLAP_TOKEN_SIZE = int(os.getenv("LMSTUDIO_CHUNK_OVERLAP_TOKEN_SIZE", "100"))
MAX_DOC_CHARS = int(os.getenv("LMSTUDIO_MAX_DOC_CHARS", "0"))


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
            "enable_cot": False,
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
        batch_size = int(os.getenv("LMSTUDIO_INGEST_BATCH_SIZE", "50"))
        file_paths = [doc["rel"] for doc in docs]
        print(f"Ingesting {len(docs)} files (batch size: {batch_size}):")
        for doc in docs:
            suffix = f" [{doc['scope']}; layer={doc.get('layer', 'active')}]"
            if doc["project"]:
                suffix += f" project={doc['project']}"
            print(f"- {doc['rel']}{suffix}")

        for i in range(0, len(docs), batch_size):
            batch = docs[i : i + batch_size]
            batch_paths = file_paths[i : i + batch_size]
            print(f"  Batch {i // batch_size + 1}: {len(batch)} files...")
            await rag.ainsert([doc["text"] for doc in batch], file_paths=batch_paths)
    finally:
        await rag.finalize_storages()

    print(f"Done. Indexed {len(docs)} Markdown files with LM Studio.")


if __name__ == "__main__":
    asyncio.run(main())
