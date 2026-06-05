from __future__ import annotations

import datetime as dt
import json
import os
import re
import subprocess
import threading
import tkinter as tk
from pathlib import Path
from tkinter import colorchooser, messagebox, ttk


ROOT = Path(__file__).resolve().parents[1]
VAULT_DIR = ROOT / "Obsidian-Test-Vault"
SCRIPTS_DIR = ROOT / "scripts"
QUERY_SCRIPT = SCRIPTS_DIR / "query-vault-scope-lmstudio.ps1"
INGEST_SCRIPT = SCRIPTS_DIR / "ingest-vault-scope-lmstudio.ps1"
GAME_GUARD_SCRIPT = SCRIPTS_DIR / "game-guard.ps1"
CHAT_HISTORY_PATH = ROOT / "tmp" / "knowledge-chat-history.jsonl"
SETTINGS_PATH = ROOT / "tmp" / "knowledge-chat-settings.json"

CONTEXTS = {
    "General": ("general", ""),
    "Web Development": ("web", "web-development"),
    "My Game": ("game", "my-game"),
}

URL_RE = re.compile(r"https?://[^\s<>)\]]+", re.IGNORECASE)
YOUTUBE_RE = re.compile(r"https?://(?:www\.)?(?:youtube\.com/watch\?[^\s<>)\]]+|youtu\.be/[^\s<>)\]]+)", re.IGNORECASE)
TELEGRAM_RE = re.compile(r"https?://t\.me/[^\s<>)\]]+", re.IGNORECASE)
WARNING_PREFIX = "::knowledge-warning "

BUTTON_COLOR_PRESETS = {
    "Blue": "#3d5f88",
    "Green": "#4f746e",
    "Purple": "#6f608a",
    "Graphite": "#58616b",
}

DEFAULT_SETTINGS = {
    "send_on_enter": True,
    "use_lightrag": True,
    "button_color": BUTTON_COLOR_PRESETS["Blue"],
    "game_guard_enabled": True,
}

WEB_TERMS = {
    "web",
    "frontend",
    "front-end",
    "html",
    "css",
    "javascript",
    "typescript",
    "react",
    "next.js",
    "nextjs",
    "vue",
    "svelte",
    "vite",
    "tailwind",
    "dom",
    "browser",
    "layout",
    "responsive",
    "api",
    "fetch",
    "axios",
    "auth",
    "oauth",
    "jwt",
    "node",
    "npm",
    "верстка",
    "вёрстка",
    "фронтенд",
    "бекенд",
    "сайт",
    "страница",
}

GAME_TERMS = {
    "my-game",
    "my game",
    "моя игра",
    "моей игре",
    "мой проект игры",
    "геймплей",
    "game design",
    "игровой проект",
}

TOPICS = [
    ("React", {"react", "jsx", "tsx", "hooks", "component"}),
    ("TypeScript", {"typescript", " ts ", "types", "type-safe", "типизация"}),
    ("CSS Layout", {"css", "grid", "flex", "layout", "responsive", "media query", "верстка", "вёрстка"}),
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
        x = self.widget.winfo_rootx() + 16
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 10
        self.window = tk.Toplevel(self.widget)
        self.window.wm_overrideredirect(True)
        self.window.wm_geometry(f"+{x}+{y}")
        label = tk.Label(
            self.window,
            text=self.text,
            justify="left",
            background="#1f2933",
            foreground="#ffffff",
            relief="flat",
            borderwidth=0,
            padx=10,
            pady=7,
            font=("Segoe UI", 9),
            wraplength=320,
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
            x1 + radius,
            y1,
            x2 - radius,
            y1,
            x2,
            y1,
            x2,
            y1 + radius,
            x2,
            y2 - radius,
            x2,
            y2,
            x2 - radius,
            y2,
            x1 + radius,
            y2,
            x1,
            y2,
            x1,
            y2 - radius,
            x1,
            y1 + radius,
            x1,
            y1,
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


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9а-яё_-]+", "-", value, flags=re.IGNORECASE)
    value = re.sub(r"-{2,}", "-", value).strip("-")
    return value or "note"


def clean_filename(value: str) -> str:
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "-", value).strip()
    value = re.sub(r"\s+", " ", value)
    return value[:120].strip(" .-") or "note"


