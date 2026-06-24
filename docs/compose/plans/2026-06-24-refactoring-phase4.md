# KnowledgeLab Refactoring Phase 4 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use compose:subagent (recommended) or compose:execute to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Continue decomposing the monolithic `main.py` (4,423 lines, 232 methods) by extracting 80+ methods into focused domain modules, reducing the file to ~2,500 lines.

**Architecture:** Phase-based extraction — each task extracts one cohesive group of methods into a new or existing module, updates imports in main.py, and verifies tests pass. The KnowledgeChatApp class retains only core GUI event handlers and thin delegation wrappers.

**Tech Stack:** Python 3.10, tkinter, pytest, JSONL queue, LM Studio API

## Global Constraints

- All changes must be documented in markdown files
- Run `python -m pytest tests/ -v` after every extraction batch
- Run `python -m py_compile scripts/main.py` after every extraction
- Follow existing code conventions (snake_case, type hints, docstrings)
- Preserve all existing public interfaces — no breaking changes
- Keep the app functional after each task

---

## Task 1: Extract Settings Dialog UI

**Covers:** Settings dialog methods (open_settings, close_settings, save_settings_from_window, reset_settings_to_defaults, choose_obsidian_path, choose_vault_path, select_color_preset, update_color_preview, choose_button_color, apply_settings_to_ui, update_button_colors, update_web_search_button)

**Files:**
- Create: `scripts/knowledgelab/ui/settings_dialog.py`
- Modify: `scripts/main.py` (remove methods, add import)
- Test: `tests/test_settings_dialog.py`

**Interfaces:**
- Consumes: `self.root`, `self.settings`, `self.settings_window`, `self.settings_color_preview`, `self.settings_status_var`, tkinter variables (`enter_send_var`, `lightrag_var`, etc.), `BUTTON_COLOR_PRESETS`, `UI_THEME`, `DEFAULT_VAULT_DIR`, `add_tooltip()`, `save_settings()`
- Produces: `SettingsDialog` class with `open()`, `close()`, `save()`, `reset()`, `apply_to_ui()`, `update_button_colors()`, `update_web_search_button()`

- [ ] **Step 1: Create settings_dialog.py with SettingsDialog class**

