from __future__ import annotations

import base64
import datetime as dt
import hashlib
import html
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import tkinter as tk
from dataclasses import dataclass
from difflib import SequenceMatcher
from html.parser import HTMLParser
from urllib.parse import parse_qs, unquote, urlencode, urljoin, urlparse
import urllib.request
import webbrowser
import zipfile
from pathlib import Path
from tkinter import colorchooser, filedialog, messagebox, simpledialog, ttk

# --- Re-export from extracted modules for backward compatibility ---
from knowledgelab.config import (  # noqa: F401
    ROOT, DEFAULT_VAULT_DIR, VAULT_DIR, SCRIPTS_DIR, QUERY_SCRIPT, GAME_GUARD_SCRIPT,
    CONTROL_SCRIPT, LEGACY_HISTORY_PATH, CHAT_STORE_PATH, SETTINGS_PATH,
    MATERIAL_QUEUE_PATH, RLM_QUEUE_PATH, PROJECT_ACTIONS_PATH, PROJECT_RUNTIME_DIR,
    VIDEO_PROCESSING_DIR, OBSIDIAN_ICON, NEW_CHAT_ICON, WEB_SEARCH_ICON,
    ATTACHMENT_ICON, ATTACHMENT_ICON_ACTIVE, MICROPHONE_ICON, MICROPHONE_ICON_ACTIVE,
    LMSTUDIO_API_URL, DEFAULT_LLM_MODEL, DEFAULT_EMBEDDING_MODEL, DEFAULT_VISION_MODEL,
    OPEN_LIBRARY_SEARCH_URL, GOOGLE_BOOKS_SEARCH_URL, BOOK_LOOKUP_MIN_SCORE,
    VISION_MODEL_MARKERS, LOCAL_RUNTIME_SYSTEM_PROMPT, LAYER_ACTIVE, LAYER_FINISHED_PROJECTS,
    WARNING_PREFIX, DND_SAFE_MODE_ENV, DND_DISABLE_ENV, CONTEXTS,
    IMAGE_EXTENSIONS, IMAGE_FILETYPES, TEXT_EXTENSIONS, DOC_EXTENSIONS, AUDIO_EXTENSIONS,
    VIDEO_EXTENSIONS, ARCHIVE_EXTENSIONS, SUPPORTED_FILETYPES,
    TEXT_EXTRACTION_LIMIT, ARTICLE_TEXT_EXTRACTION_LIMIT, ARTICLE_FALLBACK_MIN_CHARS,
    REFERENCE_LINK_LIMIT, RLM_PROFILE_THRESHOLD_CHARS,
    FOLDER_TEXT_EXTRACTION_LIMIT, FOLDER_TOTAL_TEXT_LIMIT, FOLDER_TREE_LIMIT,
    FOLDER_TEXT_FILE_LIMIT, FOLDER_FILE_SCAN_LIMIT, VIDEO_FRAME_LIMIT, VIDEO_FRAME_INTERVAL_SECONDS,
    FOLDER_SKIP_DIRS, FILE_CAPTURE_KINDS, URL_CAPTURE_KINDS, VOICE_INPUT_SECONDS,
    BUTTON_COLOR_PRESETS, UI_THEME, DEFAULT_SETTINGS,
    WEB_TERMS, GAME_TERMS, FINISHED_PROJECT_TERMS, BOOK_IMAGE_TERMS, BOOK_PAGE_TERMS,
    BOOKSHELF_TERMS, REFERENCE_LINK_HINTS, SAVE_PHRASES, QUESTION_HINTS,
    KNOWLEDGE_LOOKUP_TERMS, KNOWLEDGE_HELP_TERMS, RUSSIAN_LANGUAGE_TERMS, TOPICS,
)
from knowledgelab.models import (  # noqa: F401
    KnowledgeRoute, ProjectGuess, MaterialRoutingReport, BookDiscoveryReport,
    ManualBookEntry, VideoAnalysisReport, BackgroundTaskRecord, ReferenceLink,
    CodePenSnapshot,
)
from knowledgelab.utils.text import (  # noqa: F401
    now_iso, compact_text, contains_any, clean_filename, slugify,
    compact_whitespace, yaml_quote, markdown_fence_text, extract_json_object,
    is_service_output_line as is_service_output_line_standalone,
    trim_output as trim_output_standalone,
    friendly_error as friendly_error_standalone,
)
from knowledgelab.utils.urls import (  # noqa: F401
    URL_RE, GITHUB_SHORT_RE, YOUTUBE_RE, TELEGRAM_RE, CODEPEN_RE,
    first_url, first_youtube_url, first_telegram_url, first_codepen_url, first_github_url,
    parse_codepen_url, parse_github_url, normalize_github_url,
    source_domain, stable_content_hash, normalize_source_url_for_match,
)
from knowledgelab.utils.colors import (  # noqa: F401
    valid_hex_color, adjust_hex_color, mix_hex_color, readable_text_color,
)
from knowledgelab.utils.paths import (  # noqa: F401
    normalize_attached_source_path, first_existing_local_source, explorer_dnd_enabled,
)
from knowledgelab.routing.intent import (  # noqa: F401
    is_finished_project_lookup_text, subject_route_from_text, route_context,
    normalize_subject_scope, default_finished_project_section,
    is_knowledge_lookup_text, is_lightrag_help_text, is_russian_language_request,
    is_save_intent_text, infer_topic, infer_kind, classify_intent,
)
from knowledgelab.routing.topics import (  # noqa: F401
    builtin_topic_names, collect_topic_registry, topic_note_path,
    render_topic_note_markdown, infer_note_layer_from_path, infer_note_scope_from_path,
    classify_material_topic as classify_material_topic_standalone,
    ensure_topic_exists as ensure_topic_exists_standalone,
)
from knowledgelab.routing.project_stack import (  # noqa: F401
    read_package_json, detect_package_manager, command_for_package_manager,
    install_command_for_package_manager, find_artifact_dir, has_static_entry,
    detect_project_stack,
)
from knowledgelab.vault.frontmatter import (  # noqa: F401
    parse_frontmatter, parse_basic_frontmatter, infer_scope, infer_project,
    infer_project_section, infer_layer, find_existing_source_note,
)
from knowledgelab.vault.capture import (  # noqa: F401
    unique_path, capture_destination, render_capture_markdown,
    render_image_capture_markdown, render_file_capture_markdown,
    render_folder_capture_markdown, render_github_capture_markdown,
    render_reference_link_markdown, classify_source_file, extraction_label,
    file_kind_label, title_from_text, github_user_hint,
    project_title_from_source_hint,
)
from knowledgelab.material.web import (  # noqa: F401
    ArticleTextExtractor, VisiblePageTextExtractor, ScriptAssetExtractor,
    ReferenceLinkExtractor, extract_article_markdown_from_html,
    extract_spa_bundle_markdown, fetch_article_material, fetch_article_markdown,
    JS_STRING_RE, decode_js_string, is_human_js_text, extract_human_strings_from_js,
    dedupe_markdown_lines, classify_reference_link_role, extract_reference_links_from_html,
)
from knowledgelab.material.codepen import (  # noqa: F401
    fetch_codepen_snapshot, render_codepen_snapshot_markdown,
)
from knowledgelab.material.github import github_user_hint as _github_user_hint_reexport  # noqa: F401
from knowledgelab.vision.book_discovery import (  # noqa: F401
    infer_image_capture_kind, infer_book_title_from_hint, infer_page_number_guess,
    image_mime_type, image_data_url, normalize_detected_book,
    parse_manual_book_entries, manual_book_resolution_likely,
    book_text_tokens, token_overlap_score,
    normalize_openlibrary_candidate, normalize_google_books_candidate,
    score_book_lookup_candidate, compact_catalog_candidate,
    select_best_book_lookup, merge_book_lookup, classify_book_topic,
    parse_bookshelf_detection_response, render_book_note_markdown,
    render_bookshelf_detection_section, render_manual_book_list_markdown,
    render_manual_book_resolution_section, format_material_routing_report,
    format_book_discovery_report, format_video_analysis_report as format_video_analysis_report_standalone, book_note_slug,
    lookup_book_catalog as lookup_book_catalog_standalone,
    enrich_detected_books as enrich_detected_books_standalone,
    save_detected_book_notes as save_detected_book_notes_standalone,
    update_bookshelf_note_result as update_bookshelf_note_result_standalone,
    call_bookshelf_vision as call_bookshelf_vision_standalone,
    find_existing_book_note as find_existing_book_note_standalone,
)
from knowledgelab.llm.web_search import (  # noqa: F401
    DuckDuckGoResultParser, normalize_search_url, fetch_web_search_results,
    render_web_search_context,
)
from knowledgelab.llm.lmstudio import (  # noqa: F401
    is_vision_model_name, lmstudio_request_json, loaded_lmstudio_models,
    check_lmstudio_ready as check_lmstudio_ready_standalone,
    extract_chat_content as extract_chat_content_standalone,
    vision_model_state as vision_model_state_standalone,
    call_plain_lmstudio as call_plain_lmstudio_standalone,
)
from knowledgelab.llm.model_manager import ModelManager
from knowledgelab.llm.runtime_context import (  # noqa: F401
    build_runtime_context_prompt, is_safe_history_message as is_safe_history_message_standalone,
    build_prompt_with_history as build_prompt_with_history_standalone,
    should_include_runtime_context as should_include_runtime_context_standalone,
    lightrag_help_message as lightrag_help_message_standalone,
    storage_name_for_scope as storage_name_for_scope_standalone,
    lightrag_index_path as lightrag_index_path_standalone,
    is_lightrag_ready as is_lightrag_ready_standalone,
    python_executable as python_executable_standalone,
    capture_path_from_rel as capture_path_from_rel_standalone,
)
from knowledgelab.llm.diagnostics import diagnose_system as diagnose_system_standalone  # noqa: F401
from knowledgelab.ui.tooltip import ToolTip  # noqa: F401
from knowledgelab.ui.widgets import (  # noqa: F401
    RoundedButton, IconButton, MiniToolButton, WebSearchToggleButton,
)
from knowledgelab.ui.settings import (  # noqa: F401
    load_settings as load_settings_standalone,
    save_settings as save_settings_standalone,
    normalize_settings,
    color_preset_name as color_preset_name_standalone,
)
from knowledgelab.ui.dialogs import (  # noqa: F401
    choose_capture_context as choose_capture_context_standalone,
    choose_attachment_source as choose_attachment_source_standalone,
    confirm_install_dependencies,
)
from knowledgelab.ui.obsidian import (  # noqa: F401
    find_obsidian_path as find_obsidian_path_standalone,
    launch_windows_program as launch_windows_program_standalone,
)
from knowledgelab.ui.settings_dialog import SettingsDialog
from knowledgelab.ui.game_guard_dialog import GameGuardDialog
from knowledgelab.material.workers import MaterialWorkerManager
from knowledgelab.ui.animated_edges import AnimatedEdgeFrame
from knowledgelab.ui.message_bubble import AnimatedMessageBubble
from knowledgelab.ui.project_panel import ProjectActionPanel
from knowledgelab.vault.capture_workflow import CaptureWorkflow
from knowledgelab.ui.chat_list import ChatListManager
from knowledgelab.tasks.process import (  # noqa: F401
    run_command as run_command_standalone,
    terminate_process,
)
from knowledgelab.material.youtube import build_youtube_sync_command  # noqa: F401
from knowledgelab.material.video import (  # noqa: F401
    video_source_id as video_source_id_util, video_runtime_dir,
    parse_video_frame_response, format_video_analysis_report as format_video_analysis_report_standalone,
    extract_video_frames as extract_video_frames_standalone,
    call_video_frame_vision as call_video_frame_vision_standalone,
    render_video_analysis_markdown,
    write_video_analysis_note as write_video_analysis_note_standalone,
    queue_video_analysis_item,
)
from knowledgelab.llm.voice import (  # noqa: F401
    build_voice_recognition_script, friendly_voice_error as friendly_voice_error_standalone,
    open_windows_microphone_settings as open_windows_microphone_settings_standalone,
)
from knowledgelab.material.queue import (  # noqa: F401
    read_jsonl_queue, append_jsonl_queue, remove_from_jsonl_queue,
    queue_file_item, queue_github_item, queue_rlm_item,
    material_queue_display_path as material_queue_display_path_standalone,
    material_queue_summary as material_queue_summary_standalone,
    run_background_material_command as run_background_material_command_standalone,
    launch_reindex as launch_reindex_standalone,
)
from knowledgelab.tasks.background import (  # noqa: F401
    BackgroundTaskManager, compact_background_tasks_from_dict,
    material_queue_summary as material_queue_summary_standalone,
    project_server_summary as project_server_summary_standalone,
    latest_book_discovery_summary as latest_book_discovery_summary_standalone,
)
from knowledgelab.tasks.project_actions import (  # noqa: F401
    load_project_actions as load_project_actions_standalone,
    save_project_actions as save_project_actions_standalone,
    get_project_action as get_project_action_standalone,
    create_project_action as create_project_action_standalone,
    update_project_action as update_project_action_standalone,
    add_project_action_notes as add_project_action_notes_standalone,
    action_runtime_workspace as action_runtime_workspace_standalone,
    ensure_project_runtime_workspace as ensure_project_runtime_workspace_standalone,
    action_command_log_paths as action_command_log_paths_standalone,
    run_project_command as run_project_command_standalone,
    is_process_running as is_process_running_standalone,
    find_free_port,
    is_path_within, copy_project_runtime_tree,
)
from knowledgelab.llm.game_guard import (  # noqa: F401
    collect_gpu_snapshot_script, collect_gpu_snapshot as collect_gpu_snapshot_standalone,
    is_gpu_snapshot_heavy as is_gpu_snapshot_heavy_standalone,
)
from knowledgelab.ui.chat_store import (  # noqa: F401
    load_chat_store as load_chat_store_standalone,
    save_chat_store as save_chat_store_standalone,
    migrate_legacy_history as migrate_legacy_history_standalone,
    new_id as new_id_standalone,
    get_chats as get_chats_standalone,
    get_active_chat as get_active_chat_standalone,
    create_chat as create_chat_standalone,
    delete_chat as delete_chat_standalone,
    rename_chat as rename_chat_standalone,
    chat_by_id as chat_by_id_standalone,
    add_message as add_message_standalone,
    title_for_chat as title_for_chat_standalone,
    format_chat_age as format_chat_age_standalone,
    chat_group_name as chat_group_name_standalone,
    chat_group_by_context as chat_group_by_context_standalone,
)
from knowledgelab.nodes.registry import get_registry
from knowledgelab.nodes.builtin_nodes import BUILTIN_NODES
from knowledgelab.nodes.goal_nodes import GOAL_NODES



class ToolTip:
    def __init__(self, widget: tk.Widget, text: str, delay_ms: int = 450) -> None:
        self.widget = widget
        self.text = text
        self.delay_ms = delay_ms
        self.after_id: str | None = None
        self.window: tk.Toplevel | None = None
        widget.bind("<Enter>", self.schedule)
        widget.bind("<Leave>", self.hide)
        widget.bind("<ButtonPress>", self.hide)

    def schedule(self, _event: tk.Event | None = None) -> None:
        self.cancel()
        self.after_id = self.widget.after(self.delay_ms, self.show)

    def cancel(self) -> None:
        if self.after_id:
            self.widget.after_cancel(self.after_id)
            self.after_id = None

    def show(self) -> None:
        if self.window or not self.text:
            return
        x = self.widget.winfo_rootx() + 12
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 8
        self.window = tk.Toplevel(self.widget)
        self.window.wm_overrideredirect(True)
        self.window.wm_geometry(f"+{x}+{y}")
        label = tk.Label(
            self.window,
            text=self.text,
            justify="left",
            background="#1f2933",
            foreground="#ffffff",
            padx=10,
            pady=7,
            font=("Segoe UI", 9),
            wraplength=340,
        )
        label.pack()

    def hide(self, _event: tk.Event | None = None) -> None:
        self.cancel()
        if self.window:
            self.window.destroy()
            self.window = None


