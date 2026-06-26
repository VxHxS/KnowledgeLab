# KnowledgeLab

KnowledgeLab is a local-first Windows knowledge system that combines LM Studio, optional LightRAG retrieval, and an Obsidian Markdown vault behind two desktop apps: `LightRAG-Chat` and `LightRAG-Control`.

## What It Does

- Runs a normal local LLM chat through LM Studio by default.
- Lets the user enable LightRAG retrieval when they want answers from the local knowledge base.
- Treats the chat as an entry point into a personal library/archive: web links, YouTube links, GitHub repositories, local folders, images, text notes, Telegram exports, PDFs, DOCX files, and other sources become lightweight Markdown materials.
- Falls back to plain LLM answers when LightRAG is off or unavailable, with a small gray note in the chat.
- Stores knowledge as Markdown in an Obsidian vault.
- Saves links and notes from the chat into Obsidian when the user says things like `вот ссылка`, `сохрани`, or `добавь в базу`.
- Parses saved web pages into Markdown when possible.
- Sends saved YouTube links through transcript sync and starts LightRAG refresh in the background.
- Saves attached files as lightweight Markdown intake notes with source path, topic guess, metadata, immediate text/DOCX extraction when possible, and pending OCR/ASR/document-processing status for heavier sources.
- Provides web-search, file-attach, and voice-input controls in the lower-left of the input composer. Web search fetches DuckDuckGo results and passes them to the LLM as context.
- Keeps LightRAG local-only. LightRAG can use web data only after a page, video, or source is saved into the vault and indexed.
- Keeps chat sessions locally with a grouped left-side history panel, rename, and delete.
- Provides settings for Enter-to-send, LightRAG, button color, Obsidian path, vault path, message detail level, and Game Guard.
- Warns about sustained GPU load after the chat opens, so local AI processes do not silently compete with games or other heavy apps.
- Provides LightRAG-Control for checks, maintenance indexing, imports, model stop, and troubleshooting.

## User Quick Start

To make the chat answer through LM Studio:

1. Open LM Studio.
2. Go to `Developer` -> `Local Server`.
3. Turn the server on and check that it is reachable at `http://127.0.0.1:1234`.
4. Download and load `qwen/qwen3-14b`.
5. For LightRAG/indexing, also load the Nomic embedding model. The API id used by this project is `text-embedding-nomic-embed-text-v1.5`.
6. If the chat still shows a diagnostic, open `LightRAG-Control` and run the checks.

## Desktop Apps

The installer creates one Desktop shortcut:

```text
%USERPROFILE%\Desktop\LightRag\LightRAG-Chat.lnk
```

The shortcut launches the latest version of KnowledgeLab via `LightRAG-Desktop-Chat.ps1`.

## Installer

Run:

```bat
Install AI Knowledge Lab.cmd
```

The installer:

- checks Python, the local virtual environment, LightRAG, LM Studio, Obsidian, Telegram Desktop, Git, and FFmpeg;
- creates or reuses `LightRAG/.venv`;
- installs selected Python package groups when requested;
- initializes chat settings with plain LM Studio mode, LightRAG off, LM Studio model IDs, and the local vault path;
- updates `LightRAG/.env` to the LM Studio profile when an older Ollama-style file is detected;
- removes legacy Game Guard startup shortcuts from Windows Startup;
- writes only `LightRAG-Chat.lnk` to the Desktop;
- writes `INSTALL_REPORT.md`;
- prints manual steps for tools that still need to be installed by hand.

**Note**: The installer uses local files from the directory it runs in. To get the latest version, run `git pull` in the project directory before installing.