```python
"""Settings dialog UI for KnowledgeChatApp."""
from __future__ import annotations

import tkinter as tk
from tkinter import colorchooser, ttk
from pathlib import Path

from knowledgelab.config import BUTTON_COLOR_PRESETS, DEFAULT_VAULT_DIR, UI_THEME
from knowledgelab.utils.colors import adjust_hex_color, readable_text_color
from knowledgelab.ui.settings import color_preset_name, normalize_settings


class SettingsDialog:
    """Manages the settings dialog window and its callbacks."""

    def __init__(self, app: "KnowledgeChatApp") -> None:
        self.app = app
        self.window: tk.Toplevel | None = None
        self.color_preview: tk.Label | None = None

    def open(self) -> None:
        """Open or raise the settings dialog."""
        if self.window and self.window.winfo_exists():
            self.window.lift()
            self.window.focus_force()
            return
        self._sync_vars_from_settings()
        self._build_window()

    def close(self) -> None:
        """Close the settings dialog."""
        if self.window and self.window.winfo_exists():
            self.window.destroy()
        self.window = None

    def _sync_vars_from_settings(self) -> None:
        s = self.app.settings
        self.app.enter_send_var.set(bool(s["send_on_enter"]))
        self.app.lightrag_var.set(bool(s["use_lightrag"]))
        self.app.game_guard_var.set(bool(s["game_guard_enabled"]))
        self.app.auto_process_links_var.set(bool(s.get("auto_process_links", True)))
        self.app.auto_route_topics_var.set(bool(s.get("auto_route_topics", True)))
        self.app.auto_create_topics_var.set(bool(s.get("auto_create_topics", True)))
        self.app.auto_detect_books_var.set(bool(s.get("auto_detect_books_in_images", True)))
        self.app.book_lookup_enabled_var.set(bool(s.get("book_lookup_enabled", True)))
        self.app.web_search_enabled_var.set(bool(s.get("web_search_enabled", False)))
        self.app.button_color_var.set(str(s["button_color"]))
        self.app.obsidian_path_var.set(str(s.get("obsidian_path", "")))
        self.app.vault_path_var.set(str(s.get("vault_path", str(DEFAULT_VAULT_DIR))))
        self.app.settings_status_var.set("")

    def _build_window(self) -> None:
        window = tk.Toplevel(self.app.root)
        self.window = window
        window.title("Настройки LightRAG Chat")
        window.transient(self.app.root)
        window.resizable(False, True)
        window.configure(bg="#f4f6f8")
        window.minsize(480, 400)
        window.maxsize(520, 700)
        window.protocol("WM_DELETE_WINDOW", self.close)

        canvas = tk.Canvas(window, bg="#f4f6f8", highlightthickness=0)
        scrollbar = ttk.Scrollbar(window, orient="vertical", command=canvas.yview)
        frame = ttk.Frame(canvas, padding=(18, 16), style="App.TFrame")

        frame.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=frame, anchor="nw", tags="frame_window")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        window.columnconfigure(0, weight=1)
        window.rowconfigure(0, weight=1)

        def on_canvas_configure(event):
            canvas.itemconfig("frame_window", width=event.width)
        canvas.bind("<Configure>", on_canvas_configure)

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind("<MouseWheel>", _on_mousewheel)
        frame.bind("<MouseWheel>", _on_mousewheel)
        frame.columnconfigure(1, weight=1)

        self._build_dialog_section(frame)
        self._build_obsidian_section(frame)
        self._build_color_section(frame)
        self._build_automation_section(frame)
        self._build_buttons(frame)

        window.update_idletasks()
        x = self.app.root.winfo_rootx() + max(30, (self.app.root.winfo_width() - window.winfo_width()) // 2)
        y = self.app.root.winfo_rooty() + max(30, (self.app.root.winfo_height() - window.winfo_height()) // 3)
        window.geometry(f"+{x}+{y}")

    def _build_dialog_section(self, frame: ttk.Frame) -> None:
        ttk.Label(frame, text="Диалог", style="SettingsHeader.TLabel").grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 10))
        # ... (all dialog checkboxes with tooltips)
        # Row 1: enter_check
        # Row 2: lightrag_check
        # Row 3: game_guard_check
        # Row 4: auto_process_check
        # Row 5: web_search_check
        ttk.Separator(frame, orient="horizontal").grid(row=6, column=0, columnspan=3, sticky="ew", pady=(14, 12))

    def _build_obsidian_section(self, frame: ttk.Frame) -> None:
        ttk.Label(frame, text="Obsidian", style="SettingsHeader.TLabel").grid(row=7, column=0, columnspan=3, sticky="w", pady=(0, 8))
        # ... obsidian_entry, vault_entry, choose buttons

    def _build_color_section(self, frame: ttk.Frame) -> None:
        ttk.Label(frame, text="Цвет основной кнопки", style="SettingsHeader.TLabel").grid(row=12, column=0, columnspan=3, sticky="w", pady=(0, 10))
        # ... preset combobox, color preview, choose button

    def _build_automation_section(self, frame: ttk.Frame) -> None:
        ttk.Label(frame, text="Автоматизация", style="SettingsHeader.TLabel").grid(row=15, column=0, columnspan=3, sticky="w", pady=(0, 8))
        # ... auto_route_check, auto_create_check, auto_books_check, book_lookup_check

    def _build_buttons(self, frame: ttk.Frame) -> None:
        ttk.Label(frame, textvariable=self.app.settings_status_var, style="SettingsStatus.TLabel").grid(row=20, column=0, columnspan=3, sticky="w", pady=(14, 0))
        buttons = ttk.Frame(frame, style="App.TFrame")
        buttons.grid(row=21, column=0, columnspan=3, sticky="ew", pady=(16, 0))
        ttk.Button(buttons, text="Сбросить настройки", command=self.reset).grid(row=0, column=0, sticky="w")
        ttk.Button(buttons, text="Отмена", command=self.close).grid(row=0, column=1, padx=(0, 8))
        ttk.Button(buttons, text="Сохранить", command=self.save).grid(row=0, column=2)

    def save(self) -> None:
        """Save settings from dialog to app settings."""
        # ... (move save_settings_from_window logic here)

    def reset(self) -> None:
        """Reset settings to defaults."""
        # ... (move reset_settings_to_defaults logic here)

    def choose_obsidian_path(self) -> None:
        """Open file dialog for Obsidian path."""
        # ... (move choose_obsidian_path logic here)

    def choose_vault_path(self) -> None:
        """Open directory dialog for vault path."""
        # ... (move choose_vault_path logic here)

    def select_color_preset(self, name: str) -> None:
        """Apply a color preset."""
        # ... (move select_color_preset logic here)

    def update_color_preview(self) -> None:
        """Update the color preview label."""
        # ... (move update_color_preview logic here)

    def choose_button_color(self) -> None:
        """Open color chooser dialog."""
        # ... (move choose_button_color logic here)

    def apply_to_ui(self) -> None:
        """Apply current settings to the main UI."""
        # ... (move apply_settings_to_ui logic here)

    def update_button_colors(self, color: str | None = None) -> None:
        """Update all button colors."""
        # ... (move update_button_colors logic here)

    def update_web_search_button(self) -> None:
        """Update web search toggle button state."""
        # ... (move update_web_search_button logic here)
```

