# KnowledgeLab Next Chat Handoff

Last updated: 2026-06-26

Use this file to continue the project in a new Codex chat without losing context.

## Update 2026-06-26

Active launcher note from the user: `C:\Users\Юрий\Desktop\LightRag` is where they start `LightRAG-Chat` / KnowledgeLab, and this launcher must point at the latest live install in `C:\MyFiles\KnowledgeLab`.

Recent UI/runtime changes:

- Follow-up 2026-06-26: the chat edge animation now paints the four corner cells as canvases too, so the moving runner does not disappear when it crosses a corner.
- Follow-up 2026-06-26: chat transcript text stays selectable/copyable by keeping the Tk `Text` widget normal while blocking edit keys/paste/cut. This fixes mouse selection in the chat without making the transcript user-editable.
- Follow-up 2026-06-26: bookshelf/photo book reports now separate newly created notes from books that were already present in `50 Library`, using `already_in_vault` / `vault_note` set at save time.
- Follow-up 2026-06-26: LM Studio settings filter model dropdowns by role. Vision only shows vision-like models, embeddings only shows embedding models, and chat LLM excludes both. A configured vision model is considered ready only when it is actually loaded in LM Studio Local Server.
- Current LM Studio smoke on this machine: neither `127.0.0.1:1234` nor `127.0.0.1:5000` was listening, so live connected models could not be read. Control smoke with sample model IDs returned LLM `qwen/qwen2.5-coder-32b`, `qwen/qwen3-14b`; Vision `qwen2.5-vl-7b-instruct`; Embeddings `text-embedding-nomic-embed-text-v1.5`.
- The chat dialog border in `scripts\knowledgelab\ui\animated_edges.py` is now a thin static frame at idle.
- Final UI setting: the dialog frame is `1px`; the animated runner is also capped to that thin width.
- Follow-up fix: for `1px` frames the runner is drawn on the `0.5px` canvas center instead of the edge coordinate, so it is not clipped/invisible; palette contrast was slightly increased while keeping muted colors.
- The animated border segment runs only while the app is busy/model is thinking, via `KnowledgeChatApp.set_busy(...)`.
- Follow-up visibility fix: the chat frame is now a thin `2px` Tk canvas border, because `1px` was too easy to miss and could still look static on light backgrounds. The runner is longer and higher-contrast but still muted.
- `finish_query()` no longer stops the frame animation before inserting the answer; `set_busy(False)` now lets the edge animation stay visible for at least a short minimum window. A direct preview path was added: sending a message containing `переливы` / `анимация рамки` shows the edge animation for a few seconds without routing that message to the LLM.
- Clipboard follow-up: `scripts\main.py` now installs explicit clipboard shortcuts for the input/chat widgets: `Ctrl+C/X/V/A`, `Ctrl+Insert`, `Shift+Insert`, Tk virtual `<<Copy>>/<<Cut>>/<<Paste>>`, and physical key handling for Russian layout (`ф/с/м/ч`). Right-click context menus were added for input and chat copy/paste/select-all flows.
- Undo follow-up: input `Text` has `undo=True`, `autoseparators=True`, `maxundo=-1`; `Ctrl+Z`, `Ctrl+Y`, `Ctrl+Shift+Z`, and Russian-layout physical keys (`я/н`) are handled explicitly. Input clear/send resets the undo stack so sent messages are not restored accidentally.
- The desktop shortcut `C:\Users\Юрий\Desktop\LightRag\LightRAG-Chat.lnk` was found pointing at staging. It was rewritten to run `C:\MyFiles\KnowledgeLab\LightRAG-Desktop\LightRAG-Desktop-Chat.ps1` with working directory `C:\MyFiles\KnowledgeLab`. The staging `desktop-launchers\Launch-KnowledgeLab.ps1` template now prefers the live root first and only falls back to staging if live is absent.
- Settings now auto-fills the Obsidian path from `find_obsidian_path(...)`; smoke detected Obsidian via Start Menu shortcut.
- LM Studio settings comboboxes no longer change selection on mouse wheel. Model lists are ranked per role: LLM, Vision, Embeddings. Smoke result: LLM `qwen/qwen2.5-coder-32b`, Vision `qwen2.5-vl-7b-instruct`, Embeddings `text-embedding-nomic-embed-text-v1.5`.
- The old animated `...` thinking bubble was disabled so the only thinking animation is the moving border segment around the dialog.
- The runner is a single muted tapered segment moving around the perimeter, inspired by the user's CodePen reference.
- LM Studio base URL normalization avoids doubled `/v1/v1/models` and converts `/api/v1` to OpenAI-compatible `/v1`.
- Port autodetect checks configured URL, remembered ports, common ports including `5000`, and listening local ports.
- Local smoke probe detected LM Studio on `http://127.0.0.1:5000/v1` and returned models:
  `qwen/qwen2.5-coder-32b`, `qwen/qwen3-14b`, `qwen2.5-vl-7b-instruct`, `text-embedding-nomic-embed-text-v1.5`.