Dry run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\install-knowledge-lab.ps1 -DryRun -SkipPythonPackages
```

## Chat

`LightRAG-Chat` is a normal chat first. The user can ask anything: casual messages, code, translation, writing, debugging, brainstorming, or questions over the knowledge base.

Default behavior:

- LightRAG is off by default.
- Plain LM Studio answers go directly through `http://127.0.0.1:1234/v1/chat/completions`.
- Every GUI request includes a generated `KnowledgeLab runtime context` block with the active root, vault path, LM Studio endpoint/models, selected route, LightRAG index readiness, DnD backend, material queue summary, background book discovery tasks, and project server state.
- **Topic adaptation**: the system prompt adapts to the user's current scope (web development, game dev, general). When the user works in the web scope, the LLM knows about React/CSS/HTML context.
- A gray italic note says when the answer did not use LightRAG.
- If a message explicitly asks to search the local knowledge base, saved materials, or Obsidian, the chat treats it as a retrieval request.
- If LightRAG is enabled in Settings but the index is missing, LightRAG turns off and the answer continues through plain LM Studio.
- The left column stores local chat sessions grouped by project/topic.
- The web-search icon toggles web context mode. When on, messages fetch DuckDuckGo search snippets and pass them into the LLM prompt. The system prompt instructs the LLM to USE search results rather than making up answers.
- The paperclip button accepts files, local folders, or GitHub repository URLs. A dedicated folder button opens the local-folder picker directly. The microphone button tries Windows Speech Recognition.
- Explorer drag-and-drop uses `tkinterdnd2` when available. To force-disable, set `KNOWLEDGELAB_DISABLE_EXPLORER_DND=1`.
- **Keyboard shortcuts**: `Ctrl+C` (copy), `Ctrl+V` (paste), `Ctrl+A` (select all) work in chat and input.
- **Duplicate detection**: when dragging files or folders, the system checks if they were already imported. If duplicates are found, a dialog offers to skip them, save as copies, or cancel.
- Settings includes an `Automation` section and a `Message detail level` option (`compact` or `full`).
- The Obsidian icon opens the Obsidian app; if not found, the user can choose `Obsidian.exe`.
- Maintenance actions are handled in `LightRAG-Control`.
- Game Guard is not installed into Windows startup; the chat samples GPU load only while open.

## Goal Nodes

KnowledgeLab includes a node system for high-level goal-oriented operations:

| Goal | Trigger phrases | What it does |
| --- | --- | --- |
| **Make Website** | "сделай сайт", "создай лендинг" | Creates a website project, detects stack, starts dev server |
| **Refactor Project** | "рефакторинг", "refactor", "перепиши код" | Analyzes codebase and suggests/apply refactoring |
| **Launch on Server** | "подними на сервере", "запусти локально" | Starts a local dev server for an imported project |
| **Analyze Project** | "проанализируй проект", "analyze project" | Scans project structure and generates summary |
| **Code Review** | "проанализируй код", "code review", "качество кода", "плохие запахи" | Reviews code for naming, smells, modularity, SOLID/DRY using LLM + Obsidian context |

## Code Review

The Code Review node analyzes code quality through the LLM:

1. Accepts code text or a project path (reads source files automatically).
2. Builds a review prompt checking: meaningful variable names, interface sizes, code smells (duplication, long methods, deep nesting, magic numbers), module splitting, SOLID/DRY principles.
3. Uses existing Obsidian vault context (programming notes) to inform recommendations.
4. Returns structured feedback: problems (critical/important/minor), recommendations with code examples, and an overall score (1-10).

## Book Discovery

When a user sends a photo of a book cover, bookshelf, or book page:

1. Saves a reference-only intake note under `50 Library/<book-slug>/`.
2. Starts a background LM Studio vision worker that reads visible spine/cover text.
3. Enriches readable books through Open Library and Google Books.
4. Shows a simple list of detected books (author — title) so the user can send book files separately.

Example output:
```
Найдено книг: 3

- Robert C. Martin — Clean Code
- Martin Fowler — Refactoring
- Erich Gamma — Design Patterns

Отправьте файлы книг (.epub, .pdf) отдельно — я добавлю их в библиотеку.
```

## Video Analysis

Video sources create `video_analysis` queue items for background processing:

- **YouTube**: caption sync + frames queued for vision-based screen text/code extraction.
- **Local videos**: FFmpeg samples frames; the local vision model extracts visible code, slides, diagrams, commands, and screen text.
- ASR remains `pending_asr` until a transcription worker is available.

## Transcript Cleanup

YouTube transcripts and video captions are post-processed in two stages:

1. **Regex cleanup** (always on): removes duplicate lines, normalizes punctuation, removes filler words (ну, ээ, как бы, короче, etc.), capitalizes sentence starts.
2. **LLM cleanup** (opt-in via Settings): sends transcript chunks to LM Studio for grammar and punctuation correction.

Enable in Settings → Automation → "LLM-постобработка транскриптов".

## Vault Sync (Free)

KnowledgeLab supports free vault synchronization between devices:

### Git-based sync (built-in)

- Auto-commits vault changes every N minutes (configurable in Settings).
- Optional push/pull to a Git remote (GitHub, GitLab, etc.).
- Commands: `vault_git_status()`, `vault_git_commit()`, `vault_git_push()`, `vault_git_pull()`.

### Syncthing integration (optional)

- Check if Syncthing is running locally.
- View sync status (folders, last sync, conflicts).
- Setup instructions included in Settings.

## Port Auto-Detection

KnowledgeLab automatically detects the LM Studio server port:

1. Environment variable `LMSTUDIO_BASE_URL`
2. Common ports (5000, 1234, 11434, 8080, 8000, 3000, 9090)
3. All listening ports on `127.0.0.1` via netstat scan
4. Port history file (`~/.knowledgelab/port_history.json`)
5. Default port (1234)

