"""Background workers for material processing pipeline."""
from __future__ import annotations

import threading
from pathlib import Path
from typing import TYPE_CHECKING

from knowledgelab.config import ROOT, RLM_QUEUE_PATH, VIDEO_PROCESSING_DIR, VIDEO_FRAME_LIMIT, DEFAULT_SETTINGS
from knowledgelab.models import KnowledgeRoute, VideoAnalysisReport
from knowledgelab.utils.text import now_iso
from knowledgelab.material.youtube import build_youtube_sync_command
from knowledgelab.material.web import fetch_article_material, extract_reference_links_from_html
from knowledgelab.material.codepen import fetch_codepen_snapshot, render_codepen_snapshot_markdown
from knowledgelab.material.video import (
    video_source_id as video_source_id_util, video_runtime_dir,
    extract_video_frames, call_video_frame_vision, write_video_analysis_note,
    queue_video_analysis_item,
)
from knowledgelab.material.queue import (
    run_background_material_command, launch_reindex,
    build_rlm_context_profile, queue_rlm_item,
)
from knowledgelab.vision.book_pipeline import process_book_image

if TYPE_CHECKING:
    from main import KnowledgeChatApp


class MaterialWorkerManager:
    """Coordinates background material processing workers."""

    def __init__(self, app: KnowledgeChatApp) -> None:
        self.app = app

    def start_auto_material_processing(self, text: str, route: KnowledgeRoute, rel_path: str) -> None:
        """Start background processing for saved material."""
        from knowledgelab.routing.intent import infer_kind
        from knowledgelab.utils.urls import first_github_url, first_codepen_url, first_url

        if not bool(self.app.settings.get("auto_process_links", True)):
            return
        url = first_github_url(text) or first_codepen_url(text) or first_url(text)
        if not url:
            return
        kind = infer_kind(text)
        if kind == "youtube_link":
            if route.is_finished_projects:
                launch_reindex(route)
                self.app.append_warning_message("YouTube-ссылка сохранена в слой Finished Projects; автоматический transcript sync для этого слоя пропущен.", persist=False)
                return
            self.app.append_warning_message("Запустил обработку YouTube-ссылки: транскрипт и обновление LightRAG пойдут в фоне.", persist=False)
            threading.Thread(target=self.auto_process_youtube_worker, args=(route,), daemon=True).start()
            if self.start_video_analysis_processing(url, rel_path, kind, route):
                self.app.append_warning_message("Дополнительно поставил YouTube в очередь video analysis: transcript + кадры/код/слайды.", persist=False)
        elif kind == "github_repository":
            self.app.append_warning_message(f"GitHub repository source was queued for import: {self.material_queue_display_path()}.", persist=False)
        elif kind == "codepen_pen":
            self.app.append_warning_message("Запустил обработку CodePen: попробую сохранить metadata/code snapshot; если CodePen заблокирует парсинг, оставлю ссылку как blocked reference.", persist=False)
            threading.Thread(target=self.auto_process_codepen_worker, args=(url, route, rel_path), daemon=True).start()
        elif kind == "article":
            self.app.append_warning_message("Запустил обработку web-страницы: попробую сохранить текст статьи и обновить LightRAG в фоне.", persist=False)
            threading.Thread(target=self.auto_process_article_worker, args=(url, route, rel_path), daemon=True).start()

    def auto_process_youtube_worker(self, route: KnowledgeRoute) -> None:
        """Background YouTube transcript sync."""
        scope = route.scope
        project = route.project
        command = build_youtube_sync_command(self.app.python_executable(), scope, project)
        ok, message = run_background_material_command(command, f"auto-youtube-{scope}")
        if ok:
            launch_reindex(route)
            self.app.root.after(0, self.app.append_warning_message, "YouTube-транскрипт обработан; обновление LightRAG запущено в фоне.", False)
        else:
            self.app.root.after(0, self.app.append_warning_message, f"YouTube-ссылка сохранена, но транскрипт не удалось получить автоматически: {message}", False)

    def auto_process_article_worker(self, url: str, route: KnowledgeRoute, rel_path: str) -> None:
        """Background article parsing."""
        path = self.app.capture_path_from_rel(rel_path)
        try:
            existing_text = path.read_text(encoding="utf-8-sig", errors="replace") if path.exists() else ""
            if "\n## Parsed Page\n" in existing_text or existing_text.startswith("## Parsed Page\n"):
                launch_reindex(route)
                self.app.root.after(0, self.app.append_warning_message, "Web-страница уже была сохранена и распарсена; повторный текст не добавляю.", False)
                return
            title, markdown, html_text = fetch_article_material(url)
            if not markdown:
                raise RuntimeError("страница не дала читаемый текст")
            reference_links = extract_reference_links_from_html(html_text, url)
            saved_reference_links = self.app.save_reference_links(reference_links, rel_path, url, route)
            rlm_profile = build_rlm_context_profile(markdown, title or url)
            if bool(rlm_profile.get("needs_rlm")) or saved_reference_links:
                self.app.queue_rlm_processing(rel_path, url, route, rlm_profile)
            with path.open("a", encoding="utf-8-sig") as handle:
                handle.write("\n## Parsed Page\n\n")
                handle.write(f"Parsed at: {now_iso()}\n\n")
                if title:
                    handle.write(f"Page title: {title}\n\n")
                handle.write(markdown)
                handle.write("\n")
                if saved_reference_links:
                    handle.write("\n## Linked References\n\n")
                    for child in saved_reference_links:
                        handle.write(f"- [[{child}]]\n")
                    handle.write("\n")
                if bool(rlm_profile.get("needs_rlm")):
                    handle.write("\n## RLM Profile\n\n")
                    handle.write("This note is queued for Recursive Language Model processing: context should be treated as an external environment and decomposed into snippets/subcalls.\n\n")
                    handle.write(f"- Approx tokens: {rlm_profile.get('approx_tokens')}\n")
                    handle.write(f"- Non-empty lines: {rlm_profile.get('non_empty_lines')}\n")
                    handle.write(f"- Queue: `{RLM_QUEUE_PATH.relative_to(ROOT).as_posix()}`\n")
            launch_reindex(route)
            self.app.root.after(0, self.app.append_warning_message, "Текст web-страницы сохранен в Markdown; обновление LightRAG запущено в фоне.", False)
        except Exception as exc:
            self.app.root.after(0, self.app.append_warning_message, f"Ссылка сохранена, но страницу не удалось автоматически распарсить: {exc}", False)

    def auto_process_codepen_worker(self, url: str, route: KnowledgeRoute, rel_path: str) -> None:
        """Background CodePen snapshot extraction."""
        path = self.app.capture_path_from_rel(rel_path)
        try:
            existing_text = path.read_text(encoding="utf-8-sig", errors="replace") if path.exists() else ""
            if "\n## CodePen Snapshot\n" in existing_text or existing_text.startswith("## CodePen Snapshot\n"):
                launch_reindex(route)
                self.app.root.after(0, self.app.append_warning_message, "CodePen уже был обработан; повторный snapshot не добавляю.", False)
                return
            snapshot = fetch_codepen_snapshot(url)
            with path.open("a", encoding="utf-8-sig") as handle:
                handle.write("\n")
                handle.write(render_codepen_snapshot_markdown(snapshot))
                handle.write("\n")
            if snapshot.status in {"extracted", "metadata"}:
                profile = build_rlm_context_profile("\n\n".join(part for part in (snapshot.html_code, snapshot.css_code, snapshot.js_code) if part), snapshot.title or url)
                if bool(profile.get("needs_rlm")):
                    self.app.queue_rlm_processing(rel_path, url, route, profile)
            launch_reindex(route)
            self.app.root.after(0, self.app.append_warning_message, f"CodePen snapshot сохранён со статусом: {snapshot.status}.", False)
        except Exception as exc:
            self.app.root.after(0, self.app.append_warning_message, f"CodePen-ссылка сохранена, но snapshot не удалось получить: {exc}", False)

    def material_queue_display_path(self) -> str:
        """Get material queue display path."""
        from knowledgelab.config import MATERIAL_QUEUE_PATH
        try:
            return MATERIAL_QUEUE_PATH.relative_to(ROOT).as_posix()
        except ValueError:
            return str(MATERIAL_QUEUE_PATH)

    def auto_process_book_image_worker(self, image_path: str, rel_path: str, kind: str, caption: str, route: KnowledgeRoute, task_id: str = "") -> None:
        """Background book detection from image."""
        should_update_parent = kind in {"book_photo", "book_page_photo", "bookshelf_photo"}
        try:
            vision_model, vision_ready, loaded_models = self.app.vision_model_state()
            pipeline_result = process_book_image(
                image_path=Path(image_path),
                rel_path=rel_path,
                kind=kind,
                caption=caption,
                route=route,
                settings=getattr(self.app, "settings", DEFAULT_SETTINGS),
                vault_dir=self.app.vault_dir(),
                vision_model=vision_model,
                vision_ready=vision_ready,
                loaded_models=loaded_models,
                base_url=self.app.lmstudio_base_url(),
                timeout=min(self.app.query_timeout_seconds, 240),
                update_parent=should_update_parent,
                on_status=(lambda detail: self.app.update_background_task(task_id, detail=detail)) if task_id else None,
            )
            report = pipeline_result.report
            has_book_outcome = bool(report.added or report.needs_clarification or report.not_found)
            if pipeline_result.parent_note_updated or pipeline_result.created_notes:
                launch_reindex(route)
            if task_id:
                task_status = "done" if pipeline_result.status == "done" else "failed"
                self.app.update_background_task(
                    task_id,
                    status=task_status,
                    result=(
                        f"added={len(report.added)}; "
                        f"needs_clarification={len(report.needs_clarification)}; "
                        f"not_found={len(report.not_found)}"
                    ),
                )
            if should_update_parent or has_book_outcome:
                self.app.root.after(0, self.app.append_book_discovery_report, report)
        except Exception as exc:
            if task_id:
                self.app.update_background_task(task_id, status="failed", result=str(exc))
            self.app.root.after(0, self.app.append_warning_message, f"Book image processing failed: {exc}", False)

    def start_auto_book_image_processing(self, image_path: Path, rel_path: str, kind: str, caption: str, route: KnowledgeRoute, *, quiet_generic: bool = False) -> bool:
        """Start background book image processing."""
        if kind not in {"book_photo", "book_page_photo", "bookshelf_photo", "image_capture"}:
            return False
        settings = getattr(self.app, "settings", DEFAULT_SETTINGS)
        if kind == "image_capture" and quiet_generic and not bool(settings.get("auto_detect_books_in_images", True)):
            return False
        task_id = self.app.start_background_task(
            "book_discovery",
            "Ищу книги на изображении",
            source_path=str(image_path),
            rel_path=rel_path,
            detail="waiting for local LM Studio vision model",
        )
        threading.Thread(
            target=self.auto_process_book_image_worker,
            args=(str(image_path), rel_path, kind, caption, route, task_id),
            daemon=True,
        ).start()
        return True

    def start_video_analysis_processing(self, source: str, rel_path: str, kind: str, route: KnowledgeRoute) -> bool:
        """Start background video analysis."""
        if kind not in {"video_file", "youtube_link"}:
            return False
        runtime_dir = VIDEO_PROCESSING_DIR / video_source_id_util(source)
        task_id = self.app.start_background_task(
            "video_frame_analysis",
            "Анализирую видео",
            source_path=source,
            rel_path=rel_path,
            detail="queued transcript + frame analysis",
        )
        queue_video_analysis_item(source, rel_path, kind, route, runtime_dir)
        threading.Thread(
            target=self.auto_process_video_worker,
            args=(source, rel_path, kind, route, runtime_dir, task_id),
            daemon=True,
        ).start()
        return True

    def auto_process_video_worker(self, source: str, rel_path: str, kind: str, route: KnowledgeRoute, runtime_dir: Path, task_id: str = "") -> None:
        """Background video analysis."""
        transcript_status = "queued_youtube_caption_sync" if kind == "youtube_link" else "pending_asr"
        frame_status = "pending"
        frame_results: list[dict[str, object]] = []
        warning = ""
        try:
            runtime_dir.mkdir(parents=True, exist_ok=True)
            if kind == "youtube_link":
                frame_status = "pending_youtube_frame_sampling"
                warning = "YouTube captions are handled by transcript sync; visual frame sampling is queued and needs a downloader step before frame OCR."
            else:
                if task_id:
                    self.app.update_background_task(task_id, detail="extracting sampled frames with ffmpeg")
                frames, frame_status = extract_video_frames(Path(source), runtime_dir)
                if frames:
                    try:
                        if task_id:
                            self.app.update_background_task(task_id, detail=f"vision analysis for {len(frames)} frame(s)")
                        for frame in frames[:VIDEO_FRAME_LIMIT]:
                            vision_model, vision_ready, loaded_models = self.app.vision_model_state()
                            frame_results.append(call_video_frame_vision(
                                frame, vision_model, vision_ready, loaded_models,
                                self.app.lmstudio_base_url(), min(self.app.query_timeout_seconds, 180),
                            ))
                        frame_status = "processed" if frame_results else "processed_no_useful_frames"
                    except Exception as exc:
                        frame_status = "pending_needs_vision_model"
                        warning = str(exc)
                transcript_status = "audio_extraction_pending_asr"
            analysis_rel_path = write_video_analysis_note(
                source, rel_path, kind, route, runtime_dir,
                transcript_status, frame_status, frame_results,
                self.app.vault_dir(), warning,
            )
            launch_reindex(route)
            report = VideoAnalysisReport(
                parent_note=rel_path,
                analysis_note=analysis_rel_path,
                source=source,
                transcript_status=transcript_status,
                frame_analysis_status=frame_status,
                frame_count=len(frame_results),
                code_snippet_count=sum(1 for item in frame_results if str(item.get("code") or item.get("visible_code") or "").strip()),
                warning=warning,
            )
            if task_id:
                self.app.update_background_task(task_id, status="done", result=f"frames={len(frame_results)}; status={frame_status}")
            self.app.root.after(0, self.app.append_video_analysis_report, report)
        except Exception as exc:
            if task_id:
                self.app.update_background_task(task_id, status="failed", result=str(exc))
            try:
                analysis_rel_path = write_video_analysis_note(
                    source, rel_path, kind, route, runtime_dir,
                    transcript_status, "failed", frame_results, self.app.vault_dir(), str(exc),
                )
            except Exception:
                analysis_rel_path = ""
            report = VideoAnalysisReport(rel_path, analysis_rel_path, source, transcript_status, "failed", 0, 0, str(exc))
            self.app.root.after(0, self.app.append_video_analysis_report, report)
