"""Settings dialog UI for KnowledgeChatApp."""
from __future__ import annotations

import tkinter as tk
from tkinter import colorchooser, filedialog, ttk
from pathlib import Path
from typing import TYPE_CHECKING

from knowledgelab.config import (
    BUTTON_COLOR_PRESETS,
    DEFAULT_SETTINGS,
    DEFAULT_VAULT_DIR,
)
from knowledgelab.utils.colors import valid_hex_color, adjust_hex_color, readable_text_color
from knowledgelab.ui.settings import color_preset_name

if TYPE_CHECKING:
    from main import KnowledgeChatApp


class SettingsDialog:
    """Manages the settings dialog window and its callbacks."""

    def __init__(self, app: KnowledgeChatApp) -> None:
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
        self._build_models_section(frame)
        self._build_color_section(frame)
        self._build_automation_section(frame)
        self._build_buttons(frame)

        window.update_idletasks()
        x = self.app.root.winfo_rootx() + max(30, (self.app.root.winfo_width() - window.winfo_width()) // 2)
        y = self.app.root.winfo_rooty() + max(30, (self.app.root.winfo_height() - window.winfo_height()) // 3)
        window.geometry(f"+{x}+{y}")

    def _build_dialog_section(self, frame: ttk.Frame) -> None:
        ttk.Label(frame, text="Диалог", style="SettingsHeader.TLabel").grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 10))

        enter_check = ttk.Checkbutton(frame, text="Enter отправляет сообщение", variable=self.app.enter_send_var)
        enter_check.grid(row=1, column=0, columnspan=3, sticky="w", pady=3)
        self.app.add_tooltip(enter_check, "Нажатие Enter отправляет сообщение. Для переноса строки используйте Shift+Enter.", delay_ms=1000)

        lightrag_check = ttk.Checkbutton(frame, text="Использовать LightRAG по умолчанию", variable=self.app.lightrag_var)
        lightrag_check.grid(row=2, column=0, columnspan=3, sticky="w", pady=3)
        self.app.add_tooltip(lightrag_check, "Включает поиск по базе знаний для каждого вопроса. Выключите, чтобы общаться напрямую с LM Studio.", delay_ms=1000)

        game_guard_check = ttk.Checkbutton(frame, text="Game Guard проверяет GPU после открытия чата", variable=self.app.game_guard_var)
        game_guard_check.grid(row=3, column=0, columnspan=3, sticky="w", pady=3)
        self.app.add_tooltip(game_guard_check, "Проверяет загрузку GPU через несколько секунд после открытия чата и предупреждает о конфликтах с играми.", delay_ms=1000)

        auto_process_check = ttk.Checkbutton(frame, text="Автоматически обрабатывать сохраненные ссылки", variable=self.app.auto_process_links_var)
        auto_process_check.grid(row=4, column=0, columnspan=3, sticky="w", pady=3)
        self.app.add_tooltip(auto_process_check, "Автоматически парсит веб-страницы и синхронизирует YouTube-транскрипты после сохранения ссылки.", delay_ms=1000)

        web_search_check = ttk.Checkbutton(frame, text="Веб-поиск включен по умолчанию", variable=self.app.web_search_enabled_var)
        web_search_check.grid(row=5, column=0, columnspan=3, sticky="w", pady=3)
        self.app.add_tooltip(web_search_check, "По умолчанию включает поиск в интернете для каждого вопроса. Результаты передаются как контекст для LLM.", delay_ms=1000)

        ttk.Separator(frame, orient="horizontal").grid(row=6, column=0, columnspan=3, sticky="ew", pady=(14, 12))

    def _build_obsidian_section(self, frame: ttk.Frame) -> None:
        ttk.Label(frame, text="Obsidian", style="SettingsHeader.TLabel").grid(row=7, column=0, columnspan=3, sticky="w", pady=(0, 8))
        obsidian_entry = ttk.Entry(frame, textvariable=self.app.obsidian_path_var, width=54)
        obsidian_entry.grid(row=8, column=0, columnspan=2, sticky="ew", padx=(0, 8))
        ttk.Button(frame, text="Выбрать...", command=self.choose_obsidian_path).grid(row=8, column=2, sticky="e")
        ttk.Label(frame, text="Vault folder", background="#f4f6f8").grid(row=9, column=0, columnspan=3, sticky="w", pady=(10, 4))
        vault_entry = ttk.Entry(frame, textvariable=self.app.vault_path_var, width=54)
        vault_entry.grid(row=10, column=0, columnspan=2, sticky="ew", padx=(0, 8))
        ttk.Button(frame, text="Выбрать...", command=self.choose_vault_path).grid(row=10, column=2, sticky="e")

        ttk.Separator(frame, orient="horizontal").grid(row=11, column=0, columnspan=3, sticky="ew", pady=(14, 12))

    def _build_models_section(self, frame: ttk.Frame) -> None:
        ttk.Label(frame, text="Модели LM Studio", style="SettingsHeader.TLabel").grid(row=12, column=0, columnspan=3, sticky="w", pady=(0, 8))

        models = self._fetch_lmstudio_models()

        ttk.Label(frame, text="LLM (чат, код, текст)", background="#f4f6f8").grid(row=13, column=0, columnspan=3, sticky="w")
        llm_combo = ttk.Combobox(frame, textvariable=self.app.llm_model_var, values=models, width=52)
        llm_combo.grid(row=14, column=0, columnspan=3, sticky="ew", pady=(0, 6))

        ttk.Label(frame, text="Vision (фото, OCR)", background="#f4f6f8").grid(row=15, column=0, columnspan=3, sticky="w")
        vision_combo = ttk.Combobox(frame, textvariable=self.app.vision_model_var, values=models, width=52)
        vision_combo.grid(row=16, column=0, columnspan=3, sticky="ew", pady=(0, 6))

        ttk.Label(frame, text="Embeddings (поиск по базе)", background="#f4f6f8").grid(row=17, column=0, columnspan=3, sticky="w")
        embed_combo = ttk.Combobox(frame, textvariable=self.app.embedding_model_var, values=models, width=52)
        embed_combo.grid(row=18, column=0, columnspan=3, sticky="ew", pady=(0, 6))

        auto_switch_check = ttk.Checkbutton(frame, text="Автопереключение моделей", variable=self.app.auto_switch_models_var)
        auto_switch_check.grid(row=19, column=0, columnspan=3, sticky="w", pady=3)
        self.app.add_tooltip(auto_switch_check, "KnowledgeLab автоматически загружает нужную модель перед каждым запросом. Отключите, если хотите переключать модели вручную в LM Studio.", delay_ms=1000)

        ttk.Separator(frame, orient="horizontal").grid(row=20, column=0, columnspan=3, sticky="ew", pady=(14, 12))

    def _fetch_lmstudio_models(self) -> list[str]:
        """Fetch available model IDs from LM Studio API."""
        import urllib.request
        import json
        base_url = str(self.app.settings.get("lmstudio_base_url", "") or "").rstrip("/")
        if not base_url:
            return []
        try:
            url = f"{base_url}/v1/models"
            request = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(request, timeout=5) as response:
                data = json.loads(response.read(50_000).decode("utf-8"))
                models = [m.get("id", "") for m in data.get("data", []) if m.get("id")]
                return sorted(models)
        except Exception:
            return []

    def _build_color_section(self, frame: ttk.Frame) -> None:
        ttk.Label(frame, text="Цвет основной кнопки", style="SettingsHeader.TLabel").grid(row=21, column=0, columnspan=3, sticky="w", pady=(0, 10))
        preset_var = tk.StringVar(value=color_preset_name(self.app.button_color_var.get()))
        preset = ttk.Combobox(frame, textvariable=preset_var, values=list(BUTTON_COLOR_PRESETS.keys()), state="readonly", width=18)
        preset.grid(row=22, column=0, sticky="w", padx=(0, 10))
        preset.bind("<<ComboboxSelected>>", lambda _event: self.select_color_preset(preset_var.get()))
        self.color_preview = tk.Label(frame, width=6, height=1, background=self.app.button_color_var.get(), relief="solid", borderwidth=1)
        self.color_preview.grid(row=22, column=1, sticky="w", padx=(0, 10))
        ttk.Button(frame, text="Выбрать...", command=self.choose_button_color).grid(row=22, column=2, sticky="e")

        ttk.Separator(frame, orient="horizontal").grid(row=23, column=0, columnspan=3, sticky="ew", pady=(14, 12))

    def _build_automation_section(self, frame: ttk.Frame) -> None:
        ttk.Label(frame, text="Автоматизация", style="SettingsHeader.TLabel").grid(row=24, column=0, columnspan=3, sticky="w", pady=(0, 8))

        auto_route_check = ttk.Checkbutton(frame, text="Автоматически распределять материалы по темам", variable=self.app.auto_route_topics_var)
        auto_route_check.grid(row=25, column=0, columnspan=3, sticky="w", pady=3)
        self.app.add_tooltip(auto_route_check, "KnowledgeLab сам выбирает тему и проект для новых материалов, а потом показывает в чате отчёт, куда всё разложено.", delay_ms=1000)

        auto_create_check = ttk.Checkbutton(frame, text="Автоматически создавать новые темы", variable=self.app.auto_create_topics_var)
        auto_create_check.grid(row=26, column=0, columnspan=3, sticky="w", pady=3)
        self.app.add_tooltip(auto_create_check, "Если подходящей темы ещё нет, будет создана папка Topics/<тема> и служебная заметка _Topic.md.", delay_ms=1000)

        auto_books_check = ttk.Checkbutton(frame, text="Автоматически искать книги по фото", variable=self.app.auto_detect_books_var)
        auto_books_check.grid(row=27, column=0, columnspan=3, sticky="w", pady=3)
        self.app.add_tooltip(auto_books_check, "Для фото книжной полки или обложки локальная vision-модель пытается прочитать корешки/названия и добавить найденные книги в 50 Library.", delay_ms=1000)

        book_lookup_check = ttk.Checkbutton(frame, text="Обогащать книги через онлайн-каталоги", variable=self.app.book_lookup_enabled_var)
        book_lookup_check.grid(row=28, column=0, columnspan=3, sticky="w", pady=3)
        self.app.add_tooltip(book_lookup_check, "Онлайн-каталоги помогают уточнить автора, ISBN, обложку и год. Сейчас используются Open Library (открытый книжный каталог Internet Archive) и Google Books. Если совпадение слабое, чат попросит уточнить книгу.", delay_ms=1000)

    def _build_buttons(self, frame: ttk.Frame) -> None:
        ttk.Label(frame, textvariable=self.app.settings_status_var, style="SettingsStatus.TLabel").grid(row=29, column=0, columnspan=3, sticky="w", pady=(14, 0))
        buttons = ttk.Frame(frame, style="App.TFrame")
        buttons.grid(row=30, column=0, columnspan=3, sticky="ew", pady=(16, 0))
        ttk.Button(buttons, text="Сбросить настройки", command=self.reset).grid(row=0, column=0, sticky="w")
        ttk.Button(buttons, text="Отмена", command=self.close).grid(row=0, column=1, padx=(0, 8))
        ttk.Button(buttons, text="Сохранить", command=self.save).grid(row=0, column=2)

    def save(self) -> None:
        """Save settings from dialog to app settings."""
        self.app.settings["send_on_enter"] = bool(self.app.enter_send_var.get())
        self.app.settings["use_lightrag"] = bool(self.app.lightrag_var.get())
        self.app.settings["button_color"] = valid_hex_color(self.app.button_color_var.get(), DEFAULT_SETTINGS["button_color"])
        self.app.settings["game_guard_enabled"] = bool(self.app.game_guard_var.get())
        self.app.settings["auto_process_links"] = bool(self.app.auto_process_links_var.get())
        self.app.settings["auto_route_topics"] = bool(self.app.auto_route_topics_var.get())
        self.app.settings["auto_create_topics"] = bool(self.app.auto_create_topics_var.get())
        self.app.settings["auto_detect_books_in_images"] = bool(self.app.auto_detect_books_var.get())
        self.app.settings["book_lookup_enabled"] = bool(self.app.book_lookup_enabled_var.get())
        self.app.settings["web_search_enabled"] = bool(self.app.web_search_enabled_var.get())
        self.app.settings["obsidian_path"] = self.app.obsidian_path_var.get().strip()
        self.app.settings["vault_path"] = self.app.vault_path_var.get().strip() or str(DEFAULT_VAULT_DIR)
        self.app.settings["llm_model"] = self.app.llm_model_var.get().strip()
        self.app.settings["vision_model"] = self.app.vision_model_var.get().strip()
        self.app.settings["embedding_model"] = self.app.embedding_model_var.get().strip()
        self.app.settings["auto_switch_models"] = bool(self.app.auto_switch_models_var.get())
        self.app.save_settings()
        import main as _main
        _main.VAULT_DIR = self.app.vault_dir()
        self.app.apply_settings_to_ui()
        self.app.status_var.set("Settings saved")
        if bool(self.app.settings["game_guard_enabled"]):
            self.app.schedule_game_guard_probe()
        self.close()

    def reset(self) -> None:
        """Reset settings to defaults."""
        self.app.enter_send_var.set(bool(DEFAULT_SETTINGS["send_on_enter"]))
        self.app.lightrag_var.set(bool(DEFAULT_SETTINGS["use_lightrag"]))
        self.app.game_guard_var.set(bool(DEFAULT_SETTINGS["game_guard_enabled"]))
        self.app.auto_process_links_var.set(bool(DEFAULT_SETTINGS.get("auto_process_links", True)))
        self.app.auto_route_topics_var.set(bool(DEFAULT_SETTINGS.get("auto_route_topics", True)))
        self.app.auto_create_topics_var.set(bool(DEFAULT_SETTINGS.get("auto_create_topics", True)))
        self.app.auto_detect_books_var.set(bool(DEFAULT_SETTINGS.get("auto_detect_books_in_images", True)))
        self.app.book_lookup_enabled_var.set(bool(DEFAULT_SETTINGS.get("book_lookup_enabled", True)))
        self.app.web_search_enabled_var.set(bool(DEFAULT_SETTINGS.get("web_search_enabled", False)))
        self.app.button_color_var.set(str(DEFAULT_SETTINGS["button_color"]))
        self.app.obsidian_path_var.set("")
        self.app.vault_path_var.set(str(DEFAULT_VAULT_DIR))
        self.app.llm_model_var.set(str(DEFAULT_SETTINGS.get("llm_model", "")))
        self.app.vision_model_var.set(str(DEFAULT_SETTINGS.get("vision_model", "")))
        self.app.embedding_model_var.set(str(DEFAULT_SETTINGS.get("embedding_model", "")))
        self.app.auto_switch_models_var.set(bool(DEFAULT_SETTINGS.get("auto_switch_models", True)))
        self.app.settings_status_var.set("Настройки сброшены до значений по умолчанию.")
        if self.color_preview:
            self.color_preview.configure(background=self.app.button_color_var.get())

    def choose_obsidian_path(self) -> None:
        """Open file dialog for Obsidian path."""
        path = filedialog.askopenfilename(
            title="Выберите Obsidian.exe",
            filetypes=[("Obsidian", "Obsidian.exe *.lnk"), ("Programs", "*.exe"), ("Shortcuts", "*.lnk"), ("All files", "*.*")],
            parent=self.window or self.app.root,
        )
        if path:
            self.app.obsidian_path_var.set(path)

    def choose_vault_path(self) -> None:
        """Open directory dialog for vault path."""
        path = filedialog.askdirectory(
            title="Выберите папку Obsidian vault",
            initialdir=str(self.app.vault_dir() if self.app.vault_dir().exists() else DEFAULT_VAULT_DIR),
            parent=self.window or self.app.root,
        )
        if path:
            self.app.vault_path_var.set(path)

    def select_color_preset(self, preset_name: str) -> None:
        """Apply a color preset."""
        color = BUTTON_COLOR_PRESETS.get(preset_name)
        if color:
            self.app.button_color_var.set(color)
            self.update_color_preview(color)

    def update_color_preview(self, color: str) -> None:
        """Update the color preview label."""
        if self.color_preview:
            self.color_preview.configure(background=valid_hex_color(color, DEFAULT_SETTINGS["button_color"]))

    def choose_button_color(self) -> None:
        """Open color chooser dialog."""
        _rgb, color = colorchooser.askcolor(
            color=valid_hex_color(self.app.button_color_var.get(), DEFAULT_SETTINGS["button_color"]),
            parent=self.window or self.app.root,
            title="Цвет основной кнопки",
        )
        if color:
            self.app.button_color_var.set(valid_hex_color(color, DEFAULT_SETTINGS["button_color"]))
            self.update_color_preview(self.app.button_color_var.get())

    def apply_to_ui(self) -> None:
        """Apply current settings to the main UI."""
        self.app.enter_send_var.set(bool(self.app.settings["send_on_enter"]))
        self.app.lightrag_var.set(bool(self.app.settings["use_lightrag"]))
        self.app.game_guard_var.set(bool(self.app.settings["game_guard_enabled"]))
        self.app.auto_process_links_var.set(bool(self.app.settings.get("auto_process_links", True)))
        self.app.auto_route_topics_var.set(bool(self.app.settings.get("auto_route_topics", True)))
        self.app.auto_create_topics_var.set(bool(self.app.settings.get("auto_create_topics", True)))
        self.app.auto_detect_books_var.set(bool(self.app.settings.get("auto_detect_books_in_images", True)))
        self.app.book_lookup_enabled_var.set(bool(self.app.settings.get("book_lookup_enabled", True)))
        self.app.web_search_enabled_var.set(bool(self.app.settings.get("web_search_enabled", False)))
        self.app.button_color_var.set(str(self.app.settings["button_color"]))
        self.app.obsidian_path_var.set(str(self.app.settings.get("obsidian_path", "")))
        self.app.vault_path_var.set(str(self.app.settings.get("vault_path", str(DEFAULT_VAULT_DIR))))
        self.app.update_button_colors()
        self.app.update_web_search_button()
        self.app.on_lightrag_toggle(save=False)

    def update_button_colors(self, color: str | None = None) -> None:
        """Update all button colors."""
        color = color or valid_hex_color(str(self.app.settings["button_color"]), DEFAULT_SETTINGS["button_color"])
        fg = readable_text_color(color)
        active_bg = adjust_hex_color(color, 0.86)
        self.app.send_button.set_colors(bg=color, active_bg=active_bg, fg=fg)

    def update_web_search_button(self) -> None:
        """Update web search toggle button state."""
        if hasattr(self.app, "web_search_button"):
            self.app.web_search_button.set_active(bool(self.app.settings.get("web_search_enabled", False)))
