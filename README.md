# KnowledgeLab

KnowledgeLab is a local-first Windows knowledge system that combines LM Studio, optional LightRAG retrieval, and an Obsidian Markdown vault behind two desktop apps: `LightRAG-Chat` and `LightRAG-Control`.

## What It Does

- Runs a normal local LLM chat through LM Studio by default.
- Lets the user enable LightRAG retrieval when they want answers from the local knowledge base.
- Treats the chat as an entry point into a personal library/archive: web links, YouTube links, GitHub repositories, local folders, images, text notes, Telegram exports, PDFs, DOCX files, and other sources should become lightweight Markdown materials.
- Falls back to plain LLM answers when LightRAG is off or unavailable, with a small gray note in the chat.
- Stores knowledge as Markdown in an Obsidian vault.
- Saves links and notes from the chat into Obsidian when the user says things like `вот ссылка`, `сохрани`, or `добавь в базу`.
- Parses saved web pages into Markdown when possible.
- Sends saved YouTube links through transcript sync and starts LightRAG refresh in the background.
- Saves attached files as lightweight Markdown intake notes with source path, topic guess, metadata, immediate text/DOCX extraction when possible, and pending OCR/ASR/document-processing status for heavier sources.
- Provides web-search, file-attach, and voice-input controls in the lower-left of the input composer. The file and microphone controls use icon assets with a muted-blue active state. Web search fetches snippets and gives them to the LLM as temporary context.
- Keeps LightRAG local-only. LightRAG can use web data only after a page, video, or source is saved into the vault and indexed.
- Keeps chat sessions locally with a grouped left-side history panel, rename, and delete.
- Provides settings for Enter-to-send, LightRAG, button color, Obsidian path, vault path, and Game Guard.
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

The installer creates only two Desktop shortcuts:

```text
%USERPROFILE%\Desktop\LightRag\LightRAG-Chat.lnk
%USERPROFILE%\Desktop\LightRag\LightRAG-Control.lnk
```

Internal launcher logic stays inside the project folder:

```text
C:\MyFiles\KnowledgeLab\LightRAG-Desktop
```

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
- writes only `LightRAG-Chat.lnk` and `LightRAG-Control.lnk` to the Desktop;
- assigns `assets/icons/LightRAG-Chat.ico` and `assets/icons/LightRAG-Control.ico`;
- writes `INSTALL_REPORT.md`;
- prints manual steps for tools that still need to be installed by hand.

Dry run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\install-knowledge-lab.ps1 -DryRun -SkipPythonPackages
```

## Chat

`LightRAG-Chat` is a normal chat first. The user can ask anything: casual messages, code, translation, writing, debugging, brainstorming, or questions over the knowledge base.

Default behavior:

- LightRAG is off by default.
- Plain LM Studio answers go directly through `http://127.0.0.1:1234/v1/chat/completions`.
- Every GUI request includes a generated `KnowledgeLab runtime context` block with the active root, vault path, LM Studio endpoint/models, selected route, LightRAG index readiness, DnD backend, material queue summary, background book discovery tasks, and project server state. The LLM answers status questions from this live context instead of hardcoded phrase templates.
- A gray italic note says when the answer did not use LightRAG.
- If a message explicitly asks to search the local knowledge base, saved materials, or Obsidian, the chat treats it as a retrieval request.
- Status questions about LightRAG, imports, queues, book discovery, DnD, local servers, or connection state are answered by the app status layer, not by retrieval.
- If LightRAG is enabled in Settings but the index is missing, LightRAG turns off and the answer continues through plain LM Studio.
- The left column stores local chat sessions grouped by project/topic.
- The web-search icon in the lower-left of the input composer toggles web context mode. When it is on, normal messages fetch search snippets and pass them into the LLM prompt; the browser is not opened for the user.
- The paperclip button accepts files, local folders, or GitHub repository URLs; local folder paths pasted into chat are also saved into Markdown intake notes. A dedicated folder button opens the local-folder picker directly. The microphone button tries Windows Speech Recognition and inserts recognized text into the input field.
- Explorer drag-and-drop uses `tkinterdnd2` when available and highlights the chat/input area while hovering. To force-disable in-window DnD on a problematic Windows/Tk build, set `KNOWLEDGELAB_DISABLE_EXPLORER_DND=1`; folders can still be added through the folder button, paperclip, or a pasted local path.
- Settings includes an `Automation` section. By default the chat automatically routes incoming materials to topics, creates missing topic folders/`_Topic.md` notes, and checks uploaded images for visible books. When these toggles are on, the app reports its routing choice in chat instead of asking `куда сохранить?`.
- LightRAG itself does not search the web. It retrieves from local indexed storage. Web material becomes LightRAG knowledge only after the material pipeline saves and indexes it.
- The Obsidian icon opens the Obsidian app; if it is not found, the user can choose `Obsidian.exe` or open the Obsidian website.
- Maintenance actions such as reindexing are handled in `LightRAG-Control`, not as large buttons in the chat.
- Game Guard is not installed into Windows startup; the chat samples GPU load only while the chat window is open.

