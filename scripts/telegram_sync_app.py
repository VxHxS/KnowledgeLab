from __future__ import annotations

import datetime as dt
import json
import queue
import re
import sys
import threading
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import tkinter as tk
from tkinter import filedialog, messagebox, ttk


from knowledgelab.config import ROOT, VAULT_DIR
from knowledgelab.utils.text import clean_filename, slugify, yaml_quote
from knowledgelab.utils.urls import URL_RE

SYNC_DIR = ROOT / ".telegram-sync"
CONFIG_PATH = SYNC_DIR / "telegram_export_sync_config.json"
DEFAULT_CHAT_NAME = "Unity ресурсы"
DEFAULT_OUTPUT_DIR = "30 Sources/Telegram"
DEFAULT_SCOPE = "general"
MSG_BLOCK_RE = re.compile(
    r"<!-- tg-msg:(-?\d+) -->\n(.*?)(?=\n<!-- tg-msg:-?\d+ -->|\Z)",
    re.DOTALL,
)


@dataclass
class TopicInfo:
    topic_id: int | None
    title: str


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return default


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8-sig")


def default_config() -> dict[str, Any]:
    return {
        "export_json": "",
        "chat_name": DEFAULT_CHAT_NAME,
        "scope": DEFAULT_SCOPE,
        "project": "",
        "output_dir": DEFAULT_OUTPUT_DIR,
    }


def load_config() -> dict[str, Any]:
    config = default_config()
    config.update(read_json(CONFIG_PATH, {}))
    return config


def save_config(config: dict[str, Any]) -> None:
    write_json(CONFIG_PATH, config)


def flatten_export_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = str(item.get("text", ""))
                href = item.get("href")
                if href and text and href != text:
                    parts.append(f"{text} ({href})")
                else:
                    parts.append(text)
        return "".join(parts)
    return str(value)