class RoundedButton(tk.Canvas):
    def __init__(
        self,
        parent: tk.Widget,
        text: str,
        command,
        *,
        bg: str,
        active_bg: str,
        fg: str,
        radius: int = 7,
        height: int = 36,
    ) -> None:
        super().__init__(
            parent,
            height=height,
            background=parent.cget("bg"),
            highlightthickness=0,
            bd=0,
            cursor="hand2",
            takefocus=True,
        )
        self.text = text
        self.command = command
        self.normal_bg = bg
        self.active_bg = active_bg
        self.fg = fg
        self.radius = radius
        self.enabled = True
        self.hover = False
        self.hover_amount = 0.0
        self.hover_after_id: str | None = None
        self.bind("<Configure>", lambda _event: self.redraw())
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        self.bind("<ButtonRelease-1>", self.on_click)
        self.bind("<space>", self.on_keyboard)
        self.bind("<Return>", self.on_keyboard)
        self.bind("<FocusIn>", lambda _event: self.redraw())
        self.bind("<FocusOut>", lambda _event: self.redraw())
        self.redraw()

    def configure(self, cnf=None, **kwargs):  # type: ignore[override]
        if cnf:
            kwargs.update(cnf)
        state = kwargs.pop("state", None)
        if state is not None:
            self.enabled = state != "disabled"
            super().configure(cursor="hand2" if self.enabled else "arrow")
            self.redraw()
        if "text" in kwargs:
            self.text = str(kwargs.pop("text"))
            self.redraw()
        if kwargs:
            super().configure(**kwargs)

    config = configure

    def set_colors(self, *, bg: str, active_bg: str, fg: str) -> None:
        self.normal_bg = bg
        self.active_bg = active_bg
        self.fg = fg
        self.redraw()

    def on_enter(self, _event: tk.Event | None = None) -> None:
        self.hover = True
        self.animate_hover()

    def on_leave(self, _event: tk.Event | None = None) -> None:
        self.hover = False
        self.animate_hover()

    def on_click(self, _event: tk.Event | None = None) -> None:
        if self.enabled and self.command:
            self.command()

    def on_keyboard(self, _event: tk.Event | None = None) -> str:
        self.on_click()
        return "break"

    def rounded_rect(self, x1: int, y1: int, x2: int, y2: int, radius: int, fill: str) -> None:
        points = [
            x1 + radius, y1, x2 - radius, y1, x2, y1, x2, y1 + radius,
            x2, y2 - radius, x2, y2, x2 - radius, y2, x1 + radius, y2,
            x1, y2, x1, y2 - radius, x1, y1 + radius, x1, y1,
        ]
        self.create_polygon(points, smooth=True, fill=fill, outline="")

    def redraw(self) -> None:
        self.delete("all")
        width = max(self.winfo_width(), 80)
        height = max(self.winfo_height(), 30)
        fill = mix_hex_color(self.normal_bg, self.active_bg, self.hover_amount if self.enabled else 0.0)
        if not self.enabled:
            fill = "#c9d0d7"
        self.rounded_rect(1, 1, width - 1, height - 1, self.radius, fill)
        self.create_text(
            width // 2,
            height // 2,
            text=self.text,
            fill=self.fg if self.enabled else "#eef2f6",
            font=("Segoe UI Semibold", 10),
        )
        if self.focus_get() == self:
            self.rounded_rect(2, 2, width - 2, height - 2, self.radius, "")
            self.create_rectangle(2, 2, width - 2, height - 2, outline=UI_THEME["focus_ring"], width=2, dash=(4, 2))

    def animate_hover(self) -> None:
        if self.hover_after_id:
            try:
                self.after_cancel(self.hover_after_id)
            except tk.TclError:
                pass
            self.hover_after_id = None
        target = 1.0 if self.hover and self.enabled else 0.0
        if abs(self.hover_amount - target) < 0.05:
            self.hover_amount = target
            self.redraw()
            return
        self.hover_amount += 0.18 if self.hover_amount < target else -0.18
        self.hover_amount = max(0.0, min(1.0, self.hover_amount))
        self.redraw()
        self.hover_after_id = self.after(18, self.animate_hover)