- Settings model dropdowns now use the shared LM Studio model helper and show a short status line when models are found, empty, or unavailable.
- Russian routing phrases for save/delete/question detection were added to `scripts\knowledgelab\resources\messages.ru.json` so live configs that read these phrases from JSON import cleanly.
- Live install `C:\MyFiles\KnowledgeLab` was synced with the updated runtime files, plus dependent packages that were missing/stale in live: `llm\model_manager.py`, `routing\intent.py`, `nodes\`, `sync\`, and `vision\`.
- Active verification after sync:
  - `py_compile`: OK
  - `scripts\main.py --self-test`: OK
  - LM Studio autodetect: `http://127.0.0.1:5000/v1`, found models `qwen/qwen2.5-coder-32b`, `qwen/qwen3-14b`, `qwen2.5-vl-7b-instruct`, `text-embedding-nomic-embed-text-v1.5`
  - staging/live hashes match for key runtime files.

## Update 2026-06-25

Active launcher path was re-verified: `KnowledgeLab-Chat` starts the live install in `C:\MyFiles\KnowledgeLab`.

Recent runtime changes synced to live:

- Russian/user-facing prompt strings for the high-risk LM Studio/runtime path were moved into `scripts\knowledgelab\resources\messages.ru.json`.
- Code now reads those strings through `scripts\knowledgelab\i18n\messages.py` via `msg(...)` / `msg_list(...)`.
- Plain greetings such as `Привет` no longer include the hidden KnowledgeLab runtime context in the LLM prompt; runtime context is injected only for status/runtime/LightRAG/model/import-style questions.
- The chat frame animation is implemented in `scripts\knowledgelab\ui\animated_edges.py` as one moving tapered border segment, inspired by the CodePen-style moving line segment rather than a full glowing border.
- Message bubbles use the same tapered runner idea in `scripts\knowledgelab\ui\message_bubble.py`.
- Long LightRAG storage/run names are shortened with a stable SHA suffix so pid/log paths stay short.

Verification after sync:

```text
active --self-test: OK
active message catalog smoke: OK
active hashes match staging for synced runtime files
```

## Start Prompt For New Chat

Continue working on the local KnowledgeLab desktop system.

Main staging repo:

```text
C:\Users\Юрий\Documents\Freelance\KnowledgeLab-staging-20260605211949
```

Live install:

```text
C:\MyFiles\KnowledgeLab
```

Remote:

```text
https://github.com/VxHxS/KnowledgeLab
```

The product goal is a local-first personal archive/library:

- `LightRAG-Chat` must be a normal LM Studio chat first.
- LightRAG is optional local retrieval from the Obsidian Markdown vault.
- The chat should save links/files/materials into Obsidian, then process/transcribe/parse them into lightweight Markdown.
- Heavy files should not be kept permanently after extraction unless the user explicitly wants that.
- Web search is for the LLM context, not for opening a browser for the user.
- Game Guard should run only while the chat is open and only warn when GPU load suggests a conflict.
- Desktop should stay clean: only `LightRAG-Chat` and `LightRAG-Control` shortcuts.

## Current Git State

At the time of this handoff:

```text
branch: main
status: main...origin/main [ahead 1]
local commit not pushed: 09cee23 011 refine chat controls and image intake
working tree: scripts/main.py has unfinished edits for general file intake
```

Already pushed commits:

```text
007 stabilize chat architecture and diagnostics
008 add web search toggle and library pipeline
009 keep chat Russian by default
010 add LLM web context and icon buttons
```

Local-only commit:

```text
011 refine chat controls and image intake
```

Important: `011` was committed locally but was not pushed and was not synced into `C:\MyFiles\KnowledgeLab` because filesystem/network escalation was previously blocked by the environment.

## Current Unfinished Work

The latest user request was:

- sync Live and push;
- finish the interrupted work;
- move the web-search button to the bottom-left of the input area;
- add small shadows to chat windows/panels;
- if LM Studio responds or Obsidian is found, remove the corresponding diagnostic note;
- add voice input;
- allow sending images or any file to chat;
- large files should be routed to the right archive area, transcribed/processed into meaningful text, and the heavy original should not be kept permanently;
- add this Markdown handoff.

This file completes only the handoff part.

Update from 2026-06-13:

- general file intake was completed in `scripts/main.py`;
- `IMG` was replaced by a paperclip-style file control;
- web search moved to the lower-left composer tool row;
- a microphone control was added; it uses Windows Speech Recognition when available and inserts recognized text into the input field;
- attached files now create lightweight Markdown notes without copying heavy originals into the vault;
- text and DOCX extraction run immediately when possible;
- images, PDFs, audio, video, and generic files are queued in `tmp/material-processing-queue.jsonl` for later OCR/ASR/document processing;
- subtle shadow shells were added around the sidebar, chat panel, and composer;
- startup health hints are redrawn so resolved LM Studio/Obsidian diagnostics do not linger in the empty intro area;
- `README.md` and `ARCHITECTURE.md` were updated for the new pipeline.
- selected files were synced to live install `C:\MyFiles\KnowledgeLab`:
  `scripts\main.py`, `README.md`, `ARCHITECTURE.md`, `NEXT_CHAT_HANDOFF.md`;
- stale live file `assets\icons\rename-chat.png` was removed to match staging.

Second update from 2026-06-13:

- user-provided microphone and paperclip SVG files were added under `assets\icons`;
- generated Tkinter-friendly PNG variants:
  `microphone.png`, `microphone-active.png`, `attachment.png`, `attachment-active.png`;
- file and microphone composer buttons now use these icon assets;
- pressing/active state changes the icon itself to muted blue;
- microphone input is now cancelable by pressing the active microphone again;
- Windows native file drag-and-drop was added for the root window, chat area, and input field;
- dropped files use the same file-intake route as the paperclip button.

Verification run:

```text
py_compile: OK
--self-test: OK
live py_compile: OK
live --self-test: OK
icon asset self-test: OK
git diff --check: OK
installer dry-run: OK
--behavior-test: blocked because LM Studio API at 127.0.0.1:1234 refused connection
```

Current partial code edits in `scripts/main.py`:

- added `MATERIAL_QUEUE_PATH`;
- added file extension groups for text/doc/audio/video;
- added `SUPPORTED_FILETYPES`;
- added helper functions:
  - `classify_source_file`
  - `extraction_label`
  - `read_text_source`
  - `read_docx_source`
  - `extract_lightweight_file_text`
  - `render_file_capture_markdown`
- extended `capture_destination` for generic file intake paths.

Completed from this list:

- replaced `attach_images()` UI flow with a general `attach_files()` flow;
- added `save_file_capture()` and queue writing to `tmp/material-processing-queue.jsonl`;
- replaced the `IMG` input button with a small drawn attachment control;
- kept image intake working through the new general file flow;
- added static self-tests for text/docx/image/general file intake helpers;
- updated README/ARCHITECTURE.

Still needs completion after this chat:

- run behavior test after LM Studio server is started;
- visually smoke-test the Tkinter UI from the live launcher;
- commit the second update, suggested message: `013 add icon buttons and file drop`;
- push `main` to GitHub.

## Key Files

