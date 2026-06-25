# KnowledgeLab Architecture

Audit date: 2026-06-25.

## What KnowledgeLab Is

KnowledgeLab is a local-first Windows desktop knowledge system. Its main job is to accept a user request, keep useful materials in an Obsidian Markdown vault, optionally retrieve indexed context through LightRAG, and ask a local LM Studio model to form the final answer.

KnowledgeLab is not the future visual application builder. The builder can use KnowledgeLab later as a knowledge/backend layer, but KnowledgeLab itself should remain a local knowledge, analysis, and response system.

## Current Roots

- Git working copy: `C:\Users\Юрий\Documents\Freelance\KnowledgeLab-staging-20260605211949`
- Active installed app launched by desktop shortcuts: `C:\MyFiles\KnowledgeLab`
- Desktop shortcuts folder: `C:\Users\Юрий\Desktop\LightRag`
- GitHub remote recorded in the staging clone: `https://github.com/VxHxS/KnowledgeLab.git`

The two desktop shortcuts are PowerShell launchers:

- `KnowledgeLab-Chat.lnk` -> `C:\MyFiles\KnowledgeLab\LightRAG-Desktop\LightRAG-Desktop-Chat.ps1`
- `KnowledgeLab-Control.lnk` -> `C:\MyFiles\KnowledgeLab\LightRAG-Desktop\LightRAG-Control\LightRAG-Control.ps1`

`C:\Windows\System32\WindowsPowerShell\v1.0` is only the PowerShell executable location, not the project folder.

## Stack

- Desktop UI: Python `tkinter`, optional `tkinterdnd2` for Explorer drag-and-drop.
- Launch layer: PowerShell `.ps1` and `.cmd` files.
- Local LLM: LM Studio OpenAI-compatible API at `http://127.0.0.1:1234/v1`.
- Main model default: `qwen/qwen3-14b`.
- Embedding model default: `text-embedding-nomic-embed-text-v1.5`.
- Retrieval: `lightrag-hku`.
- Knowledge storage: Obsidian-compatible Markdown vault.
- Runtime queues and chat state: JSON/JSONL files under `tmp/`.

## Main Entry Points

- `scripts/main.py` is the main desktop chat entry point.
- `LightRAG-Desktop/LightRAG-Desktop-Chat.ps1` resolves the KnowledgeLab root, chooses `LightRAG\.venv\Scripts\pythonw.exe` or `python.exe`, and starts `scripts/main.py`.
- `LightRAG-Desktop/LightRAG-Control/LightRAG-Control.ps1` is the control/maintenance UI.
- `scripts/query-vault-scope-lmstudio.ps1` is the scoped CLI/query bridge.
- `scripts/ingest-vault-scope-lmstudio.ps1` indexes a selected vault scope into a selected LightRAG storage.

## Desktop UI

`scripts/main.py` still owns the `KnowledgeChatApp` coordinator and the final GUI layout. After the Mimo refactor, much domain logic was moved into `scripts/knowledgelab/`, but the main app class still coordinates:

- chat list and chat persistence;
- input composer and tool buttons;
- settings dialog;
- file/folder/GitHub attachment flows;
- drag-and-drop;
- background tasks;
- LightRAG/plain-LM Studio query routing;
- Obsidian open/settings actions;
- Game Guard warning flow;
- project action panels.

Several extracted UI helpers exist under `scripts/knowledgelab/ui/`. Some local UI classes still remain in `main.py`; this is a known post-refactor duplication risk, not an immediate launch blocker.

## Package Layout

The refactor introduced a Python package under `scripts/knowledgelab/`:

- `config.py`: paths, environment defaults, model defaults, UI theme, settings defaults, term lists.
- `models.py`: dataclasses such as `KnowledgeRoute`, `MaterialRoutingReport`, `BookDiscoveryReport`, `VideoAnalysisReport`.
- `routing/`: intent, scope, topic, and project-stack routing.
- `vault/`: frontmatter parsing and capture Markdown rendering/workflows.
- `material/`: web, CodePen, GitHub, YouTube, queue, video, and worker helpers.
- `vision/`: book discovery, catalog enrichment, image/vision parsing.
- `llm/`: LM Studio adapter, runtime context prompt, web search, voice, diagnostics, Game Guard.
- `ui/`: widgets, settings, dialogs, Obsidian launcher helpers, chat list/store.
- `tasks/`: process, background, and project-action helpers.
- `tests/`: currently only a self-test placeholder; full tests live in top-level `tests/`.

## Request Flow

Normal chat flow:

1. User enters text or attaches material in the desktop chat.
2. `KnowledgeChatApp` chooses a `KnowledgeRoute` with context, scope, project, and layer.
3. The app builds a runtime context prompt with active root, vault path, LM Studio settings, LightRAG index state, DnD backend, queues, and background tasks.
4. If LightRAG is disabled or not ready, the app calls plain LM Studio through `scripts/knowledgelab/llm/lmstudio.py`.
5. If retrieval is requested and an index is ready, the app calls the PowerShell query bridge and `scripts/query-vault-lmstudio.py`.
6. The final answer is saved into the local chat session store under `tmp/knowledge-chat-sessions.json`.

Material intake flow:

1. The chat detects save intent, pasted URL, dropped file/folder, image, video, or GitHub URL.
2. `CaptureWorkflow` writes a lightweight Markdown note into the vault.
3. Heavy work is queued in `tmp/material-processing-queue.jsonl`.
4. Background workers may parse web pages, sync YouTube transcripts, analyze videos, detect books, or launch LightRAG reindexing.
5. LightRAG can later retrieve from the indexed Markdown, not directly from the live web.

## Current LightRAG Scopes

- `general` -> `LightRAG/rag_storage_general`
- `web` + `web-development` -> `LightRAG/rag_storage_web`
- `game` + `my-game` -> `LightRAG/rag_storage_game_my-game`
- `finished-projects` layer -> `LightRAG/rag_storage_finished_projects`

## Important Current State

- The staging repo is a real git clone; the active installed app is not a git clone.
- The GitHub remote could not be refreshed during this audit because `git fetch origin --prune` hung and had to be stopped.
- The active app and staging app may need explicit sync before desktop shortcuts run the newest audited code.
- Full `pytest` could not be run because the discovered Python environments do not have `pytest` installed.
- `scripts/main.py --self-test` now runs before GUI initialization and passes without LM Studio.