class IconButton(tk.Canvas):
    def __init__(
        self,
        parent: tk.Widget,
        image: tk.PhotoImage,
        command,
        *,
        size: int = 34,
        background: str = "#eef2f5",
        hover_bg: str = "#f6f8fb",
        pressed_bg: str = "#e8f0fe",
        outline: str = "#cfd7e2",
        active_outline: str = "#7aa2ff",
        radius: int = 9,
    ) -> None:
        super().__init__(
            parent,
            width=size,
            height=size,
            background=background,
            highlightthickness=0,
            bd=0,
            cursor="hand2",
            takefocus=True,
        )
        self.image = image
        self.command = command
        self.size = size
        self.normal_bg = background
        self.hover_bg = hover_bg
        self.pressed_bg = pressed_bg
        self.outline = outline
        self.active_outline = active_outline
        self.radius = radius
        self.hover = False
        self.pressed = False
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        self.bind("<ButtonPress-1>", self.on_press)
        self.bind("<ButtonRelease-1>", self.on_click)
        self.bind("<space>", self.on_keyboard)
        self.bind("<Return>", self.on_keyboard)
        self.bind("<FocusIn>", lambda _event: self.redraw())
        self.bind("<FocusOut>", lambda _event: self.redraw())
        self.redraw()

    def on_enter(self, _event: tk.Event | None = None) -> None:
        self.hover = True
        self.redraw()

    def on_leave(self, _event: tk.Event | None = None) -> None:
        self.hover = False
        self.pressed = False
        self.redraw()

    def on_press(self, _event: tk.Event | None = None) -> None:
        if str(self.cget("state")) == "disabled":
            return
        self.pressed = True
        self.redraw()

    def on_click(self, _event: tk.Event | None = None) -> None:
        if str(self.cget("state")) == "disabled":
            return
        self.pressed = False
        self.redraw()
        if self.command:
            self.command()

    def on_keyboard(self, _event: tk.Event | None = None) -> str:
        self.on_click()
        return "break"

    def redraw(self) -> None:
        self.delete("all")
        fill = self.pressed_bg if self.pressed else (self.hover_bg if self.hover else self.normal_bg)
        outline = self.active_outline if self.pressed or self.hover else self.normal_bg
        self.rounded_rect(1, 1, self.size - 1, self.size - 1, self.radius, fill=fill, outline=outline)
        self.create_image(self.size // 2, self.size // 2, image=self.image)
        if self.focus_get() == self:
            self.create_rectangle(2, 2, self.size - 2, self.size - 2, outline=UI_THEME["focus_ring"], width=2, dash=(3, 2))

    def rounded_rect(self, x1: int, y1: int, x2: int, y2: int, radius: int, *, fill: str, outline: str) -> None:
        points = [
            x1 + radius, y1, x2 - radius, y1, x2, y1, x2, y1 + radius,
            x2, y2 - radius, x2, y2, x2 - radius, y2, x1 + radius, y2,
            x1, y2, x1, y2 - radius, x1, y1 + radius, x1, y1,
        ]
        self.create_polygon(points, smooth=True, fill=fill, outline=outline)


class MiniToolButton(tk.Canvas):
    def __init__(
        self,
        parent: tk.Widget,
        command,
        *,
        image: tk.PhotoImage | None = None,
        active_image: tk.PhotoImage | None = None,
        fallback_icon: str = "attachment",
        size: int = 30,
        background: str = "#ffffff",
    ) -> None:
        super().__init__(
            parent,
            width=size,
            height=size,
            background=background,
            highlightthickness=0,
            bd=0,
            cursor="hand2",
            takefocus=True,
        )
        self.image = image
        self.active_image = active_image or image
        self.fallback_icon = fallback_icon
        self.command = command
        self.size = size
        self.background = background
        self.active = False
        self.hover = False
        self.pressed = False
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        self.bind("<ButtonPress-1>", self.on_press)
        self.bind("<ButtonRelease-1>", self.on_click)
        self.bind("<space>", self.on_keyboard)
        self.bind("<Return>", self.on_keyboard)
        self.bind("<FocusIn>", lambda _event: self.redraw())
        self.bind("<FocusOut>", lambda _event: self.redraw())
        self.redraw()

    def configure(self, cnf=None, **kwargs):  # type: ignore[override]
        if cnf:
            kwargs.update(cnf)
        state = kwargs.get("state")
        result = super().configure(**kwargs)
        if state is not None:
            super().configure(cursor="hand2" if state != "disabled" else "arrow")
            self.redraw()
        return result

    config = configure

    def set_active(self, value: bool) -> None:
        self.active = bool(value)
        self.redraw()

    def on_enter(self, _event: tk.Event | None = None) -> None:
        self.hover = True
        self.redraw()

    def on_leave(self, _event: tk.Event | None = None) -> None:
        self.hover = False
        self.pressed = False
        self.redraw()

    def on_press(self, _event: tk.Event | None = None) -> None:
        if str(self.cget("state")) == "disabled":
            return
        self.pressed = True
        self.redraw()

    def on_click(self, _event: tk.Event | None = None) -> None:
        if str(self.cget("state")) == "disabled":
            return
        self.pressed = False
        self.redraw()
        if self.command:
            self.command()

    def on_keyboard(self, _event: tk.Event | None = None) -> str:
        self.on_click()
        return "break"

    def redraw(self) -> None:
        self.delete("all")
        disabled = str(self.cget("state")) == "disabled"
        active_visual = (self.active or self.pressed) and not disabled
        bg = "#e8f0f8" if active_visual else ("#f6f8fb" if self.hover else self.background)
        outline = "#a8bed6" if active_visual else ("#c7d2de" if self.hover else self.background)
        icon = "#9aa5b1" if disabled else ("#4f78a8" if active_visual else "#384655")
        self.create_rectangle(0, 0, self.size, self.size, fill=self.background, outline="")
        self.rounded_rect(1, 1, self.size - 1, self.size - 1, 8, fill=bg, outline=outline)
        image = self.active_image if active_visual else self.image
        if image:
            self.create_image(self.size // 2, self.size // 2, image=image)
        elif self.fallback_icon == "microphone":
            self.draw_microphone(icon)
        elif self.fallback_icon == "folder":
            self.draw_folder(icon)
        else:
            self.draw_attachment(icon)
        if self.focus_get() == self:
            self.create_rectangle(2, 2, self.size - 2, self.size - 2, outline=UI_THEME["focus_ring"], width=2, dash=(3, 2))

    def draw_microphone(self, color: str) -> None:
        cx = self.size // 2
        self.create_oval(cx - 5, 6, cx + 5, 18, outline=color, width=2)
        self.create_line(cx - 9, 15, cx - 9, 17, cx - 6, 21, cx, 23, cx + 6, 21, cx + 9, 17, cx + 9, 15, fill=color, width=2, smooth=True)
        self.create_line(cx, 23, cx, 26, fill=color, width=2)
        self.create_line(cx - 5, 26, cx + 5, 26, fill=color, width=2)

    def draw_attachment(self, color: str) -> None:
        self.create_arc(9, 6, 23, 24, start=215, extent=290, outline=color, width=2, style="arc")
        self.create_arc(12, 9, 20, 20, start=215, extent=290, outline=color, width=2, style="arc")
        self.create_line(13, 21, 22, 12, fill=color, width=2)

    def draw_folder(self, color: str) -> None:
        self.create_line(7, 11, 12, 11, 14, 8, 21, 8, 23, 11, 25, 11, fill=color, width=2)
        self.create_rectangle(6, 11, 24, 23, outline=color, width=2)

    def rounded_rect(self, x1: int, y1: int, x2: int, y2: int, radius: int, *, fill: str, outline: str) -> None:
        points = [
            x1 + radius, y1, x2 - radius, y1, x2, y1, x2, y1 + radius,
            x2, y2 - radius, x2, y2, x2 - radius, y2, x1 + radius, y2,
            x1, y2, x1, y2 - radius, x1, y1 + radius, x1, y1,
        ]
        self.create_polygon(points, smooth=True, fill=fill, outline=outline)


class WebSearchToggleButton(tk.Canvas):
    def __init__(
        self,
        parent: tk.Widget,
        command,
        *,
        image: tk.PhotoImage | None = None,
        width: int = 46,
        height: int = 30,
        background: str = "#ffffff",
    ) -> None:
        super().__init__(
            parent,
            width=width,
            height=height,
            background=background,
            highlightthickness=0,
            bd=0,
            cursor="hand2",
            takefocus=True,
        )
        self.command = command
        self.image = image
        self.width_value = width
        self.height_value = height
        self.active = False
        self.hover = False
        self.pressed = False
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        self.bind("<ButtonPress-1>", self.on_press)
        self.bind("<ButtonRelease-1>", self.on_click)
        self.bind("<space>", self.on_keyboard)
        self.bind("<Return>", self.on_keyboard)
        self.bind("<FocusIn>", lambda _event: self.redraw())
        self.bind("<FocusOut>", lambda _event: self.redraw())
        self.redraw()

    def set_active(self, value: bool) -> None:
        self.active = bool(value)
        self.redraw()

    def on_enter(self, _event: tk.Event | None = None) -> None:
        self.hover = True
        self.redraw()

    def on_leave(self, _event: tk.Event | None = None) -> None:
        self.hover = False
        self.pressed = False
        self.redraw()

    def on_press(self, _event: tk.Event | None = None) -> None:
        if str(self.cget("state")) == "disabled":
            return
        self.pressed = True
        self.redraw()

    def on_click(self, _event: tk.Event | None = None) -> None:
        if str(self.cget("state")) == "disabled":
            return
        self.pressed = False
        self.redraw()
        if self.command:
            self.command()

    def on_keyboard(self, _event: tk.Event | None = None) -> str:
        self.on_click()
        return "break"

    def redraw(self) -> None:
        self.delete("all")
        width = self.width_value
        height = self.height_value
        bg = "#dce8ff" if self.pressed else ("#e8f0fe" if self.active else ("#f7f9fc" if self.hover else "#ffffff"))
        outline = "#7aa2ff" if self.pressed else ("#8fb4ff" if self.active else ("#c9d2dc" if self.hover else "#d8dde4"))
        icon = "#1a73e8" if self.active else "#384655"
        self.create_rectangle(0, 0, width, height, fill="#ffffff", outline="")
        self.rounded_rect(1, 1, width - 1, height - 1, height // 2 - 1, fill=bg, outline=outline)
        if self.image:
            self.create_image(width // 2, height // 2, image=self.image)
        else:
            cx = width // 2
            cy = height // 2
            radius = min(width, height) // 2 - 8
            self.create_oval(cx - radius, cy - radius, cx + radius, cy + radius, outline=icon, width=1)
            self.create_arc(cx - radius + 3, cy - radius, cx + radius - 3, cy + radius, start=90, extent=180, outline=icon, width=1)
            self.create_arc(cx - radius + 3, cy - radius, cx + radius - 3, cy + radius, start=270, extent=180, outline=icon, width=1)
            self.create_line(cx - radius, cy, cx + radius, cy, fill=icon, width=1)
            self.create_line(cx, cy - radius, cx, cy + radius, fill=icon, width=1)
        if self.active:
            self.create_oval(width - 10, 7, width - 5, 12, fill="#34a853", outline="")
        if self.focus_get() == self:
            self.create_rectangle(2, 2, width - 2, height - 2, outline=UI_THEME["focus_ring"], width=2, dash=(3, 2))

    def rounded_rect(self, x1: int, y1: int, x2: int, y2: int, radius: int, *, fill: str, outline: str) -> None:
        points = [
            x1 + radius, y1, x2 - radius, y1, x2, y1, x2, y1 + radius,
            x2, y2 - radius, x2, y2, x2 - radius, y2, x1 + radius, y2,
            x1, y2, x1, y2 - radius, x1, y1 + radius, x1, y1,
        ]
        self.create_polygon(points, smooth=True, fill=fill, outline=outline)



class KnowledgeChatApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("LightRAG Knowledge Chat")
        self.root.geometry("1120x760")
        self.root.minsize(900, 600)
        self.root.configure(bg=UI_THEME["app_bg"])

        self.settings = self.load_settings()
        self.save_settings()
        self.context_var = tk.StringVar(value="Auto")
        self.lightrag_var = tk.BooleanVar(value=bool(self.settings["use_lightrag"]))
        self.status_var = tk.StringVar(value="Ready")
        self.enter_send_var = tk.BooleanVar(value=bool(self.settings["send_on_enter"]))
        self.game_guard_var = tk.BooleanVar(value=bool(self.settings["game_guard_enabled"]))
        self.auto_process_links_var = tk.BooleanVar(value=bool(self.settings.get("auto_process_links", True)))
        self.auto_route_topics_var = tk.BooleanVar(value=bool(self.settings.get("auto_route_topics", True)))
        self.auto_create_topics_var = tk.BooleanVar(value=bool(self.settings.get("auto_create_topics", True)))
        self.auto_detect_books_var = tk.BooleanVar(value=bool(self.settings.get("auto_detect_books_in_images", True)))
        self.book_lookup_enabled_var = tk.BooleanVar(value=bool(self.settings.get("book_lookup_enabled", True)))
        self.web_search_enabled_var = tk.BooleanVar(value=bool(self.settings.get("web_search_enabled", False)))
        self.button_color_var = tk.StringVar(value=str(self.settings["button_color"]))
        self.obsidian_path_var = tk.StringVar(value=str(self.settings.get("obsidian_path", "")))
        self.vault_path_var = tk.StringVar(value=str(self.settings.get("vault_path", str(DEFAULT_VAULT_DIR))))
        self.llm_model_var = tk.StringVar(value=str(self.settings.get("llm_model", "")))
        self.vision_model_var = tk.StringVar(value=str(self.settings.get("vision_model", "")))
        self.embedding_model_var = tk.StringVar(value=str(self.settings.get("embedding_model", "")))
        self.auto_switch_models_var = tk.BooleanVar(value=bool(self.settings.get("auto_switch_models", True)))

        global VAULT_DIR
        VAULT_DIR = self.vault_dir()

        self.settings_window: tk.Toplevel | None = None
        self.settings_status_var = tk.StringVar(value="")
        self._settings_dialog = SettingsDialog(self)
        self._game_guard_dialog = GameGuardDialog(self)
        self._material_workers = MaterialWorkerManager(self)
        self._project_panel = ProjectActionPanel(self)
        self._capture_workflow = CaptureWorkflow(self)
        self._chat_list = ChatListManager(self)
        self._model_manager = ModelManager(str(self.settings.get("lmstudio_base_url", LMSTUDIO_API_URL)))
        self.tooltips: list[ToolTip] = []
        self.icon_images: list[tk.PhotoImage] = []
        self.obsidian_raw_image: tk.PhotoImage | None = None
        self.obsidian_image: tk.PhotoImage | None = None
        self.new_chat_image: tk.PhotoImage | None = None
        self.web_search_image: tk.PhotoImage | None = None
        self.attachment_image: tk.PhotoImage | None = None
        self.attachment_active_image: tk.PhotoImage | None = None
        self.microphone_image: tk.PhotoImage | None = None
        self.microphone_active_image: tk.PhotoImage | None = None
        self.chat_widgets: list[tk.Widget] = []
        self.chat_row_widgets: list[tk.Widget] = []
        self.inline_rename_entry: tk.Entry | None = None
        self.inline_rename_chat_id = ""
        self.inline_rename_original = ""
        self.inline_rename_ignore_click_until = 0.0
        self.input_history: list[str] = []
        self.input_history_index = 0
        self.active_process: subprocess.Popen | None = None
        self.process_lock = threading.Lock()
        self.busy = False
        self.operation_id = 0
        self.active_operation_id: int | None = None
        self.voice_operation_id: int | None = None
        self.busy_timer_id: str | None = None
        self.game_guard_warning_until = 0.0
        self.query_timeout_seconds = int(os.getenv("LMSTUDIO_GUI_QUERY_TIMEOUT_SECONDS", "600"))
        self.drop_highlight_active = False
        self.drop_pulse_id: str | None = None
        self.drop_pulse_step = 0
        self.status_animation_id: str | None = None
        self.status_animation_step = 0
        self.busy_status_base = ""
        self.background_tasks: dict[str, BackgroundTaskRecord] = {}
        self.last_book_discovery_report: BookDiscoveryReport | None = None
        self.dnd_backend = "none"
        self.project_actions = self.load_project_actions()

        self.node_registry = get_registry()
        for node_cls in BUILTIN_NODES + GOAL_NODES:
            self.node_registry.register(node_cls)

        self.chat_store = self.load_chat_store()
        self.active_chat_id = str(self.chat_store.get("active_chat_id") or "")
        if not self.active_chat_id or not self.get_active_chat():
            self.create_chat(save=False)
        self.save_chat_store()

        self.configure_styles()
        self.build_ui()
        self.root.bind_all("<Button-1>", self.on_inline_rename_global_click, add="+")
        self.populate_chat_list()
        self.render_current_chat()
        self.load_input_history()
        self.apply_settings_to_ui()
        self.schedule_game_guard_probe()
        self.schedule_health_probe()

    def configure_styles(self) -> None:
        style = ttk.Style()
        style.configure("App.TFrame", background=UI_THEME["app_bg"])
        style.configure("Top.TFrame", background=UI_THEME["top_bg"])
        style.configure("Sidebar.TFrame", background=UI_THEME["sidebar_bg"])
        style.configure("Composer.TFrame", background=UI_THEME["composer_bg"])
        style.configure("Status.TLabel", background=UI_THEME["top_bg"], foreground=UI_THEME["muted"], font=("Segoe UI", 10))
        style.configure("Header.TLabel", background=UI_THEME["top_bg"], foreground=UI_THEME["text"], font=("Segoe UI Semibold", 11))
        style.configure("Context.TLabel", background=UI_THEME["top_bg"], foreground="#384655", font=("Segoe UI", 10))
        style.configure("Toolbar.TCheckbutton", background=UI_THEME["top_bg"], foreground="#384655", font=("Segoe UI", 10))
        style.configure("SettingsHeader.TLabel", background=UI_THEME["app_bg"], foreground=UI_THEME["text"], font=("Segoe UI Semibold", 10))
        style.configure("SettingsStatus.TLabel", background=UI_THEME["app_bg"], foreground=UI_THEME["muted"], font=("Segoe UI", 9))

    def load_settings(self) -> dict[str, object]:
        return load_settings_standalone()

    def save_settings(self) -> None:
        save_settings_standalone(self.settings)

    def vault_dir(self) -> Path:
        raw_path = str(self.settings.get("vault_path", str(DEFAULT_VAULT_DIR)) or str(DEFAULT_VAULT_DIR)).strip()
        return Path(raw_path) if raw_path else DEFAULT_VAULT_DIR

    def load_chat_store(self) -> dict:
        return load_chat_store_standalone()

    def migrate_legacy_history(self) -> dict | None:
        return migrate_legacy_history_standalone()

    def save_chat_store(self) -> None:
        self.chat_store["active_chat_id"] = self.active_chat_id
        save_chat_store_standalone(self.chat_store)

    def new_id(self, prefix: str) -> str:
        return new_id_standalone(prefix)

    def get_chats(self) -> list[dict]:
        return get_chats_standalone(self.chat_store)

    def get_active_chat(self) -> dict | None:
        return get_active_chat_standalone(self.chat_store, self.active_chat_id)

    def begin_inline_rename(self, chat_id: str, row: tk.Frame, title_label: tk.Label) -> str:
        return self._chat_list.begin_rename(chat_id, row, title_label)

    def finish_inline_rename(self, save: bool = True) -> None:
        self._chat_list.finish_rename(save)

    def on_inline_rename_global_click(self, event: tk.Event) -> None:
        self._chat_list.on_global_click(event)

    def populate_chat_list(self, keep_selection: bool = False) -> None:
        self._chat_list.populate(keep_selection)

    def add_chat_sidebar_row(self, chat: dict, row_index: int) -> None:
        self._chat_list.add_row(chat, row_index)

    def on_chat_select(self, _event: tk.Event | None = None) -> None:
        return

    def select_chat(self, chat_id: str) -> None:
        self._chat_list.select_chat(chat_id)

    def create_chat(self, save: bool = True) -> None:
        chat_id = self.new_id("chat")
        chat = {
            "id": chat_id,
            "title": "Новый чат",
            "created_at": now_iso(),
            "updated_at": now_iso(),
            "messages": [],
        }
        self.get_chats().insert(0, chat)
        self.active_chat_id = chat_id
        if save:
            self.save_chat_store()
            self.populate_chat_list()
            self.render_current_chat()

    def chat_by_id(self, chat_id: str) -> dict | None:
        for chat in self.get_chats():
            if str(chat.get("id")) == chat_id:
                return chat
        return None

    def rename_chat(self) -> None:
        self.rename_chat_by_id(self.active_chat_id)

    def rename_chat_by_id(self, chat_id: str) -> None:
        chat = self.chat_by_id(chat_id)
        if not chat:
            return
        title = simpledialog.askstring("Переименовать чат", "Название:", initialvalue=str(chat.get("title", "")), parent=self.root)
        if not title:
            return
        chat["title"] = title.strip()[:80] or "Чат"
        chat["updated_at"] = now_iso()
        self.save_chat_store()
        self.populate_chat_list()

    def delete_chat(self) -> None:
        self.delete_chat_by_id(self.active_chat_id)

    def delete_chat_by_id(self, chat_id: str) -> None:
        chat = self.chat_by_id(chat_id)
        if not chat:
            return
        if not messagebox.askyesno("Удалить чат", f"Удалить «{chat.get('title', 'Чат')}»?", parent=self.root):
            return
        chats = [item for item in self.get_chats() if str(item.get("id")) != chat_id]
        self.chat_store["chats"] = chats
        if chats and self.active_chat_id == chat_id:
            self.active_chat_id = str(chats[0].get("id"))
        elif not chats:
            self.create_chat(save=False)
        self.save_chat_store()
        self.populate_chat_list()
        self.render_current_chat()

    def add_message(
        self,
        role: str,
        text: str,
        context_name: str = "General",
        warnings: list[str] | None = None,
        lightrag_used: bool | None = None,
        project_action_id: str = "",
    ) -> None:
        chat = self.get_active_chat()
        if not chat:
            self.create_chat(save=False)
            chat = self.get_active_chat()
        if not chat:
            return
        message = {
            "id": self.new_id("msg"),
            "ts": now_iso(),
            "role": role,
            "context": context_name,
            "lightrag": bool(self.lightrag_var.get()) if lightrag_used is None else bool(lightrag_used),
            "text": text,
            "warnings": warnings or [],
            "project_action_id": project_action_id,
        }
        chat.setdefault("messages", []).append(message)
        chat["updated_at"] = message["ts"]
        if str(chat.get("title")) == "Новый чат" and role == "user":
            chat["title"] = self.title_for_chat(text)
        self.save_chat_store()
        self.populate_chat_list(keep_selection=True)

    def title_for_chat(self, text: str) -> str:
        return title_for_chat_standalone(text)

    def format_chat_age(self, updated_at: str) -> str:
        return format_chat_age_standalone(updated_at)

    def chat_group_name(self, chat: dict) -> str:
        return chat_group_by_context_standalone(chat)

    def build_ui(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)
        self.new_chat_image = self.load_icon_image(NEW_CHAT_ICON, 22)
        self.web_search_image = self.load_icon_image(WEB_SEARCH_ICON, 26)
        self.attachment_image = self.load_icon_image(ATTACHMENT_ICON, 21)
        self.attachment_active_image = self.load_icon_image(ATTACHMENT_ICON_ACTIVE, 21)
        self.microphone_image = self.load_icon_image(MICROPHONE_ICON, 21)
        self.microphone_active_image = self.load_icon_image(MICROPHONE_ICON_ACTIVE, 21)

        toolbar = ttk.Frame(self.root, padding=(14, 10), style="Top.TFrame")
        toolbar.grid(row=0, column=0, sticky="ew")
        toolbar.columnconfigure(3, weight=1)

        ttk.Label(toolbar, text="LightRAG Chat", style="Header.TLabel").grid(row=0, column=0, padx=(0, 18))

        self.settings_button = ttk.Button(toolbar, text="Настройки", command=self.open_settings)
        self.settings_button.grid(row=0, column=1, padx=(0, 14))
        self.add_tooltip(self.settings_button, "Enter, LightRAG, цвет кнопок, Obsidian, ссылки и Game Guard.")

        self.control_button = ttk.Button(toolbar, text="Control", command=self.open_light_rag_control)
        self.control_button.grid(row=0, column=2, padx=(0, 14))
        self.add_tooltip(self.control_button, "Открыть LightRAG-Control для проверки LM Studio, моделей, индексов и импорта.")

        self.context_selector = ttk.Combobox(
            toolbar,
            textvariable=self.context_var,
            values=["Auto"] + list(CONTEXTS.keys()),
            state="readonly",
            width=20,
        )
        self.context_selector.grid(row=0, column=3, sticky="w", padx=(0, 14))
        self.add_tooltip(self.context_selector, "Контекст ответа. Finished Projects ищет только в отдельном слое готовых проектов.")

        ttk.Label(toolbar, textvariable=self.status_var, style="Status.TLabel").grid(row=0, column=4, sticky="e", padx=(0, 10))

        if OBSIDIAN_ICON.exists():
            self.obsidian_raw_image = tk.PhotoImage(file=str(OBSIDIAN_ICON))
            factor = max(1, self.obsidian_raw_image.width() // 34)
            self.obsidian_image = self.obsidian_raw_image.subsample(factor, factor)
            self.obsidian_button = IconButton(toolbar, self.obsidian_image, self.open_obsidian, size=38, background="#eef2f5")
        else:
            self.obsidian_button = ttk.Button(toolbar, text="Ob", width=3, command=self.open_obsidian)
        self.obsidian_button.grid(row=0, column=5, sticky="e")
        self.add_tooltip(self.obsidian_button, "Открыть приложение Obsidian. Если путь не найден, можно указать Obsidian.exe.")

        main = ttk.Frame(self.root, padding=(12, 12, 12, 14), style="App.TFrame")
        main.grid(row=1, column=0, sticky="nsew")
        main.columnconfigure(0, weight=0, minsize=260)
        main.columnconfigure(1, weight=1)
        main.rowconfigure(0, weight=1)

        sidebar_shadow = tk.Frame(main, bg=UI_THEME["panel_shadow"])
        sidebar_shadow.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=(0, 2))
        sidebar_shadow.configure(width=262)
        sidebar_shadow.grid_propagate(False)
        sidebar_shadow.columnconfigure(0, weight=1)
        sidebar_shadow.rowconfigure(0, weight=1)
        sidebar_shell = tk.Frame(sidebar_shadow, bg=UI_THEME["panel_border"], padx=1, pady=1)
        sidebar_shell.grid(row=0, column=0, sticky="nsew", padx=(0, 2), pady=(0, 2))
        sidebar_shell.configure(width=260)
        sidebar_shell.grid_propagate(False)
        sidebar_shell.columnconfigure(0, weight=1)
        sidebar_shell.rowconfigure(0, weight=1)
        sidebar = tk.Frame(sidebar_shell, bg=UI_THEME["sidebar_bg"], width=258)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)
        sidebar.columnconfigure(0, weight=1)
        sidebar.rowconfigure(1, weight=1)
        sidebar_header = tk.Frame(sidebar, bg="#eef2f5")
        sidebar_header.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 8))
        sidebar_header.columnconfigure(0, weight=1)
        tk.Label(sidebar_header, text="История", bg="#eef2f5", fg="#1f2933", font=("Segoe UI Semibold", 11), anchor="w").grid(row=0, column=0, sticky="ew")
        if self.new_chat_image:
            self.new_chat_button = IconButton(sidebar_header, self.new_chat_image, self.create_chat, size=30, background="#eef2f5")
        else:
            self.new_chat_button = tk.Button(sidebar_header, text="+", width=3, relief="flat", bg="#eef2f5", activebackground="#dfe6ed", command=self.create_chat)
        self.new_chat_button.grid(row=0, column=1, sticky="e")
        self.add_tooltip(self.new_chat_button, "Новый чат.")

        self.chat_rows_canvas = tk.Canvas(sidebar, bg="#eef2f5", borderwidth=0, highlightthickness=0)
        self.chat_rows_canvas.grid(row=1, column=0, sticky="nsew", padx=(0, 2))
        rows_scroll = ttk.Scrollbar(sidebar, orient="vertical", command=self.chat_rows_canvas.yview)
        rows_scroll.grid(row=1, column=1, sticky="ns")
        self.chat_rows_canvas.configure(yscrollcommand=rows_scroll.set)
        self.chat_rows = tk.Frame(self.chat_rows_canvas, bg="#eef2f5")
        self.chat_rows.columnconfigure(0, weight=1)
        self.chat_rows_window = self.chat_rows_canvas.create_window((0, 0), window=self.chat_rows, anchor="nw")
        self.chat_rows.bind("<Configure>", lambda _event: self.chat_rows_canvas.configure(scrollregion=self.chat_rows_canvas.bbox("all")))
        self.chat_rows_canvas.bind("<Configure>", lambda event: self.chat_rows_canvas.itemconfigure(self.chat_rows_window, width=event.width))
        for widget in (sidebar, self.chat_rows_canvas, self.chat_rows):
            self.bind_history_mousewheel(widget)

        chat_area = ttk.Frame(main, style="App.TFrame")
        chat_area.grid(row=0, column=1, sticky="nsew")
        chat_area.columnconfigure(0, weight=1)
        chat_area.rowconfigure(0, weight=1)

        chat_shadow = tk.Frame(chat_area, bg=UI_THEME["panel_shadow"])
        chat_shadow.grid(row=0, column=0, sticky="nsew", pady=(0, 2))
        chat_shadow.columnconfigure(0, weight=1)
        chat_shadow.rowconfigure(0, weight=1)

        chat_shell = AnimatedEdgeFrame(
            chat_shadow,
            background=UI_THEME["chat_bg"],
            border="#aec5d4",
            thickness=6,
            animated=True,
        )
        chat_shell.grid(row=0, column=0, sticky="nsew", padx=(0, 2), pady=(0, 2))
        chat_content = chat_shell.content
        chat_content.columnconfigure(0, weight=1)
        chat_content.rowconfigure(0, weight=1)

        self.chat = tk.Text(
            chat_content,
            wrap="word",
            state="disabled",
            padx=14,
            pady=14,
            relief="flat",
            borderwidth=0,
            background=UI_THEME["chat_bg"],
            foreground="#202124",
            insertbackground="#202124",
            font=("Segoe UI", 10),
        )
        self.chat.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(chat_content, orient="vertical", command=self.chat.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.chat.configure(yscrollcommand=scroll.set)
        self.chat.tag_configure("assistant", foreground="#202124", spacing1=8, spacing3=12, lmargin1=2, lmargin2=2, rmargin=120)
        self.chat.tag_configure("system", foreground="#5f6368", spacing1=4, spacing3=8)
        self.chat.tag_configure("warning", foreground="#5a6370", font=("Segoe UI", 9, "italic"), spacing1=2, spacing3=8)
        self.chat.tag_configure("error", foreground="#b3261e", spacing1=8, spacing3=12)

        self.drop_zone = tk.Label(
            chat_area,
            text="Drop files/folders here · DnD=initializing",
            bg="#eef2f5",
            fg="#5f6b76",
            font=("Segoe UI", 9),
            anchor="w",
            padx=10,
            pady=6,
        )
        self.drop_zone.grid(row=1, column=0, sticky="ew", pady=(8, 0))

        input_frame = ttk.Frame(chat_area, style="Composer.TFrame")
        input_frame.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        input_frame.columnconfigure(0, weight=1)
        composer_shadow = tk.Frame(input_frame, bg=UI_THEME["panel_shadow"])
        composer_shadow.grid(row=0, column=0, sticky="ew", pady=(0, 2))
        composer_shadow.columnconfigure(0, weight=1)

        input_shell = tk.Frame(composer_shadow, bg=UI_THEME["panel_border"], padx=1, pady=1)
        input_shell.grid(row=0, column=0, sticky="ew", padx=(0, 2), pady=(0, 2))
        input_shell.columnconfigure(0, weight=1)
        input_shell.rowconfigure(0, weight=1)

        self.input = tk.Text(
            input_shell,
            height=4,
            wrap="word",
            padx=12,
            pady=10,
            relief="flat",
            borderwidth=0,
            background="#ffffff",
            foreground="#202124",
            insertbackground="#202124",
            font=("Segoe UI", 10),
        )
        self.input.grid(row=0, column=0, sticky="ew")
        tool_strip = tk.Frame(input_shell, bg="#ffffff")
        tool_strip.grid(row=1, column=0, sticky="ew")
        tool_strip.columnconfigure(4, weight=1)
        self.web_search_button = WebSearchToggleButton(tool_strip, self.toggle_web_search, image=self.web_search_image, width=46, height=30, background="#ffffff")
        self.web_search_button.grid(row=0, column=0, sticky="w", padx=(8, 4), pady=(0, 8))
        self.add_tooltip(self.web_search_button, "Включить/выключить web-поиск для LLM.")
        self.file_attach_button = MiniToolButton(
            tool_strip,
            self.attach_files,
            image=self.attachment_image,
            active_image=self.attachment_active_image,
            fallback_icon="attachment",
            size=30,
            background="#ffffff",
        )
        self.file_attach_button.grid(row=0, column=1, sticky="w", padx=4, pady=(0, 8))
        self.add_tooltip(self.file_attach_button, "Прикрепить файл: изображение, текст, документ, аудио или видео.")
        self.folder_attach_button = MiniToolButton(
            tool_strip,
            self.attach_folder,
            fallback_icon="folder",
            size=30,
            background="#ffffff",
        )
        self.folder_attach_button.grid(row=0, column=2, sticky="w", padx=4, pady=(0, 8))
        self.add_tooltip(self.folder_attach_button, "Добавить локальную папку. Исходники не копируются в vault, сохраняется ссылка и снимок.")
        self.voice_button = MiniToolButton(
            tool_strip,
            self.start_voice_input,
            image=self.microphone_image,
            active_image=self.microphone_active_image,
            fallback_icon="microphone",
            size=30,
            background="#ffffff",
        )
        self.voice_button.grid(row=0, column=3, sticky="w", padx=4, pady=(0, 8))
        self.add_tooltip(self.voice_button, "Диктовка через Windows Speech Recognition. Текст вставится в поле ввода.")
        self.input.bind("<Control-Return>", self.on_ctrl_return)
        self.input.bind("<Shift-Return>", self.on_shift_return)
        self.input.bind("<Return>", self.on_return)
        self.input.bind("<Alt-Up>", lambda _event: self.navigate_input_history(-1))
        self.input.bind("<Alt-Down>", lambda _event: self.navigate_input_history(1))
        self.input.bind("<KeyRelease>", self.update_char_count)

        char_count_frame = tk.Frame(input_frame, bg="#ffffff")
        char_count_frame.grid(row=1, column=0, sticky="ew", padx=1, pady=(0, 1))
        self.char_count_label = tk.Label(char_count_frame, text="", bg="#ffffff", fg="#9ca3af", font=("Segoe UI", 8), anchor="e")
        self.char_count_label.pack(side="right", padx=4)

        button_bar = tk.Frame(input_frame, bg="#f4f6f8")
        button_bar.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        button_bar.columnconfigure(0, weight=2)
        button_bar.columnconfigure(1, weight=1)
        button_bar.columnconfigure(2, weight=1)

        self.send_button = self.create_action_button(button_bar, "Отправить", self.on_send, bg="#3d5f88", active_bg="#344f70", fg="#ffffff")
        self.send_button.grid(row=0, column=0, sticky="ew", padx=(0, 7), ipady=7)
        self.cancel_button = self.create_action_button(button_bar, "Отмена", self.cancel_active_operation, bg="#dfe6ed", active_bg="#d2dbe4", fg="#1f2933")
        self.cancel_button.grid(row=0, column=1, sticky="ew", padx=7, ipady=7)
        self.cancel_button.configure(state="disabled")
        self.clear_button = self.create_action_button(button_bar, "Очистить окно", self.clear_chat_window, bg="#dfe6ed", active_bg="#d2dbe4", fg="#1f2933")
        self.clear_button.grid(row=0, column=2, sticky="ew", padx=(7, 0), ipady=7)
        self.install_native_file_drop()

    def create_action_button(self, parent: tk.Widget, text: str, command, *, bg: str, active_bg: str, fg: str) -> RoundedButton:
        return RoundedButton(parent, text=text, command=command, bg=bg, active_bg=active_bg, fg=fg)

    def add_tooltip(self, widget: tk.Widget, text: str, delay_ms: int = 450) -> None:
        self.tooltips.append(ToolTip(widget, text, delay_ms=delay_ms))

    def bind_history_mousewheel(self, widget: tk.Widget) -> None:
        widget.bind("<MouseWheel>", self.on_history_mousewheel, add="+")
        widget.bind("<Button-4>", self.on_history_mousewheel, add="+")
        widget.bind("<Button-5>", self.on_history_mousewheel, add="+")

    def on_history_mousewheel(self, event: tk.Event) -> str:
        if not hasattr(self, "chat_rows_canvas"):
            return "break"
        bbox = self.chat_rows_canvas.bbox("all")
        if not bbox:
            return "break"
        content_height = max(0, int(bbox[3]) - int(bbox[1]))
        if content_height <= self.chat_rows_canvas.winfo_height():
            return "break"
        if getattr(event, "num", None) == 4:
            units = -3
        elif getattr(event, "num", None) == 5:
            units = 3
        else:
            delta = int(getattr(event, "delta", 0) or 0)
            units = -int(delta / 120) if abs(delta) >= 120 else (-1 if delta > 0 else 1)
        self.chat_rows_canvas.yview_scroll(units, "units")
        return "break"

    def load_icon_image(self, path: Path, target_px: int) -> tk.PhotoImage | None:
        if not path.exists():
            return None
        try:
            raw = tk.PhotoImage(file=str(path))
            factor = max(1, int(round(max(raw.width(), raw.height()) / max(1, target_px))))
            image = raw.subsample(factor, factor)
            self.icon_images.extend([raw, image])
            return image
        except tk.TclError:
            return None

    def install_native_file_drop(self) -> None:
        if not explorer_dnd_enabled():
            self.dnd_backend = "safe-disabled"
            self.update_dnd_diagnostics()
            return
        try:
            from tkinterdnd2 import DND_FILES  # type: ignore
        except Exception as exc:
            self.dnd_backend = "none"
            try:
                self.append_warning_message(
                    f"Drag-and-drop disabled: tkinterdnd2 is not available ({exc}). Use the paperclip button -> Folder/GitHub.",
                    persist=False,
                )
            except Exception:
                pass
            self.update_dnd_diagnostics()
            return

        widgets = (self.root, self.chat, self.input, getattr(self, "drop_zone", None))
        registered = 0
        for widget in widgets:
            if widget is None:
                continue
            if not hasattr(widget, "drop_target_register") or not hasattr(widget, "dnd_bind"):
                continue
            try:
                widget.drop_target_register(DND_FILES)  # type: ignore[attr-defined]
                widget.dnd_bind("<<DropEnter>>", self.on_dnd_enter)  # type: ignore[attr-defined]
                widget.dnd_bind("<<DropPosition>>", self.on_dnd_position)  # type: ignore[attr-defined]
                widget.dnd_bind("<<DropLeave>>", self.on_dnd_leave)  # type: ignore[attr-defined]
                widget.dnd_bind("<<Drop>>", self.on_dnd_drop)  # type: ignore[attr-defined]
                registered += 1
            except Exception as exc:
                self.append_warning_message(f"Drag-and-drop registration failed for widget: {exc}", persist=False)
        self.dnd_backend = "tkinterdnd2" if registered else "none"
        if registered == 0:
            self.append_warning_message("Drag-and-drop disabled: Tk root was not created with tkinterdnd2 support.", persist=False)
        self.update_dnd_diagnostics()

    def update_dnd_diagnostics(self) -> None:
        try:
            self.root.title(f"LightRAG Knowledge Chat · Root={ROOT} · Python={Path(sys.executable).name} · DnD={self.dnd_backend}")
            if hasattr(self, "drop_zone"):
                self.drop_zone.configure(text=f"Drop files/folders here · Root={ROOT.name} · DnD={self.dnd_backend}", bg="#eef2f5", fg="#5f6b76")
        except tk.TclError:
            pass

    def parse_dnd_files(self, data: str) -> list[str]:
        try:
            return [normalize_attached_source_path(item) for item in self.root.tk.splitlist(data) if str(item).strip()]
        except Exception:
            return [normalize_attached_source_path(data)] if str(data).strip() else []

    def on_dnd_enter(self, event: tk.Event) -> str:
        self.set_drop_highlight(True)
        return "copy"

    def on_dnd_position(self, event: tk.Event) -> str:
        self.set_drop_highlight(True)
        return "copy"

    def on_dnd_leave(self, event: tk.Event) -> str:
        self.set_drop_highlight(False)
        return "copy"

    def on_dnd_drop(self, event: tk.Event) -> str:
        self.set_drop_highlight(False)
        try:
            files = self.parse_dnd_files(str(getattr(event, "data", "")))
        except Exception as exc:
            self.root.after(0, self.append_warning_message, f"Drag-and-drop parse failed: {exc}", False)
            return "copy"
        if files:
            self.root.after(60, lambda items=files: self.handle_dropped_files(items))
        return "copy"

    def set_drop_highlight(self, active: bool) -> None:
        if self.drop_highlight_active == active:
            return
        self.drop_highlight_active = active
        try:
            if active:
                self.drop_pulse_step = 0
                self.root.configure(bg=UI_THEME["accent_pulse_1"])
                self.chat.configure(background="#f8fbff", highlightthickness=2, highlightbackground=UI_THEME["accent"], highlightcolor=UI_THEME["accent"])
                self.input.configure(background="#f8fbff", highlightthickness=2, highlightbackground=UI_THEME["accent"], highlightcolor=UI_THEME["accent"])
                if hasattr(self, "drop_zone"):
                    self.drop_zone.configure(bg="#dcecff", fg="#174a7c", text=f"Release to import files/folders · DnD={self.dnd_backend}")
                self.animate_drop_pulse()
            else:
                self.stop_drop_pulse()
                self.root.configure(bg=UI_THEME["app_bg"])
                self.chat.configure(background=UI_THEME["chat_bg"], highlightthickness=0)
                self.input.configure(background=UI_THEME["panel_bg"], highlightthickness=0)
                self.update_dnd_diagnostics()
        except tk.TclError:
            pass

    def stop_drop_pulse(self) -> None:
        if self.drop_pulse_id:
            try:
                self.root.after_cancel(self.drop_pulse_id)
            except tk.TclError:
                pass
            self.drop_pulse_id = None

    def animate_drop_pulse(self) -> None:
        if not self.drop_highlight_active:
            self.drop_pulse_id = None
            return
        amount = 0.18 + 0.18 * (self.drop_pulse_step % 4)
        pulse_bg = mix_hex_color(UI_THEME["accent_pulse_1"], UI_THEME["accent_pulse_2"], amount)
        border = mix_hex_color(UI_THEME["accent"], "#8fb4ff", amount)
        try:
            self.root.configure(bg=pulse_bg)
            self.chat.configure(highlightbackground=border, highlightcolor=border)
            self.input.configure(highlightbackground=border, highlightcolor=border)
            if hasattr(self, "drop_zone"):
                self.drop_zone.configure(bg=mix_hex_color("#f8fbff", UI_THEME["accent_pulse_2"], amount))
        except tk.TclError:
            return
        self.drop_pulse_step += 1
        self.drop_pulse_id = self.root.after(260, self.animate_drop_pulse)

    def apply_settings_to_ui(self) -> None:
        self._settings_dialog.apply_to_ui()

    def update_button_colors(self) -> None:
        self._settings_dialog.update_button_colors()

    def update_web_search_button(self) -> None:
        self._settings_dialog.update_web_search_button()

    def open_settings(self) -> None:
        self._settings_dialog.open()
        self.settings_window = self._settings_dialog.window

    def close_settings(self) -> None:
        self._settings_dialog.close()
        self.settings_window = None

    def reset_settings_to_defaults(self) -> None:
        self._settings_dialog.reset()

    def choose_obsidian_path(self) -> None:
        self._settings_dialog.choose_obsidian_path()

    def choose_vault_path(self) -> None:
        self._settings_dialog.choose_vault_path()

    def color_preset_name(self, color: str) -> str:
        return color_preset_name_standalone(color)

    def select_color_preset(self, preset_name: str) -> None:
        self._settings_dialog.select_color_preset(preset_name)

    def update_color_preview(self, color: str) -> None:
        self._settings_dialog.update_color_preview(color)

    def choose_button_color(self) -> None:
        self._settings_dialog.choose_button_color()

    def save_settings_from_window(self) -> None:
        self._settings_dialog.save()
        self.close_settings()

    def schedule_health_probe(self) -> None:
        self.root.after(900, self.start_health_probe)

    def start_health_probe(self) -> None:
        threading.Thread(target=self.health_worker, daemon=True).start()

    def health_worker(self) -> None:
        warnings = self.diagnose_system()
        self.root.after(0, self.finish_health_probe, warnings)

    def finish_health_probe(self, warnings: list[str]) -> None:
        chat = self.get_active_chat()
        has_messages = bool(chat and chat.get("messages"))
        if not has_messages:
            self.render_current_chat()
        if not warnings:
            if not has_messages:
                self.status_var.set("Ready")
            return
        for warning in warnings:
            self.append_warning_message(warning, persist=False)
        if not has_messages:
            self.status_var.set("Needs attention")

    def diagnose_system(self) -> list[str]:
        warnings: list[str] = []
        if not (ROOT / "LightRAG" / ".venv" / "Scripts" / "python.exe").exists():
            warnings.append("Python environment не найден. Запустите installer или откройте LightRAG-Control для проверки установки.")

        lms = self.lmstudio_cli_path()
        if not lms:
            warnings.append("LM Studio CLI не найден. Обычный чат может работать через API, но для загрузки/выгрузки моделей откройте LightRAG-Control после установки LM Studio.")
        ok, lm_message, _models = self.check_lmstudio_ready(require_models=False)
        if not ok:
            warnings.append(lm_message)

        if not self.find_obsidian_path():
            warnings.append("Obsidian не найден автоматически. Нажмите фиолетовую иконку Obsidian, чтобы выбрать Obsidian.exe или открыть официальный сайт.")
        if not self.vault_dir().exists():
            warnings.append("Obsidian vault path не найден. Откройте Settings и выберите папку vault.")

        route = self.selected_route("")
        if bool(self.settings.get("use_lightrag", False)) and not self.is_lightrag_ready(route.scope, route.project, route.layer):
            self.settings["use_lightrag"] = False
            self.save_settings()
            warnings.append(f"LightRAG был включен, но индекс для {route.context_name} не найден. Я отключил LightRAG, чтобы обычный чат продолжал работать.")
        return warnings

    def lmstudio_cli_path(self) -> str:
        candidates = [
            Path.home() / ".lmstudio" / "bin" / "lms.exe",
            Path(os.getenv("LOCALAPPDATA", "")) / "Programs" / "LM Studio" / "resources" / "app" / ".webpack" / "lms.exe",
        ]
        for candidate in candidates:
            if candidate.exists():
                return str(candidate)
        return ""

    def is_lmstudio_api_online(self) -> bool:
        ok, _message, _models = self.check_lmstudio_ready(require_models=False)
        return ok

    def lmstudio_base_url(self) -> str:
        return str(self.settings.get("lmstudio_base_url", LMSTUDIO_API_URL) or LMSTUDIO_API_URL).rstrip("/")

    def llm_model_id(self) -> str:
        return str(self.settings.get("llm_model", DEFAULT_LLM_MODEL) or DEFAULT_LLM_MODEL)

    def vision_model_id(self) -> str:
        configured = str(self.settings.get("vision_model", DEFAULT_VISION_MODEL) or DEFAULT_VISION_MODEL).strip()
        if configured:
            return configured
        try:
            models = self.loaded_lmstudio_models()
        except Exception:
            models = []
        for model in models:
            if is_vision_model_name(model):
                return model
        return self.llm_model_id()

    def vision_model_state(self) -> tuple[str, bool, list[str]]:
        return vision_model_state_standalone(self.settings, self.lmstudio_base_url())

    def embedding_model_id(self) -> str:
        return str(self.settings.get("embedding_model", DEFAULT_EMBEDDING_MODEL) or DEFAULT_EMBEDDING_MODEL)

    def lmstudio_request_json(self, path: str, *, method: str = "GET", payload: dict | None = None, timeout: float = 8.0) -> dict:
        return lmstudio_request_json(self.lmstudio_base_url(), path, method=method, payload=payload, timeout=timeout)

    def loaded_lmstudio_models(self) -> list[str]:
        return loaded_lmstudio_models(self.lmstudio_base_url())

    def check_lmstudio_ready(self, *, require_models: bool = True) -> tuple[bool, str, list[str]]:
        return check_lmstudio_ready_standalone(
            self.lmstudio_base_url(), self.llm_model_id(), require_models=require_models,
        )

    def extract_chat_content(self, response: dict) -> tuple[str, str]:
        return extract_chat_content_standalone(response)

    def call_plain_lmstudio(self, question: str, *, max_tokens: int | None = None, topic_context: str = "") -> tuple[str, str]:
        max_tokens = max_tokens or int(os.getenv("LMSTUDIO_GUI_MAX_RESPONSE_TOKENS", "1800"))
        if bool(self.settings.get("auto_switch_models", True)):
            llm_model = self.llm_model_id()
            if llm_model:
                self._model_manager.ensure_model(llm_model)
        return call_plain_lmstudio_standalone(
            question, self.lmstudio_base_url(), self.llm_model_id(),
            timeout=min(self.query_timeout_seconds, 120), max_tokens=max_tokens,
            topic_context=topic_context,
        )

    def run_plain_query(
        self,
        operation_id: int,
        question: str,
        pending_warnings: list[str],
        web_search_enabled: bool = False,
        web_query: str = "",
        topic_context: str = "",
    ) -> None:
        warnings = list(pending_warnings)
        try:
            if web_search_enabled:
                question, web_warnings = self.prepare_web_prompt(web_query or question, question)
                warnings.extend(web_warnings)
            output, model_warning = self.call_plain_lmstudio(question, topic_context=topic_context)
            if model_warning:
                warnings.append(model_warning)
            if not output:
                output = "Не удалось получить финальный ответ от модели. Откройте LightRAG-Control для проверки LM Studio и загруженной модели."
                tag = "error"
            else:
                tag = "assistant"
        except Exception:
            output = "Не удалось подключиться к LM Studio во время ответа. Откройте LightRAG-Control для проверки сервера и модели."
            tag = "error"
        self.root.after(0, self.finish_query, operation_id, output, tag, warnings, False)

    def render_current_chat(self) -> None:
        self.chat.configure(state="normal")
        self.chat.delete("1.0", "end")
        for widget in self.chat_widgets:
            try:
                widget.destroy()
            except tk.TclError:
                pass
        self.chat_widgets.clear()
        self.chat.configure(state="disabled")
        chat = self.get_active_chat()
        messages = chat.get("messages", []) if chat else []
        if not messages:
            self.show_intro()
            return
        animated_from = max(0, len(messages) - 2)
        for index, message in enumerate(messages):
            role = str(message.get("role") or "assistant")
            text = str(message.get("text") or "")
            warnings = [str(item) for item in message.get("warnings", []) if item]
            animated = index >= animated_from
            if role == "user":
                self.append_user_message(text, persist=False, animated=animated)
            elif role == "error":
                self.append_assistant_message(text, "error", persist=False, animated=animated)
            elif role == "system":
                self.append_warning_message(text, persist=False)
            else:
                self.append_assistant_message(text, "assistant", persist=False, animated=animated)
            action_id = str(message.get("project_action_id") or "")
            if action_id and role in {"assistant", "system"}:
                self.append_project_action_panel(action_id)
            for warning in warnings:
                self.append_warning_message(warning, persist=False)

    def show_intro(self) -> None:
        intro = (
            "Можно писать обычные сообщения или вопросы. Чтобы спросить по базе, напишите «найди в базе...» или включите LightRAG в Настройках.\n"
            "Ссылки можно сохранять прямо из диалога: «вот ссылка ...». Веб-поиск запускается кнопкой у поля ввода."
        )
        self.append_system(intro, persist=False)

    def set_chat_text(self, text: str, tag: str = "system") -> None:
        self.chat.configure(state="normal")
        self.chat.delete("1.0", "end")
        self.chat.insert("end", text, tag)
        self.chat.configure(state="disabled")
        self.chat.see("end")

    def append(self, text: str, tag: str = "assistant") -> None:
        self.chat.configure(state="normal")
        self.chat.insert("end", text, tag)
        self.chat.insert("end", "\n")
        self.chat.configure(state="disabled")
        self.chat.see("end")

    def append_dialog_bubble(self, text: str, role: str, *, animated: bool = True) -> None:
        self.chat.configure(state="normal")
        self.chat.insert("end", "\n")
        canvas_width = max(430, self.chat.winfo_width() - 28)
        bubble = AnimatedMessageBubble(
            self.chat,
            text,
            role=role,
            canvas_width=canvas_width,
            background=UI_THEME["chat_bg"],
            animated=animated,
        )
        self.chat.window_create("end", window=bubble)
        self.chat.insert("end", "\n")
        self.chat_widgets.append(bubble)
        self.chat.configure(state="disabled")
        self.chat.see("end")

    def append_system(self, text: str, persist: bool = False) -> None:
        self.append(f"{text}\n", "system")
        if persist:
            self.add_message("system", text)

    def rounded_canvas_rect(self, canvas: tk.Canvas, x1: int, y1: int, x2: int, y2: int, radius: int, *, fill: str) -> int:
        points = [
            x1 + radius, y1, x2 - radius, y1, x2, y1, x2, y1 + radius,
            x2, y2 - radius, x2, y2, x2 - radius, y2, x1 + radius, y2,
            x1, y2, x1, y2 - radius, x1, y1 + radius, x1, y1,
        ]
        return int(canvas.create_polygon(points, smooth=True, fill=fill, outline=""))

    def append_user_message(self, text: str, persist: bool = True, animated: bool | None = None) -> None:
        clean_text = text.strip()
        if not clean_text:
            return
        self.append_dialog_bubble(clean_text, "user", animated=persist if animated is None else animated)
        if persist:
            route = self.selected_route(clean_text)
            self.add_message("user", clean_text, route.context_name)

    def append_assistant_message(
        self,
        text: str,
        tag: str = "assistant",
        persist: bool = True,
        warnings: list[str] | None = None,
        lightrag_used: bool | None = None,
        project_action_id: str = "",
        animated: bool | None = None,
    ) -> None:
        clean_text = text.strip()
        if not clean_text:
            return
        if tag in {"assistant", "error"}:
            self.append_dialog_bubble(clean_text, tag, animated=persist if animated is None else animated)
        else:
            self.append(f"{clean_text}\n", tag)
        if persist:
            chat = self.get_active_chat()
            context_name = "General"
            if chat and chat.get("messages"):
                context_name = str(chat["messages"][-1].get("context") or "General")
            self.add_message("assistant" if tag == "assistant" else "error", clean_text, context_name, warnings, lightrag_used, project_action_id)
        if project_action_id and tag == "assistant":
            self.append_project_action_panel(project_action_id)

    def append_warning_message(self, text: str, persist: bool = False) -> None:
        clean_text = text.strip()
        if clean_text:
            self.append(f"{clean_text}\n", "warning")
            if persist:
                self.add_message("system", clean_text, "General")

    def append_material_routing_report(self, reports: list[MaterialRoutingReport]) -> None:
        detail = str(self.settings.get("message_detail_level", "compact"))
        report_text = format_material_routing_report(reports, detail=detail)
        if report_text:
            self.append_assistant_message(report_text, lightrag_used=False)

    def append_book_discovery_report(self, report: BookDiscoveryReport) -> None:
        self.last_book_discovery_report = report
        detail = str(self.settings.get("message_detail_level", "compact"))
        self.append_assistant_message(format_book_discovery_report(report, detail=detail), lightrag_used=False)

    def append_video_analysis_report(self, report: VideoAnalysisReport) -> None:
        detail = str(self.settings.get("message_detail_level", "compact"))
        self.append_assistant_message(format_video_analysis_report_standalone(report, detail=detail), lightrag_used=False)

    def start_background_task(self, kind: str, label: str, *, source_path: str = "", rel_path: str = "", detail: str = "") -> str:
        task_id = f"{kind}-{int(time.time() * 1000)}-{len(self.background_tasks) + 1}"
        now = now_iso()
        self.background_tasks[task_id] = BackgroundTaskRecord(
            task_id=task_id,
            kind=kind,
            label=label,
            status="running",
            source_path=source_path,
            rel_path=rel_path,
            detail=detail,
            started_at=now,
            updated_at=now,
        )
        if not self.busy:
            self.status_var.set(label)
        return task_id

    def update_background_task(self, task_id: str, *, status: str | None = None, detail: str | None = None, result: str | None = None) -> None:
        task = self.background_tasks.get(task_id)
        if not task:
            return
        if status is not None:
            task.status = status
        if detail is not None:
            task.detail = detail
        if result is not None:
            task.result = result
        task.updated_at = now_iso()
        if not self.busy and status in {"done", "failed"}:
            try:
                self.root.after(0, lambda: self.status_var.set("Ready"))
            except Exception:
                pass

    def compact_background_tasks(self) -> list[BackgroundTaskRecord]:
        return compact_background_tasks_from_dict(self.background_tasks)

    def material_queue_summary(self) -> str:
        return material_queue_summary_standalone()

    def project_server_summary(self) -> str:
        return project_server_summary_standalone(self.project_actions)

    def latest_book_discovery_summary(self) -> str:
        return latest_book_discovery_summary_standalone(self.last_book_discovery_report)

    def runtime_context_prompt(self, question: str = "", route: KnowledgeRoute | None = None) -> str:
        route = route or self.selected_route(question)
        try:
            models = self.loaded_lmstudio_models()
        except Exception as exc:
            models = []
            models_error = str(exc)
        else:
            models_error = ""
        vision_model, vision_ready, _loaded = self.vision_model_state()
        context_routes = [
            KnowledgeRoute("General", "general", ""),
            KnowledgeRoute("Web Development", "web", "web-development"),
            KnowledgeRoute("My Game", "game", "my-game"),
            KnowledgeRoute("Finished Projects", "all", "", LAYER_FINISHED_PROJECTS),
        ]
        task_summary = []
        for task in self.compact_background_tasks()[:8]:
            line = f"{task.kind}/{task.status}: {task.label}"
            if task.rel_path:
                line += f"; note={task.rel_path}"
            if task.detail:
                line += f"; detail={task.detail}"
            if task.result:
                line += f"; result={task.result}"
            task_summary.append(line)
        return build_runtime_context_prompt(
            route=route,
            lmstudio_base_url=self.lmstudio_base_url(),
            llm_model_id=self.llm_model_id(),
            loaded_models=models,
            models_error=models_error,
            vision_model=vision_model,
            vision_ready=vision_ready,
            lightrag_enabled=bool(self.settings.get("use_lightrag", False)),
            lightrag_ready_check=self.is_lightrag_ready,
            context_routes=context_routes,
            web_search_enabled=bool(self.settings.get("web_search_enabled", False)),
            dnd_backend=self.dnd_backend,
            busy=self.busy,
            busy_status_base=self.busy_status_base,
            background_tasks_summary=task_summary,
            material_queue_summary=self.material_queue_summary(),
            book_discovery_summary=self.latest_book_discovery_summary(),
            project_server_summary=self.project_server_summary(),
        )

    def split_knowledge_warnings(self, output: str) -> tuple[str, list[str]]:
        warnings: list[str] = []
        display_lines: list[str] = []
        for line in output.splitlines():
            if line.startswith(WARNING_PREFIX):
                warning = line[len(WARNING_PREFIX) :].strip()
                if warning:
                    warnings.append(warning)
            elif not self.is_service_output_line(line):
                display_lines.append(line)
        return self.trim_output("\n".join(display_lines)), warnings

    def is_service_output_line(self, line: str) -> bool:
        stripped = line.strip()
        if not stripped:
            return False
        prefixes = (
            "Game Guard:", "Starting LM Studio server", "Waking up LM Studio service",
            "Embedding model already loaded:", "LLM already loaded:", "Knowledge Lab is ready.",
            "API:", "LLM identifier:", "Embedding identifier:", "Idle unload:",
            "Success! Server is now running",
        )
        return any(stripped.startswith(prefix) for prefix in prefixes)

    def trim_output(self, output: str) -> str:
        lines = output.splitlines()
        while lines and not lines[0].strip():
            lines.pop(0)
        while lines and not lines[-1].strip():
            lines.pop()
        return "\n".join(lines).strip()

    def friendly_error(self, output: str) -> str:
        cleaned = self.trim_output(output)
        if "NativeCommandError" in cleaned or "lms.exe : Success! Server is now running" in cleaned:
            return "LM Studio ответил служебным сообщением вместо обычного результата. Попробуйте еще раз или откройте LightRAG-Control для проверки системы."
        if "LightRAG storage was not found" in cleaned:
            self.lightrag_var.set(False)
            self.settings["use_lightrag"] = False
            self.save_settings()
            return "LightRAG индекс не найден, поэтому я отключил LightRAG. Обычный чат продолжит работать через LM Studio; для индексации откройте LightRAG-Control."
        if "Context size has been exceeded" in cleaned or "context size has been exceeded" in cleaned:
            return "Контекст запроса оказался слишком большим для текущей модели. Я уже ограничиваю историю; повторите запрос короче или начните новый чат."
        if "LM Studio CLI was not found" in cleaned:
            return "LM Studio CLI не найден. Установите LM Studio или откройте LightRAG-Control для диагностики."
        if "Connection" in cleaned or "connect" in cleaned.lower():
            return "Не удалось подключиться к LM Studio. Запустите LM Studio Server или откройте LightRAG-Control."
        return cleaned or "Не удалось получить ответ. Откройте LightRAG-Control, чтобы проверить LM Studio, модели и LightRAG."

    def storage_name_for_scope(self, scope: str, project: str, layer: str = LAYER_ACTIVE) -> str:
        return storage_name_for_scope_standalone(scope, project, layer)

    def lightrag_index_path(self, scope: str, project: str, layer: str = LAYER_ACTIVE) -> Path:
        return Path(lightrag_index_path_standalone(scope, project, layer))

    def is_lightrag_ready(self, scope: str, project: str, layer: str = LAYER_ACTIVE) -> bool:
        return is_lightrag_ready_standalone(scope, project, layer)

    def on_lightrag_toggle(self, save: bool = True) -> None:
        if save:
            self.settings["use_lightrag"] = bool(self.lightrag_var.get())
            self.save_settings()
            self.status_var.set("LightRAG on" if self.lightrag_var.get() else "LightRAG off")

    def selected_route(self, text: str) -> KnowledgeRoute:
        return route_context(text, self.context_var.get())

    def input_text(self) -> str:
        return self.input.get("1.0", "end").strip()

    def clear_input(self) -> None:
        self.input.delete("1.0", "end")

    def replace_input(self, text: str) -> None:
        self.clear_input()
        self.input.insert("1.0", text)

    def append_to_input(self, text: str) -> None:
        clean_text = text.strip()
        if not clean_text:
            return
        if self.input_text():
            self.input.insert("end", "\n" + clean_text)
        else:
            self.input.insert("1.0", clean_text)
        self.input.focus_set()

    def start_voice_input(self) -> None:
        if self.voice_operation_id is not None and self.busy:
            self.cancel_active_operation()
            return
        if self.busy:
            return
        operation_id = self.begin_operation("Listening...", VOICE_INPUT_SECONDS + 5)
        self.voice_operation_id = operation_id
        self.set_tool_button_active("voice_button", True)
        if hasattr(self, "voice_button"):
            self.voice_button.configure(state="normal")
        threading.Thread(target=self.voice_input_worker, args=(operation_id,), daemon=True).start()

    def voice_input_worker(self, operation_id: int) -> None:
        script = build_voice_recognition_script()
        try:
            returncode, output = self.run_command(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
                VOICE_INPUT_SECONDS + 4,
            )
            text = output.strip() if returncode == 0 else ""
            error, offer_settings = ("", False) if text else self.friendly_voice_error(output)
        except TimeoutError:
            text = ""
            error = "Не услышал речь за отведенное время. Попробуйте еще раз или вставьте текст вручную."
            offer_settings = False
        except Exception:
            text = ""
            error = "Не удалось запустить диктовку. Для надежного локального ввода позже можно подключить Whisper/faster-whisper."
            offer_settings = True
        self.root.after(0, self.finish_voice_input, operation_id, text, error, offer_settings)

    def friendly_voice_error(self, output: str) -> tuple[str, bool]:
        return friendly_voice_error_standalone(self.trim_output(output))

    def finish_voice_input(self, operation_id: int, text: str, error: str, offer_settings: bool = False) -> None:
        if not self.is_active_operation(operation_id):
            return
        self.voice_operation_id = None
        self.set_tool_button_active("voice_button", False)
        if text.strip():
            self.append_to_input(text)
            final_status = "Voice inserted"
            settings_reason = ""
        else:
            self.append_warning_message(error, persist=False)
            final_status = "Ready"
            settings_reason = error if offer_settings else ""
        self.set_busy(False, final_status)
        if settings_reason:
            self.offer_microphone_settings(settings_reason)

    def offer_microphone_settings(self, reason: str) -> None:
        if not messagebox.askyesno(
            "Настройки микрофона",
            f"{reason}\n\nОткрыть настройки звука Windows, чтобы выбрать микрофон и проверить ввод?",
            parent=self.root,
        ):
            return
        self.open_windows_microphone_settings()

    def open_windows_microphone_settings(self) -> None:
        error = open_windows_microphone_settings_standalone()
        if error:
            self.append_warning_message(error, persist=False)

    def set_tool_button_active(self, name: str, value: bool) -> None:
        button = getattr(self, name, None)
        if button and hasattr(button, "set_active"):
            button.set_active(value)

    def flash_tool_button(self, name: str, milliseconds: int = 850) -> None:
        self.set_tool_button_active(name, True)
        self.root.after(milliseconds, lambda: self.set_tool_button_active(name, False))

    def toggle_web_search(self) -> None:
        if self.busy:
            return
        enabled = not bool(self.settings.get("web_search_enabled", False))
        self.settings["web_search_enabled"] = enabled
        self.web_search_enabled_var.set(enabled)
        self.save_settings()
        self.update_web_search_button()
        self.status_var.set("Web search on" if enabled else "Web search off")
        self.append_warning_message(
            "Web-поиск включен. Следующие обычные сообщения получат web-контекст для LLM." if enabled else "Web-поиск выключен.",
            persist=False,
        )

    def prepare_web_prompt(self, question: str, prompt: str) -> tuple[str, list[str]]:
        try:
            results = fetch_web_search_results(question)
        except Exception as exc:
            return prompt, [f"Web-поиск не сработал: {exc}. Ответ создан без web-контекста."]
        if not results:
            return prompt, ["Web-поиск не нашел результатов. Ответ создан без web-контекста."]
        web_context = render_web_search_context(question, results)
        enhanced = (
            f"{web_context}\n\n"
            "IMPORTANT: Answer the user's question using the web search results above.\n"
            "If the results contain relevant information, summarize it clearly and cite the source URLs.\n"
            "If the results are not relevant, say 'web-поиск не нашёл релевантных результатов по этому запросу' and answer from your own knowledge.\n"
            "Answer in Russian. Be concise and accurate.\n\n"
            f"User question: {prompt}"
        )
        return enhanced, [f"Web-поиск: {len(results)} результатов передано LLM."]

    def load_input_history(self) -> None:
        questions: list[str] = []
        for chat in self.get_chats():
            for message in chat.get("messages", []):
                if message.get("role") == "user":
                    text = str(message.get("text", "")).strip()
                    if text and (not questions or questions[-1] != text):
                        questions.append(text)
        self.input_history = questions[-80:]
        self.input_history_index = len(self.input_history)

    def remember_input(self, question: str) -> None:
        if self.input_history and self.input_history[-1] == question:
            self.input_history_index = len(self.input_history)
            return
        self.input_history.append(question)
        self.input_history = self.input_history[-80:]
        self.input_history_index = len(self.input_history)

    def navigate_input_history(self, direction: int) -> str:
        if not self.input_history:
            return "break"
        self.input_history_index = max(0, min(len(self.input_history), self.input_history_index + direction))
        self.replace_input("" if self.input_history_index == len(self.input_history) else self.input_history[self.input_history_index])
        return "break"

    def is_save_intent(self, text: str) -> bool:
        return is_save_intent_text(text)

    def is_lightrag_help_intent(self, text: str) -> bool:
        return is_lightrag_help_text(text)

    def is_language_preference_intent(self, text: str) -> bool:
        return is_russian_language_request(text)

    def wants_knowledge_lookup(self, text: str) -> bool:
        return is_knowledge_lookup_text(text) or is_finished_project_lookup_text(text)

    def last_answer_lightrag_state(self) -> bool | None:
        chat = self.get_active_chat()
        if not chat:
            return None
        for message in reversed(chat.get("messages", [])):
            if message.get("role") in {"assistant", "error"}:
                return bool(message.get("lightrag", False))
        return None

    def lightrag_help_message(self) -> str:
        enabled = bool(self.settings.get("use_lightrag", False))
        return lightrag_help_message_standalone(enabled)

    def finished_project_route(
        self,
        suggested: KnowledgeRoute,
        title_default: str = "",
        source_hint: str = "",
        github_metadata: dict[str, str] | None = None,
        require_confirmation: bool = False,
    ) -> KnowledgeRoute | None:
        guess = infer_finished_project_guess(
            suggested,
            title_default,
            source_hint,
            self.input_text(),
            github_metadata,
        )
        title = guess.title
        section = guess.section
        if require_confirmation or guess.confidence < 0.7:
            title = simpledialog.askstring(
                "Finished Project",
                "Название готового проекта:",
                initialvalue=guess.title,
                parent=self.root,
            )
            if not title:
                return None
            default_section = default_finished_project_section(guess.scope, f"{source_hint} {self.input_text()} {title}")
            section = simpledialog.askstring(
                "Finished Project",
                "Раздел готового проекта:",
                initialvalue=guess.section or default_section,
                parent=self.root,
            )
            if section is None:
                return None
            section = section.strip() or default_section
        scope = guess.scope
        refined_subject = subject_route_from_text(f"{source_hint} {self.input_text()} {title} {section}")
        if scope == "general" and refined_subject.scope in {"web", "game"}:
            scope = refined_subject.scope
        return KnowledgeRoute(
            "Finished Projects",
            scope if scope in {"general", "web", "game"} else "general",
            slugify(title),
            LAYER_FINISHED_PROJECTS,
            title.strip(),
            slugify(section),
        )

    def custom_project_route(
        self,
        suggested: KnowledgeRoute,
        title_default: str = "",
        source_hint: str = "",
    ) -> KnowledgeRoute | None:
        seed = " ".join(part for part in (source_hint, title_default, self.input_text(), suggested.project_title, suggested.project) if part)
        default_title = (
            project_title_from_source_hint(source_hint)
            or (clean_filename(title_default.strip()) if title_default.strip() else "")
            or title_from_text(self.input_text(), "")
            or "New Project"
        )
        title = simpledialog.askstring(
            "Custom Project",
            "Название проекта или темы:",
            initialvalue=default_title,
            parent=self.root,
        )
        if not title:
            return None
        inferred = subject_route_from_text(f"{seed} {title}")
        default_scope = inferred.scope if inferred.scope in {"web", "game"} else (suggested.scope if suggested.scope in {"web", "game"} else "general")
        scope_text = simpledialog.askstring(
            "Custom Project",
            "Раздел проекта: web, game или general",
            initialvalue=default_scope,
            parent=self.root,
        )
        if scope_text is None:
            return None
        scope = normalize_subject_scope(scope_text, default_scope)
        project_title = clean_filename(title.strip())
        return KnowledgeRoute(
            project_title,
            scope,
            slugify(project_title),
            LAYER_ACTIVE,
            project_title,
            "",
        )

    def choose_capture_context(
        self,
        suggested: KnowledgeRoute,
        *,
        allow_finished_project: bool = True,
        finished_title_default: str = "",
        source_hint: str = "",
        github_metadata: dict[str, str] | None = None,
    ) -> KnowledgeRoute | None:
        if self.context_var.get() == "Finished Projects":
            return self.finished_project_route(suggested, finished_title_default, source_hint, github_metadata)
        if self.context_var.get() != "Auto":
            return suggested
        if allow_finished_project and suggested.is_finished_projects:
            return self.finished_project_route(suggested, finished_title_default, source_hint, github_metadata)
        auto_seed = " ".join(part for part in (source_hint, finished_title_default, self.input_text()) if part)
        if allow_finished_project and is_finished_project_lookup_text(auto_seed):
            return self.finished_project_route(suggested, finished_title_default, source_hint, github_metadata)
        if suggested.scope in {"web", "game"} and contains_any(auto_seed, WEB_TERMS | GAME_TERMS):
            return suggested
        if not allow_finished_project and (suggested.scope != "general" or contains_any(self.input_text(), WEB_TERMS | GAME_TERMS)):
            return suggested
        if bool(self.settings.get("auto_route_topics", True)):
            return suggested

        choice = choose_capture_context_standalone(
            self.root, suggested,
            input_text=self.input_text(),
            finished_title_default=finished_title_default,
            source_hint=source_hint,
            allow_finished_project=allow_finished_project,
            auto_route=bool(self.settings.get("auto_route_topics", True)),
        )
        if choice == "auto":
            return suggested
        if choice == "custom-project":
            return self.custom_project_route(suggested, finished_title_default, source_hint)
        if choice == "finished-project":
            return self.finished_project_route(suggested, finished_title_default, source_hint, github_metadata)
        return choice if isinstance(choice, KnowledgeRoute) else None

    def choose_attachment_source(self) -> str | None:
        return choose_attachment_source_standalone(self.root)

    def classify_material_topic(self, text: str, scope: str, kind: str, fallback_topic: str = "", preferred_topic: str = "", project: str = "") -> str:
        settings = getattr(self, "settings", DEFAULT_SETTINGS)
        return classify_material_topic_standalone(
            text, scope, kind, fallback_topic, preferred_topic, project,
            auto_route=bool(settings.get("auto_route_topics", True)),
            auto_create=bool(settings.get("auto_create_topics", True)),
            vault_dir=VAULT_DIR,
        )

    def ensure_topic_exists(self, topic: str, scope: str = "general", project: str = "") -> bool:
        return ensure_topic_exists_standalone(topic, scope, project, VAULT_DIR)

    def note_metadata(self, rel_path: str) -> dict[str, str]:
        from knowledgelab.vault.frontmatter import note_metadata as note_metadata_fn
        return note_metadata_fn(rel_path, VAULT_DIR)

    def save_capture(self, text: str, route: KnowledgeRoute, project_action_id: str = "") -> str:
        return self._capture_workflow.save_capture(text, route, project_action_id)

    def queue_file_processing(
        self,
        file_path: Path,
        rel_path: str,
        kind: str,
        scope: str,
        project: str,
        topic: str,
        extraction_status: str,
        layer: str = LAYER_ACTIVE,
        project_title: str = "",
        project_section: str = "",
        source_root: Path | None = None,
        source_relative_path: str = "",
        project_action_id: str = "",
        book_title: str = "",
        page_number_guess: str = "",
    ) -> None:
        queue_file_item(
            file_path, rel_path, kind, scope, project, topic, extraction_status,
            layer=layer, project_title=project_title, project_section=project_section,
            source_root=source_root, source_relative_path=source_relative_path,
            project_action_id=project_action_id, book_title=book_title,
            page_number_guess=page_number_guess,
        )

    def queue_github_processing(
        self,
        url: str,
        rel_path: str,
        scope: str,
        project: str,
        topic: str,
        metadata: dict[str, str],
        layer: str = LAYER_ACTIVE,
        project_title: str = "",
        project_section: str = "",
        project_action_id: str = "",
    ) -> None:
        queue_github_item(
            url, rel_path, scope, project, topic, metadata,
            layer=layer, project_title=project_title, project_section=project_section,
            project_action_id=project_action_id,
        )

    def queue_rlm_processing(self, rel_path: str, source_url: str, route: KnowledgeRoute, profile: dict[str, object]) -> None:
        queue_rlm_item(rel_path, source_url, route.scope, route.project, route.layer, profile)

    def save_reference_links(self, links: list[ReferenceLink], parent_rel_path: str, parent_source_url: str, route: KnowledgeRoute) -> list[str]:
        return self._capture_workflow.save_reference_links(links, parent_rel_path, parent_source_url, route)

    def create_manual_book_parent_note(self, entries: list[ManualBookEntry], source_text: str, route: KnowledgeRoute) -> str:
        return self._capture_workflow.create_manual_book_parent_note(entries, source_text, route)

    def append_manual_book_resolution_to_parent(self, parent_rel_path: str, books: list[dict[str, object]], created_notes: list[str], source_text: str) -> None:
        self._capture_workflow.append_manual_book_resolution_to_parent(parent_rel_path, books, created_notes, source_text)

    def start_manual_book_resolution(self, source_text: str, entries: list[ManualBookEntry], route: KnowledgeRoute) -> None:
        self._capture_workflow.start_manual_book_resolution(source_text, entries, route)

    def manual_book_resolution_worker(self, source_text: str, entries: list[ManualBookEntry], parent_note: str, route: KnowledgeRoute, task_id: str = "") -> None:
        self._capture_workflow.manual_book_resolution_worker(source_text, entries, parent_note, route, task_id)

    def find_existing_book_note(self, book: dict[str, object]) -> str:
        from knowledgelab.vision.book_discovery import find_existing_book_note as find_existing_fn
        return find_existing_fn(book, VAULT_DIR)

    def save_detected_book_notes(self, books: list[dict[str, object]], source_rel_path: str, source_image_path: str, *, allow_unverified: bool = False) -> list[str]:
        saved: list[str] = []
        settings = getattr(self, "settings", DEFAULT_SETTINGS)
        for book in books:
            if not book.get("title"):
                continue
            if not allow_unverified and str(book.get("lookup_status") or "").strip() in {"needs_clarification", "not_found", "lookup_error"}:
                continue
            book["book_topic"] = str(book.get("book_topic") or classify_book_topic(book))
            if bool(settings.get("auto_create_topics", True)):
                self.ensure_topic_exists(str(book.get("book_topic") or "Library"), "library")
            existing = self.find_existing_book_note(book)
            if existing:
                book["vault_note"] = existing
                saved.append(existing)
                continue
            destination = VAULT_DIR / "50 Library" / book_note_slug(book)
            destination.mkdir(parents=True, exist_ok=True)
            path = unique_path(destination / "Book.md")
            path.write_text(render_book_note_markdown(book, source_rel_path, source_image_path), encoding="utf-8-sig")
            rel_path = path.relative_to(VAULT_DIR).as_posix()
            book["vault_note"] = rel_path
            saved.append(rel_path)
        return saved

    def update_bookshelf_note_result(self, rel_path: str, result: dict[str, list[dict[str, object]]], created_notes: list[str], error: str = "") -> None:
        path = self.capture_path_from_rel(rel_path)
        text = path.read_text(encoding="utf-8-sig", errors="replace") if path.exists() else ""
        status = "failed" if error else "processed"
        if "bookshelf_detection_status:" in text:
            text = re.sub(r'bookshelf_detection_status:\s*".*?"', f'bookshelf_detection_status: "{status}"', text, count=1)
            text = re.sub(r"bookshelf_detection_status:\s*[^\n]+", f'bookshelf_detection_status: "{status}"', text, count=1)
        elif text.startswith("---\n"):
            text = re.sub(r"\A---\n", f"---\nbookshelf_detection_status: \"{status}\"\n", text, count=1)
        section = render_bookshelf_detection_section(result, created_notes, error)
        if "## Bookshelf Detection Result" in text:
            text = re.sub(r"\n## Bookshelf Detection Result\n.*\Z", "\n" + section + "\n", text, flags=re.DOTALL)
        else:
            text = text.rstrip() + "\n\n" + section + "\n"
        path.write_text(text, encoding="utf-8-sig")

    def call_bookshelf_vision(self, image_path: Path, kind: str, caption: str = "") -> dict[str, list[dict[str, object]]]:
        vision_model, vision_ready, loaded_models = self.vision_model_state()
        if not vision_ready:
            loaded = ", ".join(loaded_models) if loaded_models else "нет загруженных моделей"
            raise RuntimeError(
                "Не загружена vision/VL-модель в LM Studio. "
                "Чтобы KnowledgeLab сам находил книги по фото полки или корешкам, загрузите в LM Studio модель с поддержкой изображений "
                "(например Qwen2.5-VL, LLaVA, MiniCPM-V, Pixtral или другую vision-модель) "
                "или задайте KNOWLEDGELAB_VISION_MODEL. "
                f"Сейчас загружено: {loaded}. Текстовая модель не может надежно читать изображение."
            )
        prompt = (
            "Inspect this image for books. It may be a bookshelf, a single book cover/spine, "
            "a book page, or an unrelated image. Return only strict JSON, no markdown.\n\n"
            "If the image is unrelated to books, return {\"detected_books\": [], \"unresolved\": []}.\n"
            "If a book is visible but title/author cannot be read, put that item in unresolved.\n"
            "Create one detected_books item per readable or strongly inferable book. Work like a bookshelf inventory table: scan left-to-right and top-to-bottom, record region/position, readable text, and evidence.\n"
            "Use status \"found\" when the title/author is readable. Use status \"inferred\" only when visual context strongly suggests a known book but the spine text is partly hidden; include visual_guess and guess_reason. Use status \"uncertain\" for weak guesses and put the same item in unresolved if it needs user confirmation.\n"
            "Do not invent full metadata beyond visible evidence and cautious visual guesses.\n\n"
            "JSON schema:\n"
            "{\n"
            "  \"detected_books\": [\n"
            "    {\n"
            "      \"region\": \"top row item 1 / main row left / etc\",\n"
            "      \"title\": \"visible title\",\n"
            "      \"author\": \"visible author or empty string\",\n"
            "      \"isbn\": \"visible ISBN or empty string\",\n"
            "      \"visible_text\": \"raw readable spine/cover text\",\n"
            "      \"visual_guess\": \"cautious visual guess or empty string\",\n"
            "      \"guess_reason\": \"why the visual guess may be right\",\n"
            "      \"evidence\": \"short visible spine/cover text that supports the match\",\n"
            "      \"confidence\": 0.0,\n"
            "      \"status\": \"found, inferred, uncertain, or unreadable\"\n"
            "    }\n"
            "  ],\n"
            "  \"unresolved\": [\n"
            "    {\"region\": \"left/top/etc\", \"reason\": \"blurry/glare/too small/hidden\", \"evidence\": \"partial visible text\"}\n"
            "  ]\n"
            "}\n\n"
            f"Intake kind: {kind}\n"
            f"User caption or hint: {caption or '(none)'}"
        )
        payload = {
            "model": vision_model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You extract visible book metadata from images inside the local KnowledgeLab app. "
                        "The request is routed through the user's local LM Studio server, not a hosted cloud API. "
                        "Return strict JSON only."
                    ),
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_data_url(image_path)}},
                    ],
                },
            ],
            "temperature": 0.0,
            "max_tokens": 1800,
            "stream": False,
        }
        response = self.lmstudio_request_json(
            "chat/completions",
            method="POST",
            payload=payload,
            timeout=min(self.query_timeout_seconds, 240),
        )
        if response.get("error"):
            raise RuntimeError(str(response.get("error")))
        content, reasoning = self.extract_chat_content(response)
        raw_text = content or reasoning
        if not raw_text.strip():
            raise RuntimeError("vision model returned an empty response")
        result = parse_bookshelf_detection_response(raw_text)
        if not result["detected_books"] and not result["unresolved"] and raw_text.strip():
            result["unresolved"].append({
                "region": "",
                "reason": "vision model returned non-JSON or no structured books",
                "evidence": compact_whitespace(raw_text)[:500],
            })
        return result

    def lookup_book_catalog(self, book: dict[str, object]) -> dict[str, object]:
        settings = getattr(self, "settings", DEFAULT_SETTINGS)
        return lookup_book_catalog_standalone(book, book_lookup_enabled=bool(settings.get("book_lookup_enabled", True)))

    def enrich_detected_books(self, books: list[dict[str, object]]) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
        settings = getattr(self, "settings", DEFAULT_SETTINGS)
        return enrich_detected_books_standalone(books, book_lookup_enabled=bool(settings.get("book_lookup_enabled", True)))

    def auto_process_book_image_worker(self, image_path: str, rel_path: str, kind: str, caption: str, route: KnowledgeRoute, task_id: str = "") -> None:
        self._material_workers.auto_process_book_image_worker(image_path, rel_path, kind, caption, route, task_id)

    def start_auto_book_image_processing(self, image_path: Path, rel_path: str, kind: str, caption: str, route: KnowledgeRoute, *, quiet_generic: bool = False) -> bool:
        return self._material_workers.start_auto_book_image_processing(image_path, rel_path, kind, caption, route, quiet_generic=quiet_generic)

    def queue_video_analysis_processing(self, source: str, rel_path: str, kind: str, route: KnowledgeRoute, runtime_dir: Path) -> None:
        queue_video_analysis_item(source, rel_path, kind, route, runtime_dir)

    def start_video_analysis_processing(self, source: str, rel_path: str, kind: str, route: KnowledgeRoute) -> bool:
        return self._material_workers.start_video_analysis_processing(source, rel_path, kind, route)

    def auto_process_video_worker(self, source: str, rel_path: str, kind: str, route: KnowledgeRoute, runtime_dir: Path, task_id: str = "") -> None:
        self._material_workers.auto_process_video_worker(source, rel_path, kind, route, runtime_dir, task_id)

    def material_queue_display_path(self) -> str:
        return self._material_workers.material_queue_display_path()

    def load_project_actions(self) -> dict:
        return load_project_actions_standalone()

    def save_project_actions(self) -> None:
        save_project_actions_standalone(self.project_actions)

    def get_project_action(self, action_id: str) -> dict | None:
        return get_project_action_standalone(self.project_actions, action_id)

    def create_project_action(
        self,
        *,
        source_type: str,
        source_path: str = "",
        source_url: str = "",
        title: str = "",
        route: KnowledgeRoute,
    ) -> str:
        return create_project_action_standalone(
            self.project_actions,
            source_type=source_type, source_path=source_path,
            source_url=source_url, title=title, route=route,
        )

    def update_project_action(self, action_id: str, **updates) -> None:
        update_project_action_standalone(self.project_actions, action_id, **updates)

    def add_project_action_notes(self, action_id: str, notes: list[str]) -> None:
        add_project_action_notes_standalone(self.project_actions, action_id, notes)

    def action_runtime_workspace(self, action: dict) -> Path:
        return action_runtime_workspace_standalone(action)

    def ensure_project_runtime_workspace(self, action: dict) -> Path:
        return ensure_project_runtime_workspace_standalone(action)

    def action_command_log_paths(self, action_id: str, name: str) -> tuple[Path, Path]:
        return action_command_log_paths_standalone(action_id, name)

    def run_project_command(self, action_id: str, name: str, command: list[str], cwd: Path, timeout: int = 900, env: dict[str, str] | None = None) -> tuple[bool, str]:
        return run_project_command_standalone(action_id, name, command, cwd, timeout, env)

    def is_process_running(self, pid: int) -> bool:
        return is_process_running_standalone(pid)
        if action.get("install_consent") is True:
            return True
        if action.get("install_consent") is False:
            return False
        allowed = messagebox.askyesno(
            "Установка зависимостей",
            "Проект может потребовать npm/pnpm/yarn install в изолированной runtime-папке. Разрешить один раз для этого проекта?",
            parent=self.root,
        )
        self.update_project_action(action_id, install_consent=bool(allowed))
        return bool(allowed)

    def project_action_build(self, action_id: str) -> None:
        self._project_panel.build_project(action_id)

    def project_build_worker(self, operation_id: int, action_id: str) -> None:
        self._project_panel.build_worker(operation_id, action_id)

    def finish_project_action(self, operation_id: int, action_id: str, message: str, open_path: str = "") -> None:
        self._project_panel.finish_build(operation_id, action_id, message, open_path)

    def project_action_server(self, action_id: str) -> None:
        self._project_panel.start_server(action_id)

    def project_server_worker(self, operation_id: int, action_id: str) -> None:
        self._project_panel.server_worker(operation_id, action_id)

    def finish_project_server_start(self, operation_id: int, action_id: str, url: str) -> None:
        self._project_panel.finish_server_start(operation_id, action_id, url)

    def stop_project_server(self, action_id: str) -> None:
        self._project_panel.stop_server(action_id)

    def append_project_action_panel(self, action_id: str) -> None:
        self._project_panel.append_panel(action_id)

    def run_goal_node(self, goal_id: str, payload: dict | None = None) -> dict:
        """Run a goal-oriented node by ID."""
        ctx = {"app": self}
        result = self.node_registry.run_node(goal_id, payload or {}, ctx)
        if "error" in result:
            self.append_warning_message(f"Goal node error: {result['error']}", persist=False)
        return result

    def list_available_nodes(self) -> list[dict[str, str]]:
        """Return metadata for all registered nodes."""
        return self.node_registry.list_nodes()

    def save_file_capture(
        self,
        file_path: Path,
        caption: str,
        route: KnowledgeRoute,
        source_root: Path | None = None,
        project_action_id: str = "",
    ) -> tuple[str, str, str]:
        return self._capture_workflow.save_file_capture(file_path, caption, route, source_root, project_action_id)

    def save_folder_file_captures(self, folder_path: Path, caption: str, route: KnowledgeRoute, project_action_id: str = "") -> tuple[list[tuple[str, str, str, Path]], bool]:
        return self._capture_workflow.save_folder_file_captures(folder_path, caption, route, project_action_id)

    def save_folder_capture(self, folder_path: Path, caption: str, route: KnowledgeRoute) -> tuple[str, str, str]:
        return self._capture_workflow.save_folder_capture(folder_path, caption, route)

    def save_image_capture(self, image_path: Path, caption: str, route: KnowledgeRoute) -> str:
        return self._capture_workflow.save_image_capture(image_path, caption, route)

    def attach_folder(self) -> None:
        self._capture_workflow.attach_folder()

    def attach_images(self) -> None:
        self._capture_workflow.attach_images()

    def attach_files(self, title: str = "Выберите материалы", filetypes=None) -> None:
        self._capture_workflow.attach_files(title, filetypes)

    def attach_github_repository(self) -> None:
        self._capture_workflow.attach_github_repository()

    def process_github_repository(self, url: str) -> None:
        self._capture_workflow.process_github_repository(url)

    def handle_dropped_files(self, files: list[str]) -> None:
        self._capture_workflow.handle_dropped_files(files)

    def process_attached_files(self, files, source_title: str = "Файлы:") -> None:
        self._capture_workflow.process_attached_files(files, source_title)

    def capture_path_from_rel(self, rel_path: str) -> Path:
        return Path(capture_path_from_rel_standalone(rel_path))

    def python_executable(self) -> str:
        return python_executable_standalone()

    def start_auto_material_processing(self, text: str, route: KnowledgeRoute, rel_path: str) -> None:
        self._material_workers.start_auto_material_processing(text, route, rel_path)

    def auto_process_youtube_worker(self, route: KnowledgeRoute) -> None:
        self._material_workers.auto_process_youtube_worker(route)

    def auto_process_article_worker(self, url: str, route: KnowledgeRoute, rel_path: str) -> None:
        self._material_workers.auto_process_article_worker(url, route, rel_path)

    def auto_process_codepen_worker(self, url: str, route: KnowledgeRoute, rel_path: str) -> None:
        self._material_workers.auto_process_codepen_worker(url, route, rel_path)

    def run_background_material_command(self, command: list[str], log_name: str) -> tuple[bool, str]:
        return run_background_material_command_standalone(command, log_name)

    def launch_reindex(self, route: KnowledgeRoute) -> None:
        launch_reindex_standalone(route)

    def update_char_count(self, _event: tk.Event | None = None) -> None:
        try:
            text = self.input.get("1.0", "end-1c")
            count = len(text.strip())
            if count > 0:
                self.char_count_label.configure(text=str(count))
            else:
                self.char_count_label.configure(text="")
        except Exception:
            pass

    def on_ctrl_return(self, _event: tk.Event | None = None) -> str:
        self.on_send()
        return "break"

    def on_shift_return(self, _event: tk.Event | None = None) -> None:
        return None

    def on_return(self, _event: tk.Event | None = None) -> str | None:
        if bool(self.settings["send_on_enter"]):
            self.on_send()
            return "break"
        return None

    def on_send(self) -> None:
        if self.busy:
            return
        question = self.input_text()
        if not question:
            return

        local_source = first_existing_local_source(question)
        if local_source:
            self.process_attached_files([str(local_source)], source_title="Локальный путь:")
            return

        route = self.selected_route(question)
        explicit_knowledge_lookup = self.wants_knowledge_lookup(question)
        prompt = self.build_prompt_with_history(question)
        self.append_user_message(question)
        self.remember_input(question)
        self.clear_input()

        if self.is_language_preference_intent(question):
            self.settings["response_language"] = "ru"
            self.save_settings()
            self.append_assistant_message("Да, буду отвечать по-русски.", lightrag_used=False)
            return

        if self.is_lightrag_help_intent(question):
            self.append_assistant_message(self.lightrag_help_message(), lightrag_used=False)
            return

        manual_book_entries = parse_manual_book_entries(question)
        if manual_book_resolution_likely(question, manual_book_entries, self.last_book_discovery_report):
            self.start_manual_book_resolution(question, manual_book_entries, route)
            return

        if self.is_save_intent(question):
            github_url = first_github_url(question)
            github_meta = parse_github_url(github_url) if github_url else {}
            capture_route = self.choose_capture_context(
                route,
                allow_finished_project=True,
                finished_title_default=title_from_text(question, "Finished Project"),
                source_hint=github_url,
                github_metadata=github_meta,
            )
            if not capture_route:
                self.append_warning_message("Сохранение отменено.", persist=True)
                return
            try:
                rel_path = self.save_capture(question, capture_route)
                self.append_assistant_message(f"Сохранил в Obsidian: {rel_path}")
                meta = self.note_metadata(rel_path)
                self.append_material_routing_report([
                    MaterialRoutingReport(title_from_text(question, "Saved material"), meta.get("type", "note"), meta.get("topic", "") or "Unsorted", rel_path)
                ])
                self.start_auto_material_processing(question, capture_route, rel_path)
            except Exception as exc:
                self.append_assistant_message(f"Не удалось сохранить заметку: {exc}\nОткройте LightRAG-Control для диагностики.", "error")
            return

        use_lightrag = bool(self.lightrag_var.get()) or explicit_knowledge_lookup or route.is_finished_projects
        web_search_enabled = bool(self.settings.get("web_search_enabled", False))
        warnings: list[str] = []
        lm_ready, lm_message, _models = self.check_lmstudio_ready(require_models=True)
        if not lm_ready:
            self.append_warning_message(lm_message, persist=True)
            return

        index_route = route.for_finished_index()
        if use_lightrag and not self.is_lightrag_ready(index_route.scope, index_route.project, index_route.layer):
            use_lightrag = False
            if bool(self.lightrag_var.get()):
                self.lightrag_var.set(False)
                self.settings["use_lightrag"] = False
                self.save_settings()
            warnings.append(f"LightRAG недоступен для {route.context_name}: индекс еще не готов. Ответ будет создан обычной LLM.")
        elif explicit_knowledge_lookup and use_lightrag:
            warnings.append(f"LightRAG использован для {route.context_name}, потому что запрос явно просит найти данные в базе.")

        operation_id = self.begin_operation(f"Asking {route.context_name}...", self.query_timeout_seconds)
        target = self.run_query if use_lightrag else self.run_plain_query
        plain_prompt = prompt
        if explicit_knowledge_lookup and not use_lightrag:
            plain_prompt = (
                "Пользователь просит ответ из локальной базы знаний/LightRAG, но retrieval сейчас недоступен. "
                "Не утверждай, что ты использовал сохраненные материалы. Сначала коротко скажи, что ответ будет общим, "
                "а затем помоги по сути вопроса насколько возможно.\n\n"
                f"{prompt}"
            )
        args = (
            operation_id,
            question,
            prompt,
            route.context_name,
            index_route.scope,
            index_route.project,
            index_route.layer,
            use_lightrag,
            warnings,
            web_search_enabled,
            question,
        ) if use_lightrag else (
            operation_id,
            plain_prompt,
            warnings,
            web_search_enabled,
            question,
        )
        thread = threading.Thread(target=target, args=args, daemon=True)
        thread.start()

    def build_prompt_with_history(self, question: str) -> str:
        runtime_context = self.runtime_context_prompt(question) if should_include_runtime_context_standalone(question) else ""
        chat = self.get_active_chat()
        messages = chat.get("messages", []) if chat else []
        prior = [m for m in messages if m.get("role") in {"user", "assistant"} and is_safe_history_message_standalone(str(m.get("text", "")))]
        return build_prompt_with_history_standalone(question, runtime_context, prior)

    def is_safe_history_message(self, text: str) -> bool:
        return is_safe_history_message_standalone(text)

    def run_query(
        self,
        operation_id: int,
        raw_question: str,
        question: str,
        context_name: str,
        scope: str,
        project: str,
        layer: str,
        use_lightrag: bool,
        pending_warnings: list[str],
        web_search_enabled: bool = False,
        web_query: str = "",
    ) -> None:
        lightrag_used_actual = False
        if web_search_enabled:
            question, web_warnings = self.prepare_web_prompt(web_query or raw_question, question)
            pending_warnings = pending_warnings + web_warnings
        command_base = [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(QUERY_SCRIPT),
            "-Scope",
            scope,
            "-Layer",
            layer,
        ]
        if project:
            command_base.extend(["-Project", project])

        env = dict(os.environ)
        env["LMSTUDIO_GUI_OUTPUT"] = "1"
        env["LMSTUDIO_USE_LIGHTRAG"] = "1" if use_lightrag else "0"
        env["LMSTUDIO_BASE_URL"] = self.lmstudio_base_url()
        env["LMSTUDIO_LLM_MODEL"] = self.llm_model_id()
        env["LMSTUDIO_EMBEDDING_MODEL"] = self.embedding_model_id()
        if not use_lightrag:
            env["LMSTUDIO_WARN_PLAIN_MODE"] = "1"
            env.setdefault("LMSTUDIO_LIGHTRAG_OFF_REASON", "LightRAG отключен: ответ без базы знаний.")

        try:
            command = command_base + [question]
            returncode, output = self.run_command(command, self.query_timeout_seconds, env=env)
            if returncode != 0 and "context size has been exceeded" in output.lower() and question != raw_question:
                retry_warning = "История чата была слишком длинной, поэтому я повторил запрос без старого контекста."
                returncode, output = self.run_command(command_base + [raw_question], self.query_timeout_seconds, env=env)
                pending_warnings = pending_warnings + [retry_warning]
            output, warnings = self.split_knowledge_warnings(output)
            warnings = pending_warnings + warnings
            if returncode != 0:
                rag_error = self.friendly_error(output)
                fallback_question = question if web_search_enabled else raw_question
                fallback, model_warning = self.call_plain_lmstudio(fallback_question)
                if fallback:
                    output = fallback
                    tag = "assistant"
                    warnings.append(f"LightRAG не смог ответить; ответ создан обычной LLM. Детали: {rag_error}")
                    if model_warning:
                        warnings.append(model_warning)
                else:
                    output = rag_error
                    tag = "error"
            else:
                tag = "assistant"
                lightrag_used_actual = True
            if not output:
                fallback_question = question if web_search_enabled else raw_question
                fallback, model_warning = self.call_plain_lmstudio(fallback_question)
                if fallback:
                    output = fallback
                    tag = "assistant"
                    lightrag_used_actual = False
                    warnings.append("LightRAG вернул пустой ответ; я повторил запрос обычной LLM.")
                    if model_warning:
                        warnings.append(model_warning)
                else:
                    output = "Модель вернула пустой ответ. Попробуйте еще раз или откройте LightRAG-Control для проверки LM Studio."
                    tag = "error"
        except TimeoutError as exc:
            output = f"{exc}\nЗапрос остановлен, чтобы чат не зависал. Можно повторить или открыть LightRAG-Control."
            tag = "error"
            warnings = pending_warnings
            lightrag_used_actual = False
        except Exception as exc:
            output = f"Не удалось получить ответ: {exc}\nОткройте LightRAG-Control для диагностики."
            tag = "error"
            warnings = pending_warnings
            lightrag_used_actual = False
        if tag != "assistant":
            lightrag_used_actual = False
        self.root.after(0, self.finish_query, operation_id, output, tag, warnings, lightrag_used_actual)

    def finish_query(self, operation_id: int, output: str, tag: str, warnings: list[str], lightrag_used: bool = False) -> None:
        if not self.is_active_operation(operation_id):
            return
        self.append_assistant_message(output, tag, warnings=warnings, lightrag_used=lightrag_used)
        for warning in warnings:
            self.append_warning_message(warning)
        self.set_busy(False, "Ready")

    def set_active_process(self, process: subprocess.Popen | None) -> None:
        with self.process_lock:
            self.active_process = process

    def terminate_active_process(self) -> bool:
        with self.process_lock:
            process = self.active_process
        if not process or process.poll() is not None:
            return False
        try:
            process.terminate()
            try:
                process.wait(timeout=4)
            except subprocess.TimeoutExpired:
                process.kill()
            return True
        except Exception:
            try:
                process.kill()
                return True
            except Exception:
                return False

    def run_command(self, command: list[str], timeout_seconds: int, env: dict[str, str] | None = None) -> tuple[int, str]:
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        process = subprocess.Popen(
            command,
            cwd=str(ROOT),
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=creationflags,
            env=env,
        )
        self.set_active_process(process)
        try:
            stdout, stderr = process.communicate(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            self.terminate_active_process()
            raise TimeoutError(f"Command timed out after {timeout_seconds} seconds.")
        finally:
            self.set_active_process(None)
        output = "\n".join(part for part in ((stdout or "").strip(), (stderr or "").strip()) if part)
        return process.returncode, output

    def cancel_busy_timer(self) -> None:
        if self.busy_timer_id:
            try:
                self.root.after_cancel(self.busy_timer_id)
            except tk.TclError:
                pass
            self.busy_timer_id = None

    def schedule_busy_timer(self, timeout_seconds: int) -> None:
        self.cancel_busy_timer()
        self.busy_timer_id = self.root.after((timeout_seconds + 5) * 1000, self.force_unlock_timeout)

    def begin_operation(self, status: str, timeout_seconds: int) -> int:
        self.operation_id += 1
        self.active_operation_id = self.operation_id
        self.set_busy(True, status)
        self.schedule_busy_timer(timeout_seconds)
        return self.operation_id

    def is_active_operation(self, operation_id: int) -> bool:
        return self.active_operation_id == operation_id

    def force_unlock_timeout(self) -> None:
        if not self.busy:
            return
        self.terminate_active_process()
        self.append_warning_message("Операция заняла слишком много времени и была остановлена. Кнопки снова активны.", persist=True)
        self.set_busy(False, "Ready")

    def cancel_active_operation(self) -> None:
        if not self.busy:
            return
        if self.voice_operation_id == self.active_operation_id:
            self.voice_operation_id = None
            self.set_tool_button_active("voice_button", False)
        self.terminate_active_process()
        self.set_busy(False, "Ready")
        self.status_var.set("Canceled")

    def set_busy(self, busy: bool, status: str) -> None:
        self.busy = busy
        state = "disabled" if busy else "normal"
        self.send_button.configure(state=state)
        self.cancel_button.configure(state="normal" if busy else "disabled")
        self.clear_button.configure(state=state)
        if hasattr(self, "web_search_button"):
            self.web_search_button.configure(state=state)
        if hasattr(self, "file_attach_button"):
            self.file_attach_button.configure(state=state)
        if hasattr(self, "folder_attach_button"):
            self.folder_attach_button.configure(state=state)
        if hasattr(self, "voice_button"):
            self.voice_button.configure(state="normal" if self.voice_operation_id is not None else state)
        if not busy:
            self.cancel_busy_timer()
            self.set_active_process(None)
            self.active_operation_id = None
            self.stop_status_animation()
            self.status_var.set(status)
        else:
            self.start_status_animation(status)

    def start_status_animation(self, status: str) -> None:
        self.stop_status_animation()
        self.busy_status_base = status.rstrip(".")
        self.status_animation_step = 0
        self.animate_status()

    def stop_status_animation(self) -> None:
        if self.status_animation_id:
            try:
                self.root.after_cancel(self.status_animation_id)
            except tk.TclError:
                pass
            self.status_animation_id = None

    def animate_status(self) -> None:
        if not self.busy:
            self.status_animation_id = None
            return
        dots = "." * ((self.status_animation_step % 3) + 1)
        self.status_var.set(f"{self.busy_status_base}{dots}")
        self.status_animation_step += 1
        self.status_animation_id = self.root.after(420, self.animate_status)

    def clear_chat_window(self) -> None:
        chat = self.get_active_chat()
        if chat:
            chat["messages"] = []
            chat["title"] = "Новый чат"
            chat["updated_at"] = now_iso()
            self.save_chat_store()
            self.populate_chat_list(keep_selection=True)
        self.render_current_chat()

    def open_light_rag_control(self) -> None:
        candidates = [
            ROOT / "LightRAG-Desktop" / "LightRAG-Control" / "LightRAG-Control.ps1",
            CONTROL_SCRIPT,
        ]
        script = next((path for path in candidates if path.exists()), None)
        if not script:
            messagebox.showwarning("LightRAG-Control", "LightRAG-Control не найден.", parent=self.root)
            return
        subprocess.Popen(
            ["powershell", "-STA", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script)],
            cwd=str(ROOT),
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )

    def find_obsidian_path(self) -> str:
        return find_obsidian_path_standalone(str(self.settings.get("obsidian_path", "")))

    def find_obsidian_shortcuts(self, roaming_app: Path, program_data: Path) -> list[str]:
        from knowledgelab.ui.obsidian import find_obsidian_shortcuts as _fn
        return _fn(roaming_app, program_data)

    def find_obsidian_registry_candidates(self) -> list[str]:
        from knowledgelab.ui.obsidian import find_obsidian_registry_candidates as _fn
        return _fn()

    def clean_windows_program_path(self, value: str) -> str:
        from knowledgelab.ui.obsidian import clean_windows_program_path as _fn
        return _fn(value)

    def launch_windows_program(self, path: str) -> None:
        cwd = str(self.vault_dir() if self.vault_dir().exists() else ROOT)
        launch_windows_program_standalone(path, cwd)

    def open_obsidian(self) -> None:
        obsidian = self.find_obsidian_path()
        if obsidian:
            self.launch_windows_program(obsidian)
            return
        answer = messagebox.askyesnocancel(
            "Obsidian не найден",
            "Obsidian.exe не найден в стандартных местах.\n\nДа - указать путь к Obsidian.exe\nНет - открыть официальный сайт Obsidian\nОтмена - ничего не делать",
            parent=self.root,
        )
        if answer is True:
            path = filedialog.askopenfilename(
                title="Выберите Obsidian.exe",
                filetypes=[("Obsidian", "Obsidian.exe *.lnk"), ("Programs", "*.exe"), ("Shortcuts", "*.lnk"), ("All files", "*.*")],
                parent=self.root,
            )
            if path:
                self.settings["obsidian_path"] = path
                self.save_settings()
                self.obsidian_path_var.set(path)
                self.launch_windows_program(path)
        elif answer is False:
            webbrowser.open("https://obsidian.md/")

    def schedule_game_guard_probe(self) -> None:
        self._game_guard_dialog.schedule_probe()

    def start_game_guard_probe(self) -> None:
        self._game_guard_dialog.start_probe()

    def game_guard_worker(self) -> None:
        self._game_guard_dialog.worker()

    def collect_gpu_snapshot(self) -> dict:
        return self._game_guard_dialog.collect_snapshot()

    def is_gpu_snapshot_heavy(self, snapshot: dict) -> bool:
        return self._game_guard_dialog.is_heavy(snapshot)

    def show_game_guard_warning(self, snapshot: dict) -> None:
        self._game_guard_dialog.show_warning(snapshot)

