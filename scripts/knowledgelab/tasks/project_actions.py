"""Project actions — load, save, CRUD, runtime workspace, command execution."""
from __future__ import annotations

import json
import shutil
import socket
import subprocess
import sys
from pathlib import Path

from knowledgelab.config import ROOT, PROJECT_ACTIONS_PATH, PROJECT_RUNTIME_DIR
from knowledgelab.utils.text import slugify, now_iso, clean_filename
from knowledgelab.utils.urls import parse_github_url
from knowledgelab.vault.capture import project_title_from_source_hint
from knowledgelab.routing.project_stack import detect_project_stack


def is_path_within(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def copy_project_runtime_tree(source: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copytree(str(source), str(destination), dirs_exist_ok=True)


def find_free_port(start: int = 8100, attempts: int = 50) -> int:
    for port in range(start, start + attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", port))
                return port
        except OSError:
            continue
    return start


def load_project_actions() -> dict:
    try:
        data = json.loads(PROJECT_ACTIONS_PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("actions"), dict):
            return data
    except Exception:
        pass
    return {"version": 1, "actions": {}}


def save_project_actions(data: dict) -> None:
    PROJECT_ACTIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROJECT_ACTIONS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def get_project_action(data: dict, action_id: str) -> dict | None:
    actions = data.setdefault("actions", {})
    action = actions.get(action_id) if isinstance(actions, dict) else None
    return action if isinstance(action, dict) else None


def new_id(prefix: str) -> str:
    import datetime as dt
    return f"{prefix}-{dt.datetime.now().strftime('%Y%m%d%H%M%S%f')}"


def create_project_action(
    data: dict,
    *,
    source_type: str,
    source_path: str = "",
    source_url: str = "",
    title: str = "",
    route: object,
) -> str:
    title_seed = clean_filename(title or project_title_from_source_hint(source_url or source_path) or "Project")
    action_id = new_id("project")
    runtime_workspace = PROJECT_RUNTIME_DIR / action_id / "workspace"
    action = {
        "id": action_id,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "title": title_seed,
        "source_type": source_type,
        "source_path": source_path,
        "source_url": source_url,
        "runtime_workspace": str(runtime_workspace),
        "scope": getattr(route, "scope", ""),
        "project": getattr(route, "project", ""),
        "layer": getattr(route, "layer", ""),
        "project_title": getattr(route, "project_title", ""),
        "project_section": getattr(route, "project_section", ""),
        "vault_notes": [],
        "stack": {},
        "artifact_path": "",
        "install_consent": None,
        "server": {},
    }
    data.setdefault("actions", {})[action_id] = action
    save_project_actions(data)
    return action_id


def update_project_action(data: dict, action_id: str, **updates) -> None:
    action = get_project_action(data, action_id)
    if not action:
        return
    action.update(updates)
    action["updated_at"] = now_iso()
    save_project_actions(data)


def add_project_action_notes(data: dict, action_id: str, notes: list[str]) -> None:
    action = get_project_action(data, action_id)
    if not action:
        return
    existing = [str(item) for item in action.get("vault_notes", []) if item]
    for note in notes:
        if note and note not in existing:
            existing.append(note)
    update_project_action(data, action_id, vault_notes=existing)


def action_runtime_workspace(action: dict) -> Path:
    action_id = str(action.get("id") or "project")
    raw = str(action.get("runtime_workspace") or "")
    workspace = Path(raw) if raw else PROJECT_RUNTIME_DIR / action_id / "workspace"
    if not is_path_within(workspace, PROJECT_RUNTIME_DIR):
        raise RuntimeError(f"Runtime workspace is outside project runtime root: {workspace}")
    return workspace


def ensure_project_runtime_workspace(action: dict) -> Path:
    workspace = action_runtime_workspace(action)
    source_type = str(action.get("source_type") or "")
    if workspace.exists() and any(workspace.iterdir()):
        return workspace
    if source_type == "local_folder":
        source = Path(str(action.get("source_path") or ""))
        if not source.is_dir():
            raise RuntimeError(f"Source folder was not found: {source}")
        copy_project_runtime_tree(source, workspace)
    elif source_type == "github_repository":
        url = str(action.get("source_url") or "")
        if not url:
            raise RuntimeError("GitHub repository URL is empty.")
        workspace.parent.mkdir(parents=True, exist_ok=True)
        clone_url = parse_github_url(url).get("github_clone_url", url)
        result = subprocess.run(["git", "clone", clone_url, str(workspace)], cwd=str(ROOT), text=True, capture_output=True, timeout=600)
        if result.returncode != 0:
            raise RuntimeError((result.stderr or result.stdout or "git clone failed").strip())
    else:
        raise RuntimeError(f"Unsupported project source type: {source_type}")
    return workspace


def action_command_log_paths(action_id: str, name: str) -> tuple[Path, Path]:
    log_dir = ROOT / "tmp" / "project-action-logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    safe_name = slugify(f"{action_id}-{name}")
    return log_dir / f"{safe_name}.log", log_dir / f"{safe_name}.err.log"


def run_project_command(action_id: str, name: str, command: list[str], cwd: Path, timeout: int = 900, env: dict[str, str] | None = None) -> tuple[bool, str]:
    out_path, err_path = action_command_log_paths(action_id, name)
    with out_path.open("a", encoding="utf-8") as stdout, err_path.open("a", encoding="utf-8") as stderr:
        process = subprocess.Popen(
            command,
            cwd=str(cwd),
            stdout=stdout,
            stderr=stderr,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            env=env,
        )
        try:
            code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            try:
                process.wait(timeout=5)
            except Exception:
                pass
            return False, f"timeout after {timeout}s; log: {err_path}"
    if code == 0:
        return True, str(out_path)
    return False, f"код {code}; лог: {err_path}"


def is_process_running(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        result = subprocess.run(["tasklist", "/FI", f"PID eq {pid}"], capture_output=True, text=True, timeout=8, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return str(pid) in result.stdout
    except Exception:
        return False
