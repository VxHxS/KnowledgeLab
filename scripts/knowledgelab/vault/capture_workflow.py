"""File capture and attachment workflow."""
from __future__ import annotations

import datetime as dt
import tkinter as tk
from tkinter import filedialog, simpledialog
from pathlib import Path
from typing import TYPE_CHECKING

from knowledgelab.config import (
    VAULT_DIR, ROOT, LAYER_ACTIVE, IMAGE_EXTENSIONS, IMAGE_FILETYPES,
    SUPPORTED_FILETYPES, FOLDER_FILE_SCAN_LIMIT, DEFAULT_SETTINGS,
)
from knowledgelab.models import KnowledgeRoute, MaterialRoutingReport, BookDiscoveryReport, ManualBookEntry, ReferenceLink
from knowledgelab.utils.text import clean_filename
from knowledgelab.utils.urls import (
    first_github_url, first_codepen_url, first_youtube_url, first_telegram_url, first_url,
    parse_github_url, normalize_github_url,
)
from knowledgelab.utils.paths import normalize_attached_source_path
from knowledgelab.routing.intent import infer_kind, infer_topic
from knowledgelab.routing.topics import classify_material_topic as _classify_material_topic, ensure_topic_exists as _ensure_topic_exists
from knowledgelab.vault.frontmatter import find_existing_source_note, find_existing_file_capture
from knowledgelab.vault.capture import (
    unique_path, capture_destination, render_capture_markdown,
    render_github_capture_markdown, render_reference_link_markdown,
    render_file_capture_markdown, render_folder_capture_markdown,
    file_kind_label, title_from_text, classify_source_file,
)
from knowledgelab.utils.text import extract_lightweight_file_text
from knowledgelab.vision.book_discovery import (
    infer_image_capture_kind, infer_book_title_from_hint, infer_page_number_guess,
    classify_book_topic, merge_book_lookup, render_manual_book_list_markdown,
    render_manual_book_resolution_section, save_detected_book_notes as _save_detected_book_notes,
)
from knowledgelab.material.queue import queue_file_item, queue_github_item, queue_rlm_item
from knowledgelab.material.web import collect_local_folder_files, summarize_local_folder

if TYPE_CHECKING:
    from main import KnowledgeChatApp


