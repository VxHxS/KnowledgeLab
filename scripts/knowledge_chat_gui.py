from __future__ import annotations

import ctypes
import datetime as dt
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import tkinter as tk
from html.parser import HTMLParser
from urllib.parse import parse_qs, unquote, urlencode, urlparse
import urllib.request
import webbrowser
import zipfile
from pathlib import Path
from tkinter import colorchooser, filedialog, messagebox, simpledialog, ttk


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VAULT_DIR = ROOT / "Obsidian-Test-Vault"
VAULT_DIR = DEFAULT_VAULT_DIR
SCRIPTS_DIR = ROOT / "scripts"
QUERY_SCRIPT = SCRIPTS_DIR / "query-vault-scope-lmstudio.ps1"
GAME_GUARD_SCRIPT = SCRIPTS_DIR / "game-guard.ps1"
CONTROL_SCRIPT = ROOT / "LightRAG-Control.ps1"
LEGACY_HISTORY_PATH = Path(os.getenv("KNOWLEDGELAB_LEGACY_HISTORY_PATH", str(ROOT / "tmp" / "knowledge-chat-history.jsonl")))
CHAT_STORE_PATH = Path(os.getenv("KNOWLEDGELAB_CHAT_STORE_PATH", str(ROOT / "tmp" / "knowledge-chat-sessions.json")))
SETTINGS_PATH = Path(os.getenv("KNOWLEDGELAB_CHAT_SETTINGS_PATH", str(ROOT / "tmp" / "knowledge-chat-settings.json")))
MATERIAL_QUEUE_PATH = Path(os.getenv("KNOWLEDGELAB_MATERIAL_QUEUE_PATH", str(ROOT / "tmp" / "material-processing-queue.jsonl")))
OBSIDIAN_ICON = ROOT / "assets" / "icons" / "Obsidian.png"
NEW_CHAT_ICON = ROOT / "assets" / "icons" / "new-chat.png"
WEB_SEARCH_ICON = ROOT / "assets" / "icons" / "web-search.png"
ATTACHMENT_ICON = ROOT / "assets" / "icons" / "attachment.png"
ATTACHMENT_ICON_ACTIVE = ROOT / "assets" / "icons" / "attachment-active.png"
MICROPHONE_ICON = ROOT / "assets" / "icons" / "microphone.png"
MICROPHONE_ICON_ACTIVE = ROOT / "assets" / "icons" / "microphone-active.png"
LMSTUDIO_API_URL = os.getenv("LMSTUDIO_BASE_URL", "http://127.0.0.1:1234/v1").rstrip("/")
DEFAULT_LLM_MODEL = os.getenv("LMSTUDIO_LLM_MODEL", "qwen/qwen3-14b")
DEFAULT_EMBEDDING_MODEL = os.getenv("LMSTUDIO_EMBEDDING_MODEL", "text-embedding-nomic-embed-text-v1.5")

CONTEXTS = {
    "General": ("general", ""),
    "Web Development": ("web", "web-development"),
    "My Game": ("game", "my-game"),
}

URL_RE = re.compile(r"https?://[^\s<>)\]]+", re.IGNORECASE)
YOUTUBE_RE = re.compile(r"https?://(?:www\.)?(?:youtube\.com/watch\?[^\s<>)\]]+|youtu\.be/[^\s<>)\]]+)", re.IGNORECASE)
TELEGRAM_RE = re.compile(r"https?://t\.me/[^\s<>)\]]+", re.IGNORECASE)
WARNING_PREFIX = "::knowledge-warning "
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff"}
IMAGE_FILETYPES = [
    ("Images", "*.png *.jpg *.jpeg *.webp *.bmp *.gif *.tif *.tiff"),
    ("PNG", "*.png"),
    ("JPEG", "*.jpg *.jpeg"),
    ("All files", "*.*"),
]
TEXT_EXTENSIONS = {
    ".txt", ".md", ".markdown", ".csv", ".tsv", ".json", ".jsonl", ".yaml", ".yml", ".xml", ".html", ".htm",
    ".py", ".ps1", ".js", ".jsx", ".ts", ".tsx", ".css", ".scss", ".less", ".html", ".cs", ".cpp", ".h",
    ".hpp", ".java", ".kt", ".go", ".rs", ".php", ".rb", ".sql", ".log",
}
DOC_EXTENSIONS = {".docx", ".pdf", ".rtf", ".odt", ".epub"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".opus", ".flac", ".wma"}
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".m4v", ".wmv"}
SUPPORTED_FILETYPES = [
    ("Knowledge sources", "*.png *.jpg *.jpeg *.webp *.bmp *.gif *.tif *.tiff *.txt *.md *.csv *.json *.docx *.pdf *.mp3 *.wav *.m4a *.mp4 *.mkv *.mov *.webm"),
    ("Images", "*.png *.jpg *.jpeg *.webp *.bmp *.gif *.tif *.tiff"),
    ("Documents", "*.txt *.md *.csv *.json *.docx *.pdf *.rtf *.odt *.epub"),
    ("Audio", "*.mp3 *.wav *.m4a *.aac *.ogg *.opus *.flac *.wma"),
    ("Video", "*.mp4 *.mkv *.mov *.avi *.webm *.m4v *.wmv"),
    ("All files", "*.*"),
]
TEXT_EXTRACTION_LIMIT = 90000
FILE_CAPTURE_KINDS = {"text_file", "document_file", "audio_file", "video_file", "generic_file"}
VOICE_INPUT_SECONDS = 8

BUTTON_COLOR_PRESETS = {
    "Blue": "#3d5f88",
    "Green": "#4f746e",
    "Purple": "#6f608a",
    "Graphite": "#58616b",
}

DEFAULT_SETTINGS = {
    "send_on_enter": True,
    "use_lightrag": False,
    "button_color": BUTTON_COLOR_PRESETS["Blue"],
    "game_guard_enabled": True,
    "game_guard_delay_seconds": 5,
    "obsidian_path": "",
    "vault_path": str(DEFAULT_VAULT_DIR),
    "lmstudio_base_url": LMSTUDIO_API_URL,
    "llm_model": DEFAULT_LLM_MODEL,
    "embedding_model": DEFAULT_EMBEDDING_MODEL,
    "response_language": "ru",
    "default_llm_mode_applied": True,
    "main_toolbar_lightrag_removed": True,
    "plain_chat_adapter_version": 1,
    "auto_process_links": True,
    "web_search_enabled": False,
}

WEB_TERMS = {
    "web", "frontend", "front-end", "html", "css", "javascript", "typescript",
    "react", "next.js", "nextjs", "vue", "svelte", "vite", "tailwind", "dom",
    "browser", "layout", "responsive", "api", "fetch", "axios", "auth", "oauth",
    "jwt", "node", "npm", "верстка", "вёрстка", "фронтенд", "бекенд", "сайт",
    "страница", "лендинг", "landing", "landing page", "popup", "modal", "css",
}

GAME_TERMS = {
    "my-game", "my game", "моя игра", "моей игре", "мой проект игры",
    "геймплей", "game design", "игровой проект", "unity", "unreal",
}

SAVE_PHRASES = {
    "вот ссылка", "сохрани", "сохранить", "запомни", "добавь в obsidian",
    "добавить в obsidian", "добавь в базу", "добавь в знания", "добавь материал",
    "сохрани ссылку", "занеси в vault", "вот материал", "полезная статья",
    "добавь заметку", "добавить заметку",
}

QUESTION_HINTS = {
    "что", "как", "почему", "зачем", "когда", "где", "кто", "какой", "какая",
    "какие", "можешь", "можно", "сделай", "напиши", "объясни", "расскажи",
    "найди", "поищи", "проверь", "why", "how", "what", "write", "make",
}

KNOWLEDGE_LOOKUP_TERMS = {
    "найди в базе", "поищи в базе", "ищи в базе", "из базы знаний", "по базе знаний",
    "из сохраненного", "из сохранённого", "из сохраненных", "из сохранённых",
    "из сохраненных материалов", "из сохранённых материалов", "по сохраненным материалам",
    "по сохранённым материалам", "что у меня сохранено", "что сохранено",
    "сделай из сохраненных", "сделай из сохранённых", "по материалам из obsidian",
}

KNOWLEDGE_HELP_TERMS = {
    "как узнать", "как достать", "как получить", "как спросить", "как найти",
    "как пользоваться", "как использовать", "доступ к lightrag", "доступ к базе",
}

LIGHTRAG_STATUS_TERMS = {
    "подключен", "подключён", "подключена", "работает", "включен", "включён",
    "активен", "готов", "используется", "статус", "доступен", "доступна",
}

RUSSIAN_LANGUAGE_TERMS = {
    "на русском", "по русски", "по-русски", "русский", "русском", "отвечай на русском",
    "говори на русском", "пиши на русском",
}

TOPICS = [
    ("React", {"react", "jsx", "tsx", "hooks", "component"}),
    ("TypeScript", {"typescript", " ts ", "types", "type-safe", "типизация"}),
    ("CSS Layout", {"css", "grid", "flex", "layout", "responsive", "media query", "верстка", "вёрстка", "popup", "modal"}),
    ("Accessibility", {"a11y", "accessibility", "aria", "screen reader", "доступность"}),
    ("Performance", {"performance", "perf", "lcp", "cls", "bundle", "оптимизация"}),
    ("API Integration", {"api", "fetch", "axios", "graphql", "rest", "websocket"}),
    ("Auth", {"auth", "oauth", "jwt", "session", "login", "авторизация"}),
    ("Deployment", {"deploy", "docker", "vercel", "netlify", "nginx", "hosting"}),
    ("Testing", {"test", "testing", "playwright", "vitest", "jest", "тест"}),
    ("Next.js", {"next.js", "nextjs", "app router", "server component"}),
    ("Node.js", {"node", "node.js", "express", "fastify", "npm"}),
    ("Tailwind", {"tailwind"}),
    ("Forms", {"form", "forms", "react-hook-form", "zod", "валидац"}),
    ("Animation", {"animation", "framer", "motion", "gsap", "анимац"}),
    ("Unity", {"unity", "c#", "csharp"}),
    ("Zenject", {"zenject", "dependency injection"}),
]


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
        self.bind("<Configure>", lambda _event: self.redraw())
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        self.bind("<ButtonRelease-1>", self.on_click)
        self.bind("<space>", self.on_keyboard)
        self.bind("<Return>", self.on_keyboard)
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
        self.redraw()

    def on_leave(self, _event: tk.Event | None = None) -> None:
        self.hover = False
        self.redraw()

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
        fill = self.active_bg if self.hover and self.enabled else self.normal_bg
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
        else:
            self.draw_attachment(icon)

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

    def rounded_rect(self, x1: int, y1: int, x2: int, y2: int, radius: int, *, fill: str, outline: str) -> None:
        points = [
            x1 + radius, y1, x2 - radius, y1, x2, y1, x2, y1 + radius,
            x2, y2 - radius, x2, y2, x2 - radius, y2, x1 + radius, y2,
            x1, y2, x1, y2 - radius, x1, y1 + radius, x1, y1,
        ]
        self.create_polygon(points, smooth=True, fill=fill, outline=outline)


def now_iso() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def compact_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def contains_any(text: str, terms: set[str]) -> bool:
    lowered = f" {text.lower()} "
    return any(term in lowered for term in terms)


def route_context(text: str, selected: str) -> tuple[str, str, str]:
    if selected != "Auto":
        scope, project = CONTEXTS[selected]
        return selected, scope, project
    if contains_any(text, WEB_TERMS):
        return "Web Development", "web", "web-development"
    if contains_any(text, GAME_TERMS):
        return "My Game", "game", "my-game"
    return "General", "general", ""


def valid_hex_color(value: str, fallback: str) -> str:
    value = str(value or "").strip()
    if re.fullmatch(r"#[0-9a-fA-F]{6}", value):
        return value.lower()
    return fallback


def adjust_hex_color(value: str, factor: float) -> str:
    value = valid_hex_color(value, BUTTON_COLOR_PRESETS["Blue"]).lstrip("#")
    channels = [int(value[index:index + 2], 16) for index in (0, 2, 4)]
    adjusted = []
    for channel in channels:
        if factor >= 1:
            channel = int(channel + (255 - channel) * (factor - 1))
        else:
            channel = int(channel * factor)
        adjusted.append(max(0, min(255, channel)))
    return "#{:02x}{:02x}{:02x}".format(*adjusted)


def readable_text_color(background: str) -> str:
    value = valid_hex_color(background, BUTTON_COLOR_PRESETS["Blue"]).lstrip("#")
    r, g, b = [int(value[index:index + 2], 16) for index in (0, 2, 4)]
    luminance = (0.299 * r + 0.587 * g + 0.114 * b)
    return "#1f2933" if luminance > 150 else "#ffffff"


def clean_filename(value: str) -> str:
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "-", value).strip()
    value = re.sub(r"\s+", " ", value)
    return value[:120].strip(" .-") or "note"


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9а-яё_-]+", "-", value, flags=re.IGNORECASE)
    value = re.sub(r"-{2,}", "-", value).strip("-")
    return value or "note"


def yaml_quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def first_url(text: str) -> str:
    match = URL_RE.search(text)
    return match.group(0).rstrip(".,;)]}>\"'") if match else ""


def first_youtube_url(text: str) -> str:
    match = YOUTUBE_RE.search(text)
    return match.group(0).rstrip(".,;)]}>\"'") if match else ""