- [ ] **Step 2: Move method implementations from main.py to settings_dialog.py**

Move the body of each method from `KnowledgeChatApp` to `SettingsDialog`, replacing `self.` references to app state with `self.app.` references.

- [ ] **Step 3: Update main.py to use SettingsDialog**

Replace the extracted methods in `KnowledgeChatApp` with thin wrappers:

```python
def open_settings(self) -> None:
    self._settings_dialog.open()

def close_settings(self) -> None:
    self._settings_dialog.close()

# ... etc for all extracted methods
```

Add `self._settings_dialog = SettingsDialog(self)` to `__init__`.

- [ ] **Step 4: Write tests**

```python
# tests/test_settings_dialog.py
def test_settings_dialog_import():
    from knowledgelab.ui.settings_dialog import SettingsDialog
    assert SettingsDialog is not None
```

- [ ] **Step 5: Run tests and compile**

```powershell
python -m py_compile scripts/main.py
python -m pytest tests/ -v --tb=short
```

- [ ] **Step 6: Commit**

```bash
git add scripts/knowledgelab/ui/settings_dialog.py tests/test_settings_dialog.py scripts/main.py
git commit -m "refactor: extract settings dialog to ui/settings_dialog.py"
```

---

## Task 2: Extract Game Guard Warning UI

**Covers:** show_game_guard_warning, schedule_game_guard_probe, start_game_guard_probe, game_guard_worker

**Files:**
- Create: `scripts/knowledgelab/ui/game_guard_dialog.py`
- Modify: `scripts/main.py`
- Test: `tests/test_game_guard_dialog.py`

**Interfaces:**
- Consumes: `self.root`, `self.game_guard_warning_until`, `self.settings`, `self.append_warning_message()`, `collect_gpu_snapshot_standalone`, `is_gpu_snapshot_heavy_standalone`
- Produces: `GameGuardDialog` class with `show_warning()`, `schedule_probe()`, `start_probe()`, `worker()`

- [ ] **Step 1: Create game_guard_dialog.py**

```python
"""Game Guard warning dialog for GPU conflict detection."""
from __future__ import annotations

import time
import threading
import tkinter as tk
from tkinter import messagebox

from knowledgelab.llm.game_guard import collect_gpu_snapshot, is_gpu_snapshot_heavy


class GameGuardDialog:
    """Manages GPU monitoring and warning display."""

    def __init__(self, app: "KnowledgeChatApp") -> None:
        self.app = app
        self.warning_until: float = 0

    def show_warning(self, snapshot: dict) -> None:
        """Show GPU conflict warning if appropriate."""
        if time.time() < self.warning_until:
            return
        self.warning_until = time.time() + 30 * 60
        # ... (move show_game_guard_warning logic here)

    def schedule_probe(self) -> None:
        """Schedule GPU probe after chat opens."""
        # ... (move schedule_game_guard_probe logic here)

    def start_probe(self) -> None:
        """Start background GPU probe."""
        # ... (move start_game_guard_probe logic here)

    def worker(self) -> None:
        """Background worker for GPU snapshot."""
        # ... (move game_guard_worker logic here)
```

- [ ] **Step 2: Move implementations from main.py**

- [ ] **Step 3: Update main.py with thin wrappers**

- [ ] **Step 4: Write tests and run**

- [ ] **Step 5: Commit**

---

## Task 3: Extract Material Processing Workers

**Covers:** start_auto_material_processing, auto_process_youtube_worker, auto_process_article_worker, auto_process_codepen_worker, auto_process_book_image_worker, start_auto_book_image_processing, auto_process_video_worker, start_video_analysis_processing

**Files:**
- Create: `scripts/knowledgelab/material/workers.py`
- Modify: `scripts/main.py`
- Test: `tests/test_material_workers.py`

**Interfaces:**
- Consumes: `self.root`, `self.settings`, `self.start_background_task()`, `self.update_background_task()`, `self.append_assistant_message()`, `self.append_book_discovery_report()`, `self.append_video_analysis_report()`, all standalone functions from material/ and vision/ modules
- Produces: `MaterialWorkerManager` class with all worker methods

- [ ] **Step 1: Create material/workers.py**

