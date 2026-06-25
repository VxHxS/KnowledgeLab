# LM Studio Integration

Audit date: 2026-06-25.

## Role

LM Studio is the primary local model backend for KnowledgeLab. It provides:

- chat completions for normal answers;
- embeddings for LightRAG indexing and retrieval;
- optional vision-model calls for book/image/video analysis.

KnowledgeLab should not use external LLM APIs by default.

## API Endpoint

The intended default endpoint is:

```text
http://127.0.0.1:1234/v1
```

This audit fixed stale defaults that pointed to `http://127.0.0.1:5000/v1` in:

- `scripts/knowledgelab/config.py`
- `scripts/lmstudio_common.py`

The setting can still be overridden by:

```text
LMSTUDIO_BASE_URL
```

## Models

Current defaults:

- LLM: `qwen/qwen3-14b`
- Embedding: `text-embedding-nomic-embed-text-v1.5`
- Vision: empty setting by default; the app tries to detect loaded vision-capable models by name markers.

Relevant settings:

- `lmstudio_base_url`
- `llm_model`
- `embedding_model`
- `vision_model`

Relevant environment variables:

- `LMSTUDIO_BASE_URL`
- `LMSTUDIO_API_KEY`
- `LMSTUDIO_LLM_MODEL`
- `LMSTUDIO_EMBEDDING_MODEL`
- `LMSTUDIO_EMBEDDING_DIM`
- `KNOWLEDGELAB_VISION_MODEL`

## Direct Chat Client

Current code:

- `scripts/knowledgelab/llm/lmstudio.py`

Responsibilities:

- request JSON from the LM Studio OpenAI-compatible endpoint;
- list loaded models from `/models`;
- check whether the required model is loaded;
- call `/chat/completions`;
- extract either `content` or `reasoning_content`;
- retry or warn when a Qwen-style thinking model returns reasoning without final content.

The system prompt is defined in `scripts/knowledgelab/config.py` as `LOCAL_RUNTIME_SYSTEM_PROMPT`.

## LightRAG Client

Current code:

- `scripts/lmstudio_common.py`
- `scripts/ingest-vault-lmstudio.py`
- `scripts/query-vault-lmstudio.py`

`lmstudio_common.py` defines:

- `BASE_URL`
- `API_KEY`
- `LLM_MODEL`
- `EMBEDDING_MODEL`
- `embedding_func()`
- `lmstudio_complete()`
- `chat_message_content()`

LightRAG uses LM Studio as both:

- the LLM completion backend;
- the embedding backend through `AsyncOpenAI.embeddings.create()`.

## Query Behavior

`scripts/query-vault-lmstudio.py` supports two modes:

- plain LM Studio mode when `LMSTUDIO_USE_LIGHTRAG=0`;
- LightRAG retrieval mode when LightRAG is enabled and storage exists.

Important environment flags:

- `LMSTUDIO_USE_LIGHTRAG`
- `LMSTUDIO_WARN_PLAIN_MODE`
- `LMSTUDIO_LIGHTRAG_OFF_REASON`
- `LMSTUDIO_PRECHECK_RETRIEVAL`
- `LMSTUDIO_REQUIRE_CONTEXT`
- `LMSTUDIO_FALLBACK_WITH_WARNING`
- `LMSTUDIO_SHOW_RETRIEVAL`
- `LMSTUDIO_CONTEXT_TOKENS`
- `LMSTUDIO_MAX_RESPONSE_TOKENS`
- `LMSTUDIO_QUERY_TOP_K`
- `LMSTUDIO_QUERY_CHUNK_TOP_K`
- `LMSTUDIO_QUERY_MAX_TOTAL_TOKENS`

When retrieval is missing or weak, the code can emit `::knowledge-warning` for the GUI and fall back to a plain model answer.

## PowerShell Bridge

Current code:

- `scripts/query-vault-scope-lmstudio.ps1`

Responsibilities:

- compute storage name from scope/project/layer;
- check whether LightRAG storage exists;
- optionally start background indexing;
- check whether LM Studio is ready;
- call `scripts/query-vault-lmstudio.py`.

The bridge defaults to `http://127.0.0.1:1234/v1`.

## Vision Support

Current code:

- `scripts/knowledgelab/llm/lmstudio.py`
- `scripts/knowledgelab/vision/book_discovery.py`
- `scripts/knowledgelab/material/video.py`

Vision readiness is inferred from:

- explicit `vision_model` setting;
- loaded model IDs containing markers such as `vision`, `vl`, `llava`, `moondream`, `qwen-vl`, `qwen2.5-vl`.

If no vision model is configured or detected, image/book/video analysis should remain pending or produce a clear warning rather than failing silently.

## Known Risks

- LM Studio must be running and the expected models must be loaded.
- Some handoff documentation still references `--self-test` and old assumptions; `--self-test` now exists again, while live model checks should use `--behavior-test`.
- Full behavior tests require LM Studio and cannot be treated as pure unit tests.
- `lms.exe` startup helpers assume LM Studio CLI exists under `%USERPROFILE%\.lmstudio\bin\lms.exe`.

## Recommended Improvements

1. Keep one source of truth for the LM Studio default endpoint.
2. Add a small test for `lmstudio_common.BASE_URL` default when dependencies are available.
3. Surface loaded model IDs in the Settings diagnostics UI.
4. Make vision-model unavailable states explicit in chat reports.
5. Keep external LLM API support opt-in only.

