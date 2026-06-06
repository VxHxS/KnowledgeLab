# KnowledgeLab

KnowledgeLab is a local-first Windows knowledge system that combines LM Studio, optional LightRAG retrieval, and an Obsidian Markdown vault behind two desktop apps: `LightRAG-Chat` and `LightRAG-Control`.

## What It Does

- Runs a normal local LLM chat through LM Studio by default.
- Lets the user enable LightRAG retrieval when they want answers from the local knowledge base.
- Falls back to plain LLM answers when LightRAG is off or unavailable, with a small gray note in the chat.
- Stores knowledge as Markdown in an Obsidian vault.
- Saves links and notes from the chat into Obsidian when the user says things like `вот ссылка`, `сохрани`, or `добавь в базу`.
- Keeps chat sessions locally with a left-side history panel, rename, and delete.
- Provides settings for Enter-to-send, LightRAG, button color, Obsidian path, vault path, and Game Guard.
- Warns about sustained GPU load after the chat opens, so local AI processes do not silently compete with games or other heavy apps.
- Provides LightRAG-Control for checks, maintenance indexing, imports, model stop, and troubleshooting.

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
- If LightRAG is enabled in Settings but the index is missing, LightRAG turns off and the answer continues through plain LM Studio.
- The left column stores local chat sessions.
- The Obsidian icon opens the Obsidian app; if it is not found, the user can choose `Obsidian.exe` or open the Obsidian website.
- Maintenance actions such as reindexing are handled in `LightRAG-Control`, not as large buttons in the chat.
- Game Guard is not installed into Windows startup; the chat samples GPU load only while the chat window is open.

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
Embeddings: nomic-embed
```

## Repository Notes

Generated runtime artifacts are intentionally ignored:

- `LightRAG/.venv`
- `LightRAG/rag_storage*`
- `tmp`
- `.env`
- downloaded model archives
- generated install reports
