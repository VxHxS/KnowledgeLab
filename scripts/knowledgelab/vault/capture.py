from __future__ import annotations

import hashlib
import re
from pathlib import Path

from knowledgelab.config import (
    VAULT_DIR,
    LAYER_ACTIVE,
    LAYER_FINISHED_PROJECTS,
    IMAGE_EXTENSIONS,
    TEXT_EXTENSIONS,
    DOC_EXTENSIONS,
    AUDIO_EXTENSIONS,
    VIDEO_EXTENSIONS,
    ARCHIVE_EXTENSIONS,
    VIDEO_PROCESSING_DIR,
)
from knowledgelab.models import KnowledgeRoute, ReferenceLink
from knowledgelab.utils.text import slugify, clean_filename, yaml_quote, compact_whitespace, now_iso
from knowledgelab.utils.urls import (
    first_url,
    first_github_url,
    first_codepen_url,
    first_youtube_url,
    first_telegram_url,
    normalize_source_url_for_match,
    source_domain,
    stable_content_hash,
    video_source_id,
)
from knowledgelab.routing.intent import default_finished_project_section

_SOURCE_KIND_SUBPATH: dict[str, str] = {
    "youtube_link": "YouTube/Links",
    "telegram_source": "Telegram",
    "article": "Articles",
    "image_capture": "Images",
    "document_file": "Documents",
    "audio_file": "Audio",
    "video_file": "Video",
    "archive_file": "Archives",
    "folder_source": "Folders",
    "github_repository": "GitHub",
    "codepen_pen": "CodePen",
    "reference_link": "References",
}

_GENERAL_SOURCE_KIND_SUBPATH: dict[str, str] = {
    "youtube_link": "YouTube/Links",
    "telegram_source": "Telegram",
    "article": "Articles",
    "github_repository": "GitHub",
    "codepen_pen": "CodePen",
    "reference_link": "References",
}

_GENERAL_INBOX_KIND_SUBPATH: dict[str, str] = {
    "image_capture": "Images",
    "document_file": "Documents",
    "audio_file": "Audio",
    "video_file": "Video",
    "archive_file": "Archives",
    "folder_source": "Folders",
}

_BOOK_KINDS = {"book_photo", "book_page_photo", "bookshelf_photo"}
_FILE_KINDS = {"text_file", "generic_file"}


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


def capture_destination(
    scope: str,
    topic: str,
    kind: str,
    layer: str = LAYER_ACTIVE,
    project: str = "",
    project_section: str = "",
) -> Path:
    if layer == LAYER_FINISHED_PROJECTS:
        section_slug = slugify(project_section or default_finished_project_section(scope, project or topic))
        project_slug = slugify(project or topic or "finished-project")
        return VAULT_DIR / "40 Finished Projects" / section_slug / project_slug

    safe_project = slugify(project) if project else ""

    if safe_project and safe_project not in {"web-development", "my-game"}:
        base = VAULT_DIR / "20 Projects" / clean_filename(safe_project)
        if kind in _SOURCE_KIND_SUBPATH:
            return base / "Sources" / Path(_SOURCE_KIND_SUBPATH[kind])
        if kind in _BOOK_KINDS:
            return VAULT_DIR / "50 Library" / clean_filename(project or topic or "Unsorted Book")
        if kind in _FILE_KINDS:
            return base / "Sources" / "Files"
        if kind == "solution":
            return base / "Solutions"
        return base / "Captures"

    if scope == "web":
        base = VAULT_DIR / "20 Projects" / "Web Development"
        if kind in _SOURCE_KIND_SUBPATH:
            return base / "Sources" / Path(_SOURCE_KIND_SUBPATH[kind])
        if kind in _BOOK_KINDS:
            return VAULT_DIR / "50 Library" / clean_filename(topic or "Unsorted Book")
        if kind in _FILE_KINDS:
            return base / "Sources" / "Files"
        if kind == "solution":
            return base / "Solutions"
        return base / "Topics" / clean_filename(topic)

    if scope == "game":
        base = VAULT_DIR / "20 Projects" / "My Game"
        if kind in _SOURCE_KIND_SUBPATH:
            return base / "Sources" / Path(_SOURCE_KIND_SUBPATH[kind])
        if kind in _BOOK_KINDS:
            return VAULT_DIR / "50 Library" / clean_filename(topic or "Unsorted Book")
        if kind in _FILE_KINDS:
            return base / "Sources" / "Files"
        return base / "Captures"

    if kind in _GENERAL_SOURCE_KIND_SUBPATH:
        return VAULT_DIR / "30 Sources" / Path(_GENERAL_SOURCE_KIND_SUBPATH[kind])
    if kind in _GENERAL_INBOX_KIND_SUBPATH:
        return VAULT_DIR / "00 Inbox" / Path(_GENERAL_INBOX_KIND_SUBPATH[kind])
    if kind in _BOOK_KINDS:
        return VAULT_DIR / "50 Library" / clean_filename(topic or "Unsorted Book")
    if kind in _FILE_KINDS:
        return VAULT_DIR / "00 Inbox" / "Files"
    return VAULT_DIR / "00 Inbox"


