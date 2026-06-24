"""Chat list sidebar management."""
from __future__ import annotations

import time
import tkinter as tk
from tkinter import messagebox
from typing import TYPE_CHECKING

from knowledgelab.utils.text import now_iso
from knowledgelab.ui.chat_store import title_for_chat, format_chat_age, chat_group_by_context

if TYPE_CHECKING:
    from main import KnowledgeChatApp


class ChatListManager:
    """Manages the chat list sidebar UI."""

    def __init__(self, app: KnowledgeChatApp) -> None:
        self.app = app
        self.rename_entry: tk.Entry | None = None
        self.rename_chat_id = ""
        self.rename_original = ""
        self.rename_ignore_click_until = 0.0

    def _has_sidebar(self) -> bool:
        """Check if sidebar widgets exist."""
        return hasattr(self.app, "chat_rows") and hasattr(self.app, "chat_row_widgets")

    def populate(self, keep_selection: bool = False) -> None:
        """Rebuild the chat list from store."""
        if not self._has_sidebar():
            return
        for widget in self.app.chat_row_widgets:
            try:
                widget.destroy()
            except tk.TclError:
                pass
        self.app.chat_row_widgets.clear()

        chats = sorted(self.app.get_chats(), key=lambda item: str(item.get("updated_at", "")), reverse=True)
        self.app.chat_store["chats"] = chats
        if not chats:
            empty = tk.Label(self.app.chat_rows, text="Нет чатов", bg="#eef2f5", fg="#6b7280", anchor="w", font=("Segoe UI", 9))
            empty.grid(row=0, column=0, sticky="ew", padx=12, pady=8)
            self.app.bind_history_mousewheel(empty)
            self.app.chat_row_widgets.append(empty)
            return

        grouped: dict[str, list[dict]] = {}
        for chat in chats:
            grouped.setdefault(self.get_group_name(chat), []).append(chat)

        ordered_groups = [name for name in ("Web Development", "My Game", "Finished Projects", "Без темы") if name in grouped]
        ordered_groups.extend(sorted(name for name in grouped if name not in ordered_groups))

        row_index = 0
        for group_name in ordered_groups:
            section = tk.Label(
                self.app.chat_rows,
                text=group_name,
                bg="#eef2f5",
                fg="#6b7280",
                anchor="w",
                font=("Segoe UI Semibold", 9),
            )
            section.grid(row=row_index, column=0, sticky="ew", padx=14, pady=(12 if row_index else 4, 4))
            self.app.bind_history_mousewheel(section)
            self.app.chat_row_widgets.append(section)
            row_index += 1

            for chat in grouped[group_name]:
                self.add_row(chat, row_index)
                row_index += 1

    def add_row(self, chat: dict, row_index: int) -> None:
        """Add a single chat row to the sidebar."""
        chat_id = str(chat.get("id"))
        is_active = chat_id == self.app.active_chat_id
        row_bg = "#dfe6ed" if is_active else "#eef2f5"
        row = tk.Frame(self.app.chat_rows, bg=row_bg, padx=8, pady=6)
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
        age = tk.Label(row, text=format_chat_age(str(chat.get("updated_at", ""))), bg=row_bg, fg="#6b7280", font=("Segoe UI", 8))
        age.grid(row=0, column=1, sticky="e", padx=(6, 4))
        delete = tk.Button(row, text="×", width=2, relief="flat", bg=row_bg, activebackground="#d4dde6", command=lambda cid=chat_id: self.delete_chat_by_id(cid))
        delete.grid(row=0, column=2, sticky="e", padx=(2, 0))

        hover_bg = "#e3e9f0" if is_active else "#e8edf2"
        for child in (row, title_label, age):
            child.bind("<Button-1>", lambda _event, cid=chat_id: self.select_chat(cid))
            child.bind("<Double-Button-1>", lambda _event, cid=chat_id, r=row, label=title_label: self.begin_rename(cid, r, label))
            child.bind("<Enter>", lambda _event, r=row, bg=hover_bg: r.configure(bg=bg))
            child.bind("<Leave>", lambda _event, r=row, bg=row_bg: r.configure(bg=bg))
            self.app.bind_history_mousewheel(child)
        self.app.bind_history_mousewheel(delete)
        self.app.add_tooltip(title_label, "Двойной клик, чтобы переименовать чат.")
        self.app.chat_row_widgets.append(row)

    def select_chat(self, chat_id: str) -> None:
        """Select a chat by ID."""
        if chat_id == self.app.active_chat_id:
            return
        if not self.app.chat_by_id(chat_id):
            return
        self.app.active_chat_id = chat_id
        self.app.save_chat_store()
        self.populate(keep_selection=True)
        self.app.render_current_chat()

    def delete_chat_by_id(self, chat_id: str) -> None:
        """Delete a chat by ID."""
        chat = self.app.chat_by_id(chat_id)
        if not chat:
            return
        if not messagebox.askyesno("Удалить чат", f"Удалить «{chat.get('title', 'Чат')}»?", parent=self.app.root):
            return
        chats = [item for item in self.app.get_chats() if str(item.get("id")) != chat_id]
        self.app.chat_store["chats"] = chats
        if chats and self.app.active_chat_id == chat_id:
            self.app.active_chat_id = str(chats[0].get("id"))
        elif not chats:
            self.app.create_chat(save=False)
        self.app.save_chat_store()
        self.populate()
        self.app.render_current_chat()

    def begin_rename(self, chat_id: str, row: "tk.Frame", title_label: "tk.Label") -> str:
        """Start inline rename for a chat."""
        chat = self.app.chat_by_id(chat_id)
        if not chat:
            return "break"
        if self.rename_entry:
            self.finish_rename(save=True)
        self.rename_chat_id = chat_id
        self.rename_original = str(chat.get("title") or "Чат")
        self.rename_ignore_click_until = time.time() + 0.25
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
        entry.insert(0, self.rename_original)
        entry.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        self.rename_entry = entry
        entry.bind("<Return>", lambda _event: self.finish_rename(save=True) or "break")
        entry.bind("<Escape>", lambda _event: self.finish_rename(save=False) or "break")
        entry.bind("<FocusOut>", lambda _event: self.finish_rename(save=True))
        self.app.bind_history_mousewheel(entry)
        entry.focus_set()
        entry.select_range(0, "end")
        return "break"

    def finish_rename(self, save: bool = True) -> None:
        """Finish inline rename."""
        entry = self.rename_entry
        chat_id = self.rename_chat_id
        original = self.rename_original
        self.rename_entry = None
        self.rename_chat_id = ""
        self.rename_original = ""
        self.rename_ignore_click_until = 0.0
        if not entry:
            return
        title = entry.get().strip()
        if save and title:
            chat = self.app.chat_by_id(chat_id)
            if chat and title != original:
                chat["title"] = title[:80]
                chat["updated_at"] = now_iso()
                self.app.save_chat_store()
        self.populate(keep_selection=True)

    def on_global_click(self, event: tk.Event) -> None:
        """Handle global click to finish rename."""
        entry = self.rename_entry
        if not entry:
            return
        if time.time() < self.rename_ignore_click_until:
            return
        if event.widget == entry:
            return
        self.finish_rename(save=True)

    def get_group_name(self, chat: dict) -> str:
        """Get group name for a chat."""
        return chat_group_by_context(chat)

    def get_title(self, text: str) -> str:
        """Get title for chat from text."""
        return title_for_chat(text)