def message_date(message: dict[str, Any]) -> dt.datetime:
    raw = str(message.get("date") or message.get("date_unixtime") or "")
    if raw.isdigit():
        return dt.datetime.fromtimestamp(int(raw), tz=dt.timezone.utc).replace(tzinfo=None)
    try:
        return dt.datetime.fromisoformat(raw.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return dt.datetime.now().replace(microsecond=0)


def first_line(value: str, fallback: str) -> str:
    text = re.sub(r"\s+", " ", value).strip()
    if not text:
        return fallback
    text = URL_RE.sub("", text).strip(" -:|")
    if not text:
        text = value.strip()
    return text[:72].strip() or fallback


def message_preview(message: dict[str, Any], fallback: str) -> str:
    text = flatten_export_text(message.get("text"))
    caption = flatten_export_text(message.get("caption"))
    return first_line(text or caption, fallback)


def topic_id_for_message(message: dict[str, Any]) -> int | None:
    raw_id = (
        message.get("topic_id")
        or message.get("forum_topic_id")
        or message.get("reply_to_top_message_id")
        or message.get("reply_to_message_id")
    )
    try:
        return int(raw_id) if raw_id else None
    except (TypeError, ValueError):
        return None


def build_topic_buckets(messages: list[dict[str, Any]]) -> dict[str, tuple[TopicInfo, list[dict[str, Any]]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for message in messages:
        topic_id = topic_id_for_message(message)
        key = str(topic_id) if topic_id is not None else "all"
        grouped.setdefault(key, []).append(message)

    buckets: dict[str, tuple[TopicInfo, list[dict[str, Any]]]] = {}
    for key, items in grouped.items():
        topic_id = None if key == "all" else int(key)
        if topic_id is None:
            title = "All Messages"
        else:
            title = message_preview(items[0], f"Thread {topic_id}")
        buckets[key] = (TopicInfo(topic_id=topic_id, title=title), items)
    return buckets


def extract_links(message: dict[str, Any], text: str) -> list[str]:
    links = set(URL_RE.findall(text or ""))
    for field in ("text_entities", "caption_entities"):
        for entity in message.get(field, []) or []:
            if isinstance(entity, dict):
                href = entity.get("href")
                entity_text = entity.get("text")
                if href:
                    links.add(str(href))
                if isinstance(entity_text, str):
                    links.update(URL_RE.findall(entity_text))
    return sorted(links)


def media_lines(message: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for key in ("media_type", "photo", "file", "file_name", "thumbnail", "mime_type"):
        value = message.get(key)
        if value:
            lines.append(f"- {key}: `{value}`")
    return lines


def render_message_block(message: dict[str, Any], topic: TopicInfo) -> str:
    msg_id = int(message.get("id") or 0)
    when = message_date(message)
    author = message.get("from") or message.get("actor") or message.get("from_id") or "unknown"
    text = flatten_export_text(message.get("text")).strip()
    caption = flatten_export_text(message.get("caption")).strip()
    if caption and caption not in text:
        text = f"{text}\n\n{caption}".strip()

    links = extract_links(message, text)
    media = media_lines(message)
    topic_id = topic.topic_id if topic.topic_id is not None else "all"

    lines = [
        f"<!-- tg-msg:{msg_id} -->",
        f"## {when:%Y-%m-%d %H:%M} - message {msg_id}",
        "",
        f"- topic: {topic.title}",
        f"- topic_id: {topic_id}",
        f"- author: {author}",
    ]
    if message.get("reply_to_message_id"):
        lines.append(f"- reply_to_message_id: {message.get('reply_to_message_id')}")
    if message.get("forwarded_from"):
        lines.append(f"- forwarded_from: {message.get('forwarded_from')}")
    lines.append("")

    if text:
        lines.extend([text, ""])
    if links:
        lines.extend(["### Links", *[f"- {link}" for link in links], ""])
    if media:
        lines.extend(["### Media", *media, ""])
    return "\n".join(lines).rstrip() + "\n"


def parse_existing_blocks(path: Path) -> dict[int, str]:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8-sig")
    return {int(match.group(1)): match.group(0).rstrip() + "\n" for match in MSG_BLOCK_RE.finditer(text)}


def topic_prefix(topic: TopicInfo) -> str:
    return "all" if topic.topic_id is None else f"{topic.topic_id:04d}"


def preferred_topic_path(config: dict[str, Any], chat_title: str, topic: TopicInfo) -> Path:
    output_root = VAULT_DIR / str(config.get("output_dir") or DEFAULT_OUTPUT_DIR)
    chat_dir = output_root / clean_filename(chat_title)
    return chat_dir / f"{topic_prefix(topic)} {clean_filename(topic.title)}.md"


def existing_topic_paths(config: dict[str, Any], chat_title: str, topic: TopicInfo) -> list[Path]:
    output_root = VAULT_DIR / str(config.get("output_dir") or DEFAULT_OUTPUT_DIR)
    chat_dir = output_root / clean_filename(chat_title)
    if not chat_dir.exists():
        return []
    return sorted(chat_dir.glob(f"{topic_prefix(topic)} *.md"))


def resolve_topic_path(config: dict[str, Any], chat_title: str, topic: TopicInfo) -> Path:
    preferred = preferred_topic_path(config, chat_title, topic)
    existing = [path for path in existing_topic_paths(config, chat_title, topic) if path != preferred]
    if preferred.exists():
        return preferred
    if len(existing) == 1:
        existing[0].rename(preferred)
        return preferred
    return preferred


def write_topic_file(
    path: Path,
    *,
    chat_title: str,
    topic: TopicInfo,
    scope: str,
    project: str,
    blocks: dict[int, str],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    now = dt.datetime.now().replace(microsecond=0).isoformat()
    topic_id = str(topic.topic_id if topic.topic_id is not None else "all")
    frontmatter = [
        "---",
        "type: telegram_topic",
        "source: telegram",
        f"chat: {yaml_quote(chat_title)}",
        f"topic: {yaml_quote(topic.title)}",
        f"topic_id: {yaml_quote(topic_id)}",
        f"scope: {scope}",
        f"project: {yaml_quote(project)}",
        f"message_count: {len(blocks)}",
        f"last_synced_at: {yaml_quote(now)}",
        "tags: [source/telegram, unity]",
        "---",
        "",
        f"# Telegram - {chat_title} - {topic.title}",
        "",
        f"Synced messages: {len(blocks)}",
        "",
    ]
    body = [blocks[msg_id].rstrip() for msg_id in sorted(blocks)]
    path.write_text("\n".join(frontmatter + body).rstrip() + "\n", encoding="utf-8-sig")


def run_export_sync(config: dict[str, Any], progress: Callable[[int, str], None]) -> dict[str, Any]:
    export_path = Path(str(config.get("export_json", ""))).expanduser()
    if not export_path.exists():
        raise RuntimeError(f"Telegram export JSON not found: {export_path}")

    progress(5, "Reading Telegram Desktop export...")
    data = json.loads(export_path.read_text(encoding="utf-8-sig"))
    chat_title = str(config.get("chat_name") or data.get("name") or DEFAULT_CHAT_NAME)
    scope = str(config.get("scope", DEFAULT_SCOPE) or DEFAULT_SCOPE)
    project = str(config.get("project", "") or "")
    messages = [
        message
        for message in data.get("messages", [])
        if isinstance(message, dict) and message.get("type") == "message"
    ]
    buckets = build_topic_buckets(messages)
    progress(15, f"Messages: {len(messages)}. Threads: {len(buckets)}.")

    imported_total = 0
    for index, (_, (topic, topic_messages)) in enumerate(sorted(buckets.items()), start=1):
        progress(
            15 + int((index - 1) / max(len(buckets), 1) * 80),
            f"Syncing: {topic.title}",
        )
        path = resolve_topic_path(config, chat_title, topic)
        blocks = parse_existing_blocks(path)
        before = len(blocks)
        for message in topic_messages:
            msg_id = int(message.get("id") or 0)
            if msg_id and msg_id not in blocks:
                blocks[msg_id] = render_message_block(message, topic)
        write_topic_file(
            path,
            chat_title=chat_title,
            topic=topic,
            scope=scope,
            project=project,
            blocks=blocks,
        )
        imported_total += max(0, len(blocks) - before)

    progress(100, f"Done. New messages: {imported_total}.")
    return {"threads": len(buckets), "imported": imported_total, "chat_title": chat_title}


class TelegramExportSyncApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.config = load_config()
        self.queue: queue.Queue[tuple[str, Any]] = queue.Queue()
        self.worker: threading.Thread | None = None
        self.root.title("Telegram Export Sync")
        self.root.geometry("680x430")
        self.root.minsize(620, 400)
        self.build_ui()
        self.root.after(100, self.process_queue)

    def build_ui(self) -> None:
        frame = ttk.Frame(self.root, padding=18)
        frame.pack(fill=tk.BOTH, expand=True)

        title = ttk.Label(frame, text="Telegram Export Sync", font=("Segoe UI", 18, "bold"))
        title.grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 14))

        self.vars: dict[str, tk.StringVar] = {}

        ttk.Label(frame, text="Export result.json").grid(row=1, column=0, sticky="w", pady=4)
        self.vars["export_json"] = tk.StringVar(value=str(self.config.get("export_json", "")))
        ttk.Entry(frame, textvariable=self.vars["export_json"]).grid(row=1, column=1, columnspan=2, sticky="ew", pady=4)
        ttk.Button(frame, text="Browse", command=self.browse_export_json).grid(row=1, column=3, sticky="ew", padx=(8, 0), pady=4)

        ttk.Label(frame, text="Chat name").grid(row=2, column=0, sticky="w", pady=4)
        self.vars["chat_name"] = tk.StringVar(value=str(self.config.get("chat_name", DEFAULT_CHAT_NAME)))
        ttk.Entry(frame, textvariable=self.vars["chat_name"]).grid(row=2, column=1, columnspan=3, sticky="ew", pady=4)

        ttk.Label(frame, text="Scope").grid(row=3, column=0, sticky="w", pady=4)
        self.vars["scope"] = tk.StringVar(value=str(self.config.get("scope", DEFAULT_SCOPE)))
        ttk.Combobox(
            frame,
            textvariable=self.vars["scope"],
            values=["general", "game"],
            state="readonly",
        ).grid(row=3, column=1, sticky="ew", pady=4)

        ttk.Label(frame, text="Project").grid(row=3, column=2, sticky="w", padx=(12, 0), pady=4)
        self.vars["project"] = tk.StringVar(value=str(self.config.get("project", "")))
        ttk.Entry(frame, textvariable=self.vars["project"]).grid(row=3, column=3, sticky="ew", pady=4)

        hint = ttk.Label(
            frame,
            text="Use Telegram Desktop: Export chat history -> Machine-readable JSON. Media can stay unchecked.",
            foreground="#5d6975",
        )
        hint.grid(row=4, column=0, columnspan=4, sticky="w", pady=(8, 12))

        self.progress = ttk.Progressbar(frame, orient=tk.HORIZONTAL, mode="determinate", maximum=100)
        self.progress.grid(row=5, column=0, columnspan=4, sticky="ew", pady=(0, 8))
        self.status = ttk.Label(frame, text="Ready", foreground="#304050")
        self.status.grid(row=6, column=0, columnspan=4, sticky="w", pady=(0, 8))

        self.log = tk.Text(frame, height=10, wrap=tk.WORD, borderwidth=1, relief=tk.SOLID)
        self.log.grid(row=7, column=0, columnspan=4, sticky="nsew")
        self.log.configure(state=tk.DISABLED)

        buttons = ttk.Frame(frame)
        buttons.grid(row=8, column=0, columnspan=4, sticky="ew", pady=(12, 0))
        self.sync_button = ttk.Button(buttons, text="Sync", command=self.start_sync)
        self.sync_button.pack(side=tk.LEFT)
        ttk.Button(buttons, text="Close", command=self.root.destroy).pack(side=tk.RIGHT)

        frame.columnconfigure(1, weight=1)
        frame.columnconfigure(3, weight=1)
        frame.rowconfigure(7, weight=1)

    def browse_export_json(self) -> None:
        path = filedialog.askopenfilename(
            parent=self.root,
            title="Select Telegram Desktop result.json",
            filetypes=[("Telegram export JSON", "result.json"), ("JSON files", "*.json"), ("All files", "*.*")],
        )
        if path:
            self.vars["export_json"].set(path)

    def append_log(self, text: str) -> None:
        self.log.configure(state=tk.NORMAL)
        self.log.insert(tk.END, text.rstrip() + "\n")
        self.log.see(tk.END)
        self.log.configure(state=tk.DISABLED)

    def collect_config(self) -> dict[str, Any]:
        config = load_config()
        for key, var in self.vars.items():
            config[key] = var.get().strip()
        config["output_dir"] = DEFAULT_OUTPUT_DIR
        return config

    def validate_config(self, config: dict[str, Any]) -> bool:
        export_json = str(config.get("export_json", "")).strip()
        if not export_json:
            messagebox.showerror("Telegram Export Sync", "Select Telegram Desktop result.json.")
            return False
        if not Path(export_json).expanduser().exists():
            messagebox.showerror("Telegram Export Sync", f"File not found:\n{export_json}")
            return False
        return True

    def start_sync(self) -> None:
        if self.worker and self.worker.is_alive():
            return
        config = self.collect_config()
        if not self.validate_config(config):
            return
        save_config(config)
        self.progress["value"] = 0
        self.status.configure(text="Starting sync...")
        self.sync_button.configure(state=tk.DISABLED)
        self.append_log("Sync started")

        def progress(percent: int, text: str) -> None:
            self.queue.put(("progress", (percent, text)))

        def worker() -> None:
            try:
                result = run_export_sync(config, progress)
                self.queue.put(("done", result))
            except Exception as exc:
                self.queue.put(("error", f"{exc}\n\n{traceback.format_exc()}"))

        self.worker = threading.Thread(target=worker, daemon=True)
        self.worker.start()

    def process_queue(self) -> None:
        try:
            while True:
                kind, payload = self.queue.get_nowait()
                if kind == "progress":
                    percent, text = payload
                    self.progress["value"] = max(0, min(100, int(percent)))
                    self.status.configure(text=text)
                    self.append_log(text)
                elif kind == "done":
                    self.progress["value"] = 100
                    self.status.configure(text="Sync complete")
                    self.append_log(f"Done: {payload}")
                    self.sync_button.configure(state=tk.NORMAL)
                    messagebox.showinfo("Telegram Export Sync", "Sync complete: 100%.")
                elif kind == "error":
                    self.status.configure(text="Sync error")
                    self.append_log(str(payload))
                    self.sync_button.configure(state=tk.NORMAL)
                    messagebox.showerror("Telegram Export Sync", str(payload)[:1800])
        except queue.Empty:
            pass
        self.root.after(100, self.process_queue)


def main() -> None:
    if "--smoke-test" in sys.argv:
        print("Mode=Telegram Desktop export")
        print(f"ConfigPath={CONFIG_PATH}")
        print(f"VaultDir={VAULT_DIR}")
        return
    if "--sync-export" in sys.argv:
        index = sys.argv.index("--sync-export")
        config = default_config()
        config["export_json"] = sys.argv[index + 1]
        result = run_export_sync(config, lambda percent, text: print(f"{percent}% {text}"))
        print(result)
        return

    root = tk.Tk()
    TelegramExportSyncApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