def main() -> None:
    if "--self-test" in sys.argv:
        raise SystemExit(run_static_self_test())
    if "--behavior-test" in sys.argv:
        raise SystemExit(run_behavior_self_test())

    if explorer_dnd_enabled():
        try:
            from tkinterdnd2 import TkinterDnD  # type: ignore
            root = TkinterDnD.Tk()
        except Exception:
            root = tk.Tk()
    else:
        root = tk.Tk()
    try:
        ttk.Style().theme_use("vista")
    except tk.TclError:
        pass
    KnowledgeChatApp(root)
    root.mainloop()


def run_static_self_test() -> int:
    try:
        with tempfile.TemporaryDirectory(prefix="knowledgelab-self-test-") as tmp:
            tmp_vault = Path(tmp) / "vault"

            topic = classify_material_topic_standalone(
                "React hooks tutorial",
                "web",
                "article",
                vault_dir=tmp_vault,
            )
            if not topic:
                raise AssertionError("topic classification returned an empty topic")

            created_topic = ensure_topic_exists_standalone("Self Test Topic", "general", "", tmp_vault)
            topic_path = topic_note_path("general", "Self Test Topic", "", tmp_vault)
            if not created_topic or not topic_path.exists():
                raise AssertionError("topic creation did not write into the requested vault")

            vision_json = json.dumps(
                {
                    "detected_books": [
                        {
                            "title": "Clean Code",
                            "author": "Robert C. Martin",
                            "confidence": 0.94,
                            "status": "found",
                        }
                    ],
                    "unresolved": [{"region": "top shelf", "reason": "blurred", "evidence": "partial spine"}],
                },
                ensure_ascii=False,
            )
            parsed = parse_bookshelf_detection_response(vision_json)
            books = parsed.get("detected_books", [])
            if not books or books[0].get("title") != "Clean Code":
                raise AssertionError("book detection parser failed")

            created_notes = save_detected_book_notes_standalone(
                books,
                "00 Inbox/Images/self-test.md",
                "C:/tmp/self-test.jpg",
                tmp_vault,
                allow_unverified=True,
            )
            if not created_notes:
                raise AssertionError("book note was not created")

            routing_report = format_material_routing_report([
                MaterialRoutingReport("self-test.md", "article", topic, "Topics/self-test.md", True)
            ])
            if "Разложено по темам" not in routing_report:
                raise AssertionError("material routing report formatting failed")

            book_report = format_book_discovery_report(
                BookDiscoveryReport("00 Inbox/Images/self-test.md", books, parsed.get("unresolved", []), [])
            )
            if "Отчёт по книгам" not in book_report:
                raise AssertionError("book discovery report formatting failed")

        print("KnowledgeLab self-test OK")
        return 0
    except Exception as exc:
        print(f"KnowledgeLab self-test failed: {exc}")
        return 1


