# KnowledgeLab Next Chat Handoff

## Current Roots

- Staging repo: `C:\Users\Юрий\Documents\Freelance\KnowledgeLab-staging-20260605211949`
- Active installed app used by Desktop shortcut: `C:\MyFiles\KnowledgeLab`
- User launches KnowledgeLab from launcher icons in `C:\Users\Юрий\Desktop\LightRag`.
- Current launcher targets:
  - `KnowledgeLab-Chat.lnk` -> `powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\MyFiles\KnowledgeLab\LightRAG-Desktop\LightRAG-Desktop-Chat.ps1`
  - `KnowledgeLab-Control.lnk` -> `powershell.exe -STA -NoProfile -ExecutionPolicy Bypass -File C:\MyFiles\KnowledgeLab\LightRAG-Desktop\LightRAG-Control\LightRAG-Control.ps1`
  - Both shortcuts use working directory `C:\MyFiles\KnowledgeLab`.
- Important launcher rule: after every sync/install/update, verify these Desktop icons still point to the latest active install. If the active root changes, recreate/update the `.lnk` files in `C:\Users\Юрий\Desktop\LightRag` so the user never launches an old copy by accident.

## Architecture Refactoring (2026-06-23) — IN PROGRESS

The monolithic `scripts/main.py` (9,380 lines) has been refactored into a proper Python package under `scripts/knowledgelab/`. The main file is now **3,225 lines** (reduced by ~6,155 lines). **389 tests passing.** **43 modules** in knowledgelab package.

### Package layout (43 modules):

```
scripts/
├── main.py                          # Entry point (3,225 lines)
├── knowledgelab/
│   ├── config.py                    # All constants, paths, settings, env vars
│   ├── models.py                    # All dataclasses
│   ├── utils/
│   │   ├── text.py                  # slugify, clean_filename, yaml_quote, etc.
│   │   ├── urls.py                  # URL patterns, parsing, normalization
│   │   ├── colors.py                # Hex color manipulation
│   │   └── paths.py                 # Path normalization, DnD detection
│   ├── routing/
│   │   ├── intent.py                # Intent classification, scope routing
│   │   ├── topics.py                # Topic registry, auto-route, auto-create
│   │   └── project_stack.py         # npm/pnpm/yarn detection
│   ├── vault/
│   │   ├── frontmatter.py           # Frontmatter parsing, scope/layer inference
│   │   ├── capture.py               # File capture, markdown rendering, project_title_from_source_hint
│   │   └── capture_workflow.py      # File capture and attachment workflow
│   ├── material/
│   │   ├── web.py                   # Article extraction, SPA bundle, HTML parsers
│   │   ├── codepen.py               # CodePen snapshot extraction
│   │   ├── github.py                # GitHub metadata
│   │   ├── queue.py                 # JSONL queue management + queue_file/github/rlm_item
│   │   ├── youtube.py               # YouTube sync command building
│   │   ├── video.py                 # Video analysis, frame parsing, report formatting
│   │   └── workers.py               # Background material processing workers
│   ├── vision/
│   │   ├── book_discovery.py        # Book detection, catalog enrichment
│   │   └── html_parsers.py          # Re-export from material.web
│   ├── llm/
│   │   ├── lmstudio.py              # LM Studio API client, model checks
│   │   ├── runtime_context.py       # Runtime context prompt generation
│   │   ├── diagnostics.py           # System diagnostics
│   │   ├── web_search.py            # DuckDuckGo search
│   │   ├── voice.py                 # Voice input script building, error handling
│   │   └── game_guard.py            # GPU snapshot collection, heavy-load detection
│   ├── ui/
│   │   ├── widgets.py               # InteractiveButton ABC + 4 subclasses
│   │   ├── theme.py                 # UI_THEME, BUTTON_COLOR_PRESETS
│   │   ├── tooltip.py               # ToolTip class
│   │   ├── chat_store.py            # Chat session persistence and CRUD
│   │   ├── settings.py              # Settings persistence, normalization, color presets
│   │   ├── settings_dialog.py       # Settings dialog UI
│   │   ├── game_guard_dialog.py     # GPU conflict warning dialog
│   │   ├── project_panel.py         # Project action panel UI and workers
│   │   └── chat_list.py             # Chat list sidebar management (not yet integrated)
│   ├── tasks/
│   │   ├── background.py            # BackgroundTaskManager
│   │   └── project_actions.py       # Project actions CRUD, runtime workspace, command execution
│   └── tests/
│       └── self_test.py             # Self-test (stub)
├── lmstudio_common.py               # Shared LM Studio config (uses knowledgelab.config)
├── vault_sources.py                 # Vault document collector (uses knowledgelab.utils.text)
└── [other scripts...]               # All use shared ROOT from knowledgelab.config
```