```python
"""Background workers for material processing pipeline."""
from __future__ import annotations

import threading
from pathlib import Path

from knowledgelab.material.youtube import build_youtube_sync_command
from knowledgelab.material.web import fetch_article_material, fetch_article_markdown
from knowledgelab.material.codepen import fetch_codepen_snapshot
from knowledgelab.material.video import (
    extract_video_frames, call_video_frame_vision, write_video_analysis_note,
    video_source_id as video_source_id_util, video_runtime_dir,
)
from knowledgelab.vision.book_discovery import (
    lookup_book_catalog, enrich_detected_books, save_detected_book_notes,
    call_bookshelf_vision, find_existing_book_note,
)


class MaterialWorkerManager:
    """Coordinates background material processing workers."""

    def __init__(self, app: "KnowledgeChatApp") -> None:
        self.app = app

    def start_auto_material_processing(self, source_text: str, route: "KnowledgeRoute", rel_path: str) -> None:
        """Start background processing for saved material."""
        # ... (move implementation)

    def auto_process_youtube_worker(self, url: str, rel_path: str, scope: str, project: str, topic: str, layer: str) -> None:
        """Background YouTube transcript sync."""
        # ... (move implementation)

    def auto_process_article_worker(self, url: str, rel_path: str, scope: str, project: str, topic: str, layer: str) -> None:
        """Background article parsing."""
        # ... (move implementation)

    def auto_process_codepen_worker(self, url: str, rel_path: str, scope: str, project: str, topic: str, layer: str) -> None:
        """Background CodePen snapshot extraction."""
        # ... (move implementation)

    def auto_process_book_image_worker(self, image_path: str, rel_path: str, caption: str, route: "KnowledgeRoute") -> None:
        """Background book detection from image."""
        # ... (move implementation)

    def start_auto_book_image_processing(self, image_path: Path, rel_path: str, caption: str, route: "KnowledgeRoute") -> None:
        """Start background book image processing."""
        # ... (move implementation)

    def auto_process_video_worker(self, source_url: str, rel_path: str, scope: str, project: str, topic: str, layer: str) -> None:
        """Background video analysis."""
        # ... (move implementation)

    def start_video_analysis_processing(self, source_url: str, rel_path: str, scope: str, project: str, topic: str, layer: str) -> None:
        """Start background video analysis."""
        # ... (move implementation)
```

- [ ] **Step 2: Move implementations from main.py**

- [ ] **Step 3: Update main.py with thin wrappers**

- [ ] **Step 4: Write tests and run**

- [ ] **Step 5: Commit**

---

## Task 4: Extract Project Action Panel UI

**Covers:** append_project_action_panel, project_action_build, project_build_worker, finish_project_action, project_action_server, project_server_worker, finish_project_server_start, stop_project_server

**Files:**
- Create: `scripts/knowledgelab/ui/project_panel.py`
- Modify: `scripts/main.py`
- Test: `tests/test_project_panel.py`

**Interfaces:**
- Consumes: `self.root`, `self.project_actions_canvas`, `self.project_action_buttons`, `self.project_action_hover`, `self.project_action_active`, `self.settings`, `self.append_assistant_message()`, `self.append_warning_message()`, `self.start_background_task()`, `self.update_background_task()`, all project_actions standalone functions
- Produces: `ProjectActionPanel` class with all panel and worker methods

- [ ] **Step 1: Create ui/project_panel.py**

```python
"""Project action panel UI and workers."""
from __future__ import annotations

import threading
from pathlib import Path

from knowledgelab.tasks.project_actions import (
    load_project_actions, save_project_actions, get_project_action,
    create_project_action, update_project_action, add_project_action_notes,
    action_runtime_workspace, ensure_project_runtime_workspace,
    action_command_log_paths, run_project_command, is_process_running,
    find_free_port, is_path_within, copy_project_runtime_tree,
)
from knowledgelab.routing.project_stack import detect_project_stack


class ProjectActionPanel:
    """Manages project action panel UI and background workers."""

    def __init__(self, app: "KnowledgeChatApp") -> None:
        self.app = app

    def append_panel(self, note_rel: str, source_url: str = "") -> None:
        """Append project action buttons to chat."""
        # ... (move append_project_action_panel logic)

    def build_project(self, action_id: str) -> None:
        """Start project build."""
        # ... (move project_action_build logic)

    def build_worker(self, action_id: str, workspace: Path, install_cmd: str, build_cmd: str) -> None:
        """Background build worker."""
        # ... (move project_build_worker logic)

    def finish_build(self, action_id: str, success: bool, output: str) -> None:
        """Finish project build."""
        # ... (move finish_project_action logic)

    def start_server(self, action_id: str) -> None:
        """Start project dev server."""
        # ... (move project_action_server logic)

    def server_worker(self, action_id: str, workspace: Path, cmd: str) -> None:
        """Background server worker."""
        # ... (move project_server_worker logic)

    def finish_server_start(self, action_id: str, port: int) -> None:
        """Finish server start."""
        # ... (move finish_project_server_start logic)

    def stop_server(self, action_id: str) -> None:
        """Stop project server."""
        # ... (move stop_project_server logic)
```