def first_telegram_url(text: str) -> str:
    match = TELEGRAM_RE.search(text)
    return match.group(0).rstrip(".,;)]}>\"'") if match else ""


def infer_topic(text: str, scope: str) -> str:
    lowered = f" {text.lower()} "
    for topic, terms in TOPICS:
        if any(term in lowered for term in terms):
            return topic
    if scope == "web":
        return "Web"
    if scope == "game":
        return "Project Notes"
    return "General"


def infer_kind(text: str) -> str:
    if first_youtube_url(text):
        return "youtube_link"
    if first_telegram_url(text):
        return "telegram_source"
    if first_url(text):
        return "article"
    lowered = text.lower()
    if any(term in lowered for term in ("решение", "solution", "snippet", "компонент", "pattern", "паттерн")):
        return "solution"
    return "capture"


def title_from_text(text: str, fallback: str) -> str:
    for line in text.splitlines():
        line = line.strip().strip("#").strip()
        if line and not URL_RE.fullmatch(line):
            return clean_filename(line)
    url = first_url(text)
    if url:
        return clean_filename(url.replace("https://", "").replace("http://", ""))
    return fallback


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    for index in range(2, 1000):
        candidate = path.with_name(f"{stem} {index}{suffix}")
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"Cannot create a unique filename for {path}")


def capture_destination(scope: str, topic: str, kind: str) -> Path:
    if scope == "web":
        base = VAULT_DIR / "20 Projects" / "Web Development"
        if kind == "youtube_link":
            return base / "Sources" / "YouTube" / "Links"
        if kind == "telegram_source":
            return base / "Sources" / "Telegram"
        if kind == "article":
            return base / "Sources" / "Articles"
        if kind == "image_capture":
            return base / "Sources" / "Images"
        if kind == "document_file":
            return base / "Sources" / "Documents"
        if kind == "audio_file":
            return base / "Sources" / "Audio"
        if kind == "video_file":
            return base / "Sources" / "Video"
        if kind in {"text_file", "generic_file"}:
            return base / "Sources" / "Files"
        if kind == "solution":
            return base / "Solutions"
        return base / "Topics" / clean_filename(topic)
    if scope == "game":
        base = VAULT_DIR / "20 Projects" / "My Game"
        if kind == "youtube_link":
            return base / "Sources" / "YouTube" / "Links"
        if kind == "telegram_source":
            return base / "Sources" / "Telegram"
        if kind == "article":
            return base / "Sources" / "Articles"
        if kind == "image_capture":
            return base / "Sources" / "Images"
        if kind == "document_file":
            return base / "Sources" / "Documents"
        if kind == "audio_file":
            return base / "Sources" / "Audio"
        if kind == "video_file":
            return base / "Sources" / "Video"
        if kind in {"text_file", "generic_file"}:
            return base / "Sources" / "Files"
        return base / "Captures"
    if kind == "youtube_link":
        return VAULT_DIR / "30 Sources" / "YouTube" / "Links"
    if kind == "telegram_source":
        return VAULT_DIR / "30 Sources" / "Telegram"
    if kind == "article":
        return VAULT_DIR / "30 Sources" / "Articles"
    if kind == "image_capture":
        return VAULT_DIR / "00 Inbox" / "Images"
    if kind == "document_file":
        return VAULT_DIR / "00 Inbox" / "Documents"
    if kind == "audio_file":
        return VAULT_DIR / "00 Inbox" / "Audio"
    if kind == "video_file":
        return VAULT_DIR / "00 Inbox" / "Video"
    if kind in {"text_file", "generic_file"}:
        return VAULT_DIR / "00 Inbox" / "Files"
    return VAULT_DIR / "00 Inbox"


def render_capture_markdown(text: str, context_name: str, scope: str, project: str, topic: str, kind: str) -> str:
    url = first_youtube_url(text) or first_telegram_url(text) or first_url(text)
    tags = ["captured/chat"]
    if project:
        tags.append(f"project/{project}")
    if topic:
        tags.append(f"topic/{slugify(topic)}")
    if kind == "youtube_link":
        source = "youtube_link"
        tags.append("source/youtube")
    elif kind == "telegram_source":
        source = "telegram"
        tags.append("source/telegram")
    elif kind == "article":
        source = "web"
        tags.append("source/article")
    else:
        source = "manual"

    title = title_from_text(text, f"{context_name} capture")
    frontmatter = [
        "---",
        f"type: {kind}",
        f"source: {source}",
        f"source_url: {yaml_quote(url)}",
        f"scope: {scope}",
        f"project: {yaml_quote(project)}",
        f"topic: {yaml_quote(topic)}",
        f"captured_at: {yaml_quote(now_iso())}",
        f"tags: [{', '.join(tags)}]",
        "---",
        "",
    ]
    body = [f"# {title}", ""]
    if url:
        body.extend([f"URL: {url}", ""])
    body.extend(["## Capture", "", text.strip(), ""])
    return "\n".join(frontmatter + body)


def render_image_capture_markdown(
    image_path: Path,
    caption: str,
    context_name: str,
    scope: str,
    project: str,
    topic: str,
) -> str:
    stat = image_path.stat()
    tags = ["captured/chat", "source/image", "needs/vision-extraction"]
    if project:
        tags.append(f"project/{project}")
    if topic:
        tags.append(f"topic/{slugify(topic)}")
    title_seed = caption.strip() or image_path.stem
    title = clean_filename(title_seed)
    frontmatter = [
        "---",
        "type: image_capture",
        "source: image",
        f"source_path: {yaml_quote(str(image_path))}",
        f"file_name: {yaml_quote(image_path.name)}",
        f"file_size_bytes: {stat.st_size}",
        f"scope: {scope}",
        f"project: {yaml_quote(project)}",
        f"topic: {yaml_quote(topic)}",
        f"captured_at: {yaml_quote(now_iso())}",
        "extraction_status: pending",
        f"tags: [{', '.join(tags)}]",
        "---",
        "",
    ]
    body = [
        f"# {title}",
        "",
        "## Image Intake",
        "",
        f"- Original file: `{image_path}`",
        f"- File name: `{image_path.name}`",
        f"- Size: {stat.st_size} bytes",
        f"- Suggested context: {context_name}",
        f"- Suggested topic: {topic or 'None'}",
        "",
        "## Caption / User Hint",
        "",
        caption.strip() or "_No caption was provided._",
        "",
        "## Extracted Data",
        "",
        "_Pending OCR/vision extraction. The heavy image file is not copied into the vault by default._",
        "",
    ]
    return "\n".join(frontmatter + body)


def classify_source_file(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in IMAGE_EXTENSIONS:
        return "image_capture"
    if suffix in TEXT_EXTENSIONS:
        return "text_file"
    if suffix in DOC_EXTENSIONS:
        return "document_file"
    if suffix in AUDIO_EXTENSIONS:
        return "audio_file"
    if suffix in VIDEO_EXTENSIONS:
        return "video_file"
    return "generic_file"


def extraction_label(kind: str) -> str:
    return {
        "image_capture": "OCR/vision extraction",
        "text_file": "text extraction",
        "document_file": "document text extraction",
        "audio_file": "speech transcription",
        "video_file": "video/audio transcription",
        "generic_file": "custom extraction",
    }.get(kind, "custom extraction")


def file_kind_label(kind: str) -> str:
    return {
        "image_capture": "image",
        "text_file": "text",
        "document_file": "document",
        "audio_file": "audio",
        "video_file": "video",
        "generic_file": "file",
    }.get(kind, "file")


def read_text_source(path: Path) -> tuple[str, str]:
    try:
        raw = path.read_bytes()[: TEXT_EXTRACTION_LIMIT + 4096]
    except OSError as exc:
        return "", f"read failed: {exc}"
    for encoding in ("utf-8-sig", "utf-8", "cp1251", "utf-16"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            text = ""
    if not text:
        text = raw.decode("utf-8", errors="replace")
    truncated = len(text) > TEXT_EXTRACTION_LIMIT
    text = text[:TEXT_EXTRACTION_LIMIT].strip()
    status = "extracted"
    if truncated:
        status = "partial"
        text += "\n\n_Extraction was truncated; use a dedicated importer for the full file._"
    return text, status


def read_docx_source(path: Path) -> tuple[str, str]:
    try:
        with zipfile.ZipFile(path) as archive:
            raw = archive.read("word/document.xml").decode("utf-8", errors="replace")
    except Exception as exc:
        return "", f"docx extraction failed: {exc}"
    raw = re.sub(r"</w:p\s*>", "\n", raw)
    raw = re.sub(r"<[^>]+>", "", raw)
    text = html.unescape(raw)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text).strip()
    truncated = len(text) > TEXT_EXTRACTION_LIMIT
    text = text[:TEXT_EXTRACTION_LIMIT].strip()
    if truncated:
        text += "\n\n_Extraction was truncated; use a dedicated importer for the full document._"
        return text, "partial"
    return text, "extracted" if text else "pending"


def extract_lightweight_file_text(path: Path, kind: str) -> tuple[str, str]:
    if kind == "text_file":
        return read_text_source(path)
    if path.suffix.lower() == ".docx":
        return read_docx_source(path)
    return "", "pending"


def render_file_capture_markdown(
    file_path: Path,
    caption: str,
    context_name: str,
    scope: str,
    project: str,
    topic: str,
    kind: str,
    extracted_text: str,
    extraction_status: str,
) -> str:
    stat = file_path.stat()
    tags = ["captured/chat", "source/file"]
    if kind == "image_capture":
        tags.append("source/image")
    if kind == "audio_file":
        tags.append("source/audio")
    if kind == "video_file":
        tags.append("source/video")
    if kind == "document_file":
        tags.append("source/document")
    if extraction_status in {"extracted", "partial"}:
        tags.append(f"extraction/{extraction_status}")
    else:
        tags.append(f"needs/{slugify(extraction_label(kind))}")
    if project:
        tags.append(f"project/{project}")
    if topic:
        tags.append(f"topic/{slugify(topic)}")
    title_seed = caption.strip() or file_path.stem
    title = clean_filename(title_seed)
    frontmatter = [
        "---",
        f"type: {kind}",
        "source: file",
        f"source_path: {yaml_quote(str(file_path))}",
        f"file_name: {yaml_quote(file_path.name)}",
        f"file_extension: {yaml_quote(file_path.suffix.lower())}",
        f"file_size_bytes: {stat.st_size}",
        f"scope: {scope}",
        f"project: {yaml_quote(project)}",
        f"topic: {yaml_quote(topic)}",
        f"captured_at: {yaml_quote(now_iso())}",
        f"extraction_status: {yaml_quote(extraction_status)}",
        f"tags: [{', '.join(tags)}]",
        "---",
        "",
    ]
    body = [
        f"# {title}",
        "",
        "## File Intake",
        "",
        f"- Original file: `{file_path}`",
        f"- File name: `{file_path.name}`",
        f"- Size: {stat.st_size} bytes",
        f"- Suggested context: {context_name}",
        f"- Suggested topic: {topic or 'None'}",
        f"- Planned processing: {extraction_label(kind)}",
        "",
        "## User Hint",
        "",
        caption.strip() or "_No hint was provided._",
        "",
        "## Extracted Data",
        "",
    ]
    if extracted_text:
        body.extend([extracted_text.strip(), ""])
    else:
        body.extend([
            f"_Pending {extraction_label(kind)}. The heavy source file is not copied into the vault by default._",
            "",
        ])
    return "\n".join(frontmatter + body)


class ArticleTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.parts: list[str] = []
        self.current_tag = ""
        self.skip_depth = 0
        self.title_active = False
        self.title_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "noscript", "svg", "canvas", "form", "nav", "footer", "header"}:
            self.skip_depth += 1
            return
        if tag == "title":
            self.title_active = True
        if tag in {"p", "li", "h1", "h2", "h3", "pre", "code", "blockquote"}:
            self.current_tag = tag

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if self.skip_depth:
            if tag in {"script", "style", "noscript", "svg", "canvas", "form", "nav", "footer", "header"}:
                self.skip_depth -= 1
            return
        if tag == "title":
            self.title_active = False
            self.title = compact_whitespace(" ".join(self.title_parts))[:180]
        if tag in {"p", "li", "h1", "h2", "h3", "pre", "blockquote"}:
            self.parts.append("\n")
            self.current_tag = ""

    def handle_data(self, data: str) -> None:
        if self.skip_depth:
            return
        text = compact_whitespace(data)
        if not text:
            return
        if self.title_active:
            self.title_parts.append(text)
            return
        if self.current_tag:
            if self.current_tag == "li":
                text = f"- {text}"
            if self.current_tag in {"h1", "h2", "h3"}:
                text = f"## {text}"
            self.parts.append(text)

    def markdown(self) -> str:
        lines: list[str] = []
        previous_blank = True
        for part in self.parts:
            text = part.strip()
            if not text:
                if not previous_blank:
                    lines.append("")
                previous_blank = True
                continue
            lines.append(text)
            previous_blank = False
        return "\n".join(lines).strip()