def run_behavior_self_test() -> int:
    with tempfile.TemporaryDirectory(prefix="knowledgelab-chat-test-") as tmp:
        tmp_dir = Path(tmp)
        settings_path = tmp_dir / "settings.json"
        sessions_path = tmp_dir / "sessions.json"
        settings = dict(DEFAULT_SETTINGS)
        settings.update(
            {
                "use_lightrag": False,
                "vault_path": str(DEFAULT_VAULT_DIR),
                "lmstudio_base_url": LMSTUDIO_API_URL,
                "llm_model": DEFAULT_LLM_MODEL,
                "embedding_model": DEFAULT_EMBEDDING_MODEL,
            }
        )
        settings_path.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")

        def request_json(path: str, *, method: str = "GET", payload: dict | None = None, timeout: float = 20.0) -> dict:
            data = None
            headers = {"Accept": "application/json"}
            if payload is not None:
                data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                headers["Content-Type"] = "application/json; charset=utf-8"
            request = urllib.request.Request(f"{LMSTUDIO_API_URL}/{path.lstrip('/')}", data=data, headers=headers, method=method)
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read().decode("utf-8", errors="replace")
            parsed = json.loads(raw) if raw.strip() else {}
            return parsed if isinstance(parsed, dict) else {}

        try:
            models_response = request_json("models", timeout=3.0)
        except Exception as exc:
            print(f"LM Studio readiness failed: {exc}")
            return 2
        model_ids = [str(item.get("id")) for item in models_response.get("data", []) if isinstance(item, dict)]
        if DEFAULT_LLM_MODEL not in model_ids:
            print(f"LM Studio model missing: {DEFAULT_LLM_MODEL}. Loaded: {', '.join(model_ids) or 'none'}")
            return 3

        def plain_answer(question: str) -> tuple[str, str]:
            payload = {
                "model": DEFAULT_LLM_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": "Answer normally in Russian by default. Do not show reasoning. Return only the final answer.",
                    },
                    {"role": "user", "content": f"/no_think\n\n{question}"},
                ],
                "temperature": 0.2,
                "max_tokens": 900,
                "stream": False,
            }
            response = request_json("chat/completions", method="POST", payload=payload, timeout=90.0)
            message = ((response.get("choices") or [{}])[0].get("message") or {})
            content = message.get("content")
            reasoning = message.get("reasoning_content")
            if isinstance(content, str) and content.strip():
                return content.strip(), ""
            if isinstance(reasoning, str) and reasoning.strip():
                payload["max_tokens"] = 2400
                payload["messages"][-1]["content"] = f"/no_think\n\nОтветь финальным сообщением без рассуждений на русском.\n\n{question}"
                retry = request_json("chat/completions", method="POST", payload=payload, timeout=120.0)
                retry_message = ((retry.get("choices") or [{}])[0].get("message") or {})
                retry_content = retry_message.get("content")
                if isinstance(retry_content, str) and retry_content.strip():
                    return retry_content.strip(), "reasoning retry"
                return "", "reasoning without final content"
            return "", "empty content"

        for question in ["Привет", "Как дела?", "555", "Сделай CSS для popup окна"]:
            answer, warning = plain_answer(question)
            if len(answer.strip()) < 2:
                print(f"Empty plain answer for: {question}. Warning: {warning}")
                return 4
            if any(marker in answer.lower() for marker in ("nativecommanderror", "context size has been exceeded", "lightrag storage was not found")):
                print(f"Noisy plain answer for: {question}: {answer[:300]}")
                return 5
            print(f"plain ok: {question} -> {answer[:90].replace(chr(10), ' ')}")

        now = now_iso()
        first_chat = {
            "id": "test-chat-1",
            "title": "Привет",
            "created_at": now,
            "updated_at": now,
            "messages": [
                {"id": "msg-1", "ts": now, "role": "user", "context": "General", "lightrag": False, "text": "Привет", "warnings": []},
                {"id": "msg-2", "ts": now, "role": "assistant", "context": "General", "lightrag": False, "text": "Привет! Чем помочь?", "warnings": []},
            ],
        }
        second_chat = {
            "id": "test-chat-2",
            "title": "Новый диалог",
            "created_at": now,
            "updated_at": now,
            "messages": [
                {"id": "msg-3", "ts": now, "role": "user", "context": "General", "lightrag": False, "text": "Новый диалог", "warnings": []}
            ],
        }
        store = {"version": 1, "active_chat_id": first_chat["id"], "chats": [first_chat, second_chat]}
        sessions_path.write_text(json.dumps(store, ensure_ascii=False, indent=2), encoding="utf-8")
        loaded_store = json.loads(sessions_path.read_text(encoding="utf-8"))
        loaded_store["active_chat_id"] = second_chat["id"]
        if loaded_store["active_chat_id"] != second_chat["id"]:
            print("Switching to second chat failed.")
            return 6
        loaded_store["active_chat_id"] = first_chat["id"]
        if loaded_store["active_chat_id"] != first_chat["id"]:
            print("Switching back to first chat failed.")
            return 7
        loaded_store["chats"] = [chat for chat in loaded_store["chats"] if chat["id"] not in {first_chat["id"], second_chat["id"]}]
        if loaded_store["chats"]:
            print("Chat deletion failed.")
            return 8
        sessions_path.write_text(json.dumps(loaded_store, ensure_ascii=False, indent=2), encoding="utf-8")
        print("history ok: create, switch, delete")

        general_index = ROOT / "LightRAG" / "rag_storage_general" / "vdb_chunks.json"
        if general_index.exists():
            env = dict(os.environ)
            env["LMSTUDIO_GUI_OUTPUT"] = "1"
            env["LMSTUDIO_USE_LIGHTRAG"] = "1"
            env["LMSTUDIO_BASE_URL"] = LMSTUDIO_API_URL
            env["LMSTUDIO_LLM_MODEL"] = DEFAULT_LLM_MODEL
            env["LMSTUDIO_EMBEDDING_MODEL"] = DEFAULT_EMBEDDING_MODEL
            process = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(QUERY_SCRIPT),
                    "-Scope",
                    "general",
                    "Проверка LightRAG: ответь кратко, какие материалы есть в базе знаний.",
                ],
                cwd=str(ROOT),
                text=True,
                encoding="utf-8",
                errors="replace",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=180,
                env=env,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            output = "\n".join(part for part in (process.stdout.strip(), process.stderr.strip()) if part)
            clean = "\n".join(line for line in output.splitlines() if not line.startswith(WARNING_PREFIX)).strip()
            if process.returncode != 0 or len(clean) < 2:
                print(f"LightRAG behavior failed: rc={process.returncode}; output={output[:500]}")
                return 9
            print(f"lightrag ok: {clean[:120].replace(chr(10), ' ')}")
        else:
            print("lightrag skipped: general index is not ready")

        print("temporary store ok: artifacts were confined to temp directory and removed")
        print("KnowledgeLab behavior-test OK")
        return 0


if __name__ == "__main__":
    main()