### Key abstractions introduced:
- **InteractiveButton ABC** — common base for all 4 canvas button widgets
- **Dict-based dispatch** in `capture_destination()` — replaced 140-line if-chain
- **Standalone functions** for LM Studio, voice, game guard, project actions, chat store, queue management

### Methods delegated from KnowledgeChatApp to modules:
| Method | Delegates to |
|--------|-------------|
| `lmstudio_request_json` | `llm/lmstudio.lmstudio_request_json()` |
| `loaded_lmstudio_models` | `llm/lmstudio.loaded_lmstudio_models()` |
| `check_lmstudio_ready` | `llm/lmstudio.check_lmstudio_ready()` |
| `extract_chat_content` | `llm/lmstudio.extract_chat_content()` |
| `vision_model_state` | `llm/lmstudio.vision_model_state()` |
| `runtime_context_prompt` | `llm/runtime_context.build_runtime_context_prompt()` |
| `voice_input_worker` | `llm/voice.build_voice_recognition_script()` |
| `friendly_voice_error` | `llm/voice.friendly_voice_error()` |
| `auto_process_youtube_worker` | `material/youtube.build_youtube_sync_command()` |
| `collect_gpu_snapshot` | `llm/game_guard.collect_gpu_snapshot()` |
| `is_gpu_snapshot_heavy` | `llm/game_guard.is_gpu_snapshot_heavy()` |
| `load/save_chat_store` | `ui/chat_store.load/save_chat_store()` |
| `get_chats, get_active_chat` | `ui/chat_store.get_chats, get_active_chat()` |
| `load/save_project_actions` | `tasks/project_actions.load/save_project_actions()` |
| `create/update/get_project_action` | `tasks/project_actions.create/update/get_project_action()` |
| `run_project_command` | `tasks/project_actions.run_project_command()` |
| `is_process_running` | `tasks/project_actions.is_process_running()` |
| `queue_file/github/rlm_processing` | `material/queue.queue_file/github/rlm_item()` |
| `load/save_settings` | `ui/settings.load/save_settings()` |
| `color_preset_name` | `ui/settings.color_preset_name()` |
| `choose_capture_context` | `ui/dialogs.choose_capture_context()` |
| `choose_attachment_source` | `ui/dialogs.choose_attachment_source()` |
| `ensure_project_install_consent` | `ui/dialogs.confirm_install_dependencies()` |
| `lookup_book_catalog` | `vision/book_discovery.lookup_book_catalog()` |
| `enrich_detected_books` | `vision/book_discovery.enrich_detected_books()` |
| `extract_video_frames` | `material/video.extract_video_frames()` |
| `call_video_frame_vision` | `material/video.call_video_frame_vision()` |
| `write_video_analysis_note` | `material/video.write_video_analysis_note()` |
| `queue_video_analysis_processing` | `material/video.queue_video_analysis_item()` |
| `title_for_chat` | `ui/chat_store.title_for_chat()` |
| `format_chat_age` | `ui/chat_store.format_chat_age()` |
| `open_windows_microphone_settings` | `llm/voice.open_windows_microphone_settings()` |
| `lightrag_help_message` | `llm/runtime_context.lightrag_help_message()` |
| `is_safe_history_message` | `llm/runtime_context.is_safe_history_message()` |
| `build_prompt_with_history` | `llm/runtime_context.build_prompt_with_history()` |
| `run_background_material_command` | `material/queue.run_background_material_command()` |
| `launch_reindex` | `material/queue.launch_reindex()` |
| `call_plain_lmstudio` | `llm/lmstudio.call_plain_lmstudio()` |
| `chat_group_name` | `ui/chat_store.chat_group_by_context()` |
| `split_knowledge_warnings` | `utils/text.is_service_output_line()` + `trim_output()` |
| `is_service_output_line` | `utils/text.is_service_output_line()` |
| `trim_output` | `utils/text.trim_output()` |
| `storage_name_for_scope` | `llm/runtime_context.storage_name_for_scope()` |
| `lightrag_index_path` | `llm/runtime_context.lightrag_index_path()` |
| `is_lightrag_ready` | `llm/runtime_context.is_lightrag_ready()` |
| `python_executable` | `llm/runtime_context.python_executable()` |
| `capture_path_from_rel` | `llm/runtime_context.capture_path_from_rel()` |
| `compact_background_tasks` | `tasks/background.compact_background_tasks_from_dict()` |
| `material_queue_summary` | `tasks/background.material_queue_summary()` |
| `project_server_summary` | `tasks/background.project_server_summary()` |
| `latest_book_discovery_summary` | `tasks/background.latest_book_discovery_summary()` |
| `find_obsidian_path` | `ui/obsidian.find_obsidian_path()` |
| `find_obsidian_shortcuts` | `ui/obsidian.find_obsidian_shortcuts()` |
| `find_obsidian_registry_candidates` | `ui/obsidian.find_obsidian_registry_candidates()` |
| `clean_windows_program_path` | `ui/obsidian.clean_windows_program_path()` |
| `launch_windows_program` | `ui/obsidian.launch_windows_program()` |
| `run_command` | `tasks/process.run_command()` |
| `terminate_active_process` | `tasks/process.terminate_process()` |