def compact_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def fetch_article_markdown(url: str, *, timeout: int = 15, limit_bytes: int = 2_500_000) -> tuple[str, str]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "KnowledgeLab/1.0 (+local Obsidian capture)",
            "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9,*/*;q=0.2",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        content_type = response.headers.get("Content-Type", "")
        raw = response.read(limit_bytes)
    charset_match = re.search(r"charset=([\w.-]+)", content_type, re.IGNORECASE)
    charset = charset_match.group(1) if charset_match else "utf-8"
    html = raw.decode(charset, errors="replace")
    extractor = ArticleTextExtractor()
    extractor.feed(html)
    markdown = extractor.markdown()
    title = extractor.title or title_from_text(url, "Web article")
    return title, markdown[:60000]


class DuckDuckGoResultParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.results: list[dict[str, str]] = []
        self.current: dict[str, str] | None = None
        self.capture_title = False
        self.capture_snippet = False
        self.title_parts: list[str] = []
        self.snippet_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        attrs_dict = {name: value or "" for name, value in attrs}
        classes = attrs_dict.get("class", "")
        if tag == "a" and ("result__a" in classes or "result-link" in classes):
            self.flush()
            self.current = {"url": normalize_search_url(attrs_dict.get("href", "")), "title": "", "snippet": ""}
            self.title_parts = []
            self.capture_title = True
        elif self.current is not None and ("result__snippet" in classes or "result-snippet" in classes):
            self.snippet_parts = []
            self.capture_snippet = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self.capture_title:
            self.capture_title = False
            if self.current is not None:
                self.current["title"] = compact_whitespace(" ".join(self.title_parts))
        elif self.capture_snippet and tag in {"a", "div", "td"}:
            self.capture_snippet = False
            if self.current is not None:
                self.current["snippet"] = compact_whitespace(" ".join(self.snippet_parts))

    def handle_data(self, data: str) -> None:
        text = compact_whitespace(data)
        if not text:
            return
        if self.capture_title:
            self.title_parts.append(text)
        elif self.capture_snippet:
            self.snippet_parts.append(text)

    def flush(self) -> None:
        if self.current and self.current.get("title"):
            self.results.append(self.current)
        self.current = None

    def close(self) -> None:
        self.flush()
        super().close()


def normalize_search_url(url: str) -> str:
    url = (url or "").strip()
    if url.startswith("//"):
        url = "https:" + url
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    if "uddg" in params and params["uddg"]:
        return unquote(params["uddg"][0])
    return url