- [ ] **Step 2: Move implementations from main.py**

- [ ] **Step 3: Update main.py with thin wrappers**

- [ ] **Step 4: Write tests and run**

- [ ] **Step 5: Commit**

---

## Task 5: Extract Capture Workflow

**Covers:** save_file_capture, save_folder_file_captures, save_folder_capture, save_image_capture, save_capture, save_reference_links, attach_folder, attach_images, attach_files, attach_github_repository, process_github_repository, handle_dropped_files, process_attached_files

**Files:**
- Create: `scripts/knowledgelab/vault/capture_workflow.py`
- Modify: `scripts/main.py`
- Test: `tests/test_capture_workflow.py`

**Interfaces:**
- Consumes: `self.root`, `self.settings`, `self.selected_route()`, `self.choose_capture_context()`, `self.choose_attachment_source()`, `self.classify_material_topic()`, `self.ensure_topic_exists()`, `self.note_metadata()`, `self.append_assistant_message()`, `self.append_warning_message()`, `self.append_material_routing_report()`, `self.start_auto_material_processing()`, all standalone functions from vault/capture.py, material/queue.py, material/web.py, material/github.py, material/codepen.py
- Produces: `CaptureWorkflow` class with all capture and attachment methods

- [ ] **Step 1: Create vault/capture_workflow.py**

```python
"""File capture and attachment workflow."""
from __future__ import annotations

from pathlib import Path
from tkinter import filedialog

from knowledgelab.config import VAULT_DIR, ROOT
from knowledgelab.models import KnowledgeRoute, MaterialRoutingReport
from knowledgelab.vault.capture import (
    unique_path, capture_destination, render_capture_markdown,
    render_image_capture_markdown, render_file_capture_markdown,
    render_folder_capture_markdown, render_github_capture_markdown,
    render_reference_link_markdown, classify_source_file, extraction_label,
    file_kind_label, title_from_text, github_user_hint,
    project_title_from_source_hint,
)
from knowledgelab.material.queue import queue_file_item, queue_github_item, queue_rlm_item


class CaptureWorkflow:
    """Manages file capture, attachment, and intake workflows."""

    def __init__(self, app: "KnowledgeChatApp") -> None:
        self.app = app

    def save_file_capture(self, file_path: Path, caption: str, route: KnowledgeRoute,
                          source_root: Path | None = None, project_action_id: str = "") -> tuple[str, str, str]:
        """Save a single file as a capture note."""
        # ... (move save_file_capture logic)

    def save_folder_file_captures(self, folder_path: Path, caption: str, route: KnowledgeRoute,
                                   project_action_id: str = "") -> tuple[list[tuple[str, str, str, Path]], bool]:
        """Save all files in a folder as capture notes."""
        # ... (move save_folder_file_captures logic)

    def save_folder_capture(self, folder_path: Path, caption: str, route: KnowledgeRoute) -> tuple[str, str, str]:
        """Save a folder as a capture note."""
        # ... (move save_folder_capture logic)

    def save_image_capture(self, file_path: Path, caption: str, route: KnowledgeRoute) -> tuple[str, str, str]:
        """Save an image as a capture note."""
        # ... (move save_image_capture logic)

    def save_capture(self, text: str, route: KnowledgeRoute) -> str:
        """Save text/URL as a capture note."""
        # ... (move save_capture logic)

    def save_reference_links(self, parent_rel: str, links: list[dict], route: KnowledgeRoute) -> list[str]:
        """Save extracted reference links as notes."""
        # ... (move save_reference_links logic)

    def attach_folder(self) -> None:
        """Attach a folder from file dialog."""
        # ... (move attach_folder logic)

    def attach_images(self) -> None:
        """Attach images from file dialog."""
        # ... (move attach_images logic)

    def attach_files(self) -> None:
        """Attach files from file dialog."""
        # ... (move attach_files logic)

    def attach_github_repository(self) -> None:
        """Attach a GitHub repository."""
        # ... (move attach_github_repository logic)

    def process_github_repository(self, url: str, caption: str = "") -> str:
        """Process a GitHub repository URL."""
        # ... (move process_github_repository logic)

    def handle_dropped_files(self, files: list[str]) -> None:
        """Handle files dropped onto the chat window."""
        # ... (move handle_dropped_files logic)

    def process_attached_files(self, file_paths: list[str], source_title: str = "") -> None:
        """Process a list of attached files."""
        # ... (move process_attached_files logic)
```

- [ ] **Step 2: Move implementations from main.py**

- [ ] **Step 3: Update main.py with thin wrappers**

