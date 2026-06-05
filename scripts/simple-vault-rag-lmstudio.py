import asyncio
import os
import sys
from pathlib import Path

import numpy as np
from openai import AsyncOpenAI

from vault_sources import collect_markdown_documents


ROOT = Path(__file__).resolve().parents[1]
VAULT_DIR = ROOT / "Obsidian-Test-Vault"
BASE_URL = os.getenv("LMSTUDIO_BASE_URL", "http://127.0.0.1:1234/v1")
API_KEY = os.getenv("LMSTUDIO_API_KEY", "lm-studio")
LLM_MODEL = os.getenv("LMSTUDIO_LLM_MODEL", "qwen/qwen3-14b")
EMBEDDING_MODEL = os.getenv("LMSTUDIO_EMBEDDING_MODEL", "nomic-embed")


def collect_chunks(max_chars: int = 1200) -> list[dict[str, str]]:
    chunks = []
    for doc in collect_markdown_documents(VAULT_DIR):
        rel = doc["rel"]
        text = doc["text"]
        current: list[str] = []
        current_len = 0
        for paragraph in text.split("\n\n"):
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            if current and current_len + len(paragraph) > max_chars:
                chunks.append({"source": rel, "text": "\n\n".join(current)})
                current = []
                current_len = 0
            current.append(paragraph)
            current_len += len(paragraph)
        if current:
            chunks.append({"source": rel, "text": "\n\n".join(current)})
    return chunks


def normalize(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1
    return matrix / norms


async def embed(client: AsyncOpenAI, texts: list[str]) -> np.ndarray:
    response = await client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
    return np.array([item.embedding for item in response.data], dtype=np.float32)


async def main() -> None:
    question = " ".join(sys.argv[1:]).strip()
    if not question:
        question = "Какой Unity workflow описан в этом vault?"

    client = AsyncOpenAI(base_url=BASE_URL, api_key=API_KEY)
    chunks = collect_chunks()
    if not chunks:
        raise SystemExit(f"No Markdown files found in {VAULT_DIR}")

    chunk_embeddings = normalize(await embed(client, [chunk["text"] for chunk in chunks]))
    query_embedding = normalize(await embed(client, [question]))[0]
    scores = chunk_embeddings @ query_embedding
    top_indices = np.argsort(scores)[-4:][::-1]

    context_parts = []
    for rank, index in enumerate(top_indices, start=1):
        chunk = chunks[int(index)]
        context_parts.append(
            f"[{rank}] Source: {chunk['source']}\n{chunk['text']}"
        )
    context = "\n\n---\n\n".join(context_parts)

    response = await client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "Answer in Russian using only the provided Obsidian context. "
                    "Mention source file names when they matter."
                ),
            },
            {
                "role": "user",
                "content": f"Question: {question}\n\nObsidian context:\n{context}\n\n/no_think",
            },
        ],
        temperature=0.2,
        max_tokens=700,
        stream=False,
    )
    answer = response.choices[0].message.content or ""
    print(answer.strip())


if __name__ == "__main__":
    asyncio.run(main())
