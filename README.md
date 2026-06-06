# KnowledgeLab

KnowledgeLab is a local-first Windows knowledge system that combines LM Studio, optional LightRAG retrieval, and an Obsidian Markdown vault behind two desktop apps: `LightRAG-Chat` and `LightRAG-Control`.

## What It Does

- Runs a normal local LLM chat through LM Studio by default.
- Lets the user enable LightRAG retrieval when they want answers from the local knowledge base.
- Treats the chat as an entry point into a personal library/archive: web links, YouTube links, text notes, Telegram exports, PDFs, DOCX files, and other sources should become lightweight Markdown materials.
- Falls back to plain LLM answers when LightRAG is off or unavailable, with a small gray note in the chat.
- Stores knowledge as Markdown in an Obsidian vault.
- Saves links and notes from the chat into Obsidian when the user says things like `вот ссылка`, `сохрани`, or `добавь в базу`.
- Parses saved web pages into Markdown when possible.
- Sends saved YouTube links through transcript sync and starts LightRAG refresh in the background.
- Provides a web-search toggle near the input. When enabled, the chat fetches web-search snippets and gives them to the LLM as temporary context.
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
- A gray italic note says when the answer did not use LightRAG.
- If a message explicitly asks to search the local knowledge base, saved materials, or Obsidian, the chat treats it as a retrieval request.
- Simple status questions such as `lightrag подключен?` are answered by the app status layer, not by retrieval.
- If LightRAG is enabled in Settings but the index is missing, LightRAG turns off and the answer continues through plain LM Studio.
- The left column stores local chat sessions grouped by project/topic.
- The web-search icon near the input toggles web context mode. When it is on, normal messages fetch search snippets and pass them into the LLM prompt; the browser is not opened for the user.
- LightRAG itself does not search the web. It retrieves from local indexed storage. Web material becomes LightRAG knowledge only after the material pipeline saves and indexes it.
- The Obsidian icon opens the Obsidian app; if it is not found, the user can choose `Obsidian.exe` or open the Obsidian website.
- Maintenance actions such as reindexing are handled in `LightRAG-Control`, not as large buttons in the chat.
- Game Guard is not installed into Windows startup; the chat samples GPU load only while the chat window is open.

## Material Pipeline

KnowledgeLab should keep permanent storage lightweight:

- Web pages are saved as Markdown notes and parsed text when possible.
- YouTube links are stored as link notes, then converted into transcript Markdown through `sync-youtube-links.py`.
- Heavy source files should be temporary inputs. After processing, keep extracted text, transcript, metadata, and references, not the original large file.
- PDF, DOCX, social networks, arbitrary video links, audio transcription, and transcript cleanup are planned as importer modules around the same Markdown-first pipeline.

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

Manual maintenance indexing:

```powershell
scripts\ingest-vault-scope-lmstudio.ps1 -Scope general
scripts\ingest-vault-scope-lmstudio.ps1 -Scope web -Project web-development
scripts\ingest-vault-scope-lmstudio.ps1 -Scope game -Project my-game
```

## Diagnostics

LightRAG retrieval audit:

```powershell
$env:LMSTUDIO_SHOW_RETRIEVAL='1'
scripts\query-vault-scope-lmstudio.ps1 -Scope game -Project my-game "What is known about my-game? Give references."
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