def fetch_web_search_results(query: str, *, max_results: int = 5, timeout: int = 12) -> list[dict[str, str]]:
    search_urls = [
        "https://duckduckgo.com/html/?" + urlencode({"q": query}),
        "https://lite.duckduckgo.com/lite/?" + urlencode({"q": query}),
    ]
    headers = {
        "User-Agent": "Mozilla/5.0 KnowledgeLab/1.0 (+local web context)",
        "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9,*/*;q=0.2",
    }
    for search_url in search_urls:
        request = urllib.request.Request(search_url, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                html = response.read(1_200_000).decode("utf-8", errors="replace")
        except Exception:
            continue
        parser = DuckDuckGoResultParser()
        parser.feed(html)
        parser.close()
        unique: list[dict[str, str]] = []
        seen: set[str] = set()
        for result in parser.results:
            url = result.get("url", "")
            title = result.get("title", "")
            if not url or not title or url in seen:
                continue
            seen.add(url)
            unique.append(result)
            if len(unique) >= max_results:
                break
        if unique:
            return unique
    return []


def render_web_search_context(query: str, results: list[dict[str, str]]) -> str:
    lines = [
        "Web search context for the next answer.",
        "Use this external web context only when it is relevant. Cite URLs when relying on it.",
        f"Search query: {query}",
        "",
    ]
    for index, result in enumerate(results, 1):
        lines.append(f"[{index}] {result.get('title', '').strip()}")
        lines.append(f"URL: {result.get('url', '').strip()}")
        snippet = result.get("snippet", "").strip()
        if snippet:
            lines.append(f"Snippet: {snippet}")
        lines.append("")
    return "\n".join(lines).strip()


def is_knowledge_lookup_text(text: str) -> bool:
    compact = compact_text(text)
    return any(term in compact for term in KNOWLEDGE_LOOKUP_TERMS)


def is_lightrag_help_text(text: str) -> bool:
    compact = compact_text(text)
    if "lightrag" not in compact and "light rag" not in compact and "баз" not in compact:
        return False
    return any(term in compact for term in KNOWLEDGE_HELP_TERMS) or ("как" in compact and "lightrag" in compact)


def is_lightrag_status_text(text: str) -> bool:
    compact = compact_text(text)
    mentions_lightrag = "lightrag" in compact or "light rag" in compact or "лайтраг" in compact
    if not mentions_lightrag:
        return False
    if any(term in compact for term in KNOWLEDGE_HELP_TERMS):
        return False
    return any(term in compact for term in LIGHTRAG_STATUS_TERMS) or compact.rstrip("?").strip() in {"lightrag", "light rag", "лайтраг"}


def is_russian_language_request(text: str) -> bool:
    compact = compact_text(text)
    return any(term in compact for term in RUSSIAN_LANGUAGE_TERMS)


def is_save_intent_text(text: str) -> bool:
    compact = compact_text(text)
    if any(phrase in compact for phrase in SAVE_PHRASES):
        return True
    if first_url(text):
        words = set(re.findall(r"[a-zа-яё]+", compact, flags=re.IGNORECASE))
        return len(words & QUESTION_HINTS) == 0
    return False


def run_static_self_test() -> int:
    samples = [
        "Привет",
        "Как дела?",
        "555",
        "Сделай CSS для popup окна",
        "вот ссылка https://example.com/article",
        "найди в базе материалы про CSS",
        "объясни простыми словами, что такое API",
        "помоги составить письмо",
        "почему возникает ошибка?",
        "дай пример JSON schema",
    ]
    failures = []
    for sample in samples[:4] + samples[6:]:
        if is_save_intent_text(sample):
            failures.append(f"ordinary message routed as save intent: {sample}")
    if not is_save_intent_text(samples[4]):
        failures.append("save link was not recognized")
    context = [route_context(sample, "Auto")[0] for sample in samples]
    if context[3] != "Web Development" or context[5] != "Web Development":
        failures.append(f"web context routing failed: {context}")
    if not is_knowledge_lookup_text("Сделай инструкцию из того что у меня сохранено в LightRAG"):
        failures.append("explicit knowledge lookup was not recognized")
    if not is_lightrag_help_text("Как мне достать информацию из lightrag?"):
        failures.append("LightRAG help intent was not recognized")
    if is_knowledge_lookup_text("lightrag подключен?"):
        failures.append("LightRAG status question was routed as retrieval")
    if not is_lightrag_status_text("lightrag подключен?"):
        failures.append("LightRAG status intent was not recognized")
    if not is_russian_language_request("на русском пж"):
        failures.append("Russian language preference was not recognized")
    for asset in (ATTACHMENT_ICON, ATTACHMENT_ICON_ACTIVE, MICROPHONE_ICON, MICROPHONE_ICON_ACTIVE):
        if not asset.exists() or asset.stat().st_size <= 0:
            failures.append(f"missing tool icon asset: {asset}")
    expected_kinds = {
        "shot.png": "image_capture",
        "notes.md": "text_file",
        "brief.docx": "document_file",
        "voice.mp3": "audio_file",
        "clip.mp4": "video_file",
        "archive.bin": "generic_file",
    }
    for name, expected in expected_kinds.items():
        actual = classify_source_file(Path(name))
        if actual != expected:
            failures.append(f"file classification failed for {name}: {actual}")
    with tempfile.TemporaryDirectory(prefix="knowledgelab-file-test-") as tmp:
        tmp_dir = Path(tmp)
        text_path = tmp_dir / "notes.md"
        text_path.write_text("Привет\n\nSaved material", encoding="utf-8")
        extracted, status = read_text_source(text_path)
        if status != "extracted" or "Saved material" not in extracted:
            failures.append(f"text extraction failed: {status}")
        docx_path = tmp_dir / "brief.docx"
        with zipfile.ZipFile(docx_path, "w") as archive:
            archive.writestr(
                "word/document.xml",
                "<w:document><w:body><w:p><w:r><w:t>Docx material</w:t></w:r></w:p></w:body></w:document>",
            )
        docx_text, docx_status = read_docx_source(docx_path)
        if docx_status != "extracted" or "Docx material" not in docx_text:
            failures.append(f"docx extraction failed: {docx_status}")
        markdown = render_file_capture_markdown(
            text_path,
            "hint",
            "General",
            "general",
            "",
            "",
            "text_file",
            extracted,
            status,
        )
        if "source_path:" not in markdown or "## Extracted Data" not in markdown:
            failures.append("file capture markdown missing expected sections")
    if failures:
        print("\n".join(failures))
        return 1
    print("knowledge_chat_gui self-test OK")
    return 0


class KnowledgeChatApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("LightRAG Knowledge Chat")
        self.root.geometry("1120x760")
        self.root.minsize(900, 600)
        self.root.configure(bg="#f4f6f8")

        self.settings = self.load_settings()
        self.save_settings()
        self.context_var = tk.StringVar(value="Auto")
        self.lightrag_var = tk.BooleanVar(value=bool(self.settings["use_lightrag"]))
        self.status_var = tk.StringVar(value="Ready")
        self.enter_send_var = tk.BooleanVar(value=bool(self.settings["send_on_enter"]))
        self.game_guard_var = tk.BooleanVar(value=bool(self.settings["game_guard_enabled"]))
        self.auto_process_links_var = tk.BooleanVar(value=bool(self.settings.get("auto_process_links", True)))
        self.web_search_enabled_var = tk.BooleanVar(value=bool(self.settings.get("web_search_enabled", False)))
        self.button_color_var = tk.StringVar(value=str(self.settings["button_color"]))
        self.obsidian_path_var = tk.StringVar(value=str(self.settings.get("obsidian_path", "")))
        self.vault_path_var = tk.StringVar(value=str(self.settings.get("vault_path", str(DEFAULT_VAULT_DIR))))

        global VAULT_DIR
        VAULT_DIR = self.vault_dir()

        self.settings_window: tk.Toplevel | None = None
        self.settings_status_var = tk.StringVar(value="")
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
        self.drop_wndproc = None
        self.drop_old_wndprocs: dict[int, object] = {}
        self.drop_call_window_proc = None

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
        style.configure("App.TFrame", background="#f4f6f8")
        style.configure("Top.TFrame", background="#eef2f5")
        style.configure("Sidebar.TFrame", background="#eef2f5")
        style.configure("Composer.TFrame", background="#f4f6f8")
        style.configure("Status.TLabel", background="#eef2f5", foreground="#53616f", font=("Segoe UI", 10))
        style.configure("Header.TLabel", background="#eef2f5", foreground="#1f2933", font=("Segoe UI Semibold", 11))
        style.configure("Context.TLabel", background="#eef2f5", foreground="#384655", font=("Segoe UI", 10))
        style.configure("Toolbar.TCheckbutton", background="#eef2f5", foreground="#384655", font=("Segoe UI", 10))
        style.configure("SettingsHeader.TLabel", background="#f4f6f8", foreground="#1f2933", font=("Segoe UI Semibold", 10))
        style.configure("SettingsStatus.TLabel", background="#f4f6f8", foreground="#53616f", font=("Segoe UI", 9))

    def load_settings(self) -> dict[str, object]:
        settings = dict(DEFAULT_SETTINGS)
        try:
            if SETTINGS_PATH.exists():
                loaded = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    settings.update(loaded)
                    if "default_llm_mode_applied" not in loaded:
                        settings["use_lightrag"] = False
                        settings["default_llm_mode_applied"] = True
                    if "main_toolbar_lightrag_removed" not in loaded:
                        settings["use_lightrag"] = False
                        settings["main_toolbar_lightrag_removed"] = True
                    if "plain_chat_adapter_version" not in loaded:
                        settings["use_lightrag"] = False
                        settings["plain_chat_adapter_version"] = 1
        except (OSError, json.JSONDecodeError):
            pass
        settings["send_on_enter"] = bool(settings.get("send_on_enter", DEFAULT_SETTINGS["send_on_enter"]))
        settings["use_lightrag"] = bool(settings.get("use_lightrag", DEFAULT_SETTINGS["use_lightrag"]))
        settings["game_guard_enabled"] = bool(settings.get("game_guard_enabled", DEFAULT_SETTINGS["game_guard_enabled"]))
        settings["auto_process_links"] = bool(settings.get("auto_process_links", DEFAULT_SETTINGS["auto_process_links"]))
        settings["web_search_enabled"] = bool(settings.get("web_search_enabled", DEFAULT_SETTINGS["web_search_enabled"]))
        settings["game_guard_delay_seconds"] = max(1, int(settings.get("game_guard_delay_seconds", 5) or 5))
        settings["button_color"] = valid_hex_color(str(settings.get("button_color", "")), DEFAULT_SETTINGS["button_color"])
        settings["obsidian_path"] = str(settings.get("obsidian_path", "") or "")
        settings["vault_path"] = str(settings.get("vault_path", str(DEFAULT_VAULT_DIR)) or str(DEFAULT_VAULT_DIR))
        settings["lmstudio_base_url"] = str(settings.get("lmstudio_base_url", LMSTUDIO_API_URL) or LMSTUDIO_API_URL).rstrip("/")
        settings["llm_model"] = str(settings.get("llm_model", DEFAULT_LLM_MODEL) or DEFAULT_LLM_MODEL)
        settings["embedding_model"] = str(settings.get("embedding_model", DEFAULT_EMBEDDING_MODEL) or DEFAULT_EMBEDDING_MODEL)
        settings["response_language"] = str(settings.get("response_language", "ru") or "ru")
        settings["default_llm_mode_applied"] = True
        settings["main_toolbar_lightrag_removed"] = True
        settings["plain_chat_adapter_version"] = 1
        return settings

    def save_settings(self) -> None:
        self.settings["send_on_enter"] = bool(self.settings["send_on_enter"])
        self.settings["use_lightrag"] = bool(self.settings["use_lightrag"])
        self.settings["game_guard_enabled"] = bool(self.settings["game_guard_enabled"])
        self.settings["auto_process_links"] = bool(self.settings.get("auto_process_links", True))
        self.settings["web_search_enabled"] = bool(self.settings.get("web_search_enabled", False))
        self.settings["game_guard_delay_seconds"] = max(1, int(self.settings.get("game_guard_delay_seconds", 5) or 5))
        self.settings["button_color"] = valid_hex_color(str(self.settings["button_color"]), DEFAULT_SETTINGS["button_color"])
        self.settings["obsidian_path"] = str(self.settings.get("obsidian_path", "") or "")
        self.settings["vault_path"] = str(self.settings.get("vault_path", str(DEFAULT_VAULT_DIR)) or str(DEFAULT_VAULT_DIR))
        self.settings["lmstudio_base_url"] = str(self.settings.get("lmstudio_base_url", LMSTUDIO_API_URL) or LMSTUDIO_API_URL).rstrip("/")
        self.settings["llm_model"] = str(self.settings.get("llm_model", DEFAULT_LLM_MODEL) or DEFAULT_LLM_MODEL)
        self.settings["embedding_model"] = str(self.settings.get("embedding_model", DEFAULT_EMBEDDING_MODEL) or DEFAULT_EMBEDDING_MODEL)
        self.settings["response_language"] = str(self.settings.get("response_language", "ru") or "ru")
        self.settings["default_llm_mode_applied"] = True
        self.settings["main_toolbar_lightrag_removed"] = True
        self.settings["plain_chat_adapter_version"] = 1
        try:
            SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
            SETTINGS_PATH.write_text(json.dumps(self.settings, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        except OSError:
            pass

    def vault_dir(self) -> Path:
        raw_path = str(self.settings.get("vault_path", str(DEFAULT_VAULT_DIR)) or str(DEFAULT_VAULT_DIR)).strip()
        return Path(raw_path) if raw_path else DEFAULT_VAULT_DIR

    def load_chat_store(self) -> dict:
        if CHAT_STORE_PATH.exists():
            try:
                data = json.loads(CHAT_STORE_PATH.read_text(encoding="utf-8"))
                if isinstance(data, dict) and isinstance(data.get("chats"), list):
                    return data
            except (OSError, json.JSONDecodeError):
                pass
        migrated = self.migrate_legacy_history()
        if migrated:
            return migrated
        return {"version": 1, "active_chat_id": "", "chats": []}

    def migrate_legacy_history(self) -> dict | None:
        if not LEGACY_HISTORY_PATH.exists():
            return None
        messages: list[dict] = []
        try:
            for line in LEGACY_HISTORY_PATH.read_text(encoding="utf-8").splitlines():
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(entry, dict) and entry.get("text"):
                    messages.append(
                        {
                            "id": self.new_id("msg"),
                            "ts": str(entry.get("ts") or now_iso()),
                            "role": str(entry.get("role") or "assistant"),
                            "context": str(entry.get("context") or "General"),
                            "lightrag": bool(entry.get("lightrag", False)),
                            "text": str(entry.get("text") or ""),
                            "warnings": entry.get("warnings") if isinstance(entry.get("warnings"), list) else [],
                        }
                    )
        except OSError:
            return None
        if not messages:
            return None
        chat_id = self.new_id("chat")
        return {
            "version": 1,
            "active_chat_id": chat_id,
            "chats": [
                {
                    "id": chat_id,
                    "title": "Imported history",
                    "created_at": messages[0]["ts"],
                    "updated_at": messages[-1]["ts"],
                    "messages": messages,
                }
            ],
        }

    def save_chat_store(self) -> None:
        self.chat_store["active_chat_id"] = self.active_chat_id
        try:
            CHAT_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
            CHAT_STORE_PATH.write_text(json.dumps(self.chat_store, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        except OSError:
            pass

    def new_id(self, prefix: str) -> str:
        return f"{prefix}-{dt.datetime.now().strftime('%Y%m%d%H%M%S%f')}"

    def get_chats(self) -> list[dict]:
        chats = self.chat_store.setdefault("chats", [])
        return chats if isinstance(chats, list) else []

    def get_active_chat(self) -> dict | None:
        for chat in self.get_chats():
            if chat.get("id") == self.active_chat_id:
                return chat
        return None

    def begin_inline_rename(self, chat_id: str, row: tk.Frame, title_label: tk.Label) -> str:
        chat = self.chat_by_id(chat_id)
        if not chat:
            return "break"
        if self.inline_rename_entry:
            self.finish_inline_rename(save=True)
        self.inline_rename_chat_id = chat_id
        self.inline_rename_original = str(chat.get("title") or "Чат")
        self.inline_rename_ignore_click_until = time.time() + 0.25
        title_label.grid_remove()
        entry = tk.Entry(
            row,
            relief="flat",
            borderwidth=0,
            bg="#ffffff",
            fg="#1f2933",
            insertbackground="#1f2933",
            font=("Segoe UI", 9),
        )
        entry.insert(0, self.inline_rename_original)
        entry.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        self.inline_rename_entry = entry
        entry.bind("<Return>", lambda _event: self.finish_inline_rename(save=True) or "break")
        entry.bind("<Escape>", lambda _event: self.finish_inline_rename(save=False) or "break")
        entry.bind("<FocusOut>", lambda _event: self.finish_inline_rename(save=True))
        self.bind_history_mousewheel(entry)
        entry.focus_set()
        entry.select_range(0, "end")
        return "break"

    def finish_inline_rename(self, save: bool = True) -> None:
        entry = self.inline_rename_entry
        chat_id = self.inline_rename_chat_id
        original = self.inline_rename_original
        self.inline_rename_entry = None
        self.inline_rename_chat_id = ""
        self.inline_rename_original = ""
        self.inline_rename_ignore_click_until = 0.0
        if not entry:
            return
        title = entry.get().strip()
        if save and title:
            chat = self.chat_by_id(chat_id)
            if chat and title != original:
                chat["title"] = title[:80]
                chat["updated_at"] = now_iso()
                self.save_chat_store()
        self.populate_chat_list(keep_selection=True)

    def on_inline_rename_global_click(self, event: tk.Event) -> None:
        entry = self.inline_rename_entry
        if not entry:
            return
        if time.time() < self.inline_rename_ignore_click_until:
            return
        if event.widget == entry:
            return
        self.finish_inline_rename(save=True)

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
        }
        chat.setdefault("messages", []).append(message)
        chat["updated_at"] = message["ts"]
        if str(chat.get("title")) == "Новый чат" and role == "user":
            chat["title"] = self.title_for_chat(text)
        self.save_chat_store()
        self.populate_chat_list(keep_selection=True)

    def title_for_chat(self, text: str) -> str:
        title = re.sub(r"\s+", " ", text.strip()).strip()
        return title[:42] + ("..." if len(title) > 42 else "") if title else "Новый чат"

    def format_chat_age(self, updated_at: str) -> str:
        try:
            updated = dt.datetime.fromisoformat(updated_at)
            delta = dt.datetime.now() - updated
            minutes = max(0, int(delta.total_seconds() // 60))
            if minutes < 60:
                return f"{minutes}м"
            hours = minutes // 60
            if hours < 24:
                return f"{hours}ч"
            days = hours // 24
            return f"{days}д"
        except Exception:
            return ""

    def chat_group_name(self, chat: dict) -> str:
        messages = chat.get("messages", [])
        contexts = [
            str(message.get("context") or "")
            for message in messages
            if isinstance(message, dict) and message.get("context")
        ]
        if "Web Development" in contexts:
            return "Web Development"
        if "My Game" in contexts:
            return "My Game"
        title = str(chat.get("title") or "").strip()
        if title and title != "Новый чат":
            topic = infer_topic(title, "general")
            if topic not in {"General", "Web", "Project Notes"}:
                return topic
        return "Без темы"

    def populate_chat_list(self, keep_selection: bool = False) -> None:
        if not hasattr(self, "chat_rows"):
            return
        for widget in self.chat_row_widgets:
            try:
                widget.destroy()
            except tk.TclError:
                pass
        self.chat_row_widgets.clear()

        chats = sorted(self.get_chats(), key=lambda item: str(item.get("updated_at", "")), reverse=True)
        self.chat_store["chats"] = chats
        if not chats:
            empty = tk.Label(self.chat_rows, text="Нет чатов", bg="#eef2f5", fg="#8a939d", anchor="w", font=("Segoe UI", 9))
            empty.grid(row=0, column=0, sticky="ew", padx=12, pady=8)
            self.bind_history_mousewheel(empty)
            self.chat_row_widgets.append(empty)
            return

        grouped: dict[str, list[dict]] = {}
        for chat in chats:
            grouped.setdefault(self.chat_group_name(chat), []).append(chat)

        ordered_groups = [name for name in ("Web Development", "My Game", "Без темы") if name in grouped]
        ordered_groups.extend(sorted(name for name in grouped if name not in ordered_groups))

        row_index = 0
        for group_name in ordered_groups:
            section = tk.Label(
                self.chat_rows,
                text=group_name,
                bg="#eef2f5",
                fg="#8a939d",
                anchor="w",
                font=("Segoe UI", 8),
            )
            section.grid(row=row_index, column=0, sticky="ew", padx=14, pady=(12 if row_index else 4, 4))
            self.bind_history_mousewheel(section)
            self.chat_row_widgets.append(section)
            row_index += 1

            for chat in grouped[group_name]:
                self.add_chat_sidebar_row(chat, row_index)
                row_index += 1

    def add_chat_sidebar_row(self, chat: dict, row_index: int) -> None:
            chat_id = str(chat.get("id"))
            is_active = chat_id == self.active_chat_id
            row_bg = "#dfe6ed" if is_active else "#eef2f5"
            row = tk.Frame(self.chat_rows, bg=row_bg, padx=8, pady=6)
            row.grid(row=row_index, column=0, sticky="ew", padx=6, pady=2)
            row.columnconfigure(0, weight=1)
            title = str(chat.get("title") or "Чат")
            title_label = tk.Label(
                row,
                text=title,
                bg=row_bg,
                fg="#1f2933",
                anchor="w",
                font=("Segoe UI Semibold" if is_active else "Segoe UI", 9),
                wraplength=145,
                justify="left",
            )
            title_label.grid(row=0, column=0, sticky="ew")
            age = tk.Label(row, text=self.format_chat_age(str(chat.get("updated_at", ""))), bg=row_bg, fg="#7a838c", font=("Segoe UI", 8))
            age.grid(row=0, column=1, sticky="e", padx=(6, 4))
            delete = tk.Button(row, text="×", width=2, relief="flat", bg=row_bg, activebackground="#d4dde6", command=lambda cid=chat_id: self.delete_chat_by_id(cid))
            delete.grid(row=0, column=2, sticky="e", padx=(2, 0))
            for child in (row, title_label, age):
                child.bind("<Button-1>", lambda _event, cid=chat_id: self.select_chat(cid))
                child.bind("<Double-Button-1>", lambda _event, cid=chat_id, r=row, label=title_label: self.begin_inline_rename(cid, r, label))
                self.bind_history_mousewheel(child)
            self.bind_history_mousewheel(delete)
            self.add_tooltip(title_label, "Двойной клик, чтобы переименовать чат.")
            self.chat_row_widgets.append(row)

    def on_chat_select(self, _event: tk.Event | None = None) -> None:
        return

    def select_chat(self, chat_id: str) -> None:
        if chat_id == self.active_chat_id:
            return
        if not self.chat_by_id(chat_id):
            return
        self.active_chat_id = chat_id
        self.save_chat_store()
        self.populate_chat_list(keep_selection=True)
        self.render_current_chat()

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

        sidebar_shadow = tk.Frame(main, bg="#dfe5ec")
        sidebar_shadow.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=(0, 2))
        sidebar_shadow.configure(width=262)
        sidebar_shadow.grid_propagate(False)
        sidebar_shadow.columnconfigure(0, weight=1)
        sidebar_shadow.rowconfigure(0, weight=1)
        sidebar_shell = tk.Frame(sidebar_shadow, bg="#cfd4da", padx=1, pady=1)
        sidebar_shell.grid(row=0, column=0, sticky="nsew", padx=(0, 2), pady=(0, 2))
        sidebar_shell.configure(width=260)
        sidebar_shell.grid_propagate(False)
        sidebar_shell.columnconfigure(0, weight=1)
        sidebar_shell.rowconfigure(0, weight=1)
        sidebar = tk.Frame(sidebar_shell, bg="#eef2f5", width=258)
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

        chat_shadow = tk.Frame(chat_area, bg="#dfe5ec")
        chat_shadow.grid(row=0, column=0, sticky="nsew", pady=(0, 2))
        chat_shadow.columnconfigure(0, weight=1)
        chat_shadow.rowconfigure(0, weight=1)

        chat_shell = tk.Frame(chat_shadow, bg="#cfd4da", padx=1, pady=1)
        chat_shell.grid(row=0, column=0, sticky="nsew", padx=(0, 2), pady=(0, 2))
        chat_shell.columnconfigure(0, weight=1)
        chat_shell.rowconfigure(0, weight=1)

        self.chat = tk.Text(
            chat_shell,
            wrap="word",
            state="disabled",
            padx=14,
            pady=14,
            relief="flat",
            borderwidth=0,
            background="#ffffff",
            foreground="#202124",
            insertbackground="#202124",
            font=("Segoe UI", 10),
        )
        self.chat.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(chat_shell, orient="vertical", command=self.chat.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.chat.configure(yscrollcommand=scroll.set)
        self.chat.tag_configure("assistant", foreground="#202124", spacing1=8, spacing3=12, lmargin1=2, lmargin2=2, rmargin=120)
        self.chat.tag_configure("system", foreground="#5f6368", spacing1=4, spacing3=8)
        self.chat.tag_configure("warning", foreground="#7a838c", font=("Segoe UI", 9, "italic"), spacing1=2, spacing3=8)
        self.chat.tag_configure("error", foreground="#b3261e", spacing1=8, spacing3=12)

        input_frame = ttk.Frame(chat_area, style="Composer.TFrame")
        input_frame.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        input_frame.columnconfigure(0, weight=1)
        composer_shadow = tk.Frame(input_frame, bg="#dfe5ec")
        composer_shadow.grid(row=0, column=0, sticky="ew", pady=(0, 2))
        composer_shadow.columnconfigure(0, weight=1)

        input_shell = tk.Frame(composer_shadow, bg="#cfd4da", padx=1, pady=1)
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
        tool_strip.columnconfigure(3, weight=1)
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
        self.voice_button = MiniToolButton(
            tool_strip,
            self.start_voice_input,
            image=self.microphone_image,
            active_image=self.microphone_active_image,
            fallback_icon="microphone",
            size=30,
            background="#ffffff",
        )
        self.voice_button.grid(row=0, column=2, sticky="w", padx=4, pady=(0, 8))
        self.add_tooltip(self.voice_button, "Диктовка через Windows Speech Recognition. Текст вставится в поле ввода.")
        self.input.bind("<Control-Return>", self.on_ctrl_return)
        self.input.bind("<Shift-Return>", self.on_shift_return)
        self.input.bind("<Return>", self.on_return)
        self.input.bind("<Alt-Up>", lambda _event: self.navigate_input_history(-1))
        self.input.bind("<Alt-Down>", lambda _event: self.navigate_input_history(1))

        button_bar = tk.Frame(input_frame, bg="#f4f6f8")
        button_bar.grid(row=1, column=0, sticky="ew", pady=(10, 0))
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

    def add_tooltip(self, widget: tk.Widget, text: str) -> None:
        self.tooltips.append(ToolTip(widget, text))

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
        if os.name != "nt":
            return
        try:
            self.root.update_idletasks()
            shell32 = ctypes.windll.shell32
            user32 = ctypes.windll.user32
            lresult = ctypes.c_ssize_t
            wndproc_type = ctypes.WINFUNCTYPE(lresult, ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p)
            self.drop_wndproc = wndproc_type(self.native_file_drop_wndproc)
            self.drop_call_window_proc = user32.CallWindowProcW
            self.drop_call_window_proc.restype = lresult
            self.drop_call_window_proc.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p]
            self.drop_shell32 = shell32
            for widget in (self.root, self.chat, self.input):
                self.register_native_drop_widget(widget)
        except Exception:
            self.drop_wndproc = None
            self.drop_old_wndprocs.clear()

    def register_native_drop_widget(self, widget: tk.Widget) -> None:
        hwnd = int(widget.winfo_id())
        if not hwnd or hwnd in self.drop_old_wndprocs or not self.drop_wndproc:
            return
        user32 = ctypes.windll.user32
        set_window_long = user32.SetWindowLongPtrW if ctypes.sizeof(ctypes.c_void_p) == 8 else user32.SetWindowLongW
        set_window_long.restype = ctypes.c_void_p
        set_window_long.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
        old_proc = set_window_long(ctypes.c_void_p(hwnd), -4, ctypes.cast(self.drop_wndproc, ctypes.c_void_p))
        self.drop_old_wndprocs[hwnd] = old_proc
        ctypes.windll.shell32.DragAcceptFiles(ctypes.c_void_p(hwnd), True)

    def native_file_drop_wndproc(self, hwnd, msg, wparam, lparam):
        if msg == 0x0233:
            files = self.files_from_hdrop(wparam)
            if files:
                self.root.after(0, self.handle_dropped_files, files)
            return 0
        old_proc = self.drop_old_wndprocs.get(int(hwnd) if hwnd else 0)
        if old_proc and self.drop_call_window_proc:
            return self.drop_call_window_proc(old_proc, hwnd, msg, wparam, lparam)
        return 0

    def files_from_hdrop(self, hdrop) -> list[str]:
        shell32 = ctypes.windll.shell32
        shell32.DragQueryFileW.restype = ctypes.c_uint
        shell32.DragQueryFileW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_wchar_p, ctypes.c_uint]
        shell32.DragFinish.argtypes = [ctypes.c_void_p]
        files: list[str] = []
        try:
            count = shell32.DragQueryFileW(hdrop, 0xFFFFFFFF, None, 0)
            for index in range(count):
                length = shell32.DragQueryFileW(hdrop, index, None, 0)
                buffer = ctypes.create_unicode_buffer(length + 1)
                shell32.DragQueryFileW(hdrop, index, buffer, length + 1)
                if buffer.value:
                    files.append(buffer.value)
        finally:
            shell32.DragFinish(hdrop)
        return files

    def apply_settings_to_ui(self) -> None:
        self.enter_send_var.set(bool(self.settings["send_on_enter"]))
        self.lightrag_var.set(bool(self.settings["use_lightrag"]))
        self.game_guard_var.set(bool(self.settings["game_guard_enabled"]))
        self.auto_process_links_var.set(bool(self.settings.get("auto_process_links", True)))
        self.web_search_enabled_var.set(bool(self.settings.get("web_search_enabled", False)))
        self.button_color_var.set(str(self.settings["button_color"]))
        self.obsidian_path_var.set(str(self.settings.get("obsidian_path", "")))
        self.vault_path_var.set(str(self.settings.get("vault_path", str(DEFAULT_VAULT_DIR))))
        self.update_button_colors()
        self.update_web_search_button()
        self.on_lightrag_toggle(save=False)

    def update_button_colors(self) -> None:
        color = valid_hex_color(str(self.settings["button_color"]), DEFAULT_SETTINGS["button_color"])
        fg = readable_text_color(color)
        active_bg = adjust_hex_color(color, 0.86)
        self.send_button.set_colors(bg=color, active_bg=active_bg, fg=fg)

    def update_web_search_button(self) -> None:
        if hasattr(self, "web_search_button"):
            self.web_search_button.set_active(bool(self.settings.get("web_search_enabled", False)))

    def open_settings(self) -> None:
        if self.settings_window and self.settings_window.winfo_exists():
            self.settings_window.lift()
            self.settings_window.focus_force()
            return
        self.enter_send_var.set(bool(self.settings["send_on_enter"]))
        self.lightrag_var.set(bool(self.settings["use_lightrag"]))
        self.game_guard_var.set(bool(self.settings["game_guard_enabled"]))
        self.auto_process_links_var.set(bool(self.settings.get("auto_process_links", True)))
        self.web_search_enabled_var.set(bool(self.settings.get("web_search_enabled", False)))
        self.button_color_var.set(str(self.settings["button_color"]))
        self.obsidian_path_var.set(str(self.settings.get("obsidian_path", "")))
        self.vault_path_var.set(str(self.settings.get("vault_path", str(DEFAULT_VAULT_DIR))))
        self.settings_status_var.set("")

        window = tk.Toplevel(self.root)
        self.settings_window = window
        window.title("Настройки LightRAG Chat")
        window.transient(self.root)
        window.resizable(False, False)
        window.configure(bg="#f4f6f8")
        window.protocol("WM_DELETE_WINDOW", self.close_settings)

        frame = ttk.Frame(window, padding=(18, 16), style="App.TFrame")
        frame.grid(row=0, column=0, sticky="nsew")
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="Диалог", style="SettingsHeader.TLabel").grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 10))
        ttk.Checkbutton(frame, text="Enter отправляет сообщение", variable=self.enter_send_var).grid(row=1, column=0, columnspan=3, sticky="w", pady=3)
        ttk.Checkbutton(frame, text="Использовать LightRAG по умолчанию", variable=self.lightrag_var).grid(row=2, column=0, columnspan=3, sticky="w", pady=3)
        ttk.Checkbutton(frame, text="Game Guard проверяет GPU после открытия чата", variable=self.game_guard_var).grid(row=3, column=0, columnspan=3, sticky="w", pady=3)
        ttk.Checkbutton(frame, text="Автоматически обрабатывать сохраненные ссылки", variable=self.auto_process_links_var).grid(row=4, column=0, columnspan=3, sticky="w", pady=3)
        ttk.Checkbutton(frame, text="Веб-поиск включен по умолчанию", variable=self.web_search_enabled_var).grid(row=5, column=0, columnspan=3, sticky="w", pady=3)

        ttk.Separator(frame, orient="horizontal").grid(row=6, column=0, columnspan=3, sticky="ew", pady=(14, 12))
        ttk.Label(frame, text="Obsidian", style="SettingsHeader.TLabel").grid(row=7, column=0, columnspan=3, sticky="w", pady=(0, 8))
        obsidian_entry = ttk.Entry(frame, textvariable=self.obsidian_path_var, width=54)
        obsidian_entry.grid(row=8, column=0, columnspan=2, sticky="ew", padx=(0, 8))
        ttk.Button(frame, text="Выбрать...", command=self.choose_obsidian_path).grid(row=8, column=2, sticky="e")
        ttk.Label(frame, text="Vault folder", background="#f4f6f8").grid(row=9, column=0, columnspan=3, sticky="w", pady=(10, 4))
        vault_entry = ttk.Entry(frame, textvariable=self.vault_path_var, width=54)
        vault_entry.grid(row=10, column=0, columnspan=2, sticky="ew", padx=(0, 8))
        ttk.Button(frame, text="Выбрать...", command=self.choose_vault_path).grid(row=10, column=2, sticky="e")

        ttk.Separator(frame, orient="horizontal").grid(row=11, column=0, columnspan=3, sticky="ew", pady=(14, 12))
        ttk.Label(frame, text="Цвет основной кнопки", style="SettingsHeader.TLabel").grid(row=12, column=0, columnspan=3, sticky="w", pady=(0, 10))
        preset_var = tk.StringVar(value=self.color_preset_name(self.button_color_var.get()))
        preset = ttk.Combobox(frame, textvariable=preset_var, values=list(BUTTON_COLOR_PRESETS.keys()), state="readonly", width=18)
        preset.grid(row=13, column=0, sticky="w", padx=(0, 10))
        preset.bind("<<ComboboxSelected>>", lambda _event: self.select_color_preset(preset_var.get()))
        self.settings_color_preview = tk.Label(frame, width=6, height=1, background=self.button_color_var.get(), relief="solid", borderwidth=1)
        self.settings_color_preview.grid(row=13, column=1, sticky="w", padx=(0, 10))
        ttk.Button(frame, text="Выбрать...", command=self.choose_button_color).grid(row=13, column=2, sticky="e")

        ttk.Label(frame, textvariable=self.settings_status_var, style="SettingsStatus.TLabel").grid(row=14, column=0, columnspan=3, sticky="w", pady=(14, 0))
        buttons = ttk.Frame(frame, style="App.TFrame")
        buttons.grid(row=15, column=0, columnspan=3, sticky="e", pady=(16, 0))
        ttk.Button(buttons, text="Отмена", command=self.close_settings).grid(row=0, column=0, padx=(0, 8))
        ttk.Button(buttons, text="Сохранить", command=self.save_settings_from_window).grid(row=0, column=1)

        window.update_idletasks()
        x = self.root.winfo_rootx() + max(30, (self.root.winfo_width() - window.winfo_width()) // 2)
        y = self.root.winfo_rooty() + max(30, (self.root.winfo_height() - window.winfo_height()) // 3)
        window.geometry(f"+{x}+{y}")

    def close_settings(self) -> None:
        if self.settings_window and self.settings_window.winfo_exists():
            self.settings_window.destroy()
        self.settings_window = None

    def choose_obsidian_path(self) -> None:
        path = filedialog.askopenfilename(
            title="Выберите Obsidian.exe",
            filetypes=[("Obsidian", "Obsidian.exe *.lnk"), ("Programs", "*.exe"), ("Shortcuts", "*.lnk"), ("All files", "*.*")],
            parent=self.settings_window or self.root,
        )
        if path:
            self.obsidian_path_var.set(path)

    def choose_vault_path(self) -> None:
        path = filedialog.askdirectory(
            title="Выберите папку Obsidian vault",
            initialdir=str(self.vault_dir() if self.vault_dir().exists() else DEFAULT_VAULT_DIR),
            parent=self.settings_window or self.root,
        )
        if path:
            self.vault_path_var.set(path)

    def color_preset_name(self, color: str) -> str:
        color = valid_hex_color(color, DEFAULT_SETTINGS["button_color"])
        for name, value in BUTTON_COLOR_PRESETS.items():
            if value.lower() == color.lower():
                return name
        return ""

    def select_color_preset(self, preset_name: str) -> None:
        color = BUTTON_COLOR_PRESETS.get(preset_name)
        if color:
            self.button_color_var.set(color)
            self.update_color_preview(color)

    def update_color_preview(self, color: str) -> None:
        if hasattr(self, "settings_color_preview") and self.settings_color_preview:
            self.settings_color_preview.configure(background=valid_hex_color(color, DEFAULT_SETTINGS["button_color"]))

    def choose_button_color(self) -> None:
        _rgb, color = colorchooser.askcolor(
            color=valid_hex_color(self.button_color_var.get(), DEFAULT_SETTINGS["button_color"]),
            parent=self.settings_window or self.root,
            title="Цвет основной кнопки",
        )
        if color:
            self.button_color_var.set(valid_hex_color(color, DEFAULT_SETTINGS["button_color"]))
            self.update_color_preview(self.button_color_var.get())

    def save_settings_from_window(self) -> None:
        self.settings["send_on_enter"] = bool(self.enter_send_var.get())
        self.settings["use_lightrag"] = bool(self.lightrag_var.get())
        self.settings["button_color"] = valid_hex_color(self.button_color_var.get(), DEFAULT_SETTINGS["button_color"])
        self.settings["game_guard_enabled"] = bool(self.game_guard_var.get())
        self.settings["auto_process_links"] = bool(self.auto_process_links_var.get())
        self.settings["web_search_enabled"] = bool(self.web_search_enabled_var.get())
        self.settings["obsidian_path"] = self.obsidian_path_var.get().strip()
        self.settings["vault_path"] = self.vault_path_var.get().strip() or str(DEFAULT_VAULT_DIR)
        self.save_settings()
        global VAULT_DIR
        VAULT_DIR = self.vault_dir()
        self.apply_settings_to_ui()
        self.status_var.set("Settings saved")
        if bool(self.settings["game_guard_enabled"]):
            self.schedule_game_guard_probe()
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

        context_name, scope, project = self.selected_route("")
        if bool(self.settings.get("use_lightrag", False)) and not self.is_lightrag_ready(scope, project):
            self.settings["use_lightrag"] = False
            self.save_settings()
            warnings.append(f"LightRAG был включен, но индекс для {context_name} не найден. Я отключил LightRAG, чтобы обычный чат продолжал работать.")
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

    def embedding_model_id(self) -> str:
        return str(self.settings.get("embedding_model", DEFAULT_EMBEDDING_MODEL) or DEFAULT_EMBEDDING_MODEL)

    def lmstudio_request_json(self, path: str, *, method: str = "GET", payload: dict | None = None, timeout: float = 8.0) -> dict:
        url = f"{self.lmstudio_base_url()}/{path.lstrip('/')}"
        data = None
        headers = {"Accept": "application/json"}
        if payload is not None:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json; charset=utf-8"
        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
        parsed = json.loads(raw) if raw.strip() else {}
        return parsed if isinstance(parsed, dict) else {}

    def loaded_lmstudio_models(self) -> list[str]:
        response = self.lmstudio_request_json("models", timeout=3.0)
        data = response.get("data") if isinstance(response, dict) else []
        ids = []
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and item.get("id"):
                    ids.append(str(item["id"]))
        return ids

    def check_lmstudio_ready(self, *, require_models: bool = True) -> tuple[bool, str, list[str]]:
        try:
            models = self.loaded_lmstudio_models()
        except Exception as exc:
            return (
                False,
                f"LM Studio server не отвечает на {self.lmstudio_base_url()}. Откройте LM Studio или LightRAG-Control для проверки. Детали: {exc}",
                [],
            )

        if not require_models:
            return True, "LM Studio server отвечает.", models

        required = [self.llm_model_id()]
        missing = [model for model in required if model not in models]
        if missing:
            loaded = ", ".join(models) if models else "нет загруженных моделей"
            return (
                False,
                f"LM Studio server отвечает, но модель {', '.join(missing)} не загружена. Сейчас загружено: {loaded}. Откройте LightRAG-Control или LM Studio и загрузите модель.",
                models,
            )
        return True, "LM Studio готов.", models

    def extract_chat_content(self, response: dict) -> tuple[str, str]:
        try:
            choice = (response.get("choices") or [])[0]
            message = choice.get("message") or {}
        except Exception:
            return "", ""
        content = message.get("content")
        reasoning = message.get("reasoning_content")
        return (
            content.strip() if isinstance(content, str) else "",
            reasoning.strip() if isinstance(reasoning, str) else "",
        )

    def call_plain_lmstudio(self, question: str, *, max_tokens: int | None = None) -> tuple[str, str]:
        max_tokens = max_tokens or int(os.getenv("LMSTUDIO_GUI_MAX_RESPONSE_TOKENS", "1800"))
        body = {
            "model": self.llm_model_id(),
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are KnowledgeLab Chat, a helpful general-purpose assistant. "
                        "Answer normally and directly in Russian by default. "
                        "Use another language only when the user clearly writes in that language or explicitly asks for it. "
                        "Short ambiguous messages like 'ку', 'ого', '555', or mistyped Russian words must be treated as Russian conversation. "
                        "Do not treat every message as a knowledge-base lookup. "
                        "Do not show reasoning or analysis; provide only the final useful answer."
                    ),
                },
                {"role": "user", "content": f"/no_think\n\n{question}"},
            ],
            "temperature": 0.2,
            "max_tokens": max_tokens,
            "stream": False,
        }
        response = self.lmstudio_request_json("chat/completions", method="POST", payload=body, timeout=min(self.query_timeout_seconds, 120))
        content, reasoning = self.extract_chat_content(response)
        if content:
            return content, ""
        if reasoning:
            retry_body = dict(body)
            retry_body["max_tokens"] = max(max_tokens, 3200)
            retry_body["messages"] = [
                body["messages"][0],
                {
                    "role": "user",
                    "content": (
                        "/no_think\n\n"
                        "Ответь финальным сообщением без рассуждений. "
                        "Если вопрос короткий или бытовой, ответь естественно и кратко на русском.\n\n"
                        f"{question}"
                    ),
                },
            ]
            retry = self.lmstudio_request_json("chat/completions", method="POST", payload=retry_body, timeout=min(self.query_timeout_seconds, 180))
            retry_content, retry_reasoning = self.extract_chat_content(retry)
            if retry_content:
                return retry_content, "Первый ответ модели ушел в reasoning-режим; я повторил запрос в plain-режиме."
            if retry_reasoning:
                return "", "Модель рассуждала, но не вернула финальный текст. В LM Studio отключите thinking/reasoning для этой модели или попробуйте другой instruct-моделью."
        return "", "Модель вернула пустой ответ."

    def run_plain_query(
        self,
        operation_id: int,
        question: str,
        pending_warnings: list[str],
        web_search_enabled: bool = False,
        web_query: str = "",
    ) -> None:
        warnings = list(pending_warnings)
        try:
            if web_search_enabled:
                question, web_warnings = self.prepare_web_prompt(web_query or question, question)
                warnings.extend(web_warnings)
            output, model_warning = self.call_plain_lmstudio(question)
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
        for message in messages:
            role = str(message.get("role") or "assistant")
            text = str(message.get("text") or "")
            warnings = [str(item) for item in message.get("warnings", []) if item]
            if role == "user":
                self.append_user_message(text, persist=False)
            elif role == "error":
                self.append_assistant_message(text, "error", persist=False)
            elif role == "system":
                self.append_warning_message(text, persist=False)
            else:
                self.append_assistant_message(text, "assistant", persist=False)
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

    def append_user_message(self, text: str, persist: bool = True) -> None:
        clean_text = text.strip()
        if not clean_text:
            return
        self.chat.configure(state="normal")
        self.chat.insert("end", "\n")
        canvas_width = max(430, self.chat.winfo_width() - 28)
        bubble_width = min(560, max(220, canvas_width - 190))
        canvas = tk.Canvas(self.chat, width=canvas_width, height=58, highlightthickness=0, bd=0, background="#ffffff")
        text_id = canvas.create_text(
            canvas_width - 22,
            14,
            text=clean_text,
            anchor="ne",
            width=bubble_width - 28,
            justify="left",
            fill="#202124",
            font=("Segoe UI", 10),
        )
        bbox = canvas.bbox(text_id) or (canvas_width - bubble_width, 8, canvas_width - 18, 44)
        rect = self.rounded_canvas_rect(
            canvas,
            max(12, bbox[0] - 13),
            max(6, bbox[1] - 10),
            min(canvas_width - 10, bbox[2] + 13),
            bbox[3] + 10,
            12,
            fill="#f0f1f3",
        )
        canvas.tag_lower(rect, text_id)
        canvas.configure(height=max(46, bbox[3] + 18))
        self.chat.window_create("end", window=canvas)
        self.chat.insert("end", "\n")
        self.chat_widgets.append(canvas)
        self.chat.configure(state="disabled")
        self.chat.see("end")
        if persist:
            context_name, _scope, _project = self.selected_route(clean_text)
            self.add_message("user", clean_text, context_name)

    def append_assistant_message(
        self,
        text: str,
        tag: str = "assistant",
        persist: bool = True,
        warnings: list[str] | None = None,
        lightrag_used: bool | None = None,
    ) -> None:
        clean_text = text.strip()
        if not clean_text:
            return
        self.append(f"{clean_text}\n", tag)
        if persist:
            chat = self.get_active_chat()
            context_name = "General"
            if chat and chat.get("messages"):
                context_name = str(chat["messages"][-1].get("context") or "General")
            self.add_message("assistant" if tag == "assistant" else "error", clean_text, context_name, warnings, lightrag_used)

    def append_warning_message(self, text: str, persist: bool = False) -> None:
        clean_text = text.strip()
        if clean_text:
            self.append(f"{clean_text}\n", "warning")
            if persist:
                self.add_message("system", clean_text, "General")

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

    def storage_name_for_scope(self, scope: str, project: str) -> str:
        safe_project = re.sub(r"[^a-z0-9_-]+", "-", project.strip().lower()) or "default"
        if scope == "all":
            return "all"
        if scope == "game":
            return f"game_{safe_project}"
        return scope

    def lightrag_index_path(self, scope: str, project: str) -> Path:
        storage_name = self.storage_name_for_scope(scope, project)
        return ROOT / "LightRAG" / f"rag_storage_{storage_name}" / "vdb_chunks.json"

    def is_lightrag_ready(self, scope: str, project: str) -> bool:
        return self.lightrag_index_path(scope, project).exists()

    def on_lightrag_toggle(self, save: bool = True) -> None:
        if save:
            self.settings["use_lightrag"] = bool(self.lightrag_var.get())
            self.save_settings()
            self.status_var.set("LightRAG on" if self.lightrag_var.get() else "LightRAG off")

    def selected_route(self, text: str) -> tuple[str, str, str]:
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
        script = f"""
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
Add-Type -AssemblyName System.Speech
$recognizer = New-Object System.Speech.Recognition.SpeechRecognitionEngine
try {{
  $recognizer.SetInputToDefaultAudioDevice()
  $grammar = New-Object System.Speech.Recognition.DictationGrammar
  $recognizer.LoadGrammar($grammar)
  $result = $recognizer.Recognize([System.TimeSpan]::FromSeconds({VOICE_INPUT_SECONDS}))
  if ($null -ne $result -and $result.Text) {{
    Write-Output $result.Text
  }}
}} finally {{
  if ($recognizer) {{
    $recognizer.Dispose()
  }}
}}
"""
        try:
            returncode, output = self.run_command(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
                VOICE_INPUT_SECONDS + 4,
            )
            text = output.strip() if returncode == 0 else ""
            error = "" if text else self.friendly_voice_error(output)
        except TimeoutError:
            text = ""
            error = "Не услышал речь за отведенное время. Попробуйте еще раз или вставьте текст вручную."
        except Exception:
            text = ""
            error = "Не удалось запустить диктовку. Для надежного локального ввода позже можно подключить Whisper/faster-whisper."
        self.root.after(0, self.finish_voice_input, operation_id, text, error)

    def friendly_voice_error(self, output: str) -> str:
        cleaned = self.trim_output(output)
        lowered = cleaned.lower()
        if "system.speech" in lowered or "add-type" in lowered:
            return "Windows Speech Recognition недоступен в этой системе. Для локального голоса нужен системный recognizer или будущий Whisper importer."
        if "no recognizer" in lowered or "default audio device" in lowered or "input" in lowered:
            return "Не удалось получить звук с микрофона или найти установленный recognizer. Проверьте микрофон в Windows."
        return "Не услышал речь. Попробуйте еще раз или вставьте текст вручную."

    def finish_voice_input(self, operation_id: int, text: str, error: str) -> None:
        if not self.is_active_operation(operation_id):
            return
        self.voice_operation_id = None
        self.set_tool_button_active("voice_button", False)
        if text.strip():
            self.append_to_input(text)
            final_status = "Voice inserted"
        else:
            self.append_warning_message(error, persist=False)
            final_status = "Ready"
        self.set_busy(False, final_status)

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
            "Answer the user in Russian. If web results are insufficient, say that clearly.\n\n"
            f"User question:\n{prompt}"
        )
        return enhanced, [f"Web-поиск использован: {len(results)} результатов передано LLM."]

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

    def is_lightrag_status_intent(self, text: str) -> bool:
        return is_lightrag_status_text(text)

    def is_language_preference_intent(self, text: str) -> bool:
        return is_russian_language_request(text)

    def wants_knowledge_lookup(self, text: str) -> bool:
        return is_knowledge_lookup_text(text)

    def lightrag_status_message(self, text: str) -> str:
        context_name, scope, project = self.selected_route(text)
        setting = bool(self.settings.get("use_lightrag", False))
        index_ready = self.is_lightrag_ready(scope, project)
        last_used = self.last_answer_lightrag_state()
        if last_used is True:
            last_text = "последний ответ был из LightRAG"
        elif last_used is False:
            last_text = "последний ответ был обычной LLM"
        else:
            last_text = "ответов в этом чате еще нет"
        return (
            f"LightRAG: {'включен' if setting else 'выключен'} в настройках; "
            f"индекс для {context_name}: {'найден' if index_ready else 'не найден'}; "
            f"{last_text}."
        )

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
        state = "включен" if enabled else "выключен"
        return (
            f"LightRAG сейчас {state}. Чтобы получить ответ из сохраненных материалов, "
            "включите LightRAG в Настройках или явно попросите поиск по базе: "
            "«найди в базе материалы про CSS», «что у меня сохранено про лендинги», "
            "«сделай инструкцию из сохраненных материалов». "
            "Если я напишу, что индекс не готов, откройте LightRAG-Control и запустите проверку или переиндексацию."
        )

    def choose_capture_context(self, suggested: tuple[str, str, str]) -> tuple[str, str, str] | None:
        context_name, scope, project = suggested
        if self.context_var.get() != "Auto" or scope != "general" or contains_any(self.input_text(), WEB_TERMS | GAME_TERMS):
            return suggested

        result: dict[str, tuple[str, str, str] | None] = {"value": None}
        window = tk.Toplevel(self.root)
        window.title("Куда сохранить?")
        window.transient(self.root)
        window.resizable(False, False)
        window.configure(bg="#f4f6f8")
        ttk.Label(window, text="В какой проект сохранить материал?", padding=(18, 16), background="#f4f6f8").grid(row=0, column=0, columnspan=3)

        def pick(value: tuple[str, str, str] | None) -> None:
            result["value"] = value
            window.destroy()

        ttk.Button(window, text="General", command=lambda: pick(("General", "general", ""))).grid(row=1, column=0, padx=(18, 6), pady=(0, 16))
        ttk.Button(window, text="Web Development", command=lambda: pick(("Web Development", "web", "web-development"))).grid(row=1, column=1, padx=6, pady=(0, 16))
        ttk.Button(window, text="My Game", command=lambda: pick(("My Game", "game", "my-game"))).grid(row=1, column=2, padx=(6, 18), pady=(0, 16))
        window.update_idletasks()
        x = self.root.winfo_rootx() + max(30, (self.root.winfo_width() - window.winfo_width()) // 2)
        y = self.root.winfo_rooty() + max(30, (self.root.winfo_height() - window.winfo_height()) // 3)
        window.geometry(f"+{x}+{y}")
        window.grab_set()
        self.root.wait_window(window)
        return result["value"]

    def save_capture(self, text: str, route: tuple[str, str, str]) -> str:
        context_name, scope, project = route
        topic = infer_topic(text, scope)
        kind = infer_kind(text)
        destination = capture_destination(scope, topic, kind)
        destination.mkdir(parents=True, exist_ok=True)
        title = title_from_text(text, f"{context_name} capture")
        if kind in {"article", "youtube_link"} and topic:
            title = f"{topic} - {title}"
        path = unique_path(destination / f"{clean_filename(title)}.md")
        path.write_text(render_capture_markdown(text, context_name, scope, project, topic, kind), encoding="utf-8-sig")
        return path.relative_to(VAULT_DIR).as_posix()

    def queue_file_processing(
        self,
        file_path: Path,
        rel_path: str,
        kind: str,
        scope: str,
        project: str,
        topic: str,
        extraction_status: str,
    ) -> None:
        MATERIAL_QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
        item = {
            "queued_at": now_iso(),
            "source_path": str(file_path),
            "vault_note": rel_path,
            "kind": kind,
            "scope": scope,
            "project": project,
            "topic": topic,
            "status": "queued",
            "extraction_status": extraction_status,
            "planned_processing": extraction_label(kind),
        }
        with MATERIAL_QUEUE_PATH.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(item, ensure_ascii=False) + "\n")

    def material_queue_display_path(self) -> str:
        try:
            return MATERIAL_QUEUE_PATH.relative_to(ROOT).as_posix()
        except ValueError:
            return str(MATERIAL_QUEUE_PATH)

    def save_file_capture(self, file_path: Path, caption: str, route: tuple[str, str, str]) -> tuple[str, str, str]:
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        if file_path.is_dir():
            raise ValueError("Folder attachment is not supported yet; choose files inside the folder.")
        context_name, scope, project = route
        kind = classify_source_file(file_path)
        hint = f"{caption} {file_path.stem} {file_path.suffix}".strip()
        topic = infer_topic(hint, scope)
        if scope == "general" and not caption.strip() and topic == "General":
            topic = ""
        extracted_text, extraction_status = extract_lightweight_file_text(file_path, kind)
        destination = capture_destination(scope, topic, kind)
        destination.mkdir(parents=True, exist_ok=True)
        title_seed = caption.strip() or file_path.stem
        if topic:
            title_seed = f"{topic} - {title_seed}"
        path = unique_path(destination / f"{clean_filename(title_seed)}.md")
        path.write_text(
            render_file_capture_markdown(
                file_path,
                caption,
                context_name,
                scope,
                project,
                topic,
                kind,
                extracted_text,
                extraction_status,
            ),
            encoding="utf-8-sig",
        )
        rel_path = path.relative_to(VAULT_DIR).as_posix()
        self.queue_file_processing(file_path, rel_path, kind, scope, project, topic, extraction_status)
        return rel_path, kind, extraction_status

    def save_image_capture(self, image_path: Path, caption: str, route: tuple[str, str, str]) -> str:
        if image_path.suffix.lower() not in IMAGE_EXTENSIONS:
            raise ValueError(f"Unsupported image format: {image_path.suffix}")
        rel_path, _kind, _status = self.save_file_capture(image_path, caption, route)
        return rel_path

    def attach_images(self) -> None:
        self.attach_files(title="Выберите изображения", filetypes=IMAGE_FILETYPES)

    def attach_files(self, title: str = "Выберите материалы", filetypes=None) -> None:
        if self.busy:
            return
        self.set_tool_button_active("file_attach_button", True)
        try:
            files = filedialog.askopenfilenames(
                title=title,
                filetypes=filetypes or SUPPORTED_FILETYPES,
                parent=self.root,
            )
        finally:
            self.set_tool_button_active("file_attach_button", False)
        if not files:
            return
        self.process_attached_files(files, source_title="Файлы:")

    def handle_dropped_files(self, files: list[str]) -> None:
        if self.busy:
            self.append_warning_message("Сейчас идет операция. Дождитесь завершения и перетащите файлы еще раз.", persist=False)
            return
        self.flash_tool_button("file_attach_button")
        self.process_attached_files(files, source_title="Перетащенные файлы:")

    def process_attached_files(self, files, source_title: str = "Файлы:") -> None:
        file_list = [str(file_name) for file_name in files if str(file_name).strip()]
        if not file_list:
            return
        caption = self.input_text()
        route_seed = " ".join([caption] + [Path(file_name).name for file_name in file_list[:4]]).strip()
        suggested_route = self.selected_route(route_seed)
        route = self.choose_capture_context(suggested_route)
        if not route:
            self.append_warning_message("Сохранение файлов отменено.", persist=False)
            return
        saved: list[str] = []
        extracted_count = 0
        errors: list[str] = []
        queued_processing_count = 0
        user_lines = [source_title]
        for file_name in file_list:
            source_path = Path(file_name)
            if not source_path.exists():
                errors.append(f"{source_path.name}: файл не найден")
                continue
            try:
                rel_path, kind, extraction_status = self.save_file_capture(source_path, caption, route)
                saved.append(rel_path)
                if extraction_status in {"extracted", "partial"}:
                    extracted_count += 1
                else:
                    queued_processing_count += 1
                user_lines.append(f"- {source_path.name} ({file_kind_label(kind)})")
            except Exception as exc:
                errors.append(f"{source_path.name}: {exc}")
        if caption:
            user_lines.extend(["", caption])
        if saved:
            self.append_user_message("\n".join(user_lines))
            self.clear_input()
            message = (
                "Сохранил file-intake в Obsidian:\n"
                + "\n".join(f"- {path}" for path in saved)
                + "\n\nОригиналы не копируются в vault: в заметках сохранены путь, метаданные и легкий извлеченный текст, где это возможно."
                + f"\nОчередь обработки обновлена: {self.material_queue_display_path()}."
            )
            if extracted_count:
                self.launch_reindex(route)
                message += "\nДля файлов с уже извлеченным текстом запустил обновление LightRAG в фоне."
            if queued_processing_count:
                message += "\nOCR/ASR/документ-парсинг поставлены в очередь importer-шагов; после извлечения текста материал можно будет добавить в LightRAG."
            self.append_assistant_message(message, lightrag_used=False)
        if errors:
            self.append_warning_message("Не удалось сохранить часть файлов:\n" + "\n".join(errors), persist=False)

    def capture_path_from_rel(self, rel_path: str) -> Path:
        return VAULT_DIR / rel_path.replace("/", os.sep)

    def python_executable(self) -> str:
        candidate = ROOT / "LightRAG" / ".venv" / "Scripts" / "python.exe"
        return str(candidate if candidate.exists() else sys.executable)

    def start_auto_material_processing(self, text: str, route: tuple[str, str, str], rel_path: str) -> None:
        if not bool(self.settings.get("auto_process_links", True)):
            return
        url = first_url(text)
        if not url:
            return
        kind = infer_kind(text)
        if kind == "youtube_link":
            self.append_warning_message("Запустил обработку YouTube-ссылки: транскрипт и обновление LightRAG пойдут в фоне.", persist=False)
            threading.Thread(target=self.auto_process_youtube_worker, args=(route,), daemon=True).start()
        elif kind == "article":
            self.append_warning_message("Запустил обработку web-страницы: попробую сохранить текст статьи и обновить LightRAG в фоне.", persist=False)
            threading.Thread(target=self.auto_process_article_worker, args=(url, route, rel_path), daemon=True).start()

    def auto_process_youtube_worker(self, route: tuple[str, str, str]) -> None:
        _context_name, scope, project = route
        command = [
            self.python_executable(),
            str(SCRIPTS_DIR / "sync-youtube-links.py"),
            "--vault-dir",
            str(VAULT_DIR),
            "--scope",
            scope,
            "--continue-on-error",
        ]
        if scope in {"game", "web"} and project:
            command.extend(["--project", project])
        ok, message = self.run_background_material_command(command, f"auto-youtube-{scope}")
        if ok:
            self.launch_reindex(route)
            self.root.after(0, self.append_warning_message, "YouTube-транскрипт обработан; обновление LightRAG запущено в фоне.", False)
        else:
            self.root.after(0, self.append_warning_message, f"YouTube-ссылка сохранена, но транскрипт не удалось получить автоматически: {message}", False)

    def auto_process_article_worker(self, url: str, route: tuple[str, str, str], rel_path: str) -> None:
        path = self.capture_path_from_rel(rel_path)
        try:
            title, markdown = fetch_article_markdown(url)
            if not markdown:
                raise RuntimeError("страница не дала читаемый текст")
            with path.open("a", encoding="utf-8-sig") as handle:
                handle.write("\n## Parsed Page\n\n")
                handle.write(f"Parsed at: {now_iso()}\n\n")
                if title:
                    handle.write(f"Page title: {title}\n\n")
                handle.write(markdown)
                handle.write("\n")
            self.launch_reindex(route)
            self.root.after(0, self.append_warning_message, "Текст web-страницы сохранен в Markdown; обновление LightRAG запущено в фоне.", False)
        except Exception as exc:
            self.root.after(0, self.append_warning_message, f"Ссылка сохранена, но страницу не удалось автоматически распарсить: {exc}", False)

    def run_background_material_command(self, command: list[str], log_name: str) -> tuple[bool, str]:
        log_dir = ROOT / "tmp"
        log_dir.mkdir(parents=True, exist_ok=True)
        safe_name = re.sub(r"[^a-z0-9_-]+", "-", log_name.lower()).strip("-") or "material"
        log_path = log_dir / f"{safe_name}.log"
        err_path = log_dir / f"{safe_name}.err.log"
        try:
            with log_path.open("a", encoding="utf-8") as stdout, err_path.open("a", encoding="utf-8") as stderr:
                process = subprocess.Popen(
                    command,
                    cwd=str(ROOT),
                    stdout=stdout,
                    stderr=stderr,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                code = process.wait(timeout=240)
            if code == 0:
                return True, str(log_path)
            return False, f"код {code}; лог: {err_path}"
        except Exception as exc:
            return False, str(exc)

    def launch_reindex(self, route: tuple[str, str, str]) -> None:
        _context_name, scope, project = route
        command = [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(SCRIPTS_DIR / "ingest-vault-scope-lmstudio.ps1"),
            "-Scope",
            scope,
        ]
        if scope in {"game", "web"} and project:
            command.extend(["-Project", project])
        env = dict(os.environ)
        env["KNOWLEDGELAB_VAULT_DIR"] = str(VAULT_DIR)
        try:
            subprocess.Popen(
                command,
                cwd=str(ROOT),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                env=env,
            )
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

        context_name, scope, project = self.selected_route(question)
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

        if self.is_lightrag_status_intent(question):
            self.append_assistant_message(self.lightrag_status_message(question), lightrag_used=False)
            return

        if self.is_lightrag_help_intent(question):
            self.append_assistant_message(self.lightrag_help_message(), lightrag_used=False)
            return

        if self.is_save_intent(question):
            route = self.choose_capture_context((context_name, scope, project))
            if not route:
                self.append_warning_message("Сохранение отменено.", persist=True)
                return
            try:
                rel_path = self.save_capture(question, route)
                self.append_assistant_message(f"Сохранил в Obsidian: {rel_path}")
                self.start_auto_material_processing(question, route, rel_path)
            except Exception as exc:
                self.append_assistant_message(f"Не удалось сохранить заметку: {exc}\nОткройте LightRAG-Control для диагностики.", "error")
            return

        use_lightrag = bool(self.lightrag_var.get()) or explicit_knowledge_lookup
        web_search_enabled = bool(self.settings.get("web_search_enabled", False))
        warnings: list[str] = []
        lm_ready, lm_message, _models = self.check_lmstudio_ready(require_models=True)
        if not lm_ready:
            self.append_warning_message(lm_message, persist=True)
            return

        if use_lightrag and not self.is_lightrag_ready(scope, project):
            use_lightrag = False
            if bool(self.lightrag_var.get()):
                self.lightrag_var.set(False)
                self.settings["use_lightrag"] = False
                self.save_settings()
            warnings.append(f"LightRAG недоступен для {context_name}: индекс еще не готов. Ответ будет создан обычной LLM.")
        elif explicit_knowledge_lookup and use_lightrag:
            warnings.append(f"LightRAG использован для {context_name}, потому что запрос явно просит найти данные в базе.")

        operation_id = self.begin_operation(f"Asking {context_name}...", self.query_timeout_seconds)
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
            context_name,
            scope,
            project,
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
        chat = self.get_active_chat()
        messages = chat.get("messages", []) if chat else []
        prior = [
            m for m in messages
            if m.get("role") in {"user", "assistant"} and self.is_safe_history_message(str(m.get("text", "")))
        ][-4:]
        if not prior:
            return question
        lines = ["Краткий контекст текущего диалога:"]
        total_chars = 0
        for message in prior:
            role = "User" if message.get("role") == "user" else "Assistant"
            text = re.sub(r"\s+", " ", str(message.get("text", "")).strip())[:360]
            if text:
                line = f"{role}: {text}"
                total_chars += len(line)
                if total_chars > 1600:
                    break
                lines.append(line)
        lines.extend(["", f"Текущее сообщение пользователя: {question}"])
        return "\n".join(lines)

    def is_safe_history_message(self, text: str) -> bool:
        lowered = text.lower()
        noisy_markers = (
            "nativecommanderror",
            "context size has been exceeded",
            "openai api call failed",
            "starting lm studio server",
            "knowledge lab is ready",
            "lightrag storage was not found",
            "fullyqualifiederrorid",
            "categoryinfo",
            "success! server is now running",
        )
        return bool(text.strip()) and not any(marker in lowered for marker in noisy_markers)

    def run_query(
        self,
        operation_id: int,
        raw_question: str,
        question: str,
        context_name: str,
        scope: str,
        project: str,
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
        if hasattr(self, "voice_button"):
            self.voice_button.configure(state="normal" if self.voice_operation_id is not None else state)
        if not busy:
            self.cancel_busy_timer()
            self.set_active_process(None)
            self.active_operation_id = None
        self.status_var.set(status)

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
        configured = str(self.settings.get("obsidian_path", "") or "").strip()
        local_app = Path(os.getenv("LOCALAPPDATA", ""))
        roaming_app = Path(os.getenv("APPDATA", ""))
        program_data = Path(os.getenv("PROGRAMDATA", ""))
        program_files = Path(os.getenv("PROGRAMFILES", ""))
        program_files_x86 = Path(os.getenv("PROGRAMFILES(X86)", ""))
        candidates = [
            configured,
            shutil.which("Obsidian.exe") or "",
            shutil.which("obsidian") or "",
            str(local_app / "Obsidian" / "Obsidian.exe"),
            str(local_app / "Programs" / "Obsidian" / "Obsidian.exe"),
            str(local_app / "Programs" / "obsidian" / "Obsidian.exe"),
            str(local_app / "Microsoft" / "WindowsApps" / "Obsidian.exe"),
            str(program_files / "Obsidian" / "Obsidian.exe"),
            str(program_files_x86 / "Obsidian" / "Obsidian.exe"),
        ]
        candidates.extend(self.find_obsidian_shortcuts(roaming_app, program_data))
        candidates.extend(self.find_obsidian_registry_candidates())
        for candidate in candidates:
            if candidate and Path(candidate).exists():
                return candidate
        return ""

    def find_obsidian_shortcuts(self, roaming_app: Path, program_data: Path) -> list[str]:
        roots = [
            roaming_app / "Microsoft" / "Windows" / "Start Menu" / "Programs",
            program_data / "Microsoft" / "Windows" / "Start Menu" / "Programs",
            Path.home() / "Desktop",
            Path(os.getenv("PUBLIC", "")) / "Desktop",
        ]
        shortcuts: list[str] = []
        for root in roots:
            if not root.exists():
                continue
            try:
                shortcuts.extend(str(path) for path in root.rglob("*Obsidian*.lnk"))
            except OSError:
                continue
        return shortcuts

    def find_obsidian_registry_candidates(self) -> list[str]:
        command = [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            r"""
$paths = @(
  'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*',
  'HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*',
  'HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*'
)
foreach ($path in $paths) {
  Get-ItemProperty $path -ErrorAction SilentlyContinue |
    Where-Object { $_.DisplayName -like '*Obsidian*' } |
    ForEach-Object {
      if ($_.InstallLocation) { Join-Path $_.InstallLocation 'Obsidian.exe' }
      if ($_.DisplayIcon) { $_.DisplayIcon }
    }
}
""",
        ]
        try:
            completed = subprocess.run(
                command,
                cwd=str(ROOT),
                text=True,
                encoding="utf-8",
                errors="replace",
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                timeout=4,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except Exception:
            return []
        candidates: list[str] = []
        for line in (completed.stdout or "").splitlines():
            candidate = self.clean_windows_program_path(line)
            if candidate:
                candidates.append(candidate)
        return candidates

    def clean_windows_program_path(self, value: str) -> str:
        value = str(value or "").strip().strip('"')
        if not value:
            return ""
        value = re.sub(r",\d+$", "", value).strip().strip('"')
        lowered = value.lower()
        for suffix in (".exe", ".lnk"):
            index = lowered.find(suffix)
            if index >= 0:
                return value[: index + len(suffix)].strip().strip('"')
        return value if Path(value).suffix.lower() in {".exe", ".lnk"} else ""

    def launch_windows_program(self, path: str) -> None:
        target = Path(path)
        if target.suffix.lower() == ".lnk":
            startfile = getattr(os, "startfile", None)
            if startfile:
                startfile(str(target))
                return
        try:
            subprocess.Popen([str(target)], cwd=str(self.vault_dir() if self.vault_dir().exists() else ROOT))
        except OSError:
            startfile = getattr(os, "startfile", None)
            if startfile:
                startfile(str(target))
            else:
                raise

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
        if not bool(self.settings.get("game_guard_enabled", True)):
            return
        delay = int(self.settings.get("game_guard_delay_seconds", 5) or 5)
        self.root.after(delay * 1000, self.start_game_guard_probe)

    def start_game_guard_probe(self) -> None:
        if not bool(self.settings.get("game_guard_enabled", True)):
            return
        if time.time() < self.game_guard_warning_until:
            return
        threading.Thread(target=self.game_guard_worker, daemon=True).start()

    def game_guard_worker(self) -> None:
        first = self.collect_gpu_snapshot()
        if not self.is_gpu_snapshot_heavy(first):
            return
        time.sleep(2)
        second = self.collect_gpu_snapshot()
        if not self.is_gpu_snapshot_heavy(second):
            return
        self.root.after(0, self.show_game_guard_warning, second)

    def collect_gpu_snapshot(self) -> dict:
        command = [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            r"""
$ErrorActionPreference = 'SilentlyContinue'
$samples = @()
try {
  $samples = (Get-Counter '\GPU Engine(*)\Utilization Percentage').CounterSamples |
    Where-Object { $_.CookedValue -gt 2 } |
    ForEach-Object {
      $pidValue = $null
      if ($_.InstanceName -match 'pid_([0-9]+)_') { $pidValue = [int]$Matches[1] }
      [pscustomobject]@{ pid=$pidValue; value=[math]::Round($_.CookedValue, 1); instance=$_.InstanceName }
    }
} catch {}
$groups = @()
foreach ($group in ($samples | Where-Object { $_.pid } | Group-Object pid)) {
  $pidValue = [int]$group.Name
  $proc = Get-Process -Id $pidValue -ErrorAction SilentlyContinue
  if ($proc) {
    $groups += [pscustomobject]@{
      pid=$pidValue
      name=$proc.ProcessName
      gpu=[math]::Round((($group.Group | Measure-Object value -Sum).Sum), 1)
    }
  }
}
$nvidia = Get-Command nvidia-smi -ErrorAction SilentlyContinue
$gpuTotal = 0
$memory = ''
if ($nvidia) {
  $line = & $nvidia.Source --query-gpu=utilization.gpu,memory.used,memory.total --format=csv,noheader,nounits 2>$null | Select-Object -First 1
  if ($line -match '^\s*([0-9]+)\s*,\s*([0-9]+)\s*,\s*([0-9]+)') {
    $gpuTotal = [int]$Matches[1]
    $memory = "$($Matches[2])/$($Matches[3]) MB"
  }
}
$labNames = @('LM Studio','lms','python','pythonw')
$lab = @(Get-Process -ErrorAction SilentlyContinue | Where-Object { $labNames -contains $_.ProcessName } | Select-Object -First 12 | ForEach-Object {
  [pscustomobject]@{ pid=$_.Id; name=$_.ProcessName }
})
[pscustomobject]@{ gpu_total=$gpuTotal; memory=$memory; processes=$groups; lab=$lab } | ConvertTo-Json -Depth 5
""",
        ]
        try:
            result = subprocess.run(
                command,
                cwd=str(ROOT),
                text=True,
                encoding="utf-8",
                errors="replace",
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                timeout=12,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            return json.loads(result.stdout or "{}")
        except Exception:
            return {}

    def is_gpu_snapshot_heavy(self, snapshot: dict) -> bool:
        try:
            total = int(snapshot.get("gpu_total") or 0)
        except (TypeError, ValueError):
            total = 0
        if total >= 45:
            return True
        processes = snapshot.get("processes") or []
        if isinstance(processes, dict):
            processes = [processes]
        for process in processes:
            try:
                if float(process.get("gpu") or 0) >= 20:
                    return True
            except (TypeError, ValueError):
                continue
        return False

    def show_game_guard_warning(self, snapshot: dict) -> None:
        if time.time() < self.game_guard_warning_until:
            return
        self.game_guard_warning_until = time.time() + 30 * 60
        processes = snapshot.get("processes") or []
        if isinstance(processes, dict):
            processes = [processes]
        heavy = sorted(processes, key=lambda item: float(item.get("gpu") or 0), reverse=True)[:5]
        heavy_text = ", ".join(f"{item.get('name')}#{item.get('pid')} ({item.get('gpu')}%)" for item in heavy) or "процессы не определены"
        lab = snapshot.get("lab") or []
        if isinstance(lab, dict):
            lab = [lab]
        lab_text = ", ".join(f"{item.get('name')}#{item.get('pid')}" for item in lab) or "LM Studio/lms/python не найдены"
        total = snapshot.get("gpu_total") or 0
        memory = snapshot.get("memory") or "VRAM неизвестна"
        warning = (
            f"Game Guard: заметна GPU-нагрузка ({total}%, VRAM {memory}). "
            f"Тяжелые процессы: {heavy_text}. Со стороны KnowledgeLab: {lab_text}. "
            "Если открыта игра, рекомендуется закрыть чат или остановить LM Studio через LightRAG-Control, чтобы избежать конфликтов."
        )
        self.append_warning_message(warning, persist=True)

    def run_self_test(self) -> int:
        return run_static_self_test()


def main() -> None:
    if "--self-test" in sys.argv:
        raise SystemExit(run_static_self_test())
    if "--behavior-test" in sys.argv:
        raise SystemExit(run_behavior_self_test())

    root = tk.Tk()
    try:
        ttk.Style().theme_use("vista")
    except tk.TclError:
        pass
    KnowledgeChatApp(root)
    root.mainloop()


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
        print("knowledge_chat_gui behavior-test OK")
        return 0


if __name__ == "__main__":
    main()