def yaml_quote(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def title_from_text(text: str, fallback: str) -> str:
    for line in text.splitlines():
        line = line.strip().strip("#").strip()
        if line and not URL_RE.fullmatch(line):
            return clean_filename(line)
    return fallback


def first_url(text: str) -> str:
    match = URL_RE.search(text)
    return match.group(0).rstrip(".,;)]}>\"'") if match else ""


def first_youtube_url(text: str) -> str:
    match = YOUTUBE_RE.search(text)
    return match.group(0).rstrip(".,;)]}>\"'") if match else ""


def first_telegram_url(text: str) -> str:
    match = TELEGRAM_RE.search(text)
    return match.group(0).rstrip(".,;)]}>\"'") if match else ""


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


def capture_destination(scope: str, topic: str, kind: str) -> Path:
    if scope == "web":
        base = VAULT_DIR / "20 Projects" / "Web Development"
        if kind == "youtube_link":
            return base / "Sources" / "YouTube" / "Links"
        if kind == "telegram_source":
            return base / "Sources" / "Telegram"
        if kind == "article":
            return base / "Sources" / "Articles"
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
        return base / "Captures"

    if kind == "youtube_link":
        return VAULT_DIR / "30 Sources" / "YouTube" / "Links"
    if kind == "telegram_source":
        return VAULT_DIR / "30 Sources" / "Telegram"
    if kind == "article":
        return VAULT_DIR / "30 Sources" / "Articles"
    return VAULT_DIR / "00 Inbox"


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


def render_capture_markdown(text: str, context_name: str, scope: str, project: str, topic: str, kind: str) -> str:
    now = dt.datetime.now().replace(microsecond=0).isoformat()
    url = first_youtube_url(text) or first_telegram_url(text) or first_url(text)
    source = "manual"
    note_type = kind
    tags = ["captured/chat"]
    if project:
        tags.append(f"project/{project}")
    if topic:
        tags.append(f"topic/{slugify(topic)}")
    if kind == "youtube_link":
        source = "youtube_link"
        tags.append("source/youtube")
    elif kind == "telegram_source":
        note_type = "telegram_source"
        source = "telegram"
        tags.append("source/telegram")
    elif kind == "article":
        source = "web"
        tags.append("source/article")
    elif kind == "solution":
        tags.append("solution")

    frontmatter = [
        "---",
        f"type: {note_type}",
        f"source: {source}",
        f"source_url: {yaml_quote(url)}",
        f"scope: {scope}",
        f"project: {yaml_quote(project)}",
        f"topic: {yaml_quote(topic)}",
        f"captured_at: {yaml_quote(now)}",
        f"tags: [{', '.join(tags)}]",
        "---",
        "",
    ]
    title = title_from_text(text, f"{context_name} capture")
    body = [f"# {title}", ""]
    if url:
        body.extend([f"URL: {url}", ""])
    body.extend(["## Capture", "", text.strip(), ""])
    return "\n".join(frontmatter + body)


class KnowledgeChatApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("LightRAG Knowledge Chat")
        self.root.geometry("980x720")
        self.root.minsize(820, 560)
        self.root.configure(bg="#f4f6f8")

        self.settings = self.load_settings()
        self.context_var = tk.StringVar(value="Auto")
        self.lightrag_var = tk.BooleanVar(value=bool(self.settings["use_lightrag"]))
        self.status_var = tk.StringVar(value="Ready")
        self.settings_window: tk.Toplevel | None = None
        self.settings_status_var = tk.StringVar(value="")
        self.enter_send_var = tk.BooleanVar(value=bool(self.settings["send_on_enter"]))
        self.game_guard_var = tk.BooleanVar(value=bool(self.settings["game_guard_enabled"]))
        self.button_color_var = tk.StringVar(value=str(self.settings["button_color"]))
        self.tooltips: list[ToolTip] = []
        self.intro_visible = False
        self.input_history: list[str] = []
        self.input_history_index = 0
        self.active_process: subprocess.Popen | None = None
        self.process_lock = threading.Lock()
        self.busy = False
        self.operation_id = 0
        self.active_operation_id: int | None = None
        self.busy_timer_id: str | None = None
        self.query_timeout_seconds = int(os.getenv("LMSTUDIO_GUI_QUERY_TIMEOUT_SECONDS", "600"))
        self.reindex_timeout_seconds = int(os.getenv("LMSTUDIO_GUI_REINDEX_TIMEOUT_SECONDS", "1800"))

        self.configure_styles()
        self.build_ui()
        self.load_input_history()
        self.show_intro()
        self.apply_settings_to_ui()
        if self.settings["game_guard_enabled"]:
            self.configure_game_guard_background(True, silent=True)

    def configure_styles(self) -> None:
        style = ttk.Style()
        style.configure("App.TFrame", background="#f4f6f8")
        style.configure("Top.TFrame", background="#eef2f5")
        style.configure("Composer.TFrame", background="#f4f6f8")
        style.configure("Status.TLabel", background="#eef2f5", foreground="#53616f", font=("Segoe UI", 10))
        style.configure("Header.TLabel", background="#eef2f5", foreground="#1f2933", font=("Segoe UI Semibold", 11))
        style.configure("SettingsHeader.TLabel", background="#f4f6f8", foreground="#1f2933", font=("Segoe UI Semibold", 10))
        style.configure("SettingsStatus.TLabel", background="#f4f6f8", foreground="#53616f", font=("Segoe UI", 9))
        style.configure("Context.TLabel", background="#eef2f5", foreground="#384655", font=("Segoe UI", 10))
        style.configure("Toolbar.TCheckbutton", background="#eef2f5", foreground="#384655", font=("Segoe UI", 10))

    def load_settings(self) -> dict[str, object]:
        settings = dict(DEFAULT_SETTINGS)
        try:
            if SETTINGS_PATH.exists():
                loaded = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    settings.update(loaded)
        except (OSError, json.JSONDecodeError):
            pass

        settings["send_on_enter"] = bool(settings.get("send_on_enter", DEFAULT_SETTINGS["send_on_enter"]))
        settings["use_lightrag"] = bool(settings.get("use_lightrag", DEFAULT_SETTINGS["use_lightrag"]))
        settings["game_guard_enabled"] = bool(settings.get("game_guard_enabled", DEFAULT_SETTINGS["game_guard_enabled"]))
        settings["button_color"] = valid_hex_color(
            str(settings.get("button_color", DEFAULT_SETTINGS["button_color"])),
            str(DEFAULT_SETTINGS["button_color"]),
        )
        return settings

    def save_settings(self) -> None:
        self.settings["send_on_enter"] = bool(self.settings["send_on_enter"])
        self.settings["use_lightrag"] = bool(self.settings["use_lightrag"])
        self.settings["game_guard_enabled"] = bool(self.settings["game_guard_enabled"])
        self.settings["button_color"] = valid_hex_color(
            str(self.settings["button_color"]),
            str(DEFAULT_SETTINGS["button_color"]),
        )
        try:
            SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
            SETTINGS_PATH.write_text(
                json.dumps(self.settings, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        except OSError:
            pass

    def build_ui(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        toolbar = ttk.Frame(self.root, padding=(14, 10), style="Top.TFrame")
        toolbar.grid(row=0, column=0, sticky="ew")
        toolbar.columnconfigure(5, weight=1)

        ttk.Label(toolbar, text="LightRAG Chat", style="Header.TLabel").grid(row=0, column=0, padx=(0, 18))
        ttk.Label(toolbar, text="Контекст", style="Context.TLabel").grid(row=0, column=1, padx=(0, 6))
        self.context = ttk.Combobox(
            toolbar,
            textvariable=self.context_var,
            values=["Auto", "General", "Web Development", "My Game"],
            state="readonly",
            width=20,
        )
        self.context.grid(row=0, column=2, padx=(0, 10))
        self.add_tooltip(
            self.context,
            "Auto сам выбирает базу знаний по тексту. Можно вручную выбрать General, Web Development или My Game.",
        )

        self.lightrag_toggle = ttk.Checkbutton(
            toolbar,
            text="LightRAG",
            variable=self.lightrag_var,
            command=self.on_lightrag_toggle,
            style="Toolbar.TCheckbutton",
        )
        self.lightrag_toggle.grid(row=0, column=3, padx=(0, 14))
        self.add_tooltip(
            self.lightrag_toggle,
            "On: answer uses LightRAG retrieval. Off: answer comes directly from LM Studio and shows a gray warning.",
        )

        self.settings_button = ttk.Button(toolbar, text="Настройки", command=self.open_settings)
        self.settings_button.grid(row=0, column=4, padx=(0, 14))
        self.add_tooltip(self.settings_button, "Открыть настройки Enter, LightRAG, цвета кнопок и Game Guard.")

        ttk.Label(toolbar, textvariable=self.status_var, style="Status.TLabel").grid(row=0, column=6, sticky="e")

        main = ttk.Frame(self.root, padding=(14, 12, 14, 14), style="App.TFrame")
        main.grid(row=1, column=0, sticky="nsew")
        main.columnconfigure(0, weight=1)
        main.rowconfigure(0, weight=1)

        chat_shell = tk.Frame(main, bg="#cfd4da", padx=1, pady=1)
        chat_shell.grid(row=0, column=0, sticky="nsew")
        chat_shell.columnconfigure(0, weight=1)
        chat_shell.rowconfigure(0, weight=1)

        chat_inner = tk.Frame(chat_shell, bg="#ffffff")
        chat_inner.grid(row=0, column=0, sticky="nsew")
        chat_inner.columnconfigure(0, weight=1)
        chat_inner.rowconfigure(0, weight=1)

        self.chat = tk.Text(
            chat_inner,
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
        scroll = ttk.Scrollbar(chat_inner, orient="vertical", command=self.chat.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.chat.configure(yscrollcommand=scroll.set)
        self.chat.tag_configure("user", foreground="#174ea6")
        self.chat.tag_configure("assistant", foreground="#202124")
        self.chat.tag_configure("system", foreground="#5f6368")
        self.chat.tag_configure("warning", foreground="#7a838c", font=("Segoe UI", 9))
        self.chat.tag_configure("error", foreground="#b3261e")

        input_frame = ttk.Frame(main, style="Composer.TFrame")
        input_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        input_frame.columnconfigure(0, weight=1)
        input_shell = tk.Frame(input_frame, bg="#cfd4da", padx=1, pady=1)
        input_shell.grid(row=0, column=0, sticky="ew")
        input_shell.columnconfigure(0, weight=1)

        self.input = tk.Text(
            input_shell,
            height=5,
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
        self.input.bind("<Control-Return>", self.on_ctrl_return)
        self.input.bind("<Shift-Return>", self.on_shift_return)
        self.input.bind("<Return>", self.on_return)
        self.input.bind("<Alt-Up>", lambda _event: self.navigate_input_history(-1))
        self.input.bind("<Alt-Down>", lambda _event: self.navigate_input_history(1))

        button_bar = tk.Frame(input_frame, bg="#f4f6f8")
        button_bar.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        for column in range(6):
            button_bar.columnconfigure(column, weight=1, uniform="actions")

        self.send_button = self.create_action_button(
            button_bar,
            "Отправить",
            self.on_send,
            bg="#3d5f88",
            active_bg="#344f70",
            fg="#ffffff",
        )
        self.send_button.grid(row=0, column=0, sticky="ew", padx=(0, 7), ipady=7)
        self.add_tooltip(self.send_button, "Отправить вопрос в выбранный контекст LightRAG + LM Studio.")
        self.save_button = self.create_action_button(
            button_bar,
            "Добавить в Obsidian",
            self.on_save,
            bg="#4f746e",
            active_bg="#415f5a",
            fg="#ffffff",
        )
        self.save_button.grid(row=0, column=1, sticky="ew", padx=7, ipady=7)
        self.add_tooltip(
            self.save_button,
            "Создать Markdown-заметку из текущего текста/ссылки. YouTube, Telegram и web-ссылки раскладываются по нужным папкам Obsidian.",
        )
        self.cancel_button = self.create_action_button(
            button_bar,
            "Отмена",
            self.cancel_active_operation,
            bg="#dfe6ed",
            active_bg="#d2dbe4",
            fg="#1f2933",
        )
        self.cancel_button.grid(row=0, column=2, sticky="ew", padx=7, ipady=7)
        self.cancel_button.configure(state="disabled")
        self.add_tooltip(self.cancel_button, "Остановить зависший запрос и вернуть кнопки в рабочее состояние.")
        self.open_button = self.create_action_button(
            button_bar,
            "Открыть Obsidian",
            self.open_vault,
            bg="#dfe6ed",
            active_bg="#d2dbe4",
            fg="#1f2933",
        )
        self.open_button.grid(row=0, column=3, sticky="ew", padx=7, ipady=7)
        self.add_tooltip(
            self.open_button,
            "Открыть папку Obsidian vault, чтобы вручную посмотреть, поправить или проверить сохраненные заметки и источники.",
        )
        self.history_button = self.create_action_button(
            button_bar,
            "История",
            self.show_history,
            bg="#dfe6ed",
            active_bg="#d2dbe4",
            fg="#1f2933",
        )
        self.history_button.grid(row=0, column=4, sticky="ew", padx=7, ipady=7)
        self.add_tooltip(self.history_button, "Показать последние сохраненные сообщения этого чата.")
        self.clear_button = self.create_action_button(
            button_bar,
            "Очистить",
            self.clear_chat,
            bg="#dfe6ed",
            active_bg="#d2dbe4",
            fg="#1f2933",
        )
        self.clear_button.grid(row=0, column=5, sticky="ew", padx=(7, 0), ipady=7)
        self.add_tooltip(self.clear_button, "Очистить историю сообщений в этом окне. Заметки в Obsidian не удаляются.")

    def create_action_button(
        self,
        parent: tk.Widget,
        text: str,
        command,
        *,
        bg: str,
        active_bg: str,
        fg: str,
    ) -> RoundedButton:
        return RoundedButton(
            parent,
            text=text,
            command=command,
            bg=bg,
            active_bg=active_bg,
            fg=fg,
        )

    def add_tooltip(self, widget: tk.Widget, text: str) -> None:
        self.tooltips.append(ToolTip(widget, text))

    def apply_settings_to_ui(self) -> None:
        self.enter_send_var.set(bool(self.settings["send_on_enter"]))
        self.lightrag_var.set(bool(self.settings["use_lightrag"]))
        self.game_guard_var.set(bool(self.settings["game_guard_enabled"]))
        self.button_color_var.set(str(self.settings["button_color"]))
        self.update_button_colors()
        self.on_lightrag_toggle(save=False)

    def update_button_colors(self) -> None:
        color = valid_hex_color(str(self.settings["button_color"]), str(DEFAULT_SETTINGS["button_color"]))
        fg = readable_text_color(color)
        active_bg = adjust_hex_color(color, 0.86)
        for button in (self.send_button, self.save_button):
            button.set_colors(bg=color, active_bg=active_bg, fg=fg)

    def open_settings(self) -> None:
        if self.settings_window and self.settings_window.winfo_exists():
            self.settings_window.lift()
            self.settings_window.focus_force()
            return

        self.enter_send_var.set(bool(self.settings["send_on_enter"]))
        self.lightrag_var.set(bool(self.settings["use_lightrag"]))
        self.game_guard_var.set(bool(self.settings["game_guard_enabled"]))
        self.button_color_var.set(str(self.settings["button_color"]))
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

        ttk.Label(frame, text="Отправка и база знаний", style="SettingsHeader.TLabel").grid(
            row=0,
            column=0,
            columnspan=3,
            sticky="w",
            pady=(0, 10),
        )
        ttk.Checkbutton(
            frame,
            text="Enter отправляет сообщение",
            variable=self.enter_send_var,
        ).grid(row=1, column=0, columnspan=3, sticky="w", pady=3)
        ttk.Checkbutton(
            frame,
            text="Использовать LightRAG",
            variable=self.lightrag_var,
        ).grid(row=2, column=0, columnspan=3, sticky="w", pady=3)
        ttk.Checkbutton(
            frame,
            text="Game Guard работает в фоне",
            variable=self.game_guard_var,
        ).grid(row=3, column=0, columnspan=3, sticky="w", pady=3)

        ttk.Separator(frame, orient="horizontal").grid(row=4, column=0, columnspan=3, sticky="ew", pady=(14, 12))
        ttk.Label(frame, text="Цвет основных кнопок", style="SettingsHeader.TLabel").grid(
            row=5,
            column=0,
            columnspan=3,
            sticky="w",
            pady=(0, 10),
        )

        preset_var = tk.StringVar(value=self.color_preset_name(self.button_color_var.get()))
        presets = list(BUTTON_COLOR_PRESETS.keys())
        preset = ttk.Combobox(frame, textvariable=preset_var, values=presets, state="readonly", width=18)
        preset.grid(row=6, column=0, sticky="w", padx=(0, 10))
        preset.bind("<<ComboboxSelected>>", lambda _event: self.select_color_preset(preset_var.get()))

        self.settings_color_preview = tk.Label(
            frame,
            width=6,
            height=1,
            background=self.button_color_var.get(),
            relief="solid",
            borderwidth=1,
        )
        self.settings_color_preview.grid(row=6, column=1, sticky="w", padx=(0, 10))
        ttk.Button(frame, text="Выбрать...", command=self.choose_button_color).grid(row=6, column=2, sticky="e")

        ttk.Label(frame, textvariable=self.settings_status_var, style="SettingsStatus.TLabel").grid(
            row=7,
            column=0,
            columnspan=3,
            sticky="w",
            pady=(14, 0),
        )

        buttons = ttk.Frame(frame, style="App.TFrame")
        buttons.grid(row=8, column=0, columnspan=3, sticky="e", pady=(16, 0))
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

    def color_preset_name(self, color: str) -> str:
        color = valid_hex_color(color, str(DEFAULT_SETTINGS["button_color"]))
        for name, value in BUTTON_COLOR_PRESETS.items():
            if value.lower() == color.lower():
                return name
        return ""

    def select_color_preset(self, preset_name: str) -> None:
        color = BUTTON_COLOR_PRESETS.get(preset_name)
        if not color:
            return
        self.button_color_var.set(color)
        self.update_color_preview(color)

    def update_color_preview(self, color: str) -> None:
        if hasattr(self, "settings_color_preview") and self.settings_color_preview:
            self.settings_color_preview.configure(background=valid_hex_color(color, str(DEFAULT_SETTINGS["button_color"])))

    def choose_button_color(self) -> None:
        _rgb, color = colorchooser.askcolor(
            color=valid_hex_color(self.button_color_var.get(), str(DEFAULT_SETTINGS["button_color"])),
            parent=self.settings_window or self.root,
            title="Цвет основных кнопок",
        )
        if not color:
            return
        self.button_color_var.set(valid_hex_color(color, str(DEFAULT_SETTINGS["button_color"])))
        self.update_color_preview(self.button_color_var.get())

    def save_settings_from_window(self) -> None:
        old_game_guard = bool(self.settings["game_guard_enabled"])
        self.settings["send_on_enter"] = bool(self.enter_send_var.get())
        self.settings["use_lightrag"] = bool(self.lightrag_var.get())
        self.settings["button_color"] = valid_hex_color(self.button_color_var.get(), str(DEFAULT_SETTINGS["button_color"]))
        self.settings["game_guard_enabled"] = bool(self.game_guard_var.get())
        self.save_settings()
        self.apply_settings_to_ui()

        if old_game_guard != bool(self.settings["game_guard_enabled"]):
            self.configure_game_guard_background(bool(self.settings["game_guard_enabled"]), silent=False)
        else:
            self.status_var.set("Settings saved")
        self.close_settings()

    def configure_game_guard_background(self, enabled: bool, silent: bool = False) -> None:
        if not GAME_GUARD_SCRIPT.exists():
            if not silent:
                self.status_var.set("Game Guard script missing")
            return

        command = [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(GAME_GUARD_SCRIPT),
        ]
        if enabled:
            command.extend(["-InstallStartup", "-StartNow"])
        else:
            command.extend(["-UninstallStartup", "-StopNow"])

        def worker() -> None:
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            try:
                result = subprocess.run(
                    command,
                    cwd=str(ROOT),
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=30,
                    creationflags=creationflags,
                )
                output = "\n".join(
                    part for part in ((result.stdout or "").strip(), (result.stderr or "").strip()) if part
                )
                self.root.after(0, self.finish_game_guard_config, enabled, result.returncode, output, silent)
            except Exception as exc:
                self.root.after(0, self.finish_game_guard_config, enabled, 1, str(exc), silent)

        threading.Thread(target=worker, daemon=True).start()

    def finish_game_guard_config(self, enabled: bool, returncode: int, output: str, silent: bool) -> None:
        if returncode == 0:
            if not silent:
                self.status_var.set("Game Guard on" if enabled else "Game Guard off")
            return
        message = f"Game Guard не удалось {'включить' if enabled else 'выключить'}."
        if output:
            message = f"{message} {output.splitlines()[-1]}"
        if not silent:
            self.append(f"{message}\n", "warning")
            self.status_var.set("Game Guard warning")

    def set_chat_text(self, text: str, tag: str = "system") -> None:
        self.chat.configure(state="normal")
        self.chat.delete("1.0", "end")
        self.chat.insert("end", text, tag)
        self.chat.configure(state="disabled")
        self.chat.see("end")

    def show_intro(self) -> None:
        self.intro_visible = True
        intro = (
            "System: Здесь можно задавать вопросы по базе знаний и добавлять новые заметки/ссылки.\n"
            "Контекст выбирается автоматически. Enter отправляет сообщение, Shift+Enter добавляет новую строку; это можно изменить в настройках.\n"
            "LightRAG включен по умолчанию; если индекс еще не готов, он соберется в фоне, а ответ все равно появится.\n"
            "Obsidian открывает папку заметок для ручного просмотра и правки.\n"
        )
        self.set_chat_text(intro, "system")

    def remove_intro(self) -> None:
        if not self.intro_visible:
            return
        self.chat.configure(state="normal")
        self.chat.delete("1.0", "end")
        self.chat.configure(state="disabled")
        self.intro_visible = False

    def append(self, text: str, tag: str = "assistant") -> None:
        self.remove_intro()
        self.chat.configure(state="normal")
        self.chat.insert("end", text, tag)
        self.chat.insert("end", "\n")
        self.chat.configure(state="disabled")
        self.chat.see("end")

    def append_system(self, text: str) -> None:
        self.append(f"System: {text}\n", "system")

    def split_knowledge_warnings(self, output: str) -> tuple[str, list[str]]:
        warnings: list[str] = []
        display_lines: list[str] = []
        for line in output.splitlines():
            if line.startswith(WARNING_PREFIX):
                warning = line[len(WARNING_PREFIX) :].strip()
                if warning:
                    warnings.append(warning)
            else:
                display_lines.append(line)
        return "\n".join(display_lines).strip(), warnings

    def input_text(self) -> str:
        return self.input.get("1.0", "end").strip()

    def clear_input(self) -> None:
        self.input.delete("1.0", "end")

    def replace_input(self, text: str) -> None:
        self.clear_input()
        self.input.insert("1.0", text)

    def load_history_entries(self, limit: int = 80) -> list[dict]:
        if not CHAT_HISTORY_PATH.exists():
            return []
        entries: list[dict] = []
        try:
            for line in CHAT_HISTORY_PATH.read_text(encoding="utf-8").splitlines()[-limit:]:
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(entry, dict):
                    entries.append(entry)
        except OSError:
            return []
        return entries

    def load_input_history(self) -> None:
        questions: list[str] = []
        for entry in self.load_history_entries(limit=200):
            if entry.get("role") == "user":
                text = str(entry.get("text", "")).strip()
                if text and (not questions or questions[-1] != text):
                    questions.append(text)
        self.input_history = questions[-50:]
        self.input_history_index = len(self.input_history)

    def remember_input(self, question: str) -> None:
        if self.input_history and self.input_history[-1] == question:
            self.input_history_index = len(self.input_history)
            return
        self.input_history.append(question)
        self.input_history = self.input_history[-50:]
        self.input_history_index = len(self.input_history)

    def navigate_input_history(self, direction: int) -> str:
        if not self.input_history:
            return "break"
        self.input_history_index = max(0, min(len(self.input_history), self.input_history_index + direction))
        if self.input_history_index == len(self.input_history):
            self.replace_input("")
        else:
            self.replace_input(self.input_history[self.input_history_index])
        return "break"

    def record_history(
        self,
        role: str,
        context_name: str,
        text: str,
        warnings: list[str] | None = None,
    ) -> None:
        entry = {
            "ts": dt.datetime.now().isoformat(timespec="seconds"),
            "role": role,
            "context": context_name,
            "lightrag": bool(self.lightrag_var.get()),
            "text": text,
        }
        if warnings:
            entry["warnings"] = warnings
        try:
            CHAT_HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
            with CHAT_HISTORY_PATH.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except OSError:
            pass

    def show_history(self) -> None:
        entries = self.load_history_entries(limit=40)
        if not entries:
            self.set_chat_text("System: История пока пустая.\n", "system")
            self.intro_visible = False
            return

        self.intro_visible = False
        self.chat.configure(state="normal")
        self.chat.delete("1.0", "end")
        self.chat.insert("end", "System: Последние сообщения из локальной истории.\n\n", "system")
        for entry in entries:
            role = str(entry.get("role", "assistant"))
            context_name = str(entry.get("context", ""))
            text = str(entry.get("text", "")).strip()
            ts = str(entry.get("ts", ""))[:16].replace("T", " ")
            warnings = entry.get("warnings") if isinstance(entry.get("warnings"), list) else []
            if not text and not warnings:
                continue
            tag = "user" if role == "user" else "assistant"
            if role in {"warning", "error"}:
                tag = role
            header = role.capitalize()
            if context_name:
                header = f"{header} [{context_name}]"
            if ts:
                header = f"{header} · {ts}"
            for warning in warnings:
                self.chat.insert("end", f"{warning}\n", "warning")
            if text:
                self.chat.insert("end", f"{header}:\n{text}\n\n", tag)
        self.chat.configure(state="disabled")
        self.chat.see("end")

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
        self.append(
            "Операция заняла слишком много времени и была остановлена. Кнопки снова активны; можно отправить сообщение еще раз.\n",
            "warning",
        )
        self.set_busy(False, "Ready")

    def cancel_active_operation(self) -> None:
        if not self.busy:
            return
        stopped = self.terminate_active_process()
        if stopped:
            self.append("Операция отменена. Кнопки снова активны.\n", "warning")
        else:
            self.append("Активный процесс не найден, но интерфейс разблокирован.\n", "warning")
        self.active_operation_id = None
        self.set_busy(False, "Ready")

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

    def set_busy(self, busy: bool, status: str) -> None:
        self.busy = busy
        state = "disabled" if busy else "normal"
        self.send_button.configure(state=state)
        self.save_button.configure(state=state)
        self.cancel_button.configure(state="normal" if busy else "disabled")
        self.history_button.configure(state=state)
        self.open_button.configure(state=state)
        self.clear_button.configure(state=state)
        if not busy:
            self.cancel_busy_timer()
            self.set_active_process(None)
            self.active_operation_id = None
        self.status_var.set(status)

    def selected_route(self, text: str) -> tuple[str, str, str]:
        return route_context(text, self.context_var.get())

    def on_lightrag_toggle(self, save: bool = True) -> None:
        if save:
            self.settings["use_lightrag"] = bool(self.lightrag_var.get())
            self.save_settings()
        self.status_var.set("LightRAG on" if self.lightrag_var.get() else "LightRAG off")
        if self.settings_window and self.settings_window.winfo_exists():
            self.lightrag_var.set(bool(self.settings["use_lightrag"]))

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
        route_note = f"Auto -> {context_name}" if self.context_var.get() == "Auto" else context_name
        lightrag_enabled = bool(self.lightrag_var.get())
        if not lightrag_enabled:
            route_note = f"{route_note}, LightRAG off"
        self.append(f"You [{route_note}]:\n{question}\n", "user")
        self.record_history("user", context_name, question)
        self.remember_input(question)
        self.clear_input()
        operation_id = self.begin_operation(f"Asking {context_name}...", self.query_timeout_seconds)

        thread = threading.Thread(
            target=self.run_query,
            args=(operation_id, question, context_name, scope, project, lightrag_enabled),
            daemon=True,
        )
        thread.start()

    def run_query(
        self,
        operation_id: int,
        question: str,
        context_name: str,
        scope: str,
        project: str,
        lightrag_enabled: bool,
    ) -> None:
        command = [
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
            command.extend(["-Project", project])
        command.append(question)

        env = dict(os.environ)
        env["LMSTUDIO_GUI_OUTPUT"] = "1"
        env["LMSTUDIO_USE_LIGHTRAG"] = "1" if lightrag_enabled else "0"
        try:
            returncode, output = self.run_command(command, self.query_timeout_seconds, env=env)
            output, warnings = self.split_knowledge_warnings(output)
            if not output:
                output = f"Command exited with code {returncode} and no output."
            tag = "assistant" if returncode == 0 else "error"
        except TimeoutError as exc:
            output = f"{exc}\nЗапрос остановлен, чтобы чат не зависал. Попробуйте еще раз или откройте LightRAG-Control."
            tag = "warning"
            warnings = []
        except Exception as exc:
            output = f"ERROR: {exc}"
            tag = "error"
            warnings = []

        self.root.after(0, self.finish_query, operation_id, context_name, output, tag, warnings)

    def finish_query(
        self,
        operation_id: int,
        context_name: str,
        output: str,
        tag: str,
        warnings: list[str] | None = None,
    ) -> None:
        if not self.is_active_operation(operation_id):
            return
        for warning in warnings or []:
            self.append(f"{warning}\n", "warning")
        self.append(f"Assistant [{context_name}]:\n{output}\n", tag)
        self.record_history("assistant" if tag == "assistant" else "error", context_name, output, warnings)
        self.set_busy(False, "Ready")

    def on_save(self) -> None:
        text = self.input_text()
        if not text:
            messagebox.showinfo("Save to Obsidian", "Введите ссылку или заметку в поле сообщения.")
            return

        context_name, scope, project = self.selected_route(text)
        topic = infer_topic(text, scope)
        kind = infer_kind(text)
        destination = capture_destination(scope, topic, kind)
        destination.mkdir(parents=True, exist_ok=True)

        title = title_from_text(text, f"{context_name} capture")
        if kind in {"article", "youtube_link"} and topic:
            title = f"{topic} - {title}"
        path = unique_path(destination / f"{clean_filename(title)}.md")
        markdown = render_capture_markdown(text, context_name, scope, project, topic, kind)
        path.write_text(markdown, encoding="utf-8-sig")

        rel = path.relative_to(VAULT_DIR).as_posix()
        self.append_system(f"Saved to Obsidian: {rel}")

    def on_reindex(self) -> None:
        text = self.input_text()
        context_name, scope, project = self.selected_route(text)
        if scope == "all":
            project = ""

        if not messagebox.askyesno(
            "Reindex Context",
            f"Запустить переиндексацию для {context_name}? Это может занять время.",
        ):
            return

        operation_id = self.begin_operation(f"Reindexing {context_name}...", self.reindex_timeout_seconds)
        thread = threading.Thread(target=self.run_reindex, args=(operation_id, context_name, scope, project), daemon=True)
        thread.start()

    def run_reindex(self, operation_id: int, context_name: str, scope: str, project: str) -> None:
        command = [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(INGEST_SCRIPT),
            "-Scope",
            scope,
        ]
        if project:
            command.extend(["-Project", project])

        try:
            returncode, output = self.run_command(command, self.reindex_timeout_seconds)
            tag = "assistant" if returncode == 0 else "error"
        except TimeoutError as exc:
            output = f"{exc}\nИндексация остановлена, чтобы чат не зависал. Ее можно повторить из LightRAG-Control."
            tag = "warning"
        except Exception as exc:
            output = f"ERROR: {exc}"
            tag = "error"

        self.root.after(0, self.finish_reindex, operation_id, context_name, output, tag)

    def finish_reindex(self, operation_id: int, context_name: str, output: str, tag: str) -> None:
        if not self.is_active_operation(operation_id):
            return
        self.append(f"Reindex [{context_name}]:\n{output}\n", tag)
        self.set_busy(False, "Ready")

    def open_vault(self) -> None:
        subprocess.Popen(["explorer", str(VAULT_DIR)])

    def clear_chat(self) -> None:
        self.chat.configure(state="normal")
        self.chat.delete("1.0", "end")
        self.chat.configure(state="disabled")
        self.show_intro()


def main() -> None:
    root = tk.Tk()
    try:
        ttk.Style().theme_use("vista")
    except tk.TclError:
        pass
    KnowledgeChatApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