- [ ] **Step 4: Write tests and run**

- [ ] **Step 5: Commit**

---

## Task 6: Extract Chat List Management

**Covers:** populate_chat_list, add_chat_sidebar_row, on_chat_select, select_chat, begin_inline_rename, finish_inline_rename, on_inline_rename_global_click

**Files:**
- Create: `scripts/knowledgelab/ui/chat_list.py`
- Modify: `scripts/main.py`
- Test: `tests/test_chat_list.py`

**Interfaces:**
- Consumes: `self.root`, `self.chat_list_frame`, `self.chat_list_canvas`, `self.chat_rows`, `self.chat_row_map`, `self.chat_row_menu_map`, `self.chat_rename_entry`, `self.get_chats()`, `self.get_active_chat()`, `self.rename_chat()`, `self.delete_chat()`, `self.select_chat()`
- Produces: `ChatListManager` class with list management methods

- [ ] **Step 1: Create ui/chat_list.py**

```python
"""Chat list sidebar management."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from knowledgelab.ui.chat_store import title_for_chat, format_chat_age, chat_group_by_context


class ChatListManager:
    """Manages the chat list sidebar UI."""

    def __init__(self, app: "KnowledgeChatApp") -> None:
        self.app = app
        self.rows: dict[str, tk.Frame] = {}
        self.row_map: dict[tk.Frame, str] = {}
        self.row_menu_map: dict[str, tk.Menu] = {}
        self.rename_entry: tk.Entry | None = None

    def populate(self) -> None:
        """Rebuild the chat list from store."""
        # ... (move populate_chat_list logic)

    def add_row(self, chat: dict, index: int = -1) -> tk.Frame:
        """Add a single chat row to the sidebar."""
        # ... (move add_chat_sidebar_row logic)

    def on_select(self, chat_id: str) -> None:
        """Handle chat selection."""
        # ... (move on_chat_select logic)

    def select_chat(self, chat_id: str) -> None:
        """Select a chat by ID."""
        # ... (move select_chat logic)

    def begin_rename(self, chat_id: str) -> None:
        """Start inline rename for a chat."""
        # ... (move begin_inline_rename logic)

    def finish_rename(self, save: bool = True) -> None:
        """Finish inline rename."""
        # ... (move finish_inline_rename logic)

    def on_global_click(self, event: tk.Event) -> None:
        """Handle global click to finish rename."""
        # ... (move on_inline_rename_global_click logic)
```

- [ ] **Step 2: Move implementations from main.py**

- [ ] **Step 3: Update main.py with thin wrappers**

- [ ] **Step 4: Write tests and run**

- [ ] **Step 5: Commit**

---

## Task 7: Extract DnD Handling

**Covers:** install_native_file_drop, update_dnd_diagnostics, parse_dnd_files, on_dnd_enter, on_dnd_position, on_dnd_leave, on_dnd_drop, set_drop_highlight, stop_drop_pulse, animate_drop_pulse

**Files:**
- Create: `scripts/knowledgelab/ui/dnd.py`
- Modify: `scripts/main.py`
- Test: `tests/test_dnd.py`

**Interfaces:**
- Consumes: `self.root`, `self.chat_history_canvas`, `self.drop_highlight_active`, `self.drop_pulse_after`, `self.handle_dropped_files()`, `explorer_dnd_enabled()`
- Produces: `DnDManager` class with all drag-and-drop methods

- [ ] **Step 1: Create ui/dnd.py**

```python
"""Drag-and-drop handling for chat window."""
from __future__ import annotations

import tkinter as tk

from knowledgelab.utils.paths import explorer_dnd_enabled


class DnDManager:
    """Manages drag-and-drop for the chat window."""

    def __init__(self, app: "KnowledgeChatApp") -> None:
        self.app = app
        self.highlight_active = False
        self.pulse_after: str | None = None

    def install(self) -> None:
        """Install native file drop support."""
        # ... (move install_native_file_drop logic)

    def update_diagnostics(self) -> None:
        """Update DnD diagnostic display."""
        # ... (move update_dnd_diagnostics logic)

    def parse_files(self, data: str) -> list[str]:
        """Parse dropped file paths."""
        # ... (move parse_dnd_files logic)

    def on_enter(self, event: tk.Event) -> None:
        """Handle drag enter."""
        # ... (move on_dnd_enter logic)

    def on_position(self, event: tk.Event) -> None:
        """Handle drag position."""
        # ... (move on_dnd_position logic)

    def on_leave(self, event: tk.Event) -> None:
        """Handle drag leave."""
        # ... (move on_dnd_leave logic)

    def on_drop(self, event: tk.Event) -> None:
        """Handle file drop."""
        # ... (move on_dnd_drop logic)

    def set_highlight(self, active: bool) -> None:
        """Set drop highlight state."""
        # ... (move set_drop_highlight logic)

    def stop_pulse(self) -> None:
        """Stop drop pulse animation."""
        # ... (move stop_drop_pulse logic)

    def animate_pulse(self) -> None:
        """Animate drop pulse."""
        # ... (move animate_drop_pulse logic)
```

