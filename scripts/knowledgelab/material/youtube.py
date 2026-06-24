"""YouTube transcript sync — command building and worker logic."""

from __future__ import annotations

from knowledgelab.config import ROOT, SCRIPTS_DIR, VAULT_DIR


def build_youtube_sync_command(
    python_executable: str,
    scope: str,
    project: str = "",
) -> list[str]:
    command = [
        python_executable,
        str(SCRIPTS_DIR / "sync-youtube-links.py"),
        "--vault-dir",
        str(VAULT_DIR),
        "--scope",
        scope,
        "--continue-on-error",
    ]
    if scope in {"game", "web"} and project:
        command.extend(["--project", project])
    return command