def title_from_text(text: str, fallback: str) -> str:
    for line in text.splitlines():
        line = line.strip().strip("#").strip()
        if line and not re.fullmatch(r"https?://[^\s]+", line):
            return clean_filename(line)
    url = first_url(text)
    if url:
        return clean_filename(url.replace("https://", "").replace("http://", ""))
    return fallback


def render_capture_markdown(
    text: str,
    context_name: str,
    scope: str,
    project: str,
    topic: str,
    kind: str,
    layer: str = LAYER_ACTIVE,
    project_title: str = "",
    project_section: str = "",
) -> str:
    url = first_github_url(text) or first_codepen_url(text) or first_youtube_url(text) or first_telegram_url(text) or first_url(text)
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
    elif kind == "github_repository":
        source = "github"
        tags.append("source/github")
    elif kind == "codepen_pen":
        source = "codepen"
        tags.extend(["source/codepen", "source/example"])
    elif kind == "reference_link":
        source = "web_link"
        tags.append("source/reference-link")
    else:
        source = "manual"

    title = title_from_text(text, f"{context_name} capture")
    frontmatter = [
        "---",
        f"type: {kind}",
        f"source: {source}",
        f"source_url: {yaml_quote(url)}",
        f"normalized_source_url: {yaml_quote(normalize_source_url_for_match(url))}",
        f"source_domain: {yaml_quote(source_domain(url) if url else '')}",
        f"capture_status: {yaml_quote('pending' if kind in {'article', 'codepen_pen', 'reference_link'} else 'saved')}",
        f"content_hash: {yaml_quote(stable_content_hash(text.strip()))}",
        f"layer: {layer}",
        f"scope: {scope}",
        f"project: {yaml_quote(project)}",
        f"project_title: {yaml_quote(project_title)}",
        f"project_section: {yaml_quote(project_section)}",
        "storage_policy: reference_only",
        "copies_original: false",
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


def render_image_capture_markdown(
    image_path: Path,
    caption: str,
    context_name: str,
    scope: str,
    project: str,
    topic: str,
) -> str:
    stat = image_path.stat()
    tags = ["captured/chat", "source/image", "needs/vision-extraction"]
    if project:
        tags.append(f"project/{project}")
    if topic:
        tags.append(f"topic/{slugify(topic)}")
    title_seed = caption.strip() or image_path.stem
    title = clean_filename(title_seed)
    frontmatter = [
        "---",
        "type: image_capture",
        "source: image",
        f"source_path: {yaml_quote(str(image_path))}",
        f"file_name: {yaml_quote(image_path.name)}",
        f"file_size_bytes: {stat.st_size}",
        f"scope: {scope}",
        f"project: {yaml_quote(project)}",
        f"topic: {yaml_quote(topic)}",
        f"captured_at: {yaml_quote(now_iso())}",
        "extraction_status: pending",
        f"tags: [{', '.join(tags)}]",
        "---",
        "",
    ]
    body = [
        f"# {title}",
        "",
        "## Image Intake",
        "",
        f"- Original file: `{image_path}`",
        f"- File name: `{image_path.name}`",
        f"- Size: {stat.st_size} bytes",
        f"- Suggested context: {context_name}",
        f"- Suggested topic: {topic or 'None'}",
        "",
        "## Caption / User Hint",
        "",
        caption.strip() or "_No caption was provided._",
        "",
        "## Extracted Data",
        "",
        "_Pending OCR/vision extraction. The heavy image file is not copied into the vault by default._",
        "",
    ]
    return "\n".join(frontmatter + body)


def render_file_capture_markdown(
    file_path: Path,
    caption: str,
    context_name: str,
    scope: str,
    project: str,
    topic: str,
    kind: str,
    extracted_text: str,
    extraction_status: str,
    layer: str = LAYER_ACTIVE,
    project_title: str = "",
    project_section: str = "",
    source_root: Path | None = None,
    source_relative_path: str = "",
    project_action_id: str = "",
    book_title: str = "",
    page_number_guess: str = "",
) -> str:
    stat = file_path.stat()
    tags = ["captured/chat", "source/file"]
    if source_root:
        tags.append("source/folder-file")
    if kind == "image_capture":
        tags.append("source/image")
    if kind in {"book_photo", "book_page_photo"}:
        tags.extend(["source/book", "needs/ocr"])
    if kind == "bookshelf_photo":
        tags.extend(["source/bookshelf", "needs/vision-extraction", "needs/book-discovery"])
    if kind == "audio_file":
        tags.append("source/audio")
    if kind == "video_file":
        tags.append("source/video")
    if kind == "document_file":
        tags.append("source/document")
    if kind == "archive_file":
        tags.append("source/archive")
    if extraction_status in {"extracted", "partial"}:
        tags.append(f"extraction/{extraction_status}")
    else:
        tags.append(f"needs/{slugify(extraction_label(kind))}")
    if project:
        tags.append(f"project/{project}")
    if topic:
        tags.append(f"topic/{slugify(topic)}")
    title_seed = caption.strip() or file_path.stem
    title = clean_filename(title_seed)
    frontmatter = [
        "---",
        f"type: {kind}",
        "source: file",
        f"source_path: {yaml_quote(str(file_path))}",
        f"source_image_path: {yaml_quote(str(file_path) if kind in {'book_photo', 'book_page_photo', 'bookshelf_photo'} else '')}",
        f"source_root: {yaml_quote(str(source_root) if source_root else '')}",
        f"source_relative_path: {yaml_quote(source_relative_path)}",
        f"file_name: {yaml_quote(file_path.name)}",
        f"file_extension: {yaml_quote(file_path.suffix.lower())}",
        f"file_size_bytes: {stat.st_size}",
        f"layer: {layer}",
        f"scope: {scope}",
        f"project: {yaml_quote(project)}",
        f"project_title: {yaml_quote(project_title)}",
        f"project_section: {yaml_quote(project_section)}",
        f"project_action_id: {yaml_quote(project_action_id)}",
        f"book_title: {yaml_quote(book_title)}",
        f"page_number_guess: {yaml_quote(page_number_guess)}",
        f"ocr_status: {yaml_quote('pending' if kind in {'book_photo', 'book_page_photo', 'bookshelf_photo'} else '')}",
        f"ocr_text: {yaml_quote('')}",
        f"bookshelf_detection_status: {yaml_quote('pending' if kind == 'bookshelf_photo' else '')}",
        f"transcript_status: {yaml_quote('pending_asr' if kind == 'video_file' else '')}",
        f"frame_analysis_status: {yaml_quote('queued' if kind == 'video_file' else '')}",
        f"video_processing_workspace: {yaml_quote(str(VIDEO_PROCESSING_DIR / video_source_id(str(file_path))) if kind == 'video_file' else '')}",
        "detected_books: []",
        "storage_policy: reference_only",
        "copies_original: false",
        f"topic: {yaml_quote(topic)}",
        f"captured_at: {yaml_quote(now_iso())}",
        f"extraction_status: {yaml_quote(extraction_status)}",
        f"tags: [{', '.join(tags)}]",
        "---",
        "",
    ]
    body = [
        f"# {title}",
        "",
        "## File Intake",
        "",
        f"- Original file: `{file_path}`",
        *([f"- Source folder: `{source_root}`", f"- Relative path: `{source_relative_path}`"] if source_root else []),
        f"- File name: `{file_path.name}`",
        f"- Size: {stat.st_size} bytes",
        f"- Suggested context: {context_name}",
        f"- Suggested topic: {topic or 'None'}",
        f"- Planned processing: {extraction_label(kind)}",
        "",
        "## User Hint",
        "",
        caption.strip() or "_No hint was provided._",
        "",
        "## Extracted Data",
        "",
    ]
    if kind in {"book_photo", "book_page_photo"}:
        body.extend([
            "## Book OCR Intake",
            "",
            f"- Book title guess: {book_title or 'Unsorted Book'}",
            f"- Page number guess: {page_number_guess or 'unknown'}",
            "- OCR status: pending",
            "- OCR text: pending",
            "",
        ])
    if kind == "bookshelf_photo":
        body.extend([
            "## Bookshelf Discovery Intake",
            "",
            f"- Shelf title: {book_title or 'Bookshelf Intake'}",
            "- Detection status: pending",
            "- Detected books: pending",
            "- Expected processing: identify visible spines/covers, infer title/author/ISBN candidates, then create one canonical book note per discovered book.",
            "",
        ])
    if kind == "video_file":
        body.extend([
            "## Video Analysis Intake",
            "",
            "- Transcript status: pending_asr",
            "- Frame analysis status: queued",
            f"- Runtime workspace: `{VIDEO_PROCESSING_DIR / video_source_id(str(file_path))}`",
            "- Expected processing: transcript/audio extraction plus sampled frame analysis for visible code, slides, diagrams, commands, and important screen text.",
            "",
        ])
    if extracted_text:
        body.extend([extracted_text.strip(), ""])
    else:
        body.extend([
            f"_Pending {extraction_label(kind)}. The heavy source file is not copied into the vault by default._",
            "",
        ])
    return "\n".join(frontmatter + body)


def render_folder_capture_markdown(
    folder_path: Path,
    caption: str,
    context_name: str,
    scope: str,
    project: str,
    topic: str,
    extracted_text: str,
    extraction_status: str,
    stats: dict[str, object],
    layer: str = LAYER_ACTIVE,
    project_title: str = "",
    project_section: str = "",
) -> str:
    tags = ["captured/chat", "source/folder"]
    if extraction_status in {"extracted", "partial"}:
        tags.append(f"extraction/{extraction_status}")
    else:
        tags.append("needs/folder-ingestion")
    if project:
        tags.append(f"project/{project}")
    if topic:
        tags.append(f"topic/{slugify(topic)}")
    title_seed = caption.strip() or folder_path.name
    title = clean_filename(title_seed)
    frontmatter = [
        "---",
        f"type: {'finished_project' if layer == LAYER_FINISHED_PROJECTS else 'folder_source'}",
        "source: local_folder",
        f"source_path: {yaml_quote(str(folder_path))}",
        f"folder_name: {yaml_quote(folder_path.name)}",
        f"file_count: {int(stats.get('file_count') or 0)}",
        f"total_size_bytes: {int(stats.get('total_bytes') or 0)}",
        f"text_files_sampled: {int(stats.get('text_files_sampled') or 0)}",
        f"scan_complete: {str(bool(stats.get('scan_complete', False))).lower()}",
        f"layer: {layer}",
        f"scope: {scope}",
        f"project: {yaml_quote(project)}",
        f"project_title: {yaml_quote(project_title)}",
        f"project_section: {yaml_quote(project_section)}",
        "storage_policy: reference_only",
        "copies_original: false",
        f"topic: {yaml_quote(topic)}",
        f"captured_at: {yaml_quote(now_iso())}",
        f"extraction_status: {yaml_quote(extraction_status)}",
        f"tags: [{', '.join(tags)}]",
        "---",
        "",
    ]
    body = [
        f"# {title}",
        "",
        "## Folder Intake",
        "",
        f"- Original folder: `{folder_path}`",
        "- Storage policy: reference only; source files are not copied into the vault.",
        f"- Folder name: `{folder_path.name}`",
        f"- Suggested context: {context_name}",
        f"- Suggested topic: {topic or 'None'}",
        f"- Planned processing: {extraction_label('folder_source')}",
        "",
        "## User Hint",
        "",
        caption.strip() or "_No hint was provided._",
        "",
        "## Extracted Data",
        "",
        extracted_text.strip(),
        "",
    ]
    return "\n".join(frontmatter + body)


def github_user_hint(text: str, url: str) -> str:
    hint = text
    candidates = {
        url,
        url.replace("https://", "", 1),
        url.replace("https://www.", "www.", 1),
    }
    for candidate in sorted(candidates, key=len, reverse=True):
        if candidate and candidate in hint:
            hint = hint.replace(candidate, "", 1)
            break
    hint = hint.strip()
    return hint or "_No hint was provided._"


def render_github_capture_markdown(
    text: str,
    context_name: str,
    scope: str,
    project: str,
    topic: str,
    metadata: dict[str, str],
    layer: str = LAYER_ACTIVE,
    project_title: str = "",
    project_section: str = "",
    project_action_id: str = "",
) -> str:
    url = first_github_url(text)
    full_name = metadata.get("github_full_name", "")
    title = clean_filename(full_name or title_from_text(text, "GitHub repository"))
    tags = ["captured/chat", "source/github", "needs/git-repository-import"]
    if project:
        tags.append(f"project/{project}")
    if topic:
        tags.append(f"topic/{slugify(topic)}")
    frontmatter = [
        "---",
        f"type: {'finished_project' if layer == LAYER_FINISHED_PROJECTS else 'github_repository'}",
        "source: github",
        f"source_url: {yaml_quote(url)}",
        f"github_owner: {yaml_quote(metadata.get('github_owner', ''))}",
        f"github_repo: {yaml_quote(metadata.get('github_repo', ''))}",
        f"github_full_name: {yaml_quote(full_name)}",
        f"github_clone_url: {yaml_quote(metadata.get('github_clone_url', ''))}",
        f"github_ref: {yaml_quote(metadata.get('github_ref', ''))}",
        f"github_subpath: {yaml_quote(metadata.get('github_subpath', ''))}",
        f"layer: {layer}",
        f"scope: {scope}",
        f"project: {yaml_quote(project)}",
        f"project_title: {yaml_quote(project_title)}",
        f"project_section: {yaml_quote(project_section)}",
        f"project_action_id: {yaml_quote(project_action_id)}",
        "storage_policy: reference_only",
        "copies_original: false",
        f"topic: {yaml_quote(topic)}",
        f"captured_at: {yaml_quote(now_iso())}",
        "extraction_status: pending",
        f"tags: [{', '.join(tags)}]",
        "---",
        "",
    ]
    body = [
        f"# {full_name or title}",
        "",
        "## GitHub Intake",
        "",
        f"- Repository: `{full_name or 'unknown'}`",
        "- Storage policy: reference only; the repository is not cloned into the vault.",
        f"- URL: {url}",
        f"- Clone URL: `{metadata.get('github_clone_url', '')}`",
        f"- Ref: `{metadata.get('github_ref', '') or 'default'}`",
        f"- Subpath: `{metadata.get('github_subpath', '') or '/'}`",
        f"- Suggested context: {context_name}",
        f"- Suggested topic: {topic or 'None'}",
        f"- Planned processing: {extraction_label('github_repository')}",
        "",
        "## User Hint",
        "",
        github_user_hint(text, url),
        "",
        "## Extracted Data",
        "",
        "_Pending GitHub clone/import. The chat stores repository metadata first and does not clone the repository automatically._",
        "",
    ]
    return "\n".join(frontmatter + body)


def render_reference_link_markdown(
    link: ReferenceLink,
    parent_rel_path: str,
    parent_source_url: str,
    route: KnowledgeRoute,
    capture_status: str = "pending",
) -> str:
    normalized = normalize_source_url_for_match(link.url)
    tags = ["captured/link-reference", f"role/{slugify(link.role)}"]
    if route.project:
        tags.append(f"project/{route.project}")
    title = clean_filename(link.title or link.url)
    frontmatter = [
        "---",
        "type: reference_link",
        "source: web_link",
        f"source_url: {yaml_quote(link.url)}",
        f"normalized_source_url: {yaml_quote(normalized)}",
        f"source_domain: {yaml_quote(source_domain(link.url))}",
        f"parent_note: {yaml_quote(parent_rel_path)}",
        f"parent_source_url: {yaml_quote(parent_source_url)}",
        f"link_context: {yaml_quote(link.context)}",
        f"link_role: {yaml_quote(link.role)}",
        f"capture_status: {yaml_quote(capture_status)}",
        f"content_hash: {yaml_quote(stable_content_hash(normalized + '|' + link.context))}",
        f"layer: {route.layer}",
        f"scope: {route.scope}",
        f"project: {yaml_quote(route.project)}",
        f"project_title: {yaml_quote(route.project_title)}",
        f"project_section: {yaml_quote(route.project_section)}",
        "storage_policy: reference_only",
        "copies_original: false",
        f"captured_at: {yaml_quote(now_iso())}",
        f"tags: [{', '.join(tags)}]",
        "---",
        "",
        f"# {title}",
        "",
        f"URL: {link.url}",
        "",
        "## Link Context",
        "",
        link.context or "_No link text was available._",
        "",
        "## Parent",
        "",
        f"- Parent note: `{parent_rel_path}`",
        f"- Parent URL: {parent_source_url}",
        "",
    ]
    return "\n".join(frontmatter)


def classify_source_file(path: Path) -> str:
    if path.is_dir():
        return "folder_source"
    suffix = path.suffix.lower()
    if suffix in IMAGE_EXTENSIONS:
        return "image_capture"
    if suffix in TEXT_EXTENSIONS:
        return "text_file"
    if suffix in DOC_EXTENSIONS:
        return "document_file"
    if suffix in AUDIO_EXTENSIONS:
        return "audio_file"
    if suffix in VIDEO_EXTENSIONS:
        return "video_file"
    if suffix in ARCHIVE_EXTENSIONS:
        return "archive_file"
    return "generic_file"


def extraction_label(kind: str) -> str:
    return {
        "image_capture": "OCR/vision extraction",
        "text_file": "text extraction",
        "document_file": "document text extraction",
        "audio_file": "speech transcription",
        "video_file": "video/audio transcription",
        "archive_file": "archive extraction",
        "folder_source": "folder ingestion",
        "github_repository": "git repository import",
        "codepen_pen": "CodePen snapshot extraction",
        "reference_link": "linked reference capture",
        "book_photo": "book OCR",
        "book_page_photo": "book page OCR",
        "bookshelf_photo": "bookshelf OCR/vision book discovery",
        "generic_file": "custom extraction",
    }.get(kind, "custom extraction")


def file_kind_label(kind: str) -> str:
    return {
        "image_capture": "image",
        "text_file": "text",
        "document_file": "document",
        "audio_file": "audio",
        "video_file": "video",
        "archive_file": "archive",
        "folder_source": "folder",
        "github_repository": "GitHub",
        "codepen_pen": "CodePen",
        "reference_link": "reference link",
        "book_photo": "book photo",
        "book_page_photo": "book page photo",
        "bookshelf_photo": "bookshelf photo",
        "generic_file": "file",
    }.get(kind, "file")


def project_title_from_source_hint(source_hint: str) -> str:
    source_hint = source_hint.strip()
    if not source_hint:
        return ""
    from knowledgelab.utils.urls import parse_github_url
    github_meta = parse_github_url(source_hint)
    if github_meta:
        return github_meta.get("github_full_name", "").strip()
    if re.fullmatch(r"[^\\/:\s]+/[^\\/:\s]+", source_hint):
        return source_hint.strip()
    try:
        path = Path(source_hint)
        name = path.stem if path.suffix and not path.is_dir() else path.name
        if name:
            return clean_filename(name)
    except (OSError, ValueError):
        pass
    return clean_filename(source_hint)


def save_capture_file(
    text: str,
    context_name: str,
    scope: str,
    project: str,
    topic: str,
    kind: str,
    layer: str = LAYER_ACTIVE,
    project_title: str = "",
    project_section: str = "",
    project_action_id: str = "",
    vault_dir: Path = VAULT_DIR,
) -> tuple[str, str, str]:
    source_url = first_github_url(text) or first_codepen_url(text) or first_youtube_url(text) or first_telegram_url(text) or first_url(text)
    if kind in {"article", "youtube_link", "github_repository", "codepen_pen", "reference_link"} and source_url:
        from knowledgelab.vault.frontmatter import find_existing_source_note
        existing_rel_path = find_existing_source_note(source_url, layer, scope, project)
        if existing_rel_path:
            return existing_rel_path, kind, topic
    destination = capture_destination(scope, topic, kind, layer, project, project_section)
    destination.mkdir(parents=True, exist_ok=True)
    github_metadata: dict[str, str] = {}
    if kind == "github_repository":
        github_url = first_github_url(text)
        from knowledgelab.utils.urls import parse_github_url as _parse_github_url
        github_metadata = _parse_github_url(github_url)
    title = project_title if layer == LAYER_FINISHED_PROJECTS else (github_metadata.get("github_full_name", "") if kind == "github_repository" else title_from_text(text, f"{context_name} capture"))
    if kind in {"article", "youtube_link", "codepen_pen"} and topic:
        title = f"{topic} - {title}"
    path = unique_path(destination / f"{clean_filename(title)}.md")
    if kind == "github_repository":
        markdown = render_github_capture_markdown(text, context_name, scope, project, topic, github_metadata, layer, project_title, project_section, project_action_id)
    else:
        markdown = render_capture_markdown(text, context_name, scope, project, topic, kind, layer, project_title, project_section)
    path.write_text(markdown, encoding="utf-8-sig")
    rel_path = path.relative_to(vault_dir).as_posix()
    return rel_path, kind, topic