### Tests:
- **390 tests** across 17 test files
- Run: `python -m pytest tests/ -v`
- GUI tests use mocked tkinter (no display required)

### What remains in main.py (3,225 lines, 232 methods in KnowledgeChatApp):
- **Local widget duplicates (~500 lines)** — ToolTip, RoundedButton, IconButton, MiniToolButton, WebSearchToggleButton are defined locally (lines 246-743) AND in `knowledgelab/ui/widgets.py` + `knowledgelab/ui/tooltip.py`. These local copies should be removed first — they duplicate the extracted modules.
- **GUI event handlers** (~50%) — tkinter widget callbacks, tightly coupled to self
- **Settings dialog** — thin wrappers delegating to SettingsDialog class
- **File capture** — thin wrappers delegating to CaptureWorkflow class
- **Book discovery workers** — thin wrappers delegating to MaterialWorkerManager class
- **Video analysis workers** — thin wrappers delegating to MaterialWorkerManager class
- **Article/CodePen workers** — thin wrappers delegating to MaterialWorkerManager class
- **DnD handling** — install_native_file_drop, on_dnd_*, set_drop_highlight
- **Chat UI** — build_ui, render_current_chat
- **Query/LLM** — run_query, finish_query, build_prompt_with_history
- **Game Guard UI** — thin wrappers delegating to GameGuardDialog class
- **Project action UI** — thin wrappers delegating to ProjectActionPanel class
- **Chat list management** — thin wrappers delegating to ChatListManager class

### How to run:
```powershell
cd C:\Users\Юрий\Documents\Freelance\KnowledgeLab-staging-20260605211949
python -m pytest tests/ -v
python -m py_compile scripts/main.py
python scripts/main.py --behavior-test  # requires LM Studio running
```

## Current Status

- Staging contains the Finished Projects layer, `tkinterdnd2` drag-and-drop, visible drop-zone diagnostics, reference-only folder import, `tmp/project-actions.json`, `tmp/project-runtime`, and project action buttons.
- Active installed copy may still need sync from staging. Before sync it had old native `ctypes`/`DragAcceptFiles` DnD and no `tkinterdnd2` in `LightRAG\.venv`.
- RLM should mean Recursive Language Model, based on the attached MIT PDFs:
  - `C:\Users\Юрий\Downloads\MIT_RLM_PAPER.pdf`
  - `C:\Users\Юрий\Downloads\rlm_real_example_walkthrough.pdf`
  - `C:\Users\Юрий\Downloads\rlm_simple_principle.pdf`
  - `C:\Users\Юрий\Downloads\rlm_mit_benchmark.pdf`