class CaptureWorkflow:
    """Manages file capture, attachment, and intake workflows."""

    def __init__(self, app: KnowledgeChatApp) -> None:
        self.app = app

    def save_file_capture(
        self,
        file_path: Path,
        caption: str,
        route: KnowledgeRoute,
        source_root: Path | None = None,
        project_action_id: str = "",
    ) -> tuple[str, str, str]:
        """Save a single file as a capture note."""
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        if file_path.is_dir():
            return self.save_folder_capture(file_path, caption, route)
        context_name = route.context_name
        scope = route.scope
        project = route.project
        kind = classify_source_file(file_path)
        book_title = ""
        page_number_guess = ""
        if kind == "image_capture":
            kind = infer_image_capture_kind(file_path, caption)
            if kind in {"book_photo", "book_page_photo"}:
                book_title = infer_book_title_from_hint(caption, file_path)
                page_number_guess = infer_page_number_guess(caption, file_path)
            elif kind == "bookshelf_photo":
                book_title = infer_book_title_from_hint(caption, file_path)
                if not book_title or book_title == clean_filename(file_path.stem):
                    book_title = "Bookshelf Intake"
        source_relative_path = ""
        if source_root:
            try:
                source_relative_path = file_path.relative_to(source_root).as_posix()
            except ValueError:
                source_relative_path = file_path.name
        extracted_text, extraction_status = extract_lightweight_file_text(file_path, kind)
        hint = f"{caption} {source_root.name if source_root else ''} {source_relative_path} {file_path.stem} {file_path.suffix} {extracted_text[:2400]}".strip()
        topic = self.app.classify_material_topic(hint, scope, kind, infer_topic(hint, scope), preferred_topic=book_title, project=project)
        if kind in {"book_photo", "book_page_photo", "bookshelf_photo"}:
            topic = book_title
        if scope == "general" and not caption.strip() and topic == "General":
            topic = ""
        destination = capture_destination(scope, topic, kind, route.layer, project, route.project_section)
        destination.mkdir(parents=True, exist_ok=True)
        if source_root and source_relative_path:
            title_seed = f"{route.project_title or source_root.name} - {source_relative_path}"
        else:
            title_seed = route.project_title or caption.strip() or file_path.stem
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
                route.layer,
                route.project_title,
                route.project_section,
                source_root,
                source_relative_path,
                project_action_id,
                book_title,
                page_number_guess,
            ),
            encoding="utf-8-sig",
        )
        rel_path = path.relative_to(VAULT_DIR).as_posix()
        self.app.queue_file_processing(
            file_path,
            rel_path,
            kind,
            scope,
            project,
            topic,
            extraction_status,
            route.layer,
            route.project_title,
            route.project_section,
            source_root,
            source_relative_path,
            project_action_id,
            book_title,
            page_number_guess,
        )
        return rel_path, kind, extraction_status

    def save_folder_file_captures(self, folder_path: Path, caption: str, route: KnowledgeRoute, project_action_id: str = "") -> tuple[list[tuple[str, str, str, Path]], bool]:
        """Save all files in a folder as capture notes."""
        if not folder_path.is_dir():
            raise NotADirectoryError(f"Folder not found: {folder_path}")
        files, scan_complete = collect_local_folder_files(folder_path)
        if not files:
            return [], scan_complete
        results: list[tuple[str, str, str, Path]] = []
        for file_path in files:
            rel_path, kind, extraction_status = self.save_file_capture(file_path, caption, route, source_root=folder_path, project_action_id=project_action_id)
            results.append((rel_path, kind, extraction_status, file_path))
        return results, scan_complete

    def save_folder_capture(self, folder_path: Path, caption: str, route: KnowledgeRoute) -> tuple[str, str, str]:
        """Save a folder as a capture note."""
        if not folder_path.is_dir():
            raise NotADirectoryError(f"Folder not found: {folder_path}")
        context_name = route.context_name
        scope = route.scope
        project = route.project
        kind = "folder_source"
        hint = f"{caption} {folder_path.name}".strip()
        topic = self.app.classify_material_topic(hint, scope, kind, infer_topic(hint, scope), project=project)
        if scope == "general" and not caption.strip() and topic == "General":
            topic = ""
        extracted_text, extraction_status, stats = summarize_local_folder(folder_path)
        destination = capture_destination(scope, topic, kind, route.layer, project, route.project_section)
        destination.mkdir(parents=True, exist_ok=True)
        title_seed = route.project_title or caption.strip() or folder_path.name
        if topic:
            title_seed = f"{topic} - {title_seed}"
        path = unique_path(destination / f"{clean_filename(title_seed)}.md")
        path.write_text(
            render_folder_capture_markdown(
                folder_path,
                caption,
                context_name,
                scope,
                project,
                topic,
                extracted_text,
                extraction_status,
                stats,
                route.layer,
                route.project_title,
                route.project_section,
            ),
            encoding="utf-8-sig",
        )
        rel_path = path.relative_to(VAULT_DIR).as_posix()
        self.app.queue_file_processing(folder_path, rel_path, kind, scope, project, topic, extraction_status, route.layer, route.project_title, route.project_section)
        return rel_path, kind, extraction_status

    def save_image_capture(self, image_path: Path, caption: str, route: KnowledgeRoute) -> str:
        """Save an image as a capture note."""
        if image_path.suffix.lower() not in IMAGE_EXTENSIONS:
            raise ValueError(f"Unsupported image format: {image_path.suffix}")
        rel_path, _kind, _status = self.save_file_capture(image_path, caption, route)
        return rel_path

    def save_capture(self, text: str, route: KnowledgeRoute, project_action_id: str = "") -> str:
        """Save text/URL as a capture note."""
        context_name = route.context_name
        scope = route.scope
        project = route.project
        kind = infer_kind(text)
        topic = _classify_material_topic(text, scope, kind, infer_topic(text, scope), project=project)
        github_metadata: dict[str, str] = {}
        if kind == "github_repository":
            github_url = first_github_url(text)
            github_metadata = parse_github_url(github_url)
            if not github_metadata:
                raise ValueError("GitHub repository URL was not recognized.")
        source_url = first_github_url(text) or first_codepen_url(text) or first_youtube_url(text) or first_telegram_url(text) or first_url(text)
        if kind in {"article", "youtube_link", "github_repository", "codepen_pen", "reference_link"} and source_url:
            existing_rel_path = find_existing_source_note(source_url, route.layer, scope, project)
            if existing_rel_path:
                return existing_rel_path
        destination = capture_destination(scope, topic, kind, route.layer, project, route.project_section)
        destination.mkdir(parents=True, exist_ok=True)
        title = route.project_title if route.is_finished_projects else (github_metadata.get("github_full_name", "") if kind == "github_repository" else title_from_text(text, f"{context_name} capture"))
        if kind in {"article", "youtube_link", "codepen_pen"} and topic:
            title = f"{topic} - {title}"
        path = unique_path(destination / f"{clean_filename(title)}.md")
        if kind == "github_repository":
            markdown = render_github_capture_markdown(text, context_name, scope, project, topic, github_metadata, route.layer, route.project_title, route.project_section, project_action_id)
        else:
            markdown = render_capture_markdown(text, context_name, scope, project, topic, kind, route.layer, route.project_title, route.project_section)
        path.write_text(markdown, encoding="utf-8-sig")
        rel_path = path.relative_to(VAULT_DIR).as_posix()
        if kind == "github_repository":
            queue_github_item(first_github_url(text), rel_path, scope, project, topic, github_metadata, layer=route.layer, project_title=route.project_title, project_section=route.project_section, project_action_id=project_action_id)
        return rel_path

    def save_reference_links(self, links: list[ReferenceLink], parent_rel_path: str, parent_source_url: str, route: KnowledgeRoute) -> list[str]:
        """Save extracted reference links as notes."""
        saved: list[str] = []
        if not links:
            return saved
        destination = capture_destination(route.scope, "References", "reference_link", route.layer, route.project, route.project_section)
        destination.mkdir(parents=True, exist_ok=True)
        for link in links:
            existing_rel_path = find_existing_source_note(link.url, route.layer, route.scope, route.project)
            if existing_rel_path:
                saved.append(existing_rel_path)
                continue
            kind = "codepen_pen" if link.role == "codepen_pen" else "reference_link"
            link_destination = capture_destination(route.scope, "References", kind, route.layer, route.project, route.project_section)
            link_destination.mkdir(parents=True, exist_ok=True)
            status = "pending"
            if kind == "codepen_pen":
                status = "pending_codepen_snapshot"
            path = unique_path(link_destination / f"{clean_filename(link.title or link.url)}.md")
            path.write_text(render_reference_link_markdown(link, parent_rel_path, parent_source_url, route, status), encoding="utf-8-sig")
            saved.append(path.relative_to(VAULT_DIR).as_posix())
        return saved

    def create_manual_book_parent_note(self, entries: list[ManualBookEntry], source_text: str, route: KnowledgeRoute) -> str:
        """Create a manual book parent note."""
        destination = VAULT_DIR / "50 Library" / "Manual Book Lists"
        destination.mkdir(parents=True, exist_ok=True)
        path = unique_path(destination / f"Manual Book List {dt.datetime.now().strftime('%Y-%m-%d %H-%M-%S')}.md")
        path.write_text(render_manual_book_list_markdown(entries, source_text, route), encoding="utf-8-sig")
        return path.relative_to(VAULT_DIR).as_posix()

    def append_manual_book_resolution_to_parent(self, parent_rel_path: str, books: list[dict[str, object]], created_notes: list[str], source_text: str) -> None:
        """Append manual book resolution to parent note."""
        path = self.app.capture_path_from_rel(parent_rel_path)
        if not path.exists():
            return
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        section = render_manual_book_resolution_section(books, created_notes, source_text)
        path.write_text(text.rstrip() + "\n\n" + section + "\n", encoding="utf-8-sig")

    def start_manual_book_resolution(self, source_text: str, entries: list[ManualBookEntry], route: KnowledgeRoute) -> None:
        """Start manual book resolution."""
        import threading
        last_report = self.app.last_book_discovery_report
        parent_note = last_report.parent_note if last_report else self.create_manual_book_parent_note(entries, source_text, route)
        task_id = self.app.start_background_task(
            "book_resolution",
            "Добавляю книги из уточнения",
            rel_path=parent_note,
            detail=f"{len(entries)} book candidate(s)",
        )
        thread = threading.Thread(
            target=self.manual_book_resolution_worker,
            args=(source_text, entries, parent_note, route, task_id),
            daemon=True,
        )
        thread.start()
        self.app.append_warning_message(
            f"Запустил добавление {len(entries)} книг из твоего уточнения. Можно продолжать общаться; статус будет в следующих ответах.",
            persist=False,
        )

    def manual_book_resolution_worker(self, source_text: str, entries: list[ManualBookEntry], parent_note: str, route: KnowledgeRoute, task_id: str = "") -> None:
        """Background manual book resolution worker."""
        from knowledgelab.vision.book_discovery import lookup_book_catalog
        books: list[dict[str, object]] = []
        try:
            for index, entry in enumerate(entries, start=1):
                if task_id:
                    self.app.update_background_task(task_id, detail=f"catalog lookup {index}/{len(entries)}")
                book: dict[str, object] = {
                    "title": entry.title,
                    "author": entry.author,
                    "isbn": "",
                    "evidence": entry.user_evidence or entry.title,
                    "status": "user_confirmed",
                    "confidence": 1.0,
                    "user_confirmed": True,
                    "user_evidence": entry.user_evidence,
                    "region": entry.section,
                    "discovery_source": "manual_user_resolution",
                }
                try:
                    lookup = lookup_book_catalog(book)
                except Exception as exc:
                    lookup = {
                        "lookup_status": "lookup_error",
                        "lookup_reason": f"Book catalog lookup failed: {exc}",
                    }
                enriched = merge_book_lookup(book, lookup)
                enriched["book_topic"] = str(enriched.get("book_topic") or classify_book_topic(enriched))
                books.append(enriched)
            if task_id:
                self.app.update_background_task(task_id, detail="saving book notes")
            created_notes = _save_detected_book_notes(books, parent_note, "", allow_unverified=True)
            self.append_manual_book_resolution_to_parent(parent_note, books, created_notes, source_text)
            from knowledgelab.material.queue import launch_reindex
            launch_reindex(route)
            added = [book for book in books if book.get("vault_note")]
            needs = [book for book in books if not book.get("vault_note")]
            report = BookDiscoveryReport(parent_note, added, needs, [])
            if task_id:
                self.app.update_background_task(task_id, status="done", result=f"added={len(added)}; needs_clarification={len(needs)}")
            self.app.root.after(0, self.app.append_book_discovery_report, report)
        except Exception as exc:
            if task_id:
                self.app.update_background_task(task_id, status="failed", result=str(exc))
            report = BookDiscoveryReport(parent_note, [], [], [{"reason": "manual book resolution failed", "evidence": str(exc)}])
            self.app.root.after(0, self.app.append_book_discovery_report, report)

    def attach_folder(self) -> None:
        """Attach a folder from file dialog."""
        if self.app.busy:
            return
        self.app.set_tool_button_active("folder_attach_button", True)
        try:
            folder = filedialog.askdirectory(
                title="Выберите локальную папку",
                mustexist=True,
                parent=self.app.root,
            )
        finally:
            self.app.set_tool_button_active("folder_attach_button", False)
        if folder:
            self.process_attached_files([folder], source_title="Папка:")

    def attach_images(self) -> None:
        """Attach images from file dialog."""
        self.attach_files(title="Выберите изображения", filetypes=IMAGE_FILETYPES)

    def attach_files(self, title: str = "Выберите материалы", filetypes=None) -> None:
        """Attach files from file dialog."""
        if self.app.busy:
            return
        self.app.set_tool_button_active("file_attach_button", True)
        try:
            if filetypes is None:
                source_kind = self.app.choose_attachment_source()
                if source_kind == "folder":
                    self.attach_folder()
                    return
                if source_kind == "github":
                    self.attach_github_repository()
                    return
                if source_kind != "files":
                    return
            files = filedialog.askopenfilenames(
                title=title,
                filetypes=filetypes or SUPPORTED_FILETYPES,
                parent=self.app.root,
            )
        finally:
            self.app.set_tool_button_active("file_attach_button", False)
        if not files:
            return
        self.process_attached_files(files, source_title="Файлы:")

    def attach_github_repository(self) -> None:
        """Attach a GitHub repository."""
        default_url = first_github_url(self.app.input_text())
        url = simpledialog.askstring(
            "GitHub repository",
            "Paste GitHub repository URL:",
            initialvalue=default_url,
            parent=self.app.root,
        )
        if not url:
            return
        url = normalize_github_url(url)
        if not parse_github_url(url):
            self.app.append_warning_message("GitHub repository URL was not recognized. Use https://github.com/owner/repo.", persist=False)
            return
        self.process_github_repository(url)

    def process_github_repository(self, url: str) -> None:
        """Process a GitHub repository URL."""
        caption = self.app.input_text()
        text = "\n\n".join(part for part in (url.strip(), caption.strip()) if part)
        suggested_route = self.app.selected_route(text)
        github_meta = parse_github_url(url)
        route = self.app.choose_capture_context(
            suggested_route,
            allow_finished_project=True,
            finished_title_default=github_meta.get("github_full_name", ""),
            source_hint=url,
            github_metadata=github_meta,
        )
        if not route:
            self.app.append_warning_message("GitHub source save was canceled.", persist=False)
            return
        action_id = self.app.create_project_action(
            source_type="github_repository",
            source_url=url,
            title=github_meta.get("github_full_name", "") or url,
            route=route,
        )
        try:
            rel_path = self.save_capture(text, route, action_id)
            self.app.add_project_action_notes(action_id, [rel_path])
        except Exception as exc:
            self.app.append_warning_message(f"Could not save GitHub source: {exc}", persist=False)
            return
        self.app.append_user_message("\n".join(["GitHub:", f"- {url}"] + (["", caption] if caption else [])))
        self.app.clear_input()
        self.app.append_assistant_message(
            "Saved GitHub intake in Obsidian:\n"
            f"- {rel_path}\n\n"
            "The repository itself was not cloned or copied into the vault; the note stores only a source reference and metadata.\n"
            f"Repository import was queued in {self.app.material_queue_display_path()}.",
            lightrag_used=False,
            project_action_id=action_id,
        )

    def handle_dropped_files(self, files: list[str]) -> None:
        """Handle files dropped onto the chat window."""
        if self.app.busy:
            self.app.append_warning_message("Сейчас идет операция. Дождитесь завершения и перетащите файлы еще раз.", persist=False)
            return
        self.app.flash_tool_button("file_attach_button")
        try:
            self.process_attached_files(files, source_title="Перетащенные файлы:")
        except Exception as exc:
            self.app.append_warning_message(f"Drag-and-drop import failed: {exc}", persist=False)

    def process_attached_files(self, files, source_title: str = "Файлы:") -> None:
        """Process a list of attached files."""
        file_list = [normalize_attached_source_path(str(file_name)) for file_name in files if str(file_name).strip()]
        file_list = [file_name for file_name in file_list if file_name]
        if not file_list:
            return
        caption = self.app.input_text()
        route_seed = " ".join([caption] + [Path(file_name).name for file_name in file_list[:4]]).strip()
        suggested_route = self.app.selected_route(route_seed)
        first_existing = next((Path(file_name) for file_name in file_list if Path(file_name).exists()), None)
        route = self.app.choose_capture_context(
            suggested_route,
            allow_finished_project=True,
            finished_title_default=first_existing.stem if first_existing else "",
            source_hint=str(first_existing) if first_existing else "",
        )
        if not route:
            self.app.append_warning_message("Сохранение файлов отменено.", persist=False)
            return
        duplicates: list[tuple[str, list[dict[str, str]]]] = []
        skip_set: set[str] = set()
        for file_name in file_list:
            source_path = Path(file_name)
            if not source_path.exists():
                continue
            existing = find_existing_file_capture(str(source_path), route.layer, route.scope, route.project)
            if existing:
                duplicates.append((source_path.name, existing))
        if duplicates:
            from knowledgelab.ui.dialogs import ask_duplicate_resolution
            resolution = ask_duplicate_resolution(self.app.root, duplicates)
            if resolution == "cancel":
                self.app.append_warning_message("Импорт отменён: пользователь отменил из-за дубликатов.", persist=False)
                return
            if resolution == "skip":
                dup_names = {name for name, _ in duplicates}
                file_list = [f for f in file_list if Path(f).name not in dup_names]
                if not file_list:
                    self.app.append_warning_message("Все файлы уже были импортированы ранее. Ничего не сохранено.", persist=False)
                    return
        saved: list[str] = []
        saved_original_names: list[str] = []
        extracted_count = 0
        errors: list[str] = []
        queued_processing_count = 0
        folder_file_count = 0
        folder_limit_reached = False
        book_discovery_count = 0
        video_analysis_count = 0
        routing_reports: list[MaterialRoutingReport] = []
        project_action_ids: list[str] = []
        user_lines = [source_title]
        for file_name in file_list:
            source_path = Path(file_name)
            if not source_path.exists():
                errors.append(f"{source_path.name}: файл не найден")
                continue
            try:
                if source_path.is_dir():
                    action_id = self.app.create_project_action(
                        source_type="local_folder",
                        source_path=str(source_path),
                        title=route.project_title or caption.strip() or source_path.name,
                        route=route,
                    )
                    project_action_ids.append(action_id)
                    folder_results, scan_complete = self.app.save_folder_file_captures(source_path, caption, route, action_id)
                    if not folder_results:
                        errors.append(f"{source_path.name}: папка не содержит файлов для импорта")
                        continue
                    folder_file_count += len(folder_results)
                    folder_limit_reached = folder_limit_reached or not scan_complete
                    user_lines.append(f"- {source_path.name} (folder -> {len(folder_results)} file references)")
                    self.app.add_project_action_notes(action_id, [rel_path for rel_path, _kind, _status, _file_path in folder_results])
                    for rel_path, kind, extraction_status, file_path in folder_results:
                        saved.append(rel_path)
                        saved_original_names.append(file_path.name)
                        meta = self.app.note_metadata(rel_path)
                        routing_reports.append(MaterialRoutingReport(file_path.name, kind, meta.get("topic", "") or "Unsorted", rel_path))
                        if kind in {"book_photo", "book_page_photo", "bookshelf_photo"}:
                            if self.app.start_auto_book_image_processing(file_path, rel_path, kind, caption, route):
                                book_discovery_count += 1
                        if kind == "video_file":
                            if self.app.start_video_analysis_processing(str(file_path), rel_path, kind, route):
                                video_analysis_count += 1
                        if extraction_status in {"extracted", "partial"}:
                            extracted_count += 1
                        if extraction_status not in {"extracted", "partial"}:
                            queued_processing_count += 1
                    continue
                rel_path, kind, extraction_status = self.app.save_file_capture(source_path, caption, route)
                saved.append(rel_path)
                saved_original_names.append(source_path.name)
                meta = self.app.note_metadata(rel_path)
                routing_reports.append(MaterialRoutingReport(source_path.name, kind, meta.get("topic", "") or "Unsorted", rel_path))
                if kind in {"book_photo", "book_page_photo", "bookshelf_photo", "image_capture"} and source_path.suffix.lower() in IMAGE_EXTENSIONS:
                    if self.app.start_auto_book_image_processing(source_path, rel_path, kind, caption, route, quiet_generic=True):
                        book_discovery_count += 1
                if kind == "video_file":
                    if self.app.start_video_analysis_processing(str(source_path), rel_path, kind, route):
                        video_analysis_count += 1
                if extraction_status in {"extracted", "partial"}:
                    extracted_count += 1
                if extraction_status not in {"extracted", "partial"}:
                    queued_processing_count += 1
                user_lines.append(f"- {source_path.name} ({file_kind_label(kind)})")
            except Exception as exc:
                errors.append(f"{source_path.name}: {exc}")
        if caption:
            user_lines.extend(["", caption])
        if saved:
            self.app.append_user_message("\n".join(user_lines))
            self.app.clear_input()
            display_names = saved_original_names[:5] if saved_original_names else [Path(p).stem[:20] for p in saved[:5]]
            message = f"Сохранил {len(saved)} файл(ов)."
            if display_names:
                message += "\n" + ", ".join(display_names)
                if len(saved) > 5:
                    message += f" и ещё {len(saved) - 5}"
            if extracted_count:
                from knowledgelab.material.queue import launch_reindex
                launch_reindex(route)
            if queued_processing_count:
                message += "\nНекоторые файлы требуют обработки (OCR/парсинг)."
            if book_discovery_count:
                message += f"\nИщу книги на {book_discovery_count} изображениях..."
            if video_analysis_count:
                message += f"\nАнализирую видео ({video_analysis_count} файлов)..."
            self.app.append_assistant_message(message, lightrag_used=False, project_action_id=project_action_ids[0] if project_action_ids else "")
            self.app.append_material_routing_report(routing_reports)
        if errors:
            self.app.append_warning_message("Не удалось сохранить часть файлов:\n" + "\n".join(errors), persist=False)
