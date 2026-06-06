# KnowledgeLab Architecture

State date: 2026-06-06.

KnowledgeLab is a local-first Windows knowledge system. The chat is an ordinary LM Studio chat by default, with optional LightRAG retrieval, Obsidian capture, diagnostics, and GPU conflict warnings as capabilities around the conversation.

## Goals

- Keep normal chat unrestricted: greetings, short messages, code requests, translation, brainstorming, and questions all go to the LLM.
- Keep LightRAG optional and visible: when it is off or unavailable, the answer still completes and the UI shows a small gray note.
- Keep knowledge in plain Markdown inside an Obsidian vault.
- Keep chat history, settings, indexes, logs, and secrets local.
- Make failures understandable and point the user to LightRAG-Control when the system needs maintenance.
- Warn about likely GPU conflicts without auto-closing games or auto-starting Game Guard at Windows startup.
- Keep the Desktop clean with only `LightRAG-Chat.lnk` and `LightRAG-Control.lnk`.

## Main Paths

```text
Project root:
C:\MyFiles\KnowledgeLab

Obsidian vault:
C:\MyFiles\KnowledgeLab\Obsidian-Test-Vault

Desktop launchers:
%USERPROFILE%\Desktop\LightRag\LightRAG-Chat.lnk
%USERPROFILE%\Desktop\LightRag\LightRAG-Control.lnk

Chat sessions:
C:\MyFiles\KnowledgeLab\tmp\knowledge-chat-sessions.json

Chat settings:
C:\MyFiles\KnowledgeLab\tmp\knowledge-chat-settings.json

LM Studio API:
http://127.0.0.1:1234/v1
```

## Runtime Architecture

```mermaid
flowchart TD
    User["User"]
    Chat["LightRAG Chat<br/>scripts/knowledge_chat_gui.py"]
    Store["Conversation Store<br/>tmp/knowledge-chat-sessions.json"]
    Settings["Settings<br/>Enter, LightRAG, colors, Obsidian, Game Guard"]
    Router["Intent Router<br/>plain chat / RAG / save / diagnostics"]
    Save["Obsidian Capture<br/>Markdown notes"]
    Health["Health Hints<br/>LM Studio, LightRAG index, Obsidian path"]
    Guard["GPU Game Guard<br/>delayed warning after chat opens"]
    QueryPS["Scoped PowerShell Query<br/>query-vault-scope-lmstudio.ps1"]
    QueryPY["LLM/RAG Adapter<br/>query-vault-lmstudio.py"]
    LightRAG["LightRAG Storage<br/>rag_storage_general/web/game"]
    Vault["Obsidian Vault<br/>Markdown source of truth"]
    LMStudio["LM Studio<br/>OpenAI-compatible API"]
    Control["LightRAG-Control<br/>checks and maintenance"]
    Answer["Answer<br/>LLM text + gray capability notes"]

    User --> Chat
    Chat --> Store
    Chat --> Settings
    Chat --> Router
    Router --> Save
    Save --> Vault
    Router --> QueryPS
    QueryPS --> QueryPY
    QueryPY --> LMStudio
    QueryPY --> LightRAG
    LightRAG --> Vault
    QueryPY --> Answer
    LMStudio --> Answer
    Chat --> Guard
    Chat --> Health
    Health --> Control
    Guard --> Control
```

## Chat Flow

```mermaid
sequenceDiagram
    participant U as User
    participant GUI as LightRAG Chat
    participant R as Intent Router
    participant Q as Query Layer
    participant L as LM Studio
    participant G as LightRAG
    participant O as Obsidian

    U->>GUI: Any message
    GUI->>GUI: Save to current chat session
    GUI->>R: Classify capability intent
    alt Save/link intent
        R->>GUI: Ask project if unclear
        GUI->>O: Write Markdown note
        GUI-->>U: Saved path
    else LightRAG enabled and index ready
        R->>Q: Ask with selected scope
        Q->>G: Retrieve context
        Q->>L: Ask with context
        L-->>GUI: Answer with references/context
    else LightRAG off or unavailable
        R->>Q: Ask plain LM Studio
        Q->>L: Direct LLM request
        L-->>GUI: Normal answer
        GUI-->>U: Gray note that LightRAG was not used
    end
```

## Components

| Component | Role |
| --- | --- |
| Chat UI | Messenger-style Tkinter app with left chat history, rename/delete, settings, Obsidian icon, cancel and timeout protection |
| Conversation Store | Local JSON sessions with messages, warnings, timestamps, and current chat |
| Intent Router | Treats all input as normal chat first, then activates save/RAG/diagnostic capabilities when appropriate |
| LightRAG Adapter | Uses indexed storage only when the checkbox is enabled and storage exists |
| Obsidian Capture | Saves URLs and notes from phrases like `вот ссылка`, `сохрани`, `добавь в базу` |
| Health Hints | Converts system failures into readable guidance and suggests LightRAG-Control |
| GPU Game Guard | Samples GPU load after chat opens; warns about heavy processes and KnowledgeLab-side processes |
| LightRAG-Control | Manual checks, maintenance indexing, model stop, imports, and deeper troubleshooting |
| Installer | Checks dependencies, writes only two Desktop launchers, assigns icons, and produces `INSTALL_REPORT.md` |

## Knowledge Scopes

| Scope | Project | Storage | Purpose |
| --- | --- | --- | --- |
| `general` | empty | `LightRAG/rag_storage_general` | General notes, Unity resources, articles, music, Telegram and YouTube sources |
| `web` | `web-development` | `LightRAG/rag_storage_web` | Web-development notes, snippets, frontend/backend solutions and sources |
| `game` | `my-game` | `LightRAG/rag_storage_game_my-game` | Personal game-project knowledge |

## Behavior Rules

- Default chat mode is plain LM Studio. LightRAG is off until enabled in settings or by the checkbox.
- If LightRAG is enabled but the selected index is missing, the checkbox turns off, the answer uses plain LM Studio, and the user sees a gray note.
- `Enter` sends by default; `Shift+Enter` adds a newline. This is configurable.
- Big maintenance buttons stay out of the chat. Reindexing and deeper checks belong in LightRAG-Control.
- Obsidian opens through the small icon. If the app cannot be found, the user can select `Obsidian.exe` or open the Obsidian website.
- Game Guard does not run at Windows startup by default. It samples GPU load a few seconds after the chat opens and warns only on sustained load.
- Startup blocking by the old process-name Game Guard is opt-in through `KNOWLEDGELAB_STARTUP_GAME_GUARD=1`.

## Diagnostics

Manual retrieval audit:

```powershell
$env:LMSTUDIO_SHOW_RETRIEVAL='1'
scripts\query-vault-scope-lmstudio.ps1 -Scope game -Project my-game "What is known about my-game? Give references."
```

Plain LLM mode:

```powershell
$env:LMSTUDIO_USE_LIGHTRAG='0'
scripts\query-vault-scope-lmstudio.ps1 -Scope web -Project web-development "Make CSS for a popup window."
```

Control smoke test:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\MyFiles\KnowledgeLab\LightRAG-Desktop\LightRAG-Control\LightRAG-Control.ps1" -SmokeTest
```

## Local-Only Artifacts

These are intentionally not committed:

- `LightRAG/.venv`
- `LightRAG/rag_storage*`
- `tmp/knowledge-chat-sessions.json`
- `tmp/knowledge-chat-history.jsonl`
- `tmp/knowledge-chat-settings.json`
- `.env`
- downloaded models and archives
- generated installer reports
