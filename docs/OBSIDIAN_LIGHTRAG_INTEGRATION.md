# Obsidian And LightRAG Integration

Audit date: 2026-06-25.

## Obsidian Role

Obsidian is the durable knowledge store. KnowledgeLab writes Markdown notes into an Obsidian-compatible vault, then LightRAG indexes selected Markdown scopes.

Default vault:

```text
Obsidian-Test-Vault
```

The vault can be overridden through:

- Settings value `vault_path`;
- environment variable `KNOWLEDGELAB_VAULT_DIR`;
- indexing script setting propagation from `tmp/knowledge-chat-settings.json`.

## Vault Folders

Important current folders:

- `00 Inbox`: lightweight intake notes, images, files, capture queue.
- `10 General Knowledge`: general notes and topics.
- `10 Programming`: programming notes.
- `20 Projects/Web Development`: web project knowledge.
- `20 Projects/My Game`: game project knowledge.
- `30 Sources`: Telegram, YouTube, article, and other source material.
- `40 Finished Projects`: reference-only finished project cards.
- `50 Library`: book notes, bookshelf/photo intake, and manual book lists.
- `_Templates`: Obsidian templates, excluded from LightRAG collection.

## Capture Flow

Current code:

- `scripts/knowledgelab/vault/capture.py`
- `scripts/knowledgelab/vault/capture_workflow.py`
- `scripts/knowledgelab/routing/topics.py`

Capture creates Markdown notes with frontmatter such as:

- `type`
- `scope`
- `project`
- `layer`
- `topic`
- `source_url`
- `source_path`
- `source_root`
- `source_relative_path`
- processing statuses for OCR, ASR, video, books, or queues.

Heavy files are referenced by path rather than copied wholesale into the vault by default.

## Topic Routing

Current code:

- `scripts/knowledgelab/routing/intent.py`
- `scripts/knowledgelab/routing/topics.py`

Topic routing uses:

- built-in topic terms;
- existing `Topics/*` folders;
- frontmatter keys `topic` and `book_topic`;
- scope/project heuristics.

This audit fixed `ensure_topic_exists(..., vault_dir=...)` so topic notes are written into the passed vault, not always the global default.

## LightRAG Indexing

Current code:

- `scripts/ingest-vault-scope-lmstudio.ps1`
- `scripts/ingest-vault-lmstudio.py`
- `scripts/vault_sources.py`

Indexing flow:

1. PowerShell sets `LMSTUDIO_SCOPE`, `LMSTUDIO_PROJECT`, `LMSTUDIO_LAYER`, and `LMSTUDIO_RAG_DIR`.
2. Settings are read from `tmp/knowledge-chat-settings.json` when available.
3. YouTube links can be synced before indexing unless `LIGHTRAG_SYNC_YOUTUBE_LINKS=0`.
4. `vault_sources.py` collects Markdown documents and filters them by frontmatter/path.
5. `ingest-vault-lmstudio.py` inserts Markdown into LightRAG in batches.

Batch size:

```text
LMSTUDIO_INGEST_BATCH_SIZE=50
```

## LightRAG Querying

Current code:

- `scripts/query-vault-scope-lmstudio.ps1`
- `scripts/query-vault-lmstudio.py`
- `scripts/lightrag_query_audit.py`

Query flow:

1. Choose scope/project/layer.
2. Compute storage path.
3. If the index is missing and auto-index is enabled, start indexing in the background.
4. Use plain LM Studio for the current answer if the index is missing.
5. If LightRAG is ready, retrieve context and send it to LM Studio.
6. Emit `::knowledge-warning` for GUI-visible fallback notes.

## Storage Mapping

- `general` -> `LightRAG/rag_storage_general`
- `web`, project `web-development` -> `LightRAG/rag_storage_web`
- `game`, project `my-game` -> `LightRAG/rag_storage_game_my-game`
- custom web project -> `LightRAG/rag_storage_web_<project>`
- custom game project -> `LightRAG/rag_storage_game_<project>`
- finished projects layer -> `LightRAG/rag_storage_finished_projects`

## What LightRAG Is For

Use LightRAG when the answer needs saved, indexed knowledge from the vault:

- project notes;
- saved web materials;
- YouTube transcripts;
- Telegram imports;
- book/library notes;
- finished project references.

Do not use LightRAG as a replacement for:

- current node context;
- chat history;
- operational state;
- live web search;
- external APIs.

## Current Risks

- Several capture helpers still use global `VAULT_DIR`; the topic path bug was fixed, but the wider path model should be audited later.
- Indexing and querying require LM Studio and embedding model availability.
- Background indexing writes logs and PID files under `tmp/`.
- Auto-index can make the first answer plain LM Studio while indexing continues in the background.

## Recommended Improvements

1. Finish a pass over vault helpers to ensure custom vault paths are always respected.
2. Add explicit UI diagnostics for current vault path and current LightRAG storage path.
3. Add tests for storage-name parity between PowerShell and Python.
4. Add queue item status transitions instead of append-only queued states.
5. Keep source files reference-only unless the user explicitly asks to copy them.