## Latest Result - 2026-06-23

UI/UX polish, automatic topic routing, and chat-visible book discovery reports are implemented in staging.

Latest incremental change after that: Settings tooltips now explain automation controls after a 1-second hover, the book enrichment checkbox is renamed to `Обогащать книги через онлайн-каталоги`, and book lookup now checks both Open Library and Google Books. This latest incremental package is implemented and tested in staging; active-copy sync to `C:\MyFiles\KnowledgeLab` was blocked by the Codex approval/usage limit and should be retried before launching the desktop app.

Latest runtime-context change after that: the GUI now injects a generated `KnowledgeLab runtime context` block into every LM Studio prompt. It contains the active root, vault path, LM Studio endpoint/models, selected route, LightRAG index readiness, DnD backend, material queue summary, background book discovery tasks, latest book report, and project server state. Status answers are no longer handled through hardcoded phrase templates; the model should answer flexibly from these app-state nodes. The same local LM Studio system prompt is shared by CLI query/chat scripts so models should not claim they are running through Alibaba/OpenAI/other cloud APIs unless the user explicitly configured that.

Latest book/video change after that: manual book resolution and video analysis scaffolding are implemented in staging. If the user writes missing book titles/authors after a bookshelf report, the chat starts `book_resolution`, creates confirmed `type: book` notes under `50 Library`, routes each book to its topic, and appends `Resolved by user` to the parent shelf note. Bookshelf vision now asks for region/visible text/visual guess/status so cautious inferred books can become `Needs clarification` instead of disappearing. YouTube and local videos now create `video_analysis` queue/items; local videos sample frames with FFmpeg into `tmp/video-processing/<source-id>/` and use the local vision model for screen text/code when available, while ASR stays pending until a transcription worker exists.

What changed in the newest pass:

### Code Quality & Bug Fixes (2026-06-23)

- **Fixed empty answer bug** in `query-vault-lmstudio.py` and `chat-vault-lmstudio.py`: Now properly handles models that return only `reasoning_content` (Qwen3 thinking mode). Returns warning message instead of crashing.
- **Standardized Game Guard menus**: Both `LightRAG-Desktop/Game-Guard.ps1` and `LightRAG-Control/Game-Guard.ps1` now offer Watch and Check once only (startup is disabled by design).
- **Updated README**: Fixed shortcut names, added Environment Variables section, Automation Settings section, and Known Issues section.
- **Fixed hardcoded paths**: Updated 5 LightRAG-Desktop scripts to use `Resolve-LightRAG-Paths.ps1` instead of hardcoded `C:\MyFiles\KnowledgeLab`.
- **Updated path resolver**: `Resolve-LightRAG-Paths.ps1` now searches for `KnowledgeLab` directories in addition to `AI-Knowledge-Lab`.
- **Created shared module**: `lmstudio_common.py` with shared LM Studio configuration and utilities.
- **Updated Python files**: `ingest-vault-lmstudio.py`, `query-vault-lmstudio.py`, `chat-vault-lmstudio.py` now use the shared module.
- **Added batch ingestion**: `ingest-vault-lmstudio.py` now processes documents in batches (configurable via `LMSTUDIO_INGEST_BATCH_SIZE`, default 50).
- **Fixed silent exceptions**: Added warning messages for `stop_project_server` and `launch_reindex` in `main.py`.
- **Fixed PowerShell silent catch**: `ingest-vault-scope-lmstudio.ps1` now warns on settings parse failure.
- **Fixed duplicate .html**: Removed duplicate `.html` from `TEXT_EXTENSIONS` set in `main.py`.
- **Self-test passes**: `python scripts/main.py --self-test` completes successfully.

- `scripts/main.py` now has shared UI theme tokens, softer panel/chat/composer colors, animated busy status dots, hover interpolation for custom canvas buttons, and a pulsing drag-and-drop highlight.
- Settings has an `Automation` section with:
  - `Автоматически распределять материалы по темам` / `auto_route_topics: true`
  - `Автоматически создавать новые темы` / `auto_create_topics: true`
  - `Автоматически искать книги по фото` / `auto_detect_books_in_images: true`
  - Online catalog enrichment toggle / `book_lookup_enabled: true`