If auto-detection fails, the user can enter the port manually in Settings.

## Model Manager

KnowledgeLab manages three model types via LM Studio API:

| Type | Purpose | When loaded |
|------|---------|-------------|
| **LLM** | Chat, code, transcript cleanup | Every message |
| **Vision** | Book photos, OCR, image analysis | When photos are sent |
| **Embeddings** | Vector search across vault | LightRAG queries |

Models are loaded/unloaded automatically based on task. Disable in Settings → "Автопереключение моделей".

### Animation

When the model is thinking, a subtle animation appears on the answer bubble: 4 colorful shimmer lines travel around the border. The animation stops when the response arrives. User messages and completed answers have no animation.

## Web Search

KnowledgeLab has a built-in web search feature powered by DuckDuckGo:

- Toggle with the search icon in the input composer.
- When enabled, every message fetches DuckDuckGo results and passes them as context to the LLM.
- Uses DuckDuckGo JSON API (primary) with HTML fallback.
- The system prompt instructs the LLM to USE search results rather than making up answers.

## Drag-and-Drop

Requires `tkinterdnd2` package. Install with:
```bash
pip install tkinterdnd2
```
Once installed, drag files/folders/images from Windows Explorer directly into the chat window.

## Settings

| Setting | Default | Effect |
| --- | --- | --- |
| `auto_route_topics` | `true` | Automatically routes incoming materials to topics |
| `auto_create_topics` | `true` | Creates `Topics/<topic>/_Topic.md` for new topics |
| `auto_detect_books_in_images` | `true` | Checks uploaded images for visible books |
| `book_lookup_enabled` | `true` | Enriches detected books through online catalogs |
| `message_detail_level` | `compact` | `compact` (short summaries) or `full` (detailed reports) |
| `vault_git_auto_sync` | `false` | Auto-commit vault changes to Git every N minutes |
| `vault_git_sync_interval` | `300` | Seconds between auto-sync attempts |
| `auto_switch_models` | `true` | Auto-load/unload models via LM Studio API |
| `llm_model` | configurable | LLM model name for chat and code |
| `vision_model` | configurable | Vision model for book photos and OCR |
| `embedding_model` | configurable | Embedding model for LightRAG search |

## Material Pipeline

- Web pages are saved as Markdown notes and parsed text when possible.
- YouTube links are stored as link notes, then converted into transcript Markdown with post-processing.
- Images, files, folders are stored as Markdown intake notes. Local folders are expanded into per-file references.
- Book photos trigger vision-based detection and catalog enrichment.
- After intake, the chat shows compact reports: material routing by topic.
- Heavier sources are queued for OCR, ASR/transcription, document parsing, and LightRAG reindexing.
- Finished projects are reference-only cards; dragging a folder does not copy it into the vault.

## Local Server Launch

When a project folder or GitHub repository is imported, the chat shows "Получить результат" and "Запуск на локальном сервере" buttons.

1. **Package projects** (with `package.json`): runs `npm run dev` / `pnpm dev` / `yarn dev`.
2. **Static projects** (with `index.html`): finds the directory with `index.html` and starts a Python HTTP server with SPA fallback.
3. **Projects without `index.html`**: shows a clear error message.

## LightRAG-Control

Use `LightRAG-Control` for: LM Studio checks, LightRAG smoke test, manual reindexing, Obsidian opening, Telegram import, model stop/unload, Game Guard tools.

## Knowledge Scopes

| Scope | Project | Storage | Purpose |
| --- | --- | --- | --- |
| `general` | empty | `LightRAG/rag_storage_general` | General notes, articles, music, Telegram, YouTube |
| `web` | `web-development` | `LightRAG/rag_storage_web` | Web-development notes, snippets, solutions |
| `game` | `my-game` | `LightRAG/rag_storage_game_my-game` | Personal game-project knowledge |
| `all` + `finished-projects` | `project_section/project` | `LightRAG/rag_storage_finished_projects` | Completed project references |

## Diagnostics

```powershell
scripts\start-knowledge-lab.ps1          # Start local models
scripts\stop-knowledge-lab.ps1           # Stop local models
scripts\ingest-vault-scope-lmstudio.ps1 -Scope general  # Reindex
```

## Known Issues

- Large images have an 8 MB inline limit; local resize is a future improvement.
- Page OCR is V1: page photos are categorized and sent to vision, but dedicated OCR is a next step.
- If the active LM Studio model cannot process images, book discovery fails gracefully.
- Catalog lookup needs internet; if offline, book evidence is still saved.

## Architecture