```text
scripts\main.py
scripts\install-knowledge-lab.ps1
scripts\install_wizard_gui.py
README.md
ARCHITECTURE.md
SYSTEM_HANDOFF.md
assets\icons\
desktop-launchers\
```

## Behavior Requirements

### Chat

- Plain LM Studio answers must work with LightRAG off.
- LightRAG must never block simple chat messages.
- If LightRAG is on but the index is missing, disable LightRAG for that request and answer through LM Studio.
- Do not show raw PowerShell tracebacks in the dialog.
- Ask/answer in Russian by default.
- Status questions like `lightrag подключен?` must be answered by the app status layer, not routed into retrieval.
- Web search toggle adds web snippets to the LLM prompt; it does not open the browser.

### History Sidebar

- Chats appear in the left sidebar grouped by topic/project.
- Double click renames a chat.
- Enter or clicking elsewhere saves rename.
- Delete button removes a chat.
- Sidebar scroll must react to mouse wheel.

### Obsidian

- The Obsidian icon is the button.
- It should be on the right edge of the toolbar.
- Prefer configured `Obsidian.exe` or `.lnk`.
- If Obsidian is missing, offer to choose exe/shortcut, open official site, or cancel.
- Do not auto-open an `obsidian://open?path=...` URL that causes the “Vault not found” popup.

### File And Material Pipeline

The desired architecture:

1. User sends a link, image, PDF, DOCX, text, audio, video, or other source to chat.
2. Chat guesses project/topic from filename, user hint, and conversation.
3. If unclear, it asks where to save.
4. It creates a lightweight Markdown intake note in Obsidian.
5. Lightweight text sources can be extracted immediately.
6. Images go to OCR/vision extraction.
7. Audio/video go to ASR/transcription.
8. PDFs/DOCX go to document text extraction.
9. Extracted/transcribed content is cleaned into meaningful Markdown.
10. LightRAG is reindexed after processing.
11. Heavy original files are not copied into the vault by default.

Planned queue file:

```text
tmp\material-processing-queue.jsonl
```

Each queued item should include:

```json
{
  "queued_at": "...",
  "source_path": "...",
  "vault_note": "...",
  "kind": "image_capture|text_file|document_file|audio_file|video_file|generic_file",
  "scope": "general|web|game",
  "project": "",
  "status": "queued",
  "planned_processing": "OCR/vision extraction"
}
```

## Voice Input Plan

Recommended staged implementation:

1. Add a microphone button near the input field.
2. First version: use Windows speech recognition if available, or show a clear message that local speech input requires a recognizer.
3. Robust version: add a local Whisper/faster-whisper importer in the Python venv.
4. Voice input should insert recognized text into the input box, not auto-send unless Enter-to-send is enabled and the user confirms.

## UI Work Remaining

- Move web search button to the bottom-left inside the composer.
- Add subtle Apple-like shadows around sidebar, chat panel, and composer shell.
- Keep borders gray and quiet.
- If health checks pass, remove old non-persistent diagnostic notes from the current empty intro area.
- Avoid noisy service logs in chat.

## Suggested Next Commands

Inspect state:

```powershell
git status --short --branch
git diff -- scripts\main.py README.md ARCHITECTURE.md NEXT_CHAT_HANDOFF.md
```

Run syntax after finishing code edits:

```powershell
& "C:\MyFiles\KnowledgeLab\LightRAG\.venv\Scripts\python.exe" -m py_compile scripts\main.py
```

Run app self-test:

```powershell
& "C:\MyFiles\KnowledgeLab\LightRAG\.venv\Scripts\python.exe" scripts\main.py --self-test
```

Run behavior test:

```powershell
& "C:\MyFiles\KnowledgeLab\LightRAG\.venv\Scripts\python.exe" scripts\main.py --behavior-test
```

Installer dry-run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\install-knowledge-lab.ps1 -DryRun -SkipPythonPackages
```

After tests pass, sync selected files to Live only with approval because `C:\MyFiles\KnowledgeLab` is outside the writable sandbox.

After Live sync and smoke tests pass, commit as:

```text
012 add file intake handoff and chat polish
```

Then push `main` to GitHub.