## Book Discovery

When a user sends a photo of a book cover, bookshelf, or book page, KnowledgeLab automatically:

1. Saves a reference-only intake note under `50 Library/<book-slug>/` with `source_image_path` and OCR metadata.
2. Starts a background LM Studio vision worker that reads visible spine/cover text.
3. Enriches readable books through Open Library and Google Books by ISBN, then title/author.
4. Creates canonical `type: book` notes for confidently matched books.
5. Lists unreadable, ambiguous, or unmatched books in the parent note under `Unresolved / Not Found`.
6. Shows a chat report grouped into `Added`, `Needs clarification`, and `Not found / unreadable`.

Manual book resolution: if the user writes missing titles or authors after a shelf report, the chat starts a `book_resolution` task, creates confirmed book notes, routes each book to its topic, and appends `Resolved by user` to the parent shelf note.

Plain image attachments are also quietly checked for visible books when `auto_detect_books_in_images` is enabled; unrelated images are left alone.

## Video Analysis

Video sources create `video_analysis` queue items for background processing:

- **YouTube**: caption sync continues as before; frames are queued for vision-based screen text/code extraction.
- **Local videos**: FFmpeg samples frames into `tmp/video-processing/<source-id>/`; the local vision model extracts visible code, slides, diagrams, commands, and screen text.
- ASR (audio transcription) remains `pending_asr` until a transcription worker is available.

The worker writes results into `type: video_analysis` notes. Missing FFmpeg, ASR, or vision support becomes a clear pending status instead of a crash.

## Settings / Automation

The Settings panel includes an `Automation` section with these toggles:

| Setting | Default | Effect |
| --- | --- | --- |
| `auto_route_topics` | `true` | Automatically routes incoming materials to topics instead of asking `куда сохранить?` |
| `auto_create_topics` | `true` | Creates `Topics/<topic>/_Topic.md` service notes for new topics |
| `auto_detect_books_in_images` | `true` | Checks uploaded images for visible books; unrelated images are left alone |
| `book_lookup_enabled` | `true` | Enriches detected books through Open Library and Google Books catalog lookup |

When auto-routing is enabled, the chat reports its routing decision in chat instead of opening a context dialog.

## Material Pipeline

KnowledgeLab should keep permanent storage lightweight:

- Web pages are saved as Markdown notes and parsed text when possible.
- Parsed web pages mine useful child links such as CodePen pens, GitHub repositories, demos, examples, snippets, and external references into canonical reference notes instead of duplicating the same URL repeatedly.
- Long or link-rich parsed pages are queued in `tmp/rlm-processing-queue.jsonl` for Recursive Language Model style processing, where the source text is treated as an external environment to inspect and decompose into snippets/subcalls.
- YouTube links are stored as link notes, then converted into transcript Markdown through `sync-youtube-links.py`; they also get a queued `video_analysis` note so visual frame analysis can capture code, slides, diagrams, commands, and important screen text.
- Images, GitHub repositories, text files, DOCX/PDF documents, audio, video, archives, and generic files are stored as Markdown intake notes first. Local folders are expanded into per-file reference notes with `source_root` and `source_relative_path`; text and DOCX are extracted immediately when possible.
- Book/page/shelf photos are stored as `book_photo`, `book_page_photo`, or `bookshelf_photo` under `50 Library/<book-slug>/` with pending OCR/vision metadata; the original image is referenced by path. The chat starts a background LM Studio vision worker for book/shelf images, then enriches readable books through public online catalogs: Open Library, an open book catalog from Internet Archive, and Google Books. Canonical `type: book` notes store the best match plus nearby catalog candidates, while unreadable or failed matches go into the parent note under `Unresolved / Not Found`. If the user later writes the missing titles/authors, the chat treats that as a manual book resolution, creates confirmed book notes even for weak catalog matches, updates the parent shelf note, and routes each book to its own topic.
- Local video files create reference-only video intake notes plus a queued `video_analysis` note. The worker samples frames into `tmp/video-processing/<source-id>/` with FFmpeg when available, asks the local vision model to extract visible code/screen text, and leaves ASR as `pending_asr` until an audio transcription worker is available.
- After intake, the chat shows compact reports: material routing by topic, and for bookshelf photos a book discovery report grouped into `Added`, `Needs clarification`, and `Not found / unreadable`.
- Heavier sources are queued in `tmp/material-processing-queue.jsonl` for OCR, ASR/transcription, document parsing, cleanup, and later LightRAG reindexing. Original large files are referenced by path and are not copied into the vault by default.
- Heavy source files should be temporary inputs. After processing, keep extracted text, transcript, metadata, and references, not the original large file.
- Finished projects are reference-only cards under `40 Finished Projects/<section>/<project-slug>/`; dragging a project folder into chat does not copy that folder into the vault. Folder files are saved as per-file references under the finished-project layer. Chat first infers project title/section from the folder, GitHub repo, and caption, and only asks when that is ambiguous.
- Finished project imports also create action records in `tmp/project-actions.json`. The action buttons copy or clone sources into isolated runtime workspaces under `tmp/project-runtime/<project-id>/` only when the user asks for a build or local server; the original folder and the vault are not used as build workspaces.

