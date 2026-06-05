# KnowledgeLab

KnowledgeLab is a local-first personal knowledge system for Windows. It connects an Obsidian Markdown vault, LightRAG retrieval, and LM Studio local models behind a small desktop chat and control UI.

## What The Project Does

- Stores knowledge as Markdown in an Obsidian vault.
- Imports and organizes sources such as YouTube links, Telegram exports, articles, project notes, and web-development snippets.
- Builds LightRAG indexes from selected vault scopes.
- Queries the vault through LightRAG before sending context to the local LLM.
- Uses LM Studio as an OpenAI-compatible local API.
- Provides a desktop chat launcher for everyday use.
- Provides a desktop control launcher for checks, reindexing, opening the vault, and stopping local models.
- Shows a small gray warning in chat when no LightRAG context was found and the answer had to fall back to plain LLM mode.
- Lets the user turn LightRAG retrieval on or off from the chat UI. LightRAG is on by default.
- Keeps a local chat history in `tmp/knowledge-chat-history.jsonl`.

## Main Entry Points

The stable installer creates two Desktop launchers:

```text
%USERPROFILE%\Desktop\LightRag\LightRAG-Chat.lnk
%USERPROFILE%\Desktop\LightRag\LightRAG-Control.lnk
```

The Desktop stays clean. Internal launcher logic lives inside the project folder:

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
- installs selected Python package groups from the requirements files;
- writes only `LightRAG-Chat.lnk` and `LightRAG-Control.lnk` to the Desktop;
- assigns `assets/icons/LightRAG-Chat.ico` and `assets/icons/LightRAG-Control.ico` to those shortcuts;
- writes an `INSTALL_REPORT.md` file;
- shows a final "manual steps" section for apps or tools that still need to be installed by hand.

Dry run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\install-knowledge-lab.ps1 -DryRun -SkipPythonPackages
```

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for the current system diagram, runtime flow, paths, scopes, and fallback behavior.

Short version:

```text
Obsidian Markdown
  -> import/sync scripts
  -> LightRAG ingest
  -> LightRAG storage
  -> LightRAG query
  -> LM Studio embeddings + LLM
  -> answer with references or fallback warning
```

## Knowledge Scopes

| Scope | Project | Storage | Purpose |
| --- | --- | --- | --- |
| `general` | empty | `LightRAG/rag_storage_general` | General notes, Unity resources, articles, music, Telegram and YouTube sources |
| `web` | `web-development` | `LightRAG/rag_storage_web` | Web-development notes, snippets, frontend/backend solutions and sources |
| `game` | `my-game` | `LightRAG/rag_storage_game_my-game` | A personal game-project knowledge base |

Reindex examples:

```powershell
scripts\ingest-vault-scope-lmstudio.ps1 -Scope general
scripts\ingest-vault-scope-lmstudio.ps1 -Scope web -Project web-development
scripts\ingest-vault-scope-lmstudio.ps1 -Scope game -Project my-game
```

## Chat UI

The chat window starts with a short temporary hint. It disappears as soon as the first message is sent.

- `Context` routes questions to `Auto`, `General`, `Web Development`, or `My Game`.
- `LightRAG` toggles retrieval on or off. On is the normal mode.
- `History` shows recent local messages from `tmp/knowledge-chat-history.jsonl`.
- A gray warning line appears when the answer was generated without knowledge-base context.

## Query Diagnostics

Normal chat usage does not require a debug environment flag. LightRAG retrieval is enabled by default and can be turned off with the `LightRAG` checkbox in the chat toolbar.

`LMSTUDIO_SHOW_RETRIEVAL` is an audit flag. It prints retrieval statistics to the console so you can manually prove that context was found before the final answer:

```powershell
$env:LMSTUDIO_SHOW_RETRIEVAL='1'
scripts\query-vault-scope-lmstudio.ps1 -Scope game -Project my-game "What is known about my-game? Give references."
```

A healthy result includes:

```text
LightRAG retrieval audit:
- status: success
- chunks found: 1
- final chunks sent to answer: 1
- references: 1
- source files:
  [1] 20 Projects/My Game/_README.md
```

To force plain LM Studio mode from the command line:

```powershell
$env:LMSTUDIO_USE_LIGHTRAG='0'
scripts\query-vault-scope-lmstudio.ps1 -Scope game -Project my-game "Answer without LightRAG."
```

The GUI uses the same flag internally when the `LightRAG` checkbox is off.

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

Start local models:

```powershell
scripts\start-knowledge-lab.ps1
```

Stop local models:

```powershell
scripts\stop-knowledge-lab.ps1
```

## Repository Notes

Generated runtime artifacts are intentionally ignored:

- `LightRAG/.venv`
- `LightRAG/rag_storage*`
- `__pycache__`
- `.env`
- `tmp`
- downloaded model archives

Recreate indexes locally with the ingest scripts after cloning or moving the project.
