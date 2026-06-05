import asyncio
import logging
import os
import sys
from pathlib import Path

import numpy as np
from lightrag import LightRAG
from lightrag.kg.shared_storage import initialize_pipeline_status
from lightrag.llm.openai import openai_complete
from lightrag.utils import wrap_embedding_func_with_attrs
from openai import AsyncOpenAI

from lightrag_query_audit import (
    build_bypass_param,
    build_query_param,
    env_flag,
    env_int,
    format_context_warning,
    format_retrieval_audit,
    has_usable_context,
    llm_content,
    require_usable_context,
)
from local_tokenizer import LOCAL_TOKENIZER


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WORKING_DIR = ROOT / "LightRAG" / "rag_storage_lmstudio"
WORKING_DIR = Path(os.getenv("LMSTUDIO_RAG_DIR", str(DEFAULT_WORKING_DIR)))
if not WORKING_DIR.is_absolute():
    WORKING_DIR = ROOT / WORKING_DIR
BASE_URL = os.getenv("LMSTUDIO_BASE_URL", "http://127.0.0.1:1234/v1")
API_KEY = os.getenv("LMSTUDIO_API_KEY", "lm-studio")
LLM_MODEL = os.getenv("LMSTUDIO_LLM_MODEL", "qwen/qwen3-14b")
EMBEDDING_MODEL = os.getenv("LMSTUDIO_EMBEDDING_MODEL", "nomic-embed")
EMBEDDING_DIM = int(os.getenv("LMSTUDIO_EMBEDDING_DIM", "768"))
LLM_CONTEXT_TOKENS = env_int("LMSTUDIO_CONTEXT_TOKENS", 8192)
LLM_MAX_RESPONSE_TOKENS = env_int("LMSTUDIO_MAX_RESPONSE_TOKENS", 2048)
DEFAULT_QUERY_MAX_TOTAL_TOKENS = max(2600, LLM_CONTEXT_TOKENS - LLM_MAX_RESPONSE_TOKENS - 512)
QUERY_TOP_K = env_int("LMSTUDIO_QUERY_TOP_K", 5)
QUERY_CHUNK_TOP_K = env_int("LMSTUDIO_QUERY_CHUNK_TOP_K", 5)
QUERY_MAX_TOTAL_TOKENS = env_int("LMSTUDIO_QUERY_MAX_TOTAL_TOKENS", DEFAULT_QUERY_MAX_TOTAL_TOKENS)
PRECHECK_RETRIEVAL = env_flag("LMSTUDIO_PRECHECK_RETRIEVAL", False)
REQUIRE_CONTEXT = env_flag("LMSTUDIO_REQUIRE_CONTEXT", False)
FALLBACK_WITH_WARNING = env_flag("LMSTUDIO_FALLBACK_WITH_WARNING", True)
SHOW_RETRIEVAL = env_flag("LMSTUDIO_SHOW_RETRIEVAL", False)
USE_LIGHTRAG = env_flag("LMSTUDIO_USE_LIGHTRAG", True)
LIGHTRAG_OFF_REASON = os.getenv(
    "LMSTUDIO_LIGHTRAG_OFF_REASON",
    "LightRAG выключен вручную; ответ создан без поиска по базе знаний.",
)
ENABLE_LLM_CACHE = env_flag("LMSTUDIO_ENABLE_LLM_CACHE", False)
EMBEDDING_CLIENT = AsyncOpenAI(base_url=BASE_URL, api_key=API_KEY)


logging.basicConfig(level=logging.WARNING)
logging.getLogger("lightrag").setLevel(logging.WARNING)
logging.getLogger("nano-vectordb").setLevel(logging.WARNING)


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


def emit_warning(message: str) -> None:
    if env_flag("LMSTUDIO_GUI_OUTPUT", False):
        print(f"::knowledge-warning {message}")
    else:
        print(f"Note: {message}", file=sys.stderr)


def read_question() -> str:
    try:
        return input("\nYou: ").strip()
    except EOFError:
        return "exit"


async def plain_lmstudio_answer(question: str) -> str:
    client = AsyncOpenAI(base_url=BASE_URL, api_key=API_KEY)
    response = await client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {
                "role": "system",
                "content": "Answer directly. LightRAG retrieval is disabled for this request.",
            },
            {"role": "user", "content": f"{question}\n\n/no_think"},
        ],
        temperature=0.2,
        max_tokens=LLM_MAX_RESPONSE_TOKENS,
        stream=False,
    )
    return (response.choices[0].message.content or "").strip()