## Optimization Notes

The “Karpathy method” is treated here as context-engineering practice: clearer prompts, retrieval audits, evaluation questions, and better knowledge organization. It is not a separate model or magic module.

Google TurboQuant may become relevant later for vector-search or KV-cache compression, but it is not a fix for chat routing or UI diagnostics.

Google Quantum AI / AlphaQubit is not relevant to this local RAG chat architecture; it targets quantum error correction, not personal-library retrieval.

## LightRAG-Control

Use `LightRAG-Control` when something in the system needs checking or maintenance:

- LM Studio server/model checks.
- LightRAG smoke test.
- Manual scope reindexing.
- Obsidian vault opening.
- Telegram import.
- Model stop/unload.
- Game Guard tools.

## Knowledge Scopes

| Scope | Project | Storage | Purpose |
| --- | --- | --- | --- |
| `general` | empty | `LightRAG/rag_storage_general` | General notes, Unity resources, articles, music, Telegram and YouTube sources |
| `web` | `web-development` | `LightRAG/rag_storage_web` | Web-development notes, snippets, frontend/backend solutions and sources |
| `game` | `my-game` | `LightRAG/rag_storage_game_my-game` | Personal game-project knowledge |
| `all` + `layer: finished-projects` | `project_section/project` | `LightRAG/rag_storage_finished_projects` | Completed project references kept out of normal answers |

Manual maintenance indexing:

```powershell
scripts\ingest-vault-scope-lmstudio.ps1 -Scope general
scripts\ingest-vault-scope-lmstudio.ps1 -Scope web -Project web-development
scripts\ingest-vault-scope-lmstudio.ps1 -Scope game -Project my-game
scripts\ingest-vault-scope-lmstudio.ps1 -Layer finished-projects -Scope all
```

## Diagnostics

LightRAG retrieval audit:

```powershell
$env:LMSTUDIO_SHOW_RETRIEVAL='1'
scripts\query-vault-scope-lmstudio.ps1 -Scope game -Project my-game "What is known about my-game? Give references."
scripts\query-vault-scope-lmstudio.ps1 -Layer finished-projects -Scope all "Show similar finished projects."
```

Force plain LM Studio mode:

```powershell
$env:LMSTUDIO_USE_LIGHTRAG='0'
scripts\query-vault-scope-lmstudio.ps1 -Scope web -Project web-development "Make CSS for a popup window."
```

Start local models:

```powershell
scripts\start-knowledge-lab.ps1
```

Stop local models:

```powershell
scripts\stop-knowledge-lab.ps1
```

## Known Issues

- Large images are sent inline as data URLs with an 8 MB limit; a future improvement should add local resize/compression before the vision call.
- Page OCR is still V1 metadata only: page photos are categorized and sent to vision, but dedicated OCR text extraction for page content is a next step.
- If the active LM Studio model cannot process images, book discovery fails gracefully and writes the failure into the parent note.
- Catalog lookup needs internet; if both Open Library and Google Books are offline, visible book evidence is still saved and the parent note records `lookup_error`.

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for the current diagrams, data flow, fallback behavior, and local file layout.

Short version:

```text
User message
  -> Chat UI
  -> Intent Router
  -> direct plain LM Studio answer by default
  -> optional LightRAG retrieval when enabled and ready
  -> optional Obsidian capture when the user wants to save material
  -> readable diagnostics and LightRAG-Control suggestions on failures
```

## Local Models

Default LM Studio API:

```text
http://127.0.0.1:1234/v1
```

Default model identifiers:

```text
LLM: qwen/qwen3-14b
Embeddings: text-embedding-nomic-embed-text-v1.5
```

## Repository Notes

Generated runtime artifacts are intentionally ignored:

- `LightRAG/.venv`
- `LightRAG/rag_storage*`
- `tmp`
- `.env`
- downloaded model archives
- generated install reports
