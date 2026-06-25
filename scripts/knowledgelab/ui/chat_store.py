"""Chat store — session persistence and CRUD operations."""
from __future__ import annotations

import datetime as dt
import json
import re
import uuid
from pathlib import Path

from knowledgelab.config import CHAT_STORE_PATH, LEGACY_HISTORY_PATH
from knowledgelab.utils.text import now_iso


def new_id(prefix: str = "chat") -> str:
    return f"{prefix}-{dt.datetime.now().strftime('%Y%m%d%H%M%S%f')}"


def title_for_chat(text: str) -> str:
    title = re.sub(r"\s+", " ", text.strip()).strip()
    return title[:42] + ("..." if len(title) > 42 else "") if title else "Новый чат"


def format_chat_age(updated_at: str) -> str:
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
        if days < 30:
            return f"{days}д"
        months = days // 30
        if months < 12:
            return f"{months}мес"
        return f"{days // 365}г"
    except (ValueError, TypeError):
        return ""


def chat_group_name(updated_at: str) -> str:
    try:
        updated = dt.datetime.fromisoformat(updated_at)
        now = dt.datetime.now()
        delta = now - updated
        minutes = max(0, int(delta.total_seconds() // 60))
        if minutes < 60:
            return "Сегодня"
        if delta.days == 1:
            return "Вчера"
        if delta.days < 7:
            return "На этой неделе"
        if updated.month == now.month and updated.year == now.year:
            return "В этом месяце"
        if updated.year == now.year:
            return "Ранее в этом году"
        return "Ранее"
    except (ValueError, TypeError):
        return "Без даты"


def chat_group_by_context(chat: dict) -> str:
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
    if "Finished Projects" in contexts:
        return "Finished Projects"
    title = str(chat.get("title") or "").strip()
    if title and title != "Новый чат":
        from knowledgelab.routing.intent import infer_topic
        topic = infer_topic(title, "general")
        if topic not in {"General", "Web", "Project Notes"}:
            return topic
    return "Без темы"


def migrate_legacy_history() -> dict | None:
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
                        "id": new_id("msg"),
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
    chat_id = new_id("chat")
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


def load_chat_store() -> dict:
    if CHAT_STORE_PATH.exists():
        try:
            data = json.loads(CHAT_STORE_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict) and isinstance(data.get("chats"), list):
                data["chats"] = _dedupe_chats(data["chats"])
                return data
        except (OSError, json.JSONDecodeError):
            pass
    migrated = migrate_legacy_history()
    if migrated:
        migrated["chats"] = _dedupe_chats(migrated.get("chats", []))
        return migrated
    return {"version": 1, "active_chat_id": "", "chats": []}


def _dedupe_chats(chats: list[dict]) -> list[dict]:
    """Remove duplicate chats and limit to max 25."""
    seen: set[str] = set()
    unique: list[dict] = []
    for chat in chats:
        chat_id = str(chat.get("id", ""))
        title = str(chat.get("title", ""))
        messages = chat.get("messages", [])
        key = f"{title}|{len(messages)}"
        if key in seen:
            continue
        seen.add(key)
        unique.append(chat)
    unique.sort(key=lambda c: str(c.get("updated_at", "")), reverse=True)
    return unique[:25]


def save_chat_store(data: dict) -> None:
    try:
        CHAT_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
        CHAT_STORE_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except OSError:
        pass


def get_chats(data: dict) -> list[dict]:
    chats = data.setdefault("chats", [])
    return chats if isinstance(chats, list) else []


def get_active_chat(data: dict, active_chat_id: str = "") -> dict | None:
    active_id = active_chat_id or data.get("active_chat_id", "")
    for chat in get_chats(data):
        if chat.get("id") == active_id:
            return chat
    return None


def create_chat(data: dict, name: str = "") -> str:
    chat_id = new_id("chat")
    chat = {
        "id": chat_id,
        "title": name or "Новый чат",
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "messages": [],
    }
    get_chats(data).insert(0, chat)
    data["active_chat_id"] = chat_id
    return chat_id


def delete_chat(data: dict, chat_id: str) -> None:
    chats = [item for item in get_chats(data) if str(item.get("id")) != chat_id]
    data["chats"] = chats
    if chats and data.get("active_chat_id") == chat_id:
        data["active_chat_id"] = str(chats[0].get("id"))
    elif not chats:
        create_chat(data)


def rename_chat(data: dict, chat_id: str, new_name: str) -> None:
    for chat in get_chats(data):
        if str(chat.get("id")) == chat_id:
            chat["title"] = new_name.strip()[:80] or "Чат"
            chat["updated_at"] = now_iso()
            return


def chat_by_id(data: dict, chat_id: str) -> dict | None:
    for chat in get_chats(data):
        if str(chat.get("id")) == chat_id:
            return chat
    return None


def add_message(data: dict, chat_id: str, role: str, content: str, **kwargs) -> None:
    chat = chat_by_id(data, chat_id)
    if not chat:
        return
    message = {
        "id": new_id("msg"),
        "ts": now_iso(),
        "role": role,
        "context": kwargs.get("context", "General"),
        "lightrag": bool(kwargs.get("lightrag", False)),
        "text": content,
        "warnings": kwargs.get("warnings", []),
        "project_action_id": kwargs.get("project_action_id", ""),
    }
    chat.setdefault("messages", []).append(message)
    chat["updated_at"] = message["ts"]
