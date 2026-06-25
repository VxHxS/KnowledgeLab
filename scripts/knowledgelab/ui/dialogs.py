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


def ask_duplicate_resolution(root: tk.Tk, duplicates: list[tuple[str, list[dict[str, str]]]]) -> str:
    """Ask user how to handle detected duplicate files.

    Args:
        root: parent window
        duplicates: list of (source_name, existing_captures) tuples

    Returns:
        "skip" — skip all duplicates
        "save" — save all anyway (create copies)
        "cancel" — cancel entire import
    """
    result: dict[str, str] = {"value": "save"}
    window = tk.Toplevel(root)
    window.title("Обнаружены дубликаты")
    window.transient(root)
    window.resizable(False, False)
    window.configure(bg="#f4f6f8")

    header = f"Найдено дубликатов: {len(duplicates)}"
    ttk.Label(window, text=header, padding=(18, 12), background="#f4f6f8", font=("Segoe UI Semibold", 10)).grid(row=0, column=0, columnspan=3, sticky="w")

    list_frame = tk.Frame(window, bg="#f4f6f8")
    list_frame.grid(row=1, column=0, columnspan=3, padx=18, sticky="ew")

    canvas = tk.Canvas(list_frame, bg="#ffffff", highlightthickness=1, highlightbackground="#d0d5dd", height=min(200, 40 * len(duplicates)))
    scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
    inner = tk.Frame(canvas, bg="#ffffff")
    inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=inner, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    row = 0
    for source_name, captures in duplicates[:10]:
        name_label = tk.Label(inner, text=source_name, bg="#ffffff", fg="#1f2933", font=("Segoe UI", 9), anchor="w")
        name_label.grid(row=row, column=0, padx=(8, 12), pady=2, sticky="w")
        existing = captures[0] if captures else {}
        detail = existing.get("rel_path", "")
        if len(captures) > 1:
            detail += f" (+{len(captures) - 1} more)"
        detail_label = tk.Label(inner, text=detail, bg="#ffffff", fg="#6b7280", font=("Segoe UI", 8), anchor="w")
        detail_label.grid(row=row, column=1, padx=(0, 8), pady=2, sticky="w")
        row += 1

    if len(duplicates) > 10:
        more_label = tk.Label(inner, text=f"... и ещё {len(duplicates) - 10}", bg="#ffffff", fg="#6b7280", font=("Segoe UI", 8))
        more_label.grid(row=row, column=0, columnspan=2, padx=8, pady=2, sticky="w")

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    list_frame.grid_columnconfigure(0, weight=1)

    hint = "Эти файлы уже были импортированы в проект."
    ttk.Label(window, text=hint, padding=(18, 6), background="#f4f6f8", foreground="#6b7280").grid(row=2, column=0, columnspan=3, sticky="w")

    def pick(value: str) -> None:
        result["value"] = value
        window.destroy()

    btn_frame = tk.Frame(window, bg="#f4f6f8")
    btn_frame.grid(row=3, column=0, columnspan=3, pady=(6, 16))
    ttk.Button(btn_frame, text="Пропустить дубликаты", command=lambda: pick("skip")).pack(side="left", padx=(18, 6))
    ttk.Button(btn_frame, text="Сохранить как копии", command=lambda: pick("save")).pack(side="left", padx=6)
    ttk.Button(btn_frame, text="Отменить всё", command=lambda: pick("cancel")).pack(side="left", padx=(6, 18))

    window.protocol("WM_DELETE_WINDOW", lambda: pick("cancel"))
    _center_window(window, root)
    window.grab_set()
    root.wait_window(window)
    return result["value"]
