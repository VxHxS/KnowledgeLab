# Mimo Refactor Audit

Audit date: 2026-06-25.

## Scope

This audit inspected the staging git clone at:

`C:\Users\Юрий\Documents\Freelance\KnowledgeLab-staging-20260605211949`

The installed app launched from desktop shortcuts lives at:

`C:\MyFiles\KnowledgeLab`

The staging clone has remote:

`https://github.com/VxHxS/KnowledgeLab.git`

## What Changed After Mimo

The latest committed state already contains a major Mimo refactor:

`e935f88 refactor: decompose main.py from 9380 to 3225 lines (-66%)`

The refactor introduced `scripts/knowledgelab/` and moved logic from the old monolithic desktop app into domain modules for config, models, routing, vault capture, material processing, LM Studio, UI helpers, and tasks.

The current dirty worktree has additional uncommitted changes on top of that commit. Notable git status entries:

- many launcher and script updates;
- `scripts/knowledge_chat_gui.py` deleted;
- `.mimocode/` added as an untracked Mimo service directory;
- `Obsidian-Test-Vault/10 General Knowledge/Topics/New Test Topic/_Topic.md` added as an untracked vault note;
- new audit fixes in `scripts/knowledgelab/material/queue.py`, `scripts/knowledgelab/routing/topics.py`, `scripts/knowledgelab/config.py`, `scripts/lmstudio_common.py`, `scripts/main.py`, and tests.

## What Looks Normal

- The split into `scripts/knowledgelab/` is real and mostly coherent.
- `scripts/main.py` is still the app coordinator, but many methods now delegate into extracted modules.
- Unit tests exist under `tests/` for config, imports, models, routing, vault capture/frontmatter, LM Studio helpers, runtime context, material web parsing, voice/youtube/video, book discovery, and GUI behavior through mocks.
- PowerShell launchers now resolve the project root instead of always hardcoding `C:\MyFiles\KnowledgeLab`.
- LightRAG scope storage naming is consistently implemented in both Python and PowerShell.

## Suspicious Or Risky Points

- `.mimocode/` is very large and mostly service metadata. It should not be committed unless there is a deliberate reason.
- `Obsidian-Test-Vault/10 General Knowledge/Topics/New Test Topic/_Topic.md` looks like test/user-generated data. It should be reviewed before commit.
- The active installed app is not a git clone, so normal `git diff` does not describe what the desktop shortcut currently launches.
- Some duplicated UI widget classes remain in `scripts/main.py` despite extracted versions in `scripts/knowledgelab/ui/widgets.py` and `tooltip.py`.
- `scripts/knowledgelab/tests/self_test.py` is still a TODO placeholder.
- Several modules still use broad `except Exception`; many are acceptable UI/file-system fallbacks, but they should be reduced around background operations over time.
- `capture_destination()` and other vault helpers still rely on global `VAULT_DIR` in some places. The topic path bug found during this audit was fixed, but the wider vault-path model still needs a careful pass.
- Network-facing helpers exist for web pages, CodePen, GitHub metadata, Google Books, Open Library, DuckDuckGo snippets, and YouTube captions. They should stay explicit and controllable.

## Problems Fixed During This Audit

- Fixed `launch_reindex()` in `scripts/knowledgelab/material/queue.py`: it used `os.environ` without importing `os`, then swallowed the exception. It now imports `os` and emits a `::knowledge-warning` on launch failure.
- Fixed topic creation in `scripts/knowledgelab/routing/topics.py`: `ensure_topic_exists(..., vault_dir=...)` now actually writes into the passed vault, not the global default.
- Standardized the default LM Studio API URL to `http://127.0.0.1:1234/v1` in `scripts/knowledgelab/config.py`.
- Updated `scripts/lmstudio_common.py` to reuse `LMSTUDIO_API_URL` instead of its own `5000/v1` default.
- Added a working `scripts/main.py --self-test` path that runs before Tkinter initialization and does not require LM Studio.
- Added tests for the reindex launch environment, custom vault topic creation, and LM Studio default URL.

## Parts Not To Touch Without More Verification

- The remaining `KnowledgeChatApp` GUI body in `scripts/main.py`.
- Drag-and-drop behavior, especially Windows/Tk/tkinterdnd2 edge cases.
- Book detection and online catalog enrichment logic.
- Video frame extraction and future ASR pipeline.
- Project runtime build/server actions under `tmp/project-runtime`.
- Installer and shortcut creation scripts.
- Any deletion of old scripts or vault content.

## Verification Performed

Commands run:

```powershell
git status --short --untracked-files=all
git log --oneline -5
git diff --stat
git diff --name-status
python scripts/main.py --self-test
```

Because `python` was not available in PATH and the project/user Python environments did not have `pytest`, checks were run with the bundled Codex Python:

```powershell
& "C:\Users\Юрий\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" scripts\main.py --self-test
```

Result:

```text
KnowledgeLab self-test OK
```

Also verified by a direct import/reindex smoke check:

```text
import-config-reindex-ok
```

Not completed:

- Full `pytest` suite: `pytest` is not installed in the available Python environments.
- GitHub remote refresh: `git fetch origin --prune` hung with no output and was stopped.
- Live LM Studio behavior test: not run, because it requires a running LM Studio server and loaded models.

## Recommended Immediate Follow-Up

1. Decide whether `.mimocode/` should be ignored or committed.
2. Decide whether the generated Vault topic note belongs in the repo.
3. Install pytest into the project test environment or document the intended test interpreter.
4. Run the full test suite from a proper project venv.
5. Compare staging and `C:\MyFiles\KnowledgeLab`, then sync intentionally if desktop shortcuts should launch the newest code.

