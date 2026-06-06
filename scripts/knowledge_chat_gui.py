from __future__ import annotations

import datetime as dt
import json
import os
import re
import subprocess
import sys
import threading
import time
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import colorchooser, filedialog, messagebox, simpledialog, ttk


ROOT = Path(__file__).resolve().parents[1]
VAULT_DIR = ROOT / "Obsidian-Test-Vault"
SCRIPTS_DIR = ROOT / "scripts"
QUERY_SCRIPT = SCRIPTS_DIR / "query-vault-scope-lmstudio.ps1"
GAME_GUARD_SCRIPT = SCRIPTS_DIR / "game-guard.ps1"
CONTROL_SCRIPT = ROOT / "LightRAG-Control.ps1"
LEGACY_HISTORY_PATH = ROOT / "tmp" / "knowledge-chat-history.jsonl"
CHAT_STORE_PATH = ROOT / "tmp" / "knowledge-chat-sessions.json"
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
    "use_lightrag": False,
    "button_color": BUTTON_COLOR_PRESETS["Blue"],
    "game_guard_enabled": True,
    "game_guard_delay_seconds": 5,
    "obsidian_path": "",
    "default_llm_mode_applied": True,
}

WEB_TERMS = {
    "web", "frontend", "front-end", "html", "css", "javascript", "typescript",
    "react", "next.js", "nextjs", "vue", "svelte", "vite", "tailwind", "dom",
    "browser", "layout", "responsive", "api", "fetch", "axios", "auth", "oauth",
    "jwt", "node", "npm", "верстка", "вёрстка", "фронтенд", "бекенд", "сайт",
    "страница", "popup", "modal", "css",
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
        self.context_var = tk.StringVar(value="Auto")
        self.lightrag_var = tk.BooleanVar(value=bool(self.settings["use_lightrag"]))
        self.status_var = tk.StringVar(value="Ready")
        self.enter_send_var = tk.BooleanVar(value=bool(self.settings["send_on_enter"]))
        self.game_guard_var = tk.BooleanVar(value=bool(self.settings["game_guard_enabled"]))
        self.button_color_var = tk.StringVar(value=str(self.settings["button_color"]))
        self.obsidian_path_var = tk.StringVar(value=str(self.settings.get("obsidian_path", "")))

        self.settings_window: tk.Toplevel | None = None
        self.settings_status_var = tk.StringVar(value="")
        self.tooltips: list[ToolTip] = []
        self.chat_widgets: list[tk.Widget] = []
        self.input_history: list[str] = []
        self.input_history_index = 0
        self.active_process: subprocess.Popen | None = None
        self.process_lock = threading.Lock()
        self.busy = False
        self.operation_id = 0
        self.active_operation_id: int | None = None
        self.busy_timer_id: str | None = None
        self.game_guard_warning_until = 0.0
        self.query_timeout_seconds = int(os.getenv("LMSTUDIO_GUI_QUERY_TIMEOUT_SECONDS", "600"))

        self.chat_store = self.load_chat_store()
        self.active_chat_id = str(self.chat_store.get("active_chat_id") or "")
        if not self.active_chat_id or not self.get_active_chat():
            self.create_chat(save=False)

        self.configure_styles()
        self.build_ui()
        self.populate_chat_list()
        self.render_current_chat()
        self.load_input_history()
        self.apply_settings_to_ui()
        self.schedule_game_guard_probe()

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
        except (OSError, json.JSONDecodeError):
            pass
        settings["send_on_enter"] = bool(settings.get("send_on_enter", DEFAULT_SETTINGS["send_on_enter"]))
        settings["use_lightrag"] = bool(settings.get("use_lightrag", DEFAULT_SETTINGS["use_lightrag"]))
        settings["game_guard_enabled"] = bool(settings.get("game_guard_enabled", DEFAULT_SETTINGS["game_guard_enabled"]))
        settings["game_guard_delay_seconds"] = max(1, int(settings.get("game_guard_delay_seconds", 5) or 5))
        settings["button_color"] = valid_hex_color(str(settings.get("button_color", "")), DEFAULT_SETTINGS["button_color"])
        settings["obsidian_path"] = str(settings.get("obsidian_path", "") or "")
        settings["default_llm_mode_applied"] = True
        return settings

    def save_settings(self) -> None:
        self.settings["send_on_enter"] = bool(self.settings["send_on_enter"])
        self.settings["use_lightrag"] = bool(self.settings["use_lightrag"])
        self.settings["game_guard_enabled"] = bool(self.settings["game_guard_enabled"])
        self.settings["game_guard_delay_seconds"] = max(1, int(self.settings.get("game_guard_delay_seconds", 5) or 5))
        self.settings["button_color"] = valid_hex_color(str(self.settings["button_color"]), DEFAULT_SETTINGS["button_color"])
        self.settings["obsidian_path"] = str(self.settings.get("obsidian_path", "") or "")
        self.settings["default_llm_mode_applied"] = True
        try:
            SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
            SETTINGS_PATH.write_text(json.dumps(self.settings, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        except OSError:
            pass

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

    def rename_chat(self) -> None:
        chat = self.get_active_chat()
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
        chat = self.get_active_chat()
        if not chat:
            return
        if not messagebox.askyesno("Удалить чат", f"Удалить «{chat.get('title', 'Чат')}»?", parent=self.root):
            return
        chats = [item for item in self.get_chats() if item.get("id") != self.active_chat_id]
        self.chat_store["chats"] = chats
        if chats:
            self.active_chat_id = str(chats[0].get("id"))
        else:
            self.create_chat(save=False)
        self.save_chat_store()
        self.populate_chat_list()
        self.render_current_chat()

    def add_message(self, role: str, text: str, context_name: str = "General", warnings: list[str] | None = None) -> None:
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
            "lightrag": bool(self.lightrag_var.get()),
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

    def populate_chat_list(self, keep_selection: bool = False) -> None:
        if not hasattr(self, "chat_list"):
            return
        self.chat_list.delete(0, "end")
        active_index = 0
        chats = sorted(self.get_chats(), key=lambda item: str(item.get("updated_at", "")), reverse=True)
        self.chat_store["chats"] = chats
        for index, chat in enumerate(chats):
            if chat.get("id") == self.active_chat_id:
                active_index = index
            title = str(chat.get("title") or "Чат")
            self.chat_list.insert("end", title)
        if chats:
            self.chat_list.selection_set(active_index)
            if not keep_selection:
                self.chat_list.see(active_index)

    def on_chat_select(self, _event: tk.Event | None = None) -> None:
        selection = self.chat_list.curselection()
        if not selection:
            return
        chats = self.get_chats()
        index = int(selection[0])
        if index >= len(chats):
            return
        chat_id = str(chats[index].get("id"))
        if chat_id == self.active_chat_id:
            return
        self.active_chat_id = chat_id
        self.save_chat_store()
        self.render_current_chat()

    def build_ui(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        toolbar = ttk.Frame(self.root, padding=(14, 10), style="Top.TFrame")
        toolbar.grid(row=0, column=0, sticky="ew")
        toolbar.columnconfigure(7, weight=1)

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
        self.add_tooltip(self.context, "Auto выбирает проект по сообщению. Можно вручную выбрать General, Web Development или My Game.")

        self.lightrag_toggle = ttk.Checkbutton(
            toolbar,
            text="LightRAG",
            variable=self.lightrag_var,
            command=self.on_lightrag_toggle,
            style="Toolbar.TCheckbutton",
        )
        self.lightrag_toggle.grid(row=0, column=3, padx=(0, 12))
        self.add_tooltip(self.lightrag_toggle, "Включает поиск по базе знаний. Если индекс не готов, чат сам вернется к обычной LLM.")

        self.obsidian_button = ttk.Button(toolbar, text="◇", width=3, command=self.open_obsidian)
        self.obsidian_button.grid(row=0, column=4, padx=(0, 8))
        self.add_tooltip(self.obsidian_button, "Открыть приложение Obsidian. Если путь не найден, можно указать Obsidian.exe.")

        self.settings_button = ttk.Button(toolbar, text="Настройки", command=self.open_settings)
        self.settings_button.grid(row=0, column=5, padx=(0, 14))
        self.add_tooltip(self.settings_button, "Enter, LightRAG, цвет кнопок, Obsidian и Game Guard.")

        self.control_button = ttk.Button(toolbar, text="Control", command=self.open_light_rag_control)
        self.control_button.grid(row=0, column=6, padx=(0, 14))
        self.add_tooltip(self.control_button, "Открыть LightRAG-Control для проверки LM Studio, моделей, индексов и импорта.")

        ttk.Label(toolbar, textvariable=self.status_var, style="Status.TLabel").grid(row=0, column=8, sticky="e")

        main = ttk.Frame(self.root, padding=(12, 12, 12, 14), style="App.TFrame")
        main.grid(row=1, column=0, sticky="nsew")
        main.columnconfigure(1, weight=1)
        main.rowconfigure(0, weight=1)

        sidebar_shell = tk.Frame(main, bg="#cfd4da", padx=1, pady=1)
        sidebar_shell.grid(row=0, column=0, sticky="ns", padx=(0, 10))
        sidebar = tk.Frame(sidebar_shell, bg="#eef2f5", width=238)
        sidebar.grid(row=0, column=0, sticky="ns")
        sidebar.grid_propagate(False)
        sidebar.rowconfigure(1, weight=1)
        tk.Label(sidebar, text="История", bg="#eef2f5", fg="#1f2933", font=("Segoe UI Semibold", 11), anchor="w").grid(
            row=0, column=0, sticky="ew", padx=12, pady=(10, 8)
        )
        self.chat_list = tk.Listbox(
            sidebar,
            activestyle="none",
            borderwidth=0,
            highlightthickness=0,
            bg="#eef2f5",
            fg="#1f2933",
            selectbackground="#dfe6ed",
            selectforeground="#111827",
            font=("Segoe UI", 9),
            exportselection=False,
        )
        self.chat_list.grid(row=1, column=0, sticky="nsew", padx=8)
        self.chat_list.bind("<<ListboxSelect>>", self.on_chat_select)
        side_buttons = tk.Frame(sidebar, bg="#eef2f5")
        side_buttons.grid(row=2, column=0, sticky="ew", padx=8, pady=8)
        side_buttons.columnconfigure((0, 1, 2), weight=1)
        ttk.Button(side_buttons, text="+", width=3, command=self.create_chat).grid(row=0, column=0, sticky="ew", padx=(0, 4))
        ttk.Button(side_buttons, text="✎", width=3, command=self.rename_chat).grid(row=0, column=1, sticky="ew", padx=4)
        ttk.Button(side_buttons, text="×", width=3, command=self.delete_chat).grid(row=0, column=2, sticky="ew", padx=(4, 0))

        chat_area = ttk.Frame(main, style="App.TFrame")
        chat_area.grid(row=0, column=1, sticky="nsew")
        chat_area.columnconfigure(0, weight=1)
        chat_area.rowconfigure(0, weight=1)

        chat_shell = tk.Frame(chat_area, bg="#cfd4da", padx=1, pady=1)
        chat_shell.grid(row=0, column=0, sticky="nsew")
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
        input_shell = tk.Frame(input_frame, bg="#cfd4da", padx=1, pady=1)
        input_shell.grid(row=0, column=0, sticky="ew")
        input_shell.columnconfigure(0, weight=1)

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

    def create_action_button(self, parent: tk.Widget, text: str, command, *, bg: str, active_bg: str, fg: str) -> RoundedButton:
        return RoundedButton(parent, text=text, command=command, bg=bg, active_bg=active_bg, fg=fg)

    def add_tooltip(self, widget: tk.Widget, text: str) -> None:
        self.tooltips.append(ToolTip(widget, text))

    def apply_settings_to_ui(self) -> None:
        self.enter_send_var.set(bool(self.settings["send_on_enter"]))
        self.lightrag_var.set(bool(self.settings["use_lightrag"]))
        self.game_guard_var.set(bool(self.settings["game_guard_enabled"]))
        self.button_color_var.set(str(self.settings["button_color"]))
        self.obsidian_path_var.set(str(self.settings.get("obsidian_path", "")))
        self.update_button_colors()
        self.on_lightrag_toggle(save=False)

    def update_button_colors(self) -> None:
        color = valid_hex_color(str(self.settings["button_color"]), DEFAULT_SETTINGS["button_color"])
        fg = readable_text_color(color)
        active_bg = adjust_hex_color(color, 0.86)
        self.send_button.set_colors(bg=color, active_bg=active_bg, fg=fg)

    def open_settings(self) -> None:
        if self.settings_window and self.settings_window.winfo_exists():
            self.settings_window.lift()
            self.settings_window.focus_force()
            return
        self.enter_send_var.set(bool(self.settings["send_on_enter"]))
        self.lightrag_var.set(bool(self.settings["use_lightrag"]))
        self.game_guard_var.set(bool(self.settings["game_guard_enabled"]))
        self.button_color_var.set(str(self.settings["button_color"]))
        self.obsidian_path_var.set(str(self.settings.get("obsidian_path", "")))
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

        ttk.Separator(frame, orient="horizontal").grid(row=4, column=0, columnspan=3, sticky="ew", pady=(14, 12))
        ttk.Label(frame, text="Obsidian", style="SettingsHeader.TLabel").grid(row=5, column=0, columnspan=3, sticky="w", pady=(0, 8))
        obsidian_entry = ttk.Entry(frame, textvariable=self.obsidian_path_var, width=54)
        obsidian_entry.grid(row=6, column=0, columnspan=2, sticky="ew", padx=(0, 8))
        ttk.Button(frame, text="Выбрать...", command=self.choose_obsidian_path).grid(row=6, column=2, sticky="e")

        ttk.Separator(frame, orient="horizontal").grid(row=7, column=0, columnspan=3, sticky="ew", pady=(14, 12))
        ttk.Label(frame, text="Цвет основной кнопки", style="SettingsHeader.TLabel").grid(row=8, column=0, columnspan=3, sticky="w", pady=(0, 10))
        preset_var = tk.StringVar(value=self.color_preset_name(self.button_color_var.get()))
        preset = ttk.Combobox(frame, textvariable=preset_var, values=list(BUTTON_COLOR_PRESETS.keys()), state="readonly", width=18)
        preset.grid(row=9, column=0, sticky="w", padx=(0, 10))
        preset.bind("<<ComboboxSelected>>", lambda _event: self.select_color_preset(preset_var.get()))
        self.settings_color_preview = tk.Label(frame, width=6, height=1, background=self.button_color_var.get(), relief="solid", borderwidth=1)
        self.settings_color_preview.grid(row=9, column=1, sticky="w", padx=(0, 10))
        ttk.Button(frame, text="Выбрать...", command=self.choose_button_color).grid(row=9, column=2, sticky="e")

        ttk.Label(frame, textvariable=self.settings_status_var, style="SettingsStatus.TLabel").grid(row=10, column=0, columnspan=3, sticky="w", pady=(14, 0))
        buttons = ttk.Frame(frame, style="App.TFrame")
        buttons.grid(row=11, column=0, columnspan=3, sticky="e", pady=(16, 0))
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
            filetypes=[("Obsidian", "Obsidian.exe"), ("Programs", "*.exe"), ("All files", "*.*")],
            parent=self.settings_window or self.root,
        )
        if path:
            self.obsidian_path_var.set(path)

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
        self.settings["obsidian_path"] = self.obsidian_path_var.get().strip()
        self.save_settings()
        self.apply_settings_to_ui()
        self.status_var.set("Settings saved")
        if bool(self.settings["game_guard_enabled"]):
            self.schedule_game_guard_probe()
        self.close_settings()

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
            else:
                self.append_assistant_message(text, "assistant", persist=False)
            for warning in warnings:
                self.append_warning_message(warning, persist=False)

    def show_intro(self) -> None:
        intro = (
            "Можно писать обычные сообщения или вопросы. LightRAG подключается только когда он включен и индекс готов.\n"
            "Ссылки и заметки можно сохранять прямо из диалога: например, «вот ссылка ...»."
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

    def append_assistant_message(self, text: str, tag: str = "assistant", persist: bool = True, warnings: list[str] | None = None) -> None:
        clean_text = text.strip()
        if not clean_text:
            return
        self.append(f"{clean_text}\n", tag)
        if persist:
            chat = self.get_active_chat()
            context_name = "General"
            if chat and chat.get("messages"):
                context_name = str(chat["messages"][-1].get("context") or "General")
            self.add_message("assistant" if tag == "assistant" else "error", clean_text, context_name, warnings)

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
        prompt = self.build_prompt_with_history(question)
        self.append_user_message(question)
        self.remember_input(question)
        self.clear_input()

        if self.is_save_intent(question):
            route = self.choose_capture_context((context_name, scope, project))
            if not route:
                self.append_warning_message("Сохранение отменено.", persist=True)
                return
            try:
                rel_path = self.save_capture(question, route)
                self.append_assistant_message(f"Сохранил в Obsidian: {rel_path}")
            except Exception as exc:
                self.append_assistant_message(f"Не удалось сохранить заметку: {exc}\nОткройте LightRAG-Control для диагностики.", "error")
            return

        use_lightrag = bool(self.lightrag_var.get())
        warnings: list[str] = []
        if use_lightrag and not self.is_lightrag_ready(scope, project):
            use_lightrag = False
            self.lightrag_var.set(False)
            self.settings["use_lightrag"] = False
            self.save_settings()
            warnings.append(f"LightRAG недоступен для {context_name}: индекс еще не готов. Ответ будет создан обычной LLM.")

        operation_id = self.begin_operation(f"Asking {context_name}...", self.query_timeout_seconds)
        thread = threading.Thread(
            target=self.run_query,
            args=(operation_id, prompt, context_name, scope, project, use_lightrag, warnings),
            daemon=True,
        )
        thread.start()

    def build_prompt_with_history(self, question: str) -> str:
        chat = self.get_active_chat()
        messages = chat.get("messages", []) if chat else []
        prior = [m for m in messages if m.get("role") in {"user", "assistant"}][-8:]
        if not prior:
            return question
        lines = ["Краткий контекст текущего диалога:"]
        for message in prior:
            role = "User" if message.get("role") == "user" else "Assistant"
            text = str(message.get("text", "")).strip()
            if text:
                lines.append(f"{role}: {text[:900]}")
        lines.extend(["", f"Текущее сообщение пользователя: {question}"])
        return "\n".join(lines)

    def run_query(
        self,
        operation_id: int,
        question: str,
        context_name: str,
        scope: str,
        project: str,
        use_lightrag: bool,
        pending_warnings: list[str],
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
        env["LMSTUDIO_USE_LIGHTRAG"] = "1" if use_lightrag else "0"
        if not use_lightrag:
            env["LMSTUDIO_WARN_PLAIN_MODE"] = "1"
            env.setdefault("LMSTUDIO_LIGHTRAG_OFF_REASON", "LightRAG отключен: ответ без базы знаний.")

        try:
            returncode, output = self.run_command(command, self.query_timeout_seconds, env=env)
            output, warnings = self.split_knowledge_warnings(output)
            warnings = pending_warnings + warnings
            if returncode != 0:
                output = self.friendly_error(output)
                tag = "error"
            else:
                tag = "assistant"
            if not output:
                output = "Модель вернула пустой ответ. Попробуйте еще раз или откройте LightRAG-Control для проверки LM Studio."
                tag = "error"
        except TimeoutError as exc:
            output = f"{exc}\nЗапрос остановлен, чтобы чат не зависал. Можно повторить или открыть LightRAG-Control."
            tag = "error"
            warnings = pending_warnings
        except Exception as exc:
            output = f"Не удалось получить ответ: {exc}\nОткройте LightRAG-Control для диагностики."
            tag = "error"
            warnings = pending_warnings
        self.root.after(0, self.finish_query, operation_id, output, tag, warnings)

    def finish_query(self, operation_id: int, output: str, tag: str, warnings: list[str]) -> None:
        if not self.is_active_operation(operation_id):
            return
        self.append_assistant_message(output, tag, warnings=warnings)
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
        self.terminate_active_process()
        self.set_busy(False, "Ready")
        self.status_var.set("Canceled")

    def set_busy(self, busy: bool, status: str) -> None:
        self.busy = busy
        state = "disabled" if busy else "normal"
        self.send_button.configure(state=state)
        self.cancel_button.configure(state="normal" if busy else "disabled")
        self.clear_button.configure(state=state)
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
        candidates = [
            configured,
            str(Path(os.getenv("LOCALAPPDATA", "")) / "Obsidian" / "Obsidian.exe"),
            str(Path(os.getenv("LOCALAPPDATA", "")) / "Programs" / "Obsidian" / "Obsidian.exe"),
        ]
        for candidate in candidates:
            if candidate and Path(candidate).exists():
                return candidate
        return ""

    def open_obsidian(self) -> None:
        obsidian = self.find_obsidian_path()
        if obsidian:
            subprocess.Popen([obsidian], cwd=str(VAULT_DIR if VAULT_DIR.exists() else ROOT))
            return
        answer = messagebox.askyesnocancel(
            "Obsidian не найден",
            "Не удалось найти Obsidian.exe.\n\nДа - указать путь к Obsidian.exe\nНет - открыть сайт Obsidian\nОтмена - ничего не делать",
            parent=self.root,
        )
        if answer is True:
            path = filedialog.askopenfilename(
                title="Выберите Obsidian.exe",
                filetypes=[("Obsidian", "Obsidian.exe"), ("Programs", "*.exe"), ("All files", "*.*")],
                parent=self.root,
            )
            if path:
                self.settings["obsidian_path"] = path
                self.save_settings()
                subprocess.Popen([path], cwd=str(VAULT_DIR if VAULT_DIR.exists() else ROOT))
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

    root = tk.Tk()
    try:
        ttk.Style().theme_use("vista")
    except tk.TclError:
        pass
    KnowledgeChatApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
