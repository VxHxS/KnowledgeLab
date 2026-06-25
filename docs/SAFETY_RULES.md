# KnowledgeLab Safety Rules

Audit date: 2026-06-25.

## Core Rule

KnowledgeLab is a local knowledge system. It should not have unrestricted authority over the whole computer. All file, shell, network, model, and project-runtime behavior should be explicit, scoped, and recoverable.

## File System Rules

- Do not delete user files automatically.
- Do not move user files automatically.
- Do not rewrite arbitrary folders outside configured KnowledgeLab paths.
- Keep heavy source files reference-only by default.
- Write generated notes into the configured Obsidian vault only.
- Treat `tmp/` as runtime state, logs, queues, and isolated workspaces.
- Treat `.mimocode/` as tool metadata unless the user explicitly decides to keep it in git.

## Obsidian Vault Rules

- Respect the configured `vault_path`.
- Do not write into a default vault if the user selected another vault.
- Avoid duplicate source notes when `source_url` or source path already exists.
- Do not modify `.obsidian` settings automatically.
- Do not modify `_Templates` except through a deliberate template task.
- For uncertain topics, use safe fallback folders and frontmatter rather than asking the model to invent structure.

## LightRAG Rules

- LightRAG retrieves from local indexed Markdown only.
- LightRAG should not search the web directly.
- Missing index must be visible as a warning.
- Background indexing must be logged.
- If the current answer is plain LM Studio because indexing is missing, the chat should say so.
- Do not treat LightRAG context as node state or operational truth.

## LM Studio Rules

- Default local endpoint: `http://127.0.0.1:1234/v1`.
- Do not use cloud LLM APIs unless the user explicitly configures them.
- If the model returns only reasoning content, show a clear warning or retry in final-answer mode.
- Do not claim the app is using Alibaba/OpenAI/Anthropic cloud unless the configuration proves it.
- Vision tasks should fail softly when no vision model is configured or loaded.

## Network Rules

Network access must be explicit and tied to a feature:

- web search snippets;
- article fetching;
- CodePen fetching;
- GitHub metadata/repository intake;
- YouTube caption lookup;
- Open Library and Google Books book enrichment.

Network calls should never be hidden behind ordinary local-chat behavior.

## Shell And Process Rules

- Do not run dangerous shell commands without explicit confirmation.
- Prefer argument lists over shell strings.
- Keep background processes hidden only when they are known maintenance workers.
- Log background process output to `tmp/`.
- PID files must be validated before stopping a process.
- Stop only processes that KnowledgeLab started or clearly owns.
- Project build/server actions should run inside isolated runtime workspaces, not the original source folder or vault.

## Project Runtime Rules

- Finished projects are reference cards, not build workspaces.
- Runtime workspaces belong under `tmp/project-runtime/<project-id>/`.
- Do not install dependencies into user project folders without consent.
- Do not clone arbitrary repos without a clear user action.
- Do not expose local servers without showing the URL and stop action.

## Git Rules

- The staging clone is the git working copy.
- The active installed app at `C:\MyFiles\KnowledgeLab` is not currently a git clone.
- Do not `git push` without explicit user permission.
- Do not commit `.mimocode/` or generated vault notes until the user decides.
- Do not run destructive git commands such as reset/checkout to discard changes unless explicitly requested.

## Post-Mimo Rules

After the Mimo refactor, be especially careful with:

- deletion of old files;
- duplicate modules;
- broad exception handlers;
- path resolver changes;
- installer changes;
- vault path handling;
- syncing staging to active install.

If a module looks dead, first document it in `MIMO_REFACTOR_AUDIT.md`; do not delete it immediately.

