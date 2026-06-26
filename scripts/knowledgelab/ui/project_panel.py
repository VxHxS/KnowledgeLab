"""Project action panel UI and workers."""
from __future__ import annotations

import os
import subprocess
import sys
import threading
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import ttk
from typing import TYPE_CHECKING

from knowledgelab.utils.text import now_iso
from knowledgelab.routing.project_stack import detect_project_stack, has_static_entry, find_serveable_dir
from knowledgelab.tasks.project_actions import find_free_port

if TYPE_CHECKING:
    from main import KnowledgeChatApp


class ProjectActionPanel:
    """Manages project action panel UI and background workers."""

    def __init__(self, app: KnowledgeChatApp) -> None:
        self.app = app

    def append_panel(self, action_id: str) -> None:
        """Append project action buttons to chat."""
        action = self.app.get_project_action(action_id)
        if not action:
            return
        title = str(action.get("title") or "Project")
        server = action.get("server") if isinstance(action.get("server"), dict) else {}
        pid = int(server.get("pid") or 0)
        running = bool(pid and self.app.is_process_running(pid))
        self.app.chat.configure(state="normal")
        frame = tk.Frame(self.app.chat, bg="#ffffff", padx=0, pady=3)
        inner = tk.Frame(frame, bg="#eef2f5", padx=10, pady=8)
        inner.grid(row=0, column=0, sticky="w")
        tk.Label(inner, text=title, bg="#eef2f5", fg="#1f2933", font=("Segoe UI Semibold", 9)).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 6))
        ttk.Button(inner, text="Получить результат", command=lambda aid=action_id: self.build_project(aid)).grid(row=1, column=0, padx=(0, 6), sticky="w")
        server_text = "Остановить сервер" if running else "Запуск на локальном сервере"
        ttk.Button(inner, text=server_text, command=lambda aid=action_id: self.start_server(aid)).grid(row=1, column=1, padx=6, sticky="w")
        if server.get("url"):
            ttk.Button(inner, text="Открыть", command=lambda url=str(server.get("url")): webbrowser.open(url)).grid(row=1, column=2, padx=(6, 0), sticky="w")
        self.app.chat.window_create("end", window=frame)
        self.app.chat.insert("end", "\n")
        self.app.chat_widgets.append(frame)
        self.app.chat.see("end")

    def build_project(self, action_id: str) -> None:
        """Start project build."""
        if self.app.busy:
            return
        action = self.app.get_project_action(action_id)
        if not action:
            self.app.append_warning_message("Project action не найден.", persist=False)
            return
        operation_id = self.app.begin_operation("Building project artifact...", 900)
        threading.Thread(target=self.build_worker, args=(operation_id, action_id), daemon=True).start()

    def build_worker(self, operation_id: int, action_id: str) -> None:
        """Background build worker."""
        try:
            action = self.app.get_project_action(action_id)
            if not action:
                raise RuntimeError("Project action не найден.")
            workspace = self.app.ensure_project_runtime_workspace(action)
            stack = detect_project_stack(workspace)
            install_command = [str(item) for item in stack.get("install_command", [])]
            if stack.get("kind") == "package" and install_command and not (workspace / "node_modules").exists():
                current_action = self.app.get_project_action(action_id) or {}
                if current_action.get("install_consent") is not True and not self.app.ensure_project_install_consent_threadsafe(action_id):
                    raise RuntimeError("Установка зависимостей не разрешена для этого проекта.")
                ok, message = self.app.run_project_command(action_id, "install", install_command, workspace, timeout=1200)
                if not ok:
                    raise RuntimeError(f"Не удалось установить зависимости: {message}")
            build_command = [str(item) for item in stack.get("build_command", [])]
            if build_command:
                ok, message = self.app.run_project_command(action_id, "build", build_command, workspace, timeout=1200)
                if not ok:
                    raise RuntimeError(f"Build failed: {message}")
            stack = detect_project_stack(workspace)
            artifact_path = str(stack.get("artifact_path") or workspace)
            self.app.update_project_action(action_id, stack=stack, artifact_path=artifact_path, runtime_workspace=str(workspace))
            self.app.root.after(0, self.finish_build, operation_id, action_id, f"Готово: artifact собран.\n{artifact_path}", artifact_path)
        except Exception as exc:
            self.app.root.after(0, self.finish_build, operation_id, action_id, f"Не удалось получить результат: {exc}", "")

    def finish_build(self, operation_id: int, action_id: str, message: str, open_path: str = "") -> None:
        """Finish project build."""
        if self.app.is_active_operation(operation_id):
            self.app.set_busy(False, "Ready")
        self.app.append_warning_message(message, persist=False)
        if open_path:
            try:
                os.startfile(open_path)  # type: ignore[attr-defined]
            except Exception:
                pass
        self.app.render_current_chat()

    def start_server(self, action_id: str) -> None:
        """Start project dev server."""
        action = self.app.get_project_action(action_id)
        if not action:
            self.app.append_warning_message("Project action не найден.", persist=False)
            return
        server = action.get("server") if isinstance(action.get("server"), dict) else {}
        pid = int(server.get("pid") or 0)
        if pid and self.app.is_process_running(pid):
            self.stop_server(action_id)
            return
        if self.app.busy:
            return
        operation_id = self.app.begin_operation("Starting local project server...", 900)
        threading.Thread(target=self.server_worker, args=(operation_id, action_id), daemon=True).start()

    def server_worker(self, operation_id: int, action_id: str) -> None:
        """Background server worker."""
        try:
            action = self.app.get_project_action(action_id)
            if not action:
                raise RuntimeError("Project action не найден.")
            workspace = self.app.ensure_project_runtime_workspace(action)
            stack = detect_project_stack(workspace)
            install_command = [str(item) for item in stack.get("install_command", [])]
            if stack.get("kind") == "package" and install_command and not (workspace / "node_modules").exists():
                current_action = self.app.get_project_action(action_id) or {}
                if current_action.get("install_consent") is not True and not self.app.ensure_project_install_consent_threadsafe(action_id):
                    raise RuntimeError("Установка зависимостей не разрешена для этого проекта.")
                ok, message = self.app.run_project_command(action_id, "install", install_command, workspace, timeout=1200)
                if not ok:
                    raise RuntimeError(f"Не удалось установить зависимости: {message}")
            port = find_free_port()
            command: list[str]
            cwd = workspace
            env = dict(os.environ)
            env["PORT"] = str(port)
            framework = str(stack.get("framework") or "")
            kind = str(stack.get("kind") or "")
            server_command = [str(item) for item in stack.get("server_command", [])]
            if server_command:
                command = list(server_command)
                if framework == "vite" and "dev" in command:
                    command.extend(["--", "--host", "127.0.0.1", "--port", str(port)])
            elif kind == "static":
                artifact_path = str(stack.get("artifact_path") or workspace)
                serve_dir = find_serveable_dir(Path(artifact_path))
                if not has_static_entry(serve_dir):
                    raise RuntimeError(
                        "Проект не содержит index.html. Невозможно запустить локальный сервер.\n"
                        f"Проверьте директорию: {serve_dir}"
                    )
                cwd = serve_dir
                command = [sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1"]
            else:
                artifact = Path(str(stack.get("artifact_path") or workspace))
                cwd = artifact if artifact.exists() else workspace
                if not has_static_entry(cwd):
                    raise RuntimeError(
                        "Проект не содержит index.html и не имеет скрипта dev/start в package.json.\n"
                        f"Невозможно запустить локальный сервер для: {cwd}"
                    )
                command = [sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1"]
            out_path, err_path = self.app.action_command_log_paths(action_id, "server")
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
            url = f"http://127.0.0.1:{port}/"
            self.app.update_project_action(
                action_id,
                stack=stack,
                runtime_workspace=str(workspace),
                server={
                    "pid": process.pid,
                    "url": url,
                    "command": command,
                    "cwd": str(cwd),
                    "stdout": str(out_path),
                    "stderr": str(err_path),
                    "started_at": now_iso(),
                },
            )
            self.app.root.after(0, self.finish_server_start, operation_id, action_id, url)
        except Exception as exc:
            self.app.root.after(0, self.finish_build, operation_id, action_id, f"Не удалось запустить локальный сервер: {exc}", "")

    def finish_server_start(self, operation_id: int, action_id: str, url: str) -> None:
        """Finish server start."""
        if self.app.is_active_operation(operation_id):
            self.app.set_busy(False, "Ready")
        self.app.append_warning_message(f"Локальный сервер запущен: {url}", persist=False)
        webbrowser.open(url)
        self.app.render_current_chat()

    def stop_server(self, action_id: str) -> None:
        """Stop project server."""
        action = self.app.get_project_action(action_id)
        if not action:
            return
        server = action.get("server") if isinstance(action.get("server"), dict) else {}
        pid = int(server.get("pid") or 0)
        if pid:
            try:
                subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True, text=True, timeout=10, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            except Exception:
                self.app.append_warning_message(f"Не удалось завершить процесс PID {pid}. Возможно, процесс уже остановлен.", persist=False)
        server["stopped_at"] = now_iso()
        server["pid"] = 0
        self.app.update_project_action(action_id, server=server)
        self.app.append_warning_message("Локальный сервер остановлен.", persist=False)
        self.app.render_current_chat()
