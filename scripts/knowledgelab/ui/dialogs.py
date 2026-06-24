"""Dialog windows — standalone tkinter dialogs that return user choices."""
from __future__ import annotations
import tkinter as tk
from tkinter import ttk

from knowledgelab.config import DEFAULT_VAULT_DIR, BUTTON_COLOR_PRESETS, DEFAULT_SETTINGS
from knowledgelab.utils.colors import valid_hex_color
from knowledgelab.models import KnowledgeRoute
from knowledgelab.routing.intent import is_finished_project_lookup_text, contains_any
from knowledgelab.config import WEB_TERMS, GAME_TERMS


def _center_window(window: tk.Toplevel, root: tk.Tk) -> None:
    """Center a dialog window over its parent."""
    window.update_idletasks()
    x = root.winfo_rootx() + max(30, (root.winfo_width() - window.winfo_width()) // 2)
    y = root.winfo_rooty() + max(30, (root.winfo_height() - window.winfo_height()) // 3)
    window.geometry(f"+{x}+{y}")


def choose_capture_context(
    root: tk.Tk,
    suggested: KnowledgeRoute,
    input_text: str = "",
    finished_title_default: str = "",
    source_hint: str = "",
    allow_finished_project: bool = True,
    auto_route: bool = True,
) -> KnowledgeRoute | str | None:
    """Show dialog asking user where to save material. Returns route, 'auto', 'custom-project', 'finished-project', or None."""
    result: dict[str, KnowledgeRoute | str | None] = {"value": None}
    window = tk.Toplevel(root)
    window.title("Куда сохранить?")
    window.transient(root)
    window.resizable(False, False)
    window.configure(bg="#f4f6f8")
    ttk.Label(window, text="В какой слой сохранить материал?", padding=(18, 16), background="#f4f6f8").grid(row=0, column=0, columnspan=4)

    def pick(value: KnowledgeRoute | str | None) -> None:
        result["value"] = value
        window.destroy()

    ttk.Button(window, text="General", command=lambda: pick(KnowledgeRoute("General", "general", ""))).grid(row=1, column=0, padx=(18, 6), pady=(0, 16))
    ttk.Button(window, text="Web Development", command=lambda: pick(KnowledgeRoute("Web Development", "web", "web-development"))).grid(row=1, column=1, padx=6, pady=(0, 16))
    ttk.Button(window, text="My Game", command=lambda: pick(KnowledgeRoute("My Game", "game", "my-game"))).grid(row=1, column=2, padx=6, pady=(0, 16))
    ttk.Button(window, text="Finished Project", command=lambda: pick("finished-project")).grid(row=1, column=3, padx=(6, 18), pady=(0, 16))
    ttk.Button(window, text="Авто", command=lambda: pick("auto")).grid(row=2, column=0, padx=(18, 6), pady=(0, 16), sticky="ew")
    ttk.Button(window, text="Новый проект...", command=lambda: pick("custom-project")).grid(row=2, column=1, columnspan=2, padx=6, pady=(0, 16), sticky="ew")
    ttk.Button(window, text="Отмена", command=lambda: pick(None)).grid(row=2, column=3, padx=(6, 18), pady=(0, 16), sticky="ew")
    window.protocol("WM_DELETE_WINDOW", lambda: pick(None))
    _center_window(window, root)
    window.grab_set()
    root.wait_window(window)
    return result["value"]


def choose_attachment_source(root: tk.Tk) -> str | None:
    """Show dialog asking user what type of material to add. Returns 'folder', 'github', 'files', or None."""
    result: dict[str, str | None] = {"value": None}
    window = tk.Toplevel(root)
    window.title("Добавить материал")
    window.transient(root)
    window.resizable(False, False)
    window.configure(bg="#f4f6f8")
    ttk.Label(window, text="Что добавить в KnowledgeLab?", padding=(18, 16), background="#f4f6f8").grid(row=0, column=0, columnspan=4)

    def pick(value: str | None) -> None:
        result["value"] = value
        window.destroy()

    ttk.Button(window, text="Папка", command=lambda: pick("folder")).grid(row=1, column=0, padx=(18, 6), pady=(0, 16))
    ttk.Button(window, text="GitHub", command=lambda: pick("github")).grid(row=1, column=1, padx=6, pady=(0, 16))
    ttk.Button(window, text="Файлы", command=lambda: pick("files")).grid(row=1, column=2, padx=6, pady=(0, 16))
    ttk.Button(window, text="Отмена", command=lambda: pick(None)).grid(row=1, column=3, padx=(6, 18), pady=(0, 16))
    window.protocol("WM_DELETE_WINDOW", lambda: pick(None))
    _center_window(window, root)
    window.grab_set()
    root.wait_window(window)
    return result["value"]


def confirm_install_dependencies(root: tk.Tk) -> bool:
    """Ask user to confirm npm/pnpm/yarn install in runtime folder."""
    from tkinter import messagebox
    return messagebox.askyesno(
        "Установка зависимостей",
        "Проект может потребовать npm/pnpm/yarn install в изолированной runtime-папке. Разрешить один раз для этого проекта?",
        parent=root,
    )