- [ ] **Step 2: Move implementations from main.py**

- [ ] **Step 3: Update main.py with thin wrappers**

- [ ] **Step 4: Write tests and run**

- [ ] **Step 5: Commit**

---

## Task 8: Extract Query Workflow

**Covers:** run_plain_query, run_query, finish_query, set_active_process, cancel_busy_timer, schedule_busy_timer, begin_operation, is_active_operation, force_unlock_timeout, cancel_active_operation, set_busy, start_status_animation, stop_status_animation, animate_status

**Files:**
- Create: `scripts/knowledgelab/llm/query_workflow.py`
- Modify: `scripts/main.py`
- Test: `tests/test_query_workflow.py`

**Interfaces:**
- Consumes: `self.root`, `self.busy`, `self.active_operation_id`, `self.active_process`, `self.busy_timer_after`, `self.status_animation_after`, `self.status_var`, `self.send_button`, `self.append_assistant_message()`, `self.append_warning_message()`, `self.set_chat_text()`, `self.runtime_context_prompt()`, `self.check_lmstudio_ready()`, `self.call_plain_lmstudio()`, all standalone functions from llm/ and material/ modules
- Produces: `QueryWorkflow` class with query execution and busy state management

- [ ] **Step 1: Create llm/query_workflow.py**

```python
"""Query execution workflow and busy state management."""
from __future__ import annotations

import re
import time
import threading
import tkinter as tk

from knowledgelab.llm.lmstudio import call_plain_lmstudio
from knowledgelab.material.queue import run_background_material_command, launch_reindex


class QueryWorkflow:
    """Manages query execution and busy state."""

    def __init__(self, app: "KnowledgeChatApp") -> None:
        self.app = app
        self.busy = False
        self.active_operation_id: str = ""
        self.active_process = None
        self.busy_timer_after: str | None = None
        self.status_animation_after: str | None = None
        self.query_timeout_seconds = 120

    def run_plain_query(self, operation_id: str, question: str, prompt: str,
                        context_name: str, scope: str, project: str, layer: str,
                        use_lightrag: bool, warnings: list[str],
                        web_search_enabled: bool, original_question: str) -> None:
        """Run a plain LM Studio query."""
        # ... (move run_plain_query logic)

    def run_query(self, operation_id: str, question: str, prompt: str,
                  context_name: str, scope: str, project: str, layer: str,
                  use_lightrag: bool, warnings: list[str],
                  web_search_enabled: bool, original_question: str) -> None:
        """Run a LightRAG query."""
        # ... (move run_query logic)

    def finish_query(self, operation_id: str, answer: str, context_name: str,
                     warnings: list[str], lightrag_used: bool) -> None:
        """Finish query and display result."""
        # ... (move finish_query logic)

    def set_active_process(self, process) -> None:
        """Set the active subprocess."""
        # ... (move set_active_process logic)

    def cancel_busy_timer(self) -> None:
        """Cancel the busy timeout timer."""
        # ... (move cancel_busy_timer logic)

    def schedule_busy_timer(self, operation_id: str, timeout: float) -> None:
        """Schedule busy timeout."""
        # ... (move schedule_busy_timer logic)

    def begin_operation(self, label: str, timeout: float) -> str:
        """Begin a new operation."""
        # ... (move begin_operation logic)

    def is_active_operation(self, operation_id: str) -> bool:
        """Check if operation is still active."""
        # ... (move is_active_operation logic)

    def force_unlock_timeout(self) -> None:
        """Force unlock busy state on timeout."""
        # ... (move force_unlock_timeout logic)

    def cancel_active_operation(self) -> None:
        """Cancel the active operation."""
        # ... (move cancel_active_operation logic)

    def set_busy(self, busy: bool) -> None:
        """Set busy state."""
        # ... (move set_busy logic)

    def start_status_animation(self) -> None:
        """Start status bar animation."""
        # ... (move start_status_animation logic)

    def stop_status_animation(self) -> None:
        """Stop status bar animation."""
        # ... (move stop_status_animation logic)

    def animate_status(self) -> None:
        """Animate status bar dots."""
        # ... (move animate_status logic)
```

- [ ] **Step 2: Move implementations from main.py**

- [ ] **Step 3: Update main.py with thin wrappers**

- [ ] **Step 4: Write tests and run**

