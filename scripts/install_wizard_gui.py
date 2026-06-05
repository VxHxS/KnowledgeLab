from __future__ import annotations

import subprocess
import threading
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import messagebox, ttk


ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "scripts" / "install-knowledge-lab.ps1"
REPORT = ROOT / "INSTALL_REPORT.md"
LIGHTRAG_GITHUB = "https://github.com/HKUDS/LightRAG"
LIGHTRAG_PYPI = "https://pypi.org/project/lightrag-hku/"


COMPONENT_DESCRIPTIONS = {
    "core": (
        "Python venv and core packages. Includes LightRAG (`lightrag-hku`), OpenAI client, "
        "numpy, tiktoken and vector storage dependencies."
    ),
    "youtube": "YouTube transcript support through yt-dlp. Uses captions/auto-captions when available.",
    "telegram": "Telegram Desktop JSON export importer with ad/noise filtering for public channels.",
    "shortcuts": "Clean Desktop launchers: only LightRAG-Chat and LightRAG-Control. Working logic stays in KnowledgeLab folders.",
    "manual": "Checks external apps that are usually installed manually: LM Studio, Obsidian, Telegram Desktop, Git and FFmpeg.",
}


class InstallerWizard:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("AI Knowledge Lab Setup")
        self.root.geometry("720x520")
        self.root.minsize(680, 500)
        self.root.configure(bg="#f0f0f0")

        self.page_index = 0
        self.pages = ["welcome", "components", "install", "finish"]
        self.install_finished = False
        self.install_output = ""

        self.install_packages_var = tk.BooleanVar(value=True)
        self.youtube_var = tk.BooleanVar(value=True)
        self.telegram_var = tk.BooleanVar(value=True)
        self.shortcuts_var = tk.BooleanVar(value=True)
        self.manual_checks_var = tk.BooleanVar(value=True)

        self.build_ui()
        self.show_page()

    def build_ui(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        self.header = tk.Frame(self.root, bg="#ffffff", height=74)
        self.header.grid(row=0, column=0, sticky="ew")
        self.header.columnconfigure(0, weight=1)
        self.title_label = tk.Label(
            self.header,
            text="AI Knowledge Lab Setup",
            bg="#ffffff",
            fg="#111111",
            font=("Segoe UI Semibold", 12),
            anchor="w",
            padx=18,
        )
        self.title_label.grid(row=0, column=0, sticky="ew", pady=(12, 0))
        self.subtitle_label = tk.Label(
            self.header,
            text="",
            bg="#ffffff",
            fg="#333333",
            font=("Segoe UI", 9),
            anchor="w",
            padx=18,
        )
        self.subtitle_label.grid(row=1, column=0, sticky="ew", pady=(4, 12))

        self.content = tk.Frame(self.root, bg="#f0f0f0")
        self.content.grid(row=1, column=0, sticky="nsew", padx=18, pady=16)
        self.content.columnconfigure(0, weight=1)
        self.content.rowconfigure(0, weight=1)

        footer = tk.Frame(self.root, bg="#f0f0f0")
        footer.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 10))
        footer.columnconfigure(0, weight=1)

        self.product_label = tk.Label(
            footer,
            text="AI Knowledge Lab for Windows",
            bg="#f0f0f0",
            fg="#777777",
            font=("Segoe UI", 8),
        )
        self.product_label.grid(row=0, column=0, sticky="w", padx=(0, 10))

        self.back_button = tk.Button(footer, text="< Back", width=12, command=self.back)
        self.back_button.grid(row=0, column=1, padx=4)
        self.next_button = tk.Button(footer, text="Next >", width=12, command=self.next)
        self.next_button.grid(row=0, column=2, padx=4)
        self.cancel_button = tk.Button(footer, text="Cancel", width=12, command=self.cancel)
        self.cancel_button.grid(row=0, column=3, padx=(4, 0))

    def clear_content(self) -> None:
        for child in self.content.winfo_children():
            child.destroy()

    def show_page(self) -> None:
        self.clear_content()
        page = self.pages[self.page_index]
        if page == "welcome":
            self.show_welcome()
        elif page == "components":
            self.show_components()
        elif page == "install":
            self.show_install()
        else:
            self.show_finish()
        self.update_buttons()

    def update_buttons(self) -> None:
        page = self.pages[self.page_index]
        self.back_button.configure(state="normal" if self.page_index > 0 and page != "install" else "disabled")
        if page == "install":
            self.next_button.configure(text="Next >", state="normal" if self.install_finished else "disabled")
        elif page == "finish":
            self.next_button.configure(text="Finish", state="normal")
        else:
            self.next_button.configure(text="Next >", state="normal")

    def show_welcome(self) -> None:
        self.title_label.configure(text="Welcome to AI Knowledge Lab Setup")
        self.subtitle_label.configure(text="This wizard installs and checks the local Obsidian + LightRAG + LM Studio system.")
        text = (
            "Setup will check your computer, prepare the local Python environment, install selected "
            "Python packages, copy desktop launchers and write an INSTALL_REPORT.md file.\n\n"
            "Apps like LM Studio, Obsidian and Telegram Desktop are checked here, but if they are missing "
            "the installer will tell you what to install manually."
        )
        label = tk.Label(
            self.content,
            text=text,
            bg="#f0f0f0",
            fg="#111111",
            justify="left",
            anchor="nw",
            font=("Segoe UI", 10),
            wraplength=640,
        )
        label.grid(row=0, column=0, sticky="nsew")

    def show_components(self) -> None:
        self.title_label.configure(text="Choose Components")
        self.subtitle_label.configure(text="Choose which parts of AI Knowledge Lab you want to install or check.")
        frame = tk.Frame(self.content, bg="#f0f0f0")
        frame.grid(row=0, column=0, sticky="nsew")
        frame.columnconfigure(1, weight=1)

        tk.Label(frame, text="Select components to install:", bg="#f0f0f0", font=("Segoe UI", 9)).grid(
            row=0, column=0, sticky="nw", padx=(0, 12), pady=(8, 0)
        )
        box = tk.Frame(frame, bg="#ffffff", relief="sunken", borderwidth=1)
        box.grid(row=0, column=1, sticky="nsew")
        box.columnconfigure(0, weight=1)

        self.add_component(box, 0, "LightRAG core + Python packages", self.install_packages_var, "core")
        self.add_component(box, 1, "YouTube transcripts (yt-dlp)", self.youtube_var, "youtube")
        self.add_component(box, 2, "Telegram import and ad filter", self.telegram_var, "telegram")
        self.add_component(box, 3, "Desktop shortcuts", self.shortcuts_var, "shortcuts")
        self.add_component(box, 4, "Check manual apps and models", self.manual_checks_var, "manual")

        tk.Label(frame, text="Description", bg="#f0f0f0", font=("Segoe UI", 9)).grid(
            row=1, column=1, sticky="w", pady=(10, 0)
        )
        self.description = tk.Text(frame, height=5, wrap="word", relief="sunken", borderwidth=1, font=("Segoe UI", 9))
        self.description.grid(row=2, column=1, sticky="ew")
        self.description.insert("1.0", COMPONENT_DESCRIPTIONS["core"])
        self.description.configure(state="disabled")

        links = tk.Frame(frame, bg="#f0f0f0")
        links.grid(row=3, column=1, sticky="w", pady=(10, 0))
        tk.Button(links, text="Open LightRAG GitHub", command=lambda: webbrowser.open(LIGHTRAG_GITHUB)).grid(row=0, column=0, padx=(0, 8))
        tk.Button(links, text="Open lightrag-hku PyPI", command=lambda: webbrowser.open(LIGHTRAG_PYPI)).grid(row=0, column=1)

    def add_component(self, parent: tk.Widget, row: int, text: str, variable: tk.BooleanVar, key: str) -> None:
        item = tk.Checkbutton(
            parent,
            text=text,
            variable=variable,
            bg="#ffffff",
            activebackground="#ffffff",
            anchor="w",
            font=("Segoe UI", 9),
            padx=8,
            pady=2,
        )
        item.grid(row=row, column=0, sticky="ew")
        item.bind("<Enter>", lambda _event, k=key: self.set_description(k))
        item.bind("<FocusIn>", lambda _event, k=key: self.set_description(k))

    def set_description(self, key: str) -> None:
        if not hasattr(self, "description"):
            return
        self.description.configure(state="normal")
        self.description.delete("1.0", "end")
        self.description.insert("1.0", COMPONENT_DESCRIPTIONS[key])
        self.description.configure(state="disabled")

    def show_install(self) -> None:
        self.title_label.configure(text="Installing")
        self.subtitle_label.configure(text="Setup is checking and preparing the selected components.")
        self.output = tk.Text(self.content, wrap="word", relief="sunken", borderwidth=1, font=("Consolas", 9))
        self.output.grid(row=0, column=0, sticky="nsew")
        if not self.install_finished and not self.install_output:
            self.start_install()
        else:
            self.output.insert("1.0", self.install_output)

    def show_finish(self) -> None:
        self.title_label.configure(text="Setup Complete")
        self.subtitle_label.configure(text="AI Knowledge Lab setup has finished.")
        frame = tk.Frame(self.content, bg="#f0f0f0")
        frame.grid(row=0, column=0, sticky="nsew")
        frame.columnconfigure(0, weight=1)
        report_text = f"Report: {REPORT}" if REPORT.exists() else "Report will be created after a non-dry setup run."
        tk.Label(
            frame,
            text=f"Setup has completed.\n\n{report_text}\n\nMain launcher:\n{Path.home() / 'Desktop' / 'LightRag' / 'LightRAG-Chat.cmd'}",
            bg="#f0f0f0",
            fg="#111111",
            justify="left",
            anchor="nw",
            font=("Segoe UI", 10),
            wraplength=640,
        ).grid(row=0, column=0, sticky="nw")

        manual_steps = self.read_manual_steps()
        manual_box = tk.Frame(frame, bg="#ffffff", highlightthickness=1, highlightbackground="#cfd4da")
        manual_box.grid(row=1, column=0, sticky="ew", pady=(16, 0))
        manual_box.columnconfigure(0, weight=1)
        tk.Label(
            manual_box,
            text="Что поставить руками",
            bg="#ffffff",
            fg="#1f2933",
            font=("Segoe UI Semibold", 10),
            anchor="w",
            padx=10,
            pady=6,
        ).grid(row=0, column=0, sticky="ew")
        tk.Label(
            manual_box,
            text="\n".join(manual_steps),
            bg="#ffffff",
            fg="#374151",
            justify="left",
            anchor="nw",
            font=("Segoe UI", 9),
            wraplength=620,
            padx=10,
            pady=8,
        ).grid(row=1, column=0, sticky="ew")

        tk.Button(frame, text="Open report", command=self.open_report).grid(row=2, column=0, sticky="w", pady=(18, 0))

    def read_manual_steps(self) -> list[str]:
        if not REPORT.exists():
            return ["- Отчет еще не создан. Запусти установку, чтобы увидеть список ручных шагов."]

        text = REPORT.read_text(encoding="utf-8-sig", errors="replace")
        lines = text.splitlines()
        steps: list[str] = []
        in_manual = False
        for line in lines:
            stripped = line.strip()
            if stripped == "## Manual steps":
                in_manual = True
                continue
            if in_manual and stripped.startswith("## "):
                break
            if in_manual and stripped.startswith("- "):
                steps.append(stripped)

        if not steps or steps == ["- None."]:
            return ["- Ничего обязательного. Все найдено или уже установлено."]
        return steps

    def start_install(self) -> None:
        self.install_finished = False
        self.update_buttons()
        thread = threading.Thread(target=self.run_installer, daemon=True)
        thread.start()

    def run_installer(self) -> None:
        flags: list[str] = []
        if self.install_packages_var.get():
            flags.append("-InstallCorePackages")
        else:
            flags.append("-SkipPythonPackages")
        if self.youtube_var.get():
            flags.append("-InstallYoutubePackages")
        if self.telegram_var.get():
            flags.append("-InstallTelegramPackages")
        if not self.shortcuts_var.get():
            flags.append("-NoDesktopLaunchers")

        command = [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(INSTALLER),
            *flags,
        ]
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            result = subprocess.run(
                command,
                cwd=str(ROOT),
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                creationflags=creationflags,
            )
            output = "\n".join(part for part in (result.stdout.strip(), result.stderr.strip()) if part)
            if result.returncode != 0:
                output = f"Setup returned exit code {result.returncode}\n\n{output}"
        except Exception as exc:
            output = f"ERROR: {exc}"
        self.root.after(0, self.finish_install, output)

    def finish_install(self, output: str) -> None:
        self.install_output = output
        self.install_finished = True
        self.output.delete("1.0", "end")
        self.output.insert("1.0", output)
        self.update_buttons()

    def next(self) -> None:
        page = self.pages[self.page_index]
        if page == "finish":
            self.root.destroy()
            return
        if page == "components" and not self.install_packages_var.get():
            if not messagebox.askyesno(
                "LightRAG core",
                "LightRAG core packages are unchecked. Continue without installing Python packages?",
            ):
                return
        if self.page_index < len(self.pages) - 1:
            self.page_index += 1
            self.show_page()

    def back(self) -> None:
        if self.page_index > 0:
            self.page_index -= 1
            self.show_page()

    def cancel(self) -> None:
        if messagebox.askyesno("Cancel Setup", "Cancel AI Knowledge Lab setup?"):
            self.root.destroy()

    def open_report(self) -> None:
        if REPORT.exists():
            subprocess.Popen(["notepad", str(REPORT)])
        else:
            messagebox.showinfo("Report", "INSTALL_REPORT.md has not been created yet.")


def main() -> None:
    root = tk.Tk()
    try:
        ttk.Style().theme_use("vista")
    except tk.TclError:
        pass
    InstallerWizard(root)
    root.mainloop()


if __name__ == "__main__":
    main()