- When auto-routing is enabled, the old `куда сохранить?` context dialog is skipped; the app chooses scope/topic/project first and reports the decision in chat.
- Added topic registry helpers: existing topics come from `TOPICS`, `topic`/`book_topic` frontmatter, and `Topics/*` folders in the vault. New topics are created as `_Topic.md` service notes when `auto_create_topics` is enabled.
- Intake now emits chat summaries through `MaterialRoutingReport`: which topic each material went to and which note was created.
- Book/image discovery now emits `BookDiscoveryReport` directly in chat as `Отчёт по книгам`: `Добавлено`, `Нужно уточнить`, and `Не найдено / не прочитано`, with topic, confidence, note path, and reason.
- Book notes now store `topic` and `book_topic`; bookshelf parent notes still get `## Bookshelf Detection Result`.
- `main.py --self-test` now covers auto-topic routing, topic creation disabled/enabled behavior, book-topic classification, routing report formatting, and book discovery report formatting.

Automatic book discovery from uploaded images is also implemented in staging.

What changed:

- `scripts/main.py` now has a background LM Studio vision worker for `book_photo`, `book_page_photo`, `bookshelf_photo`, and generic image attachments.
- `DEFAULT_SETTINGS` now includes `vision_model` and `auto_detect_books_in_images: true`.
- `KNOWLEDGELAB_VISION_MODEL` can force a specific local vision model. If it is not set, the app prefers a loaded LM Studio model whose id looks vision-capable (`vision`, `vl`, `llava`, `moondream`, `minicpm`, `pixtral`, `qwen*-vl`). It does not fall back to a text-only chat model, because text-only models cannot read images reliably.
- Uploaded images remain reference-only. The vault note stores `source_image_path`; the original photo is not copied into the vault.
- The worker asks the vision model for strict JSON with `detected_books` and `unresolved`.
- Book discovery runs as a tracked background task (`book_discovery/running|done|failed`), so the user can keep chatting while the app reads the image and searches catalogs. Follow-up questions like "куда положил книги?", "ещё ищет?", or "что с LightRAG?" should be answered by the LLM from the injected runtime context rather than by brittle keyword branches.
- Readable books are then looked up as catalog records. The current V1 catalog lookup checks multiple public sources: Open Library Search API and Google Books volumes search, by ISBN first, then title/author, then visible spine evidence.
- Readable and confidently matched books become canonical `type: book` notes under `50 Library/<book-slug>/Book.md`.
- Book notes store both visible evidence from the photo and catalog metadata: `visible_title`, `visible_author`, `lookup_status`, `lookup_score`, `catalog_sources`, `catalog_candidate_count`, `catalog_url`, `openlibrary_key`, `google_books_id`, `cover_url`, `first_publish_year`, and `edition_count`.
- The parent image/shelf note is updated with `## Bookshelf Detection Result`.
- If books cannot be read, catalog lookup is weak, or the vision/API/catalog step fails, the parent note gets `Detection status: failed` or `lookup needs_clarification/not_found` plus an `Unresolved / Not Found` list instead of staying silently pending.

Expected user flow:

1. User sends a photo of a bookshelf, book cover, or book page.
2. KnowledgeLab saves an intake note with metadata and source path.
3. A background vision pass reads visible spine/cover text automatically.
4. A catalog lookup tries to convert the visible text into real book records.
5. Found books are added to `50 Library`.
6. Unreadable/unknown/ambiguous books are listed in the parent note so the user can clarify title or author.

Intended bookshelf behavior:

- The user should not need to photograph every page.
- A single shelf photo should be enough to identify as many books as possible from spines/covers.
- If a spine shows only partial text, the system should search with that partial evidence and only create a confident book note when the match is strong enough.
- If the author/title is insufficient, the system should ask for clarification or leave a clear unresolved item such as `book lookup needs_clarification`.
- Page photos remain useful for later OCR, but they are not required for adding books to the library catalog.

Important current limitation:

- If the active LM Studio model cannot process images, discovery will fail gracefully and write the failure into the parent note. For best results, load a local vision model and/or set `KNOWLEDGELAB_VISION_MODEL`.
- Catalog lookup currently uses Open Library and Google Books, so enrichment needs internet. If both are offline or blocked, the visible book evidence is still saved and the parent note records `lookup_error`; if one source fails, the other still runs.
- Large images are currently sent inline as data URLs with an 8 MB limit. A future improvement should add local resize/compression before the vision call.
- Page OCR is still V1 metadata only: page photos are categorized and sent to vision, but a dedicated OCR text extraction worker for page content is still a next step.

Latest staging checks run:

```powershell
..\.venv\Scripts\python.exe -m py_compile scripts\main.py scripts\vault_sources.py scripts\ingest-vault-lmstudio.py scripts\sync-youtube-links.py
..\.venv\Scripts\python.exe scripts\main.py --self-test
```

Result: both passed. The self-test includes parsing a fake vision JSON response, creating a `type: book` note for `Clean Code`, and updating the parent bookshelf note with `Unresolved / Not Found`.

## Implemented In Staging

- Added `RLM_QUEUE_PATH` at `tmp/rlm-processing-queue.jsonl`.
- Added RLM profile scaffolding: long/link-rich parsed pages are queued with metadata for a future REPL-style Recursive Language Model worker.
- Added recursive link capture separate from RLM:
  - Extracts CodePen, GitHub, demo/example/snippet/reference links from parsed HTML.
  - Creates canonical `reference_link` notes instead of duplicating source data.
  - Stores `parent_note`, `parent_source_url`, `source_url`, `normalized_source_url`, `source_domain`, `link_context`, `link_role`, `capture_status`, and `content_hash`.
- Added CodePen support:
  - Recognizes `https://codepen.io/<owner>/pen/<id>` as `codepen_pen`.
  - Canonicalizes CodePen URLs for dedupe.
  - Attempts oEmbed/code snapshot extraction.
  - If CodePen blocks parsing, keeps the note useful as `blocked`/`metadata`.
- Added book-photo intake:
  - Image captions/names that look like books/pages/shelves become `book_photo`, `book_page_photo`, or `bookshelf_photo`.
  - Notes go under `50 Library/<book-slug>/`.
  - Notes store `source_image_path`, `book_title`, `page_number_guess`, `ocr_status`, and empty `ocr_text`.
  - Bookshelf notes additionally store `bookshelf_detection_status: pending` and `detected_books: []`.
  - Book/shelf images start a background LM Studio vision worker. Readable spine/cover text is enriched through catalog lookup; confident matches become canonical `type: book` notes.
  - Unreadable spines/covers, weak catalog matches, lookup failures, and missing title/author cases are appended to the parent note under `Unresolved / Not Found`.
  - Generic image attachments are quietly checked for visible books when `auto_detect_books_in_images` is enabled; unrelated images are left alone.
  - Queue item keeps OCR metadata without copying original images into the vault.
- Updated docs:
  - `README.md`
  - `SOURCE_IMPORTS.md`
  - `ARCHITECTURE.md`

## Active Install Sync Checklist

Run after staging tests are green:

```powershell
$sourceRoot = 'C:\Users\Юрий\Documents\Freelance\KnowledgeLab-staging-20260605211949'
$destRoot = 'C:\MyFiles\KnowledgeLab'
$files = @(
  'ARCHITECTURE.md',
  'CHANGELOG.md',
  'README.md',
  'SOURCE_IMPORTS.md',
  'NEXT_CHAT_HANDOFF_KNOWLEDGELAB.md',
  'requirements-core.txt',
  'scripts\ingest-vault-lmstudio.py',
  'scripts\ingest-vault-scope-lmstudio.ps1',
  'scripts\install-knowledge-lab.ps1',
  'scripts\main.py',
  'scripts\lmstudio_common.py',
  'scripts\query-vault-lmstudio.py',
  'scripts\query-vault-scope-lmstudio.ps1',
  'scripts\sync-youtube-links.py',
  'scripts\vault_sources.py',
  'LightRAG-Desktop\Reindex-LightRAG-Scope.ps1',
  'LightRAG-Desktop\Import-Telegram-Export.ps1',
  'LightRAG-Desktop\Ask-Web-Development.ps1',
  'LightRAG-Desktop\Ask-My-Game.ps1',
  'LightRAG-Desktop\Ask-General-Knowledge.ps1',
  'LightRAG-Desktop\Game-Guard.ps1',
  'LightRAG-Desktop\LightRAG-Control\Game-Guard.ps1',
  'LightRAG-Desktop\LightRAG-Control\Resolve-LightRAG-Paths.ps1'
)
foreach ($file in $files) {
  $src = Join-Path $sourceRoot $file
  $dst = Join-Path $destRoot $file
  New-Item -ItemType Directory -Path (Split-Path -Parent $dst) -Force | Out-Null
  Copy-Item -LiteralPath $src -Destination $dst -Force
}
```

