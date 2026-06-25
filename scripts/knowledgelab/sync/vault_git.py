"""Git-based vault synchronization: auto-commit, push, pull."""
from __future__ import annotations

import subprocess
import threading
import time
from pathlib import Path


def _run_git(args: list[str], cwd: Path, timeout: int = 30) -> tuple[int, str]:
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return result.returncode, (result.stdout + "\n" + result.stderr).strip()
    except FileNotFoundError:
        return -1, "git not found"
    except subprocess.TimeoutExpired:
        return -2, "git timeout"
    except Exception as exc:
        return -3, str(exc)


def init_vault_git(vault_dir: Path) -> bool:
    """Initialize git repo in vault if not already initialized."""
    if (vault_dir / ".git").exists():
        return True

    code, output = _run_git(["init"], vault_dir)
    if code != 0:
        return False

    gitignore_content = """\
.obsidian/workspace.json
.obsidian/workspace-mobile.json
.obsidian/plugins/
.obsidian/themes/
.DS_Store
Thumbs.db
*.tmp
tmp/
"""
    gitignore_path = vault_dir / ".gitignore"
    if not gitignore_path.exists():
        gitignore_path.write_text(gitignore_content, encoding="utf-8")

    _run_git(["add", "-A"], vault_dir)
    _run_git(["commit", "-m", "Initial vault commit"], vault_dir)
    return True


def vault_git_status(vault_dir: Path) -> dict:
    """Get git status of the vault."""
    if not (vault_dir / ".git").exists():
        return {"initialized": False, "dirty": False, "ahead": 0, "behind": 0, "untracked": 0, "message": "Git not initialized"}

    code, output = _run_git(["status", "--porcelain"], vault_dir)
    if code != 0:
        return {"initialized": True, "dirty": False, "ahead": 0, "behind": 0, "untracked": 0, "message": output}

    lines = [l for l in output.strip().split("\n") if l.strip()]
    untracked = sum(1 for l in lines if l.startswith("??"))
    modified = len(lines) - untracked

    ahead = 0
    behind = 0
    code2, rev_list = _run_git(["rev-list", "--left-right", "--count", "HEAD...@{u}"], vault_dir)
    if code2 == 0 and rev_list:
        parts = rev_list.split()
        if len(parts) >= 2:
            ahead = int(parts[0])
            behind = int(parts[1])

    return {
        "initialized": True,
        "dirty": modified > 0 or untracked > 0,
        "ahead": ahead,
        "behind": behind,
        "untracked": untracked,
        "modified": modified,
        "message": f"{modified} modified, {untracked} untracked" if lines else "clean",
    }


def vault_git_commit(vault_dir: Path, message: str = "Auto-sync") -> tuple[bool, str]:
    """Stage all changes and commit."""
    code1, _ = _run_git(["add", "-A"], vault_dir)
    if code1 != 0:
        return False, "git add failed"

    code2, output = _run_git(["commit", "-m", message, "--allow-empty"], vault_dir)
    if code2 != 0:
        if "nothing to commit" in output.lower():
            return True, "nothing to commit"
        return False, output

    return True, output


def vault_git_push(vault_dir: Path) -> tuple[bool, str]:
    """Push to remote."""
    code, output = _run_git(["push"], vault_dir, timeout=60)
    return code == 0, output


def vault_git_pull(vault_dir: Path) -> tuple[bool, str]:
    """Pull from remote."""
    code, output = _run_git(["pull", "--rebase"], vault_dir, timeout=60)
    return code == 0, output


_auto_sync_thread: threading.Thread | None = None
_auto_sync_stop = threading.Event()


def vault_git_auto_sync(vault_dir: Path, interval_seconds: int = 300) -> None:
    """Start background auto-sync thread."""
    global _auto_sync_thread
    if _auto_sync_thread and _auto_sync_thread.is_alive():
        return

    _auto_sync_stop.clear()

    def _loop() -> None:
        while not _auto_sync_stop.is_set():
            _auto_sync_stop.wait(interval_seconds)
            if _auto_sync_stop.is_set():
                break
            if not (vault_dir / ".git").exists():
                continue
            vault_git_commit(vault_dir, "Auto-sync")
            status = vault_git_status(vault_dir)
            if status.get("ahead", 0) > 0:
                vault_git_push(vault_dir)

    _auto_sync_thread = threading.Thread(target=_loop, daemon=True, name="vault-git-sync")
    _auto_sync_thread.start()


def vault_git_stop_auto_sync() -> None:
    """Stop background auto-sync."""
    _auto_sync_stop.set()
