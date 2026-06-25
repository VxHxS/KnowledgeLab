import asyncio
import logging
import os
import sys
from pathlib import Path

from lightrag import LightRAG
from lightrag.kg.shared_storage import initialize_pipeline_status

from lmstudio_common import (
    API_KEY,
    BASE_URL,
    EMBEDDING_DIM,
    EMBEDDING_MODEL,
    LOCAL_RUNTIME_SYSTEM_PROMPT,
    LLM_MODEL,
    WORKING_DIR,
    chat_message_content,
    embedding_func,
    lmstudio_complete,
)
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
from knowledgelab.config import ROOT



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
    "LightRAG отключен: ответ без базы знаний.",
)
ENABLE_LLM_CACHE = env_flag("LMSTUDIO_ENABLE_LLM_CACHE", False)


logging.basicConfig(level=logging.WARNING)
logging.getLogger("lightrag").setLevel(logging.WARNING)
logging.getLogger("nano-vectordb").setLevel(logging.WARNING)


def emit_warning(message: str) -> None:
    if env_flag("LMSTUDIO_GUI_OUTPUT", False):
        print(f"::knowledge-warning {message}")
    else:
        print(f"Note: {message}", file=sys.stderr)


async def plain_lmstudio_answer(question: str) -> tuple[str, str]:
    """Returns (content, warning). Content is the answer, warning is any reasoning-related message."""
    client = AsyncOpenAI(base_url=BASE_URL, api_key=API_KEY)
    response = await client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {
                "role": "system",
                "content": LOCAL_RUNTIME_SYSTEM_PROMPT,
            },
            {"role": "user", "content": f"/no_think\n\n{question}"},
        ],
        temperature=0.2,
        max_tokens=LLM_MAX_RESPONSE_TOKENS,
        stream=False,
    )
    content, reasoning = chat_message_content(response)
    if content:
        return content, ""
    if reasoning:
        return "", "Модель вернула только reasoning-контент. В LM Studio отключите thinking/reasoning для этой модели."
    return "", "Модель вернула пустой ответ."


async def main() -> None:
    question = " ".join(sys.argv[1:]).strip()
    if not question:
        question = "What does this vault say about Unity and mastering workflows?"

    if not USE_LIGHTRAG:
        response, warning = await plain_lmstudio_answer(question)
        if warning:
            emit_warning(warning)
        if not response:
            raise RuntimeError("LM Studio returned an empty answer.")
        if env_flag("LMSTUDIO_WARN_PLAIN_MODE", False):
            emit_warning(LIGHTRAG_OFF_REASON)
        print(response)
        return

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
            "enable_cot": False,
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
                    print(format_retrieval_audit(retrieval_result))
                    print("")
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
                print(format_retrieval_audit(audit_result or result))
                print("")

        response = llm_content(result)
        if not response:
            raise RuntimeError("LightRAG query succeeded, but the LLM returned an empty answer.")
        if warning:
            emit_warning(warning)
        print(response)
    finally:
        await rag.finalize_storages()


if __name__ == "__main__":
    asyncio.run(main())
