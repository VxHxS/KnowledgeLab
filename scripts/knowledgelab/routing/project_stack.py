from __future__ import annotations

import json
from pathlib import Path


def read_package_json(path: Path) -> dict:
    package_path = path / "package.json"
    if not package_path.exists():
        return {}
    try:
        data = json.loads(package_path.read_text(encoding="utf-8-sig"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def detect_package_manager(workspace: Path, package_data: dict) -> str:
    package_manager = str(package_data.get("packageManager") or "").lower()
    if package_manager.startswith("pnpm"):
        return "pnpm"
    if package_manager.startswith("yarn"):
        return "yarn"
    if package_manager.startswith("npm"):
        return "npm"
    if (workspace / "pnpm-lock.yaml").exists():
        return "pnpm"
    if (workspace / "yarn.lock").exists():
        return "yarn"
    return "npm"


def command_for_package_manager(manager: str, script: str) -> list[str]:
    if manager == "pnpm":
        return ["pnpm", "run", script]
    if manager == "yarn":
        return ["yarn", script]
    return ["npm", "run", script]


def install_command_for_package_manager(manager: str) -> list[str]:
    if manager == "pnpm":
        return ["pnpm", "install"]
    if manager == "yarn":
        return ["yarn", "install"]
    return ["npm", "install"]


def find_artifact_dir(workspace: Path) -> Path:
    for name in ("dist", "build", "out", ".next"):
        candidate = workspace / name
        if candidate.exists() and candidate.is_dir():
            return candidate
    return workspace


def find_serveable_dir(workspace: Path) -> Path:
    """Find the best directory to serve: artifact with index.html, or workspace root."""
    for name in ("index.html", "index.htm"):
        if (workspace / name).exists():
            return workspace
    for subdir in ("dist", "build", "out", ".next"):
        candidate = workspace / subdir
        if candidate.is_dir() and any((candidate / n).exists() for n in ("index.html", "index.htm")):
            return candidate
    return workspace


def has_static_entry(path: Path) -> bool:
    return any((path / name).exists() for name in ("index.html", "index.htm"))


def detect_project_stack(workspace: Path) -> dict[str, object]:
    package_data = read_package_json(workspace)
    if package_data:
        scripts = package_data.get("scripts") if isinstance(package_data.get("scripts"), dict) else {}
        manager = detect_package_manager(workspace, package_data)
        build_script = "build" if "build" in scripts else ("export" if "export" in scripts else "")
        server_script = "dev" if "dev" in scripts else ("start" if "start" in scripts else "")
        deps = " ".join(
            str(value)
            for section in ("dependencies", "devDependencies")
            for value in (package_data.get(section) or {}).keys()
            if isinstance(package_data.get(section), dict)
        ).lower()
        framework = "vite" if "vite" in deps else ("next" if "next" in deps else "node")
        return {
            "kind": "package",
            "package_manager": manager,
            "framework": framework,
            "install_command": install_command_for_package_manager(manager),
            "build_command": command_for_package_manager(manager, build_script) if build_script else [],
            "server_command": command_for_package_manager(manager, server_script) if server_script else [],
            "artifact_path": str(find_artifact_dir(workspace)),
        }
    serveable = find_serveable_dir(workspace)
    if has_static_entry(serveable):
        return {
            "kind": "static",
            "package_manager": "",
            "framework": "static",
            "install_command": [],
            "build_command": [],
            "server_command": [],
            "artifact_path": str(serveable),
        }
    return {
        "kind": "unknown",
        "package_manager": "",
        "framework": "unknown",
        "install_command": [],
        "build_command": [],
        "server_command": [],
        "artifact_path": str(workspace),
    }