```text
User message
  -> Chat UI
  -> Intent Router (chat, save, knowledge, goal)
  -> Goal Nodes (make website, refactor, launch server, analyze, code review)
  -> Topic-adapted system prompt (web/game/general context)
  -> plain LM Studio answer by default
  -> optional LightRAG retrieval
  -> optional web search context (DuckDuckGo)
  -> Obsidian capture
  -> duplicate detection
  -> SPA-aware local server
  -> compact/full message formatting
  -> diagnostics
```

## Local Models

KnowledgeLab uses three model types, managed through LM Studio:

| Type | Purpose | When used |
|------|---------|-----------|
| **LLM** | Chat, code review, transcript cleanup, text analysis | Every message |
| **Vision** | Reading book spines, OCR, image analysis | When photos are sent |
| **Embeddings** | Vector search across Obsidian vault | LightRAG queries |

### Recommended setup (16GB VRAM + 32GB RAM)

```
├── qwen2.5-coder-14b          ~8.5GB   GPU   Chat, code (no restrictions)
├── qwen2.5-vl-7b-instruct     ~6.0GB   GPU   Book photos, OCR
└── text-embedding-nomic-v1.5   ~0.5GB   GPU   Search
                                         ──────
                                         15.0 / 16GB VRAM
```

### Model recommendations by VRAM

| VRAM | LLM | Vision | Notes |
|------|-----|--------|-------|
| 8GB | qwen2.5-coder-7b | qwen2.5-vl-3b | Basic, limited quality |
| 12GB | qwen2.5-coder-14b | qwen2.5-vl-7b | Good balance |
| 16GB | qwen2.5-coder-14b | qwen2.5-vl-7b | **Recommended** |
| 24GB | qwen2.5-coder-32b | qwen2.5-vl-7b | Maximum quality |

### Uncensored models (no content filters)

Default Qwen models have safety filters. For unrestricted use:

| Model | Size | VRAM | Source |
|-------|------|------|--------|
| `TheDrummer/Qwen2.5-Coder-14B-Uncensored` | 14B | 8.5GB | LM Studio search |
| `TheDrummer/Qwen2.5-Coder-32B-Uncensored` | 32B | 20GB | LM Studio search |

Download in LM Studio: Models → Search → `Qwen2.5-Coder-Uncensored`

### Auto-switching

KnowledgeLab routes model orchestration through the shared LightRAG-Control module. When a book photo is sent, Chat asks the control layer to load the configured vision model; for normal chat, it asks for the configured LLM. Disable Settings -> "Auto-switch models" if you prefer manual control in LM Studio.

### Default models

```text
API: http://127.0.0.1:1234/v1
LLM: qwen/qwen3-14b (configurable in Settings)
Vision: (none by default — configure in Settings)
Embeddings: text-embedding-nomic-embed-text-v1.5
```

## Repository Notes

Generated runtime artifacts are ignored: `LightRAG/.venv`, `LightRAG/rag_storage*`, `tmp`, `.env`.

## Node System

Lives in `scripts/knowledgelab/nodes/`:

| File | Purpose |
| --- | --- |
| `base.py` | `KnowledgeNode` protocol and `BaseNode` base class |
| `registry.py` | `NodeRegistry` singleton — register, lookup, run nodes |
| `builtin_nodes.py` | Wrappers: `IntentParserNode`, `FileCaptureNode`, `ProjectActionNode`, `LaunchOnServerNode` |
| `goal_nodes.py` | Goals: `MakeWebsiteNode`, `RefactorProjectNode`, `DeployProjectNode`, `AnalyzeProjectNode`, `CodeReviewNode` |

```python
from knowledgelab.nodes import NodeRegistry
NodeRegistry().list_nodes()
result = NodeRegistry().run_node("code_review", {"code": "def foo(): ...", "language": "python"})
```

## Module Structure

```text
scripts/
  main.py                          # Entry + KnowledgeChatApp
  knowledgelab/
    config.py, models.py
    utils/    (text, urls, colors, paths)
    routing/  (intent, topics, project_stack)
    vault/    (frontmatter, capture, capture_workflow)
    material/ (web, codepen, github, queue, youtube, video, workers, transcript_clean)
    vision/   (book_discovery, book_pipeline, book_downloads, book_sources, html_parsers)
    control/  (lightrag_control shared runtime/model orchestration)
    llm/      (lmstudio, runtime_context, diagnostics, web_search, voice, game_guard)
    ui/       (widgets, theme, tooltip, chat_store, settings, settings_dialog,
               game_guard_dialog, project_panel, chat_list, dialogs,
               message_bubble, animated_edges, obsidian)
    tasks/    (background, process, project_actions, static_server)
    nodes/    (base, registry, builtin_nodes, goal_nodes)
    sync/     (vault_git, syncthing)
    i18n/     (messages)
    resources/
    tests/    (self_test)
```
