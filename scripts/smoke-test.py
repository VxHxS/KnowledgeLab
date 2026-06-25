import asyncio
import hashlib
import shutil
from pathlib import Path

import numpy as np
from lightrag import LightRAG, QueryParam
from lightrag.kg.shared_storage import initialize_pipeline_status
from lightrag.utils import wrap_embedding_func_with_attrs

from local_tokenizer import LOCAL_TOKENIZER
from knowledgelab.config import ROOT, VAULT_DIR



WORKING_DIR = ROOT / "LightRAG" / "rag_storage_smoke"


async def dummy_llm(prompt: str, **kwargs) -> str:
    return ""


def vector_for(text: str, dims: int = 64) -> np.ndarray:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    values = np.frombuffer((digest * ((dims // len(digest)) + 1))[:dims], dtype=np.uint8)
    vector = values.astype(np.float32) / 255.0
    norm = np.linalg.norm(vector)
    return vector / norm if norm else vector


@wrap_embedding_func_with_attrs(embedding_dim=64, max_token_size=8192)
async def embedding_func(texts: list[str]) -> np.ndarray:
    return np.vstack([vector_for(text) for text in texts])


def collect_markdown() -> list[tuple[str, str]]:
    docs = []
    for path in sorted(VAULT_DIR.rglob("*.md")):
        if ".obsidian" in path.parts:
            continue
        rel = path.relative_to(VAULT_DIR).as_posix()
        text = path.read_text(encoding="utf-8")
        docs.append((rel, f"# Source: {rel}\n\n{text}"))
    return docs


async def main() -> None:
    if WORKING_DIR.exists():
        shutil.rmtree(WORKING_DIR)
    WORKING_DIR.mkdir(parents=True, exist_ok=True)

    rag = LightRAG(
        working_dir=str(WORKING_DIR),
        llm_model_func=dummy_llm,
        embedding_func=embedding_func,
        tokenizer=LOCAL_TOKENIZER,
        auto_manage_storages_states=False,
    )

    await rag.initialize_storages()
    await initialize_pipeline_status()
    try:
        docs = collect_markdown()
        for rel, text in docs:
            print(f"Ingesting {rel}")
            await rag.ainsert(text, file_paths=rel)

        context = await rag.aquery(
            "Unity profiling and mastering checklist",
            param=QueryParam(mode="naive", only_need_context=True, top_k=3),
        )
        print("\nRetrieved context preview:")
        print(str(context)[:1200])
        print(f"\nSmoke test OK. Indexed {len(docs)} Markdown files.")
    finally:
        await rag.finalize_storages()


if __name__ == "__main__":
    asyncio.run(main())