Then install/verify drag-and-drop dependency:

```powershell
C:\MyFiles\KnowledgeLab\LightRAG\.venv\Scripts\python.exe -m pip install tkinterdnd2==0.5.0
C:\MyFiles\KnowledgeLab\LightRAG\.venv\Scripts\python.exe -c "import tkinterdnd2; print('tkinterdnd2 ok')"
rg "ctypes|DragAcceptFiles|SetWindowLongPtrW|WM_DROPFILES" C:\MyFiles\KnowledgeLab\scripts\main.py
```

Expected: import succeeds and `rg` prints nothing.

Verify the launch icons after every sync:

```powershell
$shell = New-Object -ComObject WScript.Shell
Get-ChildItem -LiteralPath C:\Users\Юрий\Desktop\LightRag -Filter *.lnk | ForEach-Object {
  $shortcut = $shell.CreateShortcut($_.FullName)
  [PSCustomObject]@{
    Name = $_.Name
    TargetPath = $shortcut.TargetPath
    Arguments = $shortcut.Arguments
    WorkingDirectory = $shortcut.WorkingDirectory
  }
} | Format-List
```

Expected:

- Chat shortcut target is `powershell.exe`.
- Chat shortcut arguments include `C:\MyFiles\KnowledgeLab\LightRAG-Desktop\LightRAG-Desktop-Chat.ps1`.
- Control shortcut arguments include `C:\MyFiles\KnowledgeLab\LightRAG-Desktop\LightRAG-Control\LightRAG-Control.ps1`.
- Both working directories are `C:\MyFiles\KnowledgeLab`.

## Test Checklist

```powershell
cd C:\Users\Юрий\Documents\Freelance\KnowledgeLab-staging-20260605211949
..\.venv\Scripts\python.exe -m py_compile scripts\main.py scripts\vault_sources.py scripts\ingest-vault-lmstudio.py scripts\sync-youtube-links.py
..\.venv\Scripts\python.exe scripts\main.py --self-test
git diff --check
```

Manual smoke after syncing active install:

- Drag folder over chat: drop-zone highlights before release.
- Drop folder: app does not crash; folder becomes per-file reference notes.
- Save `https://codepen.io/oliviale/pen/gKParr`: note is `codepen_pen`, parser either adds snapshot or records blocked/metadata status.
- Save an article/Telegram preview with CodePen/GitHub links: child reference notes are created and parent gets `Linked References`.
- Drop a photo named like `Clean Code page 12.jpg` or caption it as a book page: note goes to `50 Library/...` with `ocr_status: pending`.
- Drop a photo with caption `книжная полка` or `bookshelf`: note is `bookshelf_photo`, queue has `bookshelf_detection_status: pending`, no original image is copied into the vault, and the vision worker updates the note to `processed` or `failed`.
- Drop a bookshelf photo with no caption while a vision-capable LM Studio model is loaded: generic image intake is saved, then book notes are created if visible books are detected.

## Phone Sync Recommendation

Use Syncthing for Windows + Android as the default free Obsidian Sync alternative.

Sync only the Obsidian vault/Markdown data. Exclude runtime/cache folders:

- `LightRAG/.venv`
- `LightRAG/rag_storage*`
- `tmp/project-runtime`
- `tmp/project-action-logs`
- downloaded model/cache artifacts

On Android, open the synced folder in free Obsidian Mobile as a local vault. For iPhone, use iCloud/OneDrive folder sync or a Git-based mobile workflow instead.