- [ ] **Step 5: Commit**

---

## Task 9: Extract Health Probe

**Covers:** schedule_health_probe, start_health_probe, health_worker, finish_health_probe, diagnose_system

**Files:**
- Create: `scripts/knowledgelab/ui/health_probe.py`
- Modify: `scripts/main.py`
- Test: `tests/test_health_probe.py`

**Interfaces:**
- Consumes: `self.root`, `self.settings`, `self.health_probe_after`, `self.is_lmstudio_api_online()`, `self.lmstudio_base_url()`, `diagnose_system_standalone`
- Produces: `HealthProbe` class with probe methods

- [ ] **Step 1: Create ui/health_probe.py**

```python
"""Health probe for LM Studio and LightRAG status."""
from __future__ import annotations

import threading
import tkinter as tk

from knowledgelab.llm.diagnostics import diagnose_system


class HealthProbe:
    """Manages health status probing."""

    def __init__(self, app: "KnowledgeChatApp") -> None:
        self.app = app
        self.probe_after: str | None = None

    def schedule(self, delay_ms: int = 5000) -> None:
        """Schedule health probe."""
        # ... (move schedule_health_probe logic)

    def start(self) -> None:
        """Start background health probe."""
        # ... (move start_health_probe logic)

    def worker(self) -> None:
        """Background health check worker."""
        # ... (move health_worker logic)

    def finish(self, result: dict) -> None:
        """Finish health probe and display results."""
        # ... (move finish_health_probe logic)

    def diagnose(self) -> dict:
        """Run system diagnostics."""
        # ... (move diagnose_system logic)
```

- [ ] **Step 2: Move implementations from main.py**

- [ ] **Step 3: Update main.py with thin wrappers**

- [ ] **Step 4: Write tests and run**

- [ ] **Step 5: Commit**

---

## Task 10: Remove Thin Wrappers and Update Documentation

**Covers:** Cleanup of remaining thin wrappers, update ARCHITECTURE.md and NEXT_CHAT_HANDOFF_KNOWLEDGELAB.md

**Files:**
- Modify: `scripts/main.py` (remove unused imports, clean up)
- Modify: `ARCHITECTURE.md`
- Modify: `NEXT_CHAT_HANDOFF_KNOWLEDGELAB.md`

- [ ] **Step 1: Remove unused imports from main.py**

After all extractions, many imports at the top of main.py are no longer needed. Remove them.

- [ ] **Step 2: Count final line count and method count**

```python
python -c "
import re
content = open('scripts/main.py', 'r', encoding='utf-8').read()
lines = content.split('\n')
print(f'Total lines: {len(lines)}')
class_start = None
for i, line in enumerate(lines):
    if re.match(r'^class KnowledgeChatApp', line):
        class_start = i + 1
        break
methods = [m for m in lines[class_start-1:] if re.match(r'^    def \w+\(', m)]
print(f'Methods in KnowledgeChatApp: {len(methods)}')
"
```

- [ ] **Step 3: Update ARCHITECTURE.md with new module list**

- [ ] **Step 4: Update NEXT_CHAT_HANDOFF_KNOWLEDGELAB.md with current status**

- [ ] **Step 5: Run full test suite**

```powershell
python -m py_compile scripts/main.py
python -m pytest tests/ -v
```

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "refactor: complete phase 4 extraction - main.py reduced to ~2500 lines"
```

---

## Summary

After completing all 10 tasks:

| Metric | Before | After |
|--------|--------|-------|
| main.py lines | 4,423 | ~2,500 |
| KnowledgeChatApp methods | 232 | ~68 |
| knowledgelab modules | 32 | 40+ |
| Tests | 390 | 420+ |

**New modules created:**
1. `ui/settings_dialog.py` — Settings dialog UI
2. `ui/game_guard_dialog.py` — GPU conflict warning
3. `material/workers.py` — Background material processing
4. `ui/project_panel.py` — Project action panel
5. `vault/capture_workflow.py` — File capture and attachment
6. `ui/chat_list.py` — Chat list sidebar
7. `ui/dnd.py` — Drag-and-drop handling
8. `llm/query_workflow.py` — Query execution and busy state
9. `ui/health_probe.py` — Health status probing

**Remaining in main.py (~68 methods):**
- `__init__` — App initialization
- `build_ui` — Main UI construction
- `configure_styles` — ttk style setup
- `on_send` — Core send handler
- `render_current_chat` — Chat rendering
- `show_intro` — Intro screen
- `clear_chat_window` — Window clearing
- Input handling methods
- Voice input methods
- LightRAG toggle methods
- Route selection methods
- Chat text methods (append, append_user_message, etc.)
- Icon loading methods
- Canvas drawing methods