async def main() -> None:
    if not USE_LIGHTRAG:
        print("LM Studio chat is ready. LightRAG is off.")
        print("Type exit, quit, or an empty line to close.")

        while True:
            question = read_question()
            if not question or question.lower() in {"exit", "quit"}:
                break

            try:
                response = await plain_lmstudio_answer(question)
                if not response:
                    raise RuntimeError("LM Studio returned an empty answer.")
                emit_warning(LIGHTRAG_OFF_REASON)
            except Exception as exc:
                print(f"\nERROR: {exc}")
                continue

            print("\nAssistant:")
            print(response)
        return

    if not (WORKING_DIR / "vdb_chunks.json").exists():
        raise SystemExit(f"LightRAG storage is not indexed yet: {WORKING_DIR}")

    rag = LightRAG(
        working_dir=str(WORKING_DIR),
        llm_model_func=lmstudio_complete,
        llm_model_name=LLM_MODEL,
        llm_model_kwargs={
            "base_url": BASE_URL,
            "api_key": API_KEY,
            "temperature": 0.2,
            "max_tokens": LLM_MAX_RESPONSE_TOKENS,
            "stream": False,
            "enable_cot": True,
        },
        embedding_func=embedding_func,
        tokenizer=LOCAL_TOKENIZER,
        chunk_token_size=800,
        chunk_overlap_token_size=100,
        llm_model_max_async=1,
        embedding_func_max_async=1,
        enable_llm_cache=ENABLE_LLM_CACHE,
    )

    await rag.initialize_storages()
    await initialize_pipeline_status()
    print("LightRAG chat is ready.")
    print(f"Storage: {WORKING_DIR}")
    print("Type exit, quit, or an empty line to close.")

    try:
        while True:
            question = read_question()
            if not question or question.lower() in {"exit", "quit"}:
                break

            try:
                warning: str | None = None
                use_bypass = False
                audit_result: dict | None = None

                if PRECHECK_RETRIEVAL:
                    try:
                        retrieval_result = await rag.aquery_llm(
                            question,
                            param=build_query_param(
                                top_k=QUERY_TOP_K,
                                chunk_top_k=QUERY_CHUNK_TOP_K,
                                max_total_tokens=QUERY_MAX_TOTAL_TOKENS,
                                only_need_context=True,
                            ),
                        )
                        if SHOW_RETRIEVAL:
                            print("")
                            print(format_retrieval_audit(retrieval_result))
                        if REQUIRE_CONTEXT:
                            require_usable_context(retrieval_result)
                        elif not has_usable_context(retrieval_result):
                            warning = format_context_warning(retrieval_result)
                            use_bypass = FALLBACK_WITH_WARNING
                    except Exception as exc:
                        if REQUIRE_CONTEXT or not FALLBACK_WITH_WARNING:
                            raise
                        warning = format_context_warning(error=exc)
                        use_bypass = True

                if use_bypass:
                    result = await rag.aquery_llm(question, param=build_bypass_param())
                else:
                    result = await rag.aquery_llm(
                        question,
                        param=build_query_param(
                            top_k=QUERY_TOP_K,
                            chunk_top_k=QUERY_CHUNK_TOP_K,
                            max_total_tokens=QUERY_MAX_TOTAL_TOKENS,
                        ),
                    )
                    audit_result = result
                    if REQUIRE_CONTEXT:
                        require_usable_context(result)
                    elif not has_usable_context(result):
                        warning = format_context_warning(result)
                        if FALLBACK_WITH_WARNING:
                            result = await rag.aquery_llm(question, param=build_bypass_param())
                    if SHOW_RETRIEVAL and not PRECHECK_RETRIEVAL:
                        print("")
                        print(format_retrieval_audit(audit_result or result))

                response = llm_content(result)
                if not response:
                    raise RuntimeError("LightRAG query succeeded, but the LLM returned an empty answer.")
                if warning:
                    emit_warning(warning)
            except Exception as exc:
                print(f"\nERROR: {exc}")
                continue

            print("\nAssistant:")
            print(response)
    finally:
        await rag.finalize_storages()


if __name__ == "__main__":
    os.environ.setdefault("PYTHONUTF8", "1")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
