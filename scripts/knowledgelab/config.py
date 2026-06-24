"""KnowledgeLab configuration — all constants, paths, settings, and environment variables."""

from __future__ import annotations

import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_VAULT_DIR = ROOT / "Obsidian-Test-Vault"
VAULT_DIR = Path(os.getenv("KNOWLEDGELAB_VAULT_DIR", str(DEFAULT_VAULT_DIR)))
if not VAULT_DIR.is_absolute():
    VAULT_DIR = ROOT / VAULT_DIR
SCRIPTS_DIR = ROOT / "scripts"
QUERY_SCRIPT = SCRIPTS_DIR / "query-vault-scope-lmstudio.ps1"
GAME_GUARD_SCRIPT = SCRIPTS_DIR / "game-guard.ps1"
CONTROL_SCRIPT = ROOT / "LightRAG-Control.ps1"
LEGACY_HISTORY_PATH = Path(os.getenv("KNOWLEDGELAB_LEGACY_HISTORY_PATH", str(ROOT / "tmp" / "knowledge-chat-history.jsonl")))
CHAT_STORE_PATH = Path(os.getenv("KNOWLEDGELAB_CHAT_STORE_PATH", str(ROOT / "tmp" / "knowledge-chat-sessions.json")))
SETTINGS_PATH = Path(os.getenv("KNOWLEDGELAB_CHAT_SETTINGS_PATH", str(ROOT / "tmp" / "knowledge-chat-settings.json")))
MATERIAL_QUEUE_PATH = Path(os.getenv("KNOWLEDGELAB_MATERIAL_QUEUE_PATH", str(ROOT / "tmp" / "material-processing-queue.jsonl")))
RLM_QUEUE_PATH = Path(os.getenv("KNOWLEDGELAB_RLM_QUEUE_PATH", str(ROOT / "tmp" / "rlm-processing-queue.jsonl")))
PROJECT_ACTIONS_PATH = Path(os.getenv("KNOWLEDGELAB_PROJECT_ACTIONS_PATH", str(ROOT / "tmp" / "project-actions.json")))
PROJECT_RUNTIME_DIR = Path(os.getenv("KNOWLEDGELAB_PROJECT_RUNTIME_DIR", str(ROOT / "tmp" / "project-runtime")))
VIDEO_PROCESSING_DIR = Path(os.getenv("KNOWLEDGELAB_VIDEO_PROCESSING_DIR", str(ROOT / "tmp" / "video-processing")))
OBSIDIAN_ICON = ROOT / "assets" / "icons" / "Obsidian.png"
NEW_CHAT_ICON = ROOT / "assets" / "icons" / "new-chat.png"
WEB_SEARCH_ICON = ROOT / "assets" / "icons" / "web-search.png"
ATTACHMENT_ICON = ROOT / "assets" / "icons" / "attachment.png"
ATTACHMENT_ICON_ACTIVE = ROOT / "assets" / "icons" / "attachment-active.png"
MICROPHONE_ICON = ROOT / "assets" / "icons" / "microphone.png"
MICROPHONE_ICON_ACTIVE = ROOT / "assets" / "icons" / "microphone-active.png"

LMSTUDIO_API_URL = os.getenv("LMSTUDIO_BASE_URL", "http://127.0.0.1:5000/v1").rstrip("/")
DEFAULT_LLM_MODEL = os.getenv("LMSTUDIO_LLM_MODEL", "qwen/qwen3-14b")
DEFAULT_EMBEDDING_MODEL = os.getenv("LMSTUDIO_EMBEDDING_MODEL", "text-embedding-nomic-embed-text-v1.5")
DEFAULT_VISION_MODEL = os.getenv("KNOWLEDGELAB_VISION_MODEL", "")
OPEN_LIBRARY_SEARCH_URL = "https://openlibrary.org/search.json"
GOOGLE_BOOKS_SEARCH_URL = "https://www.googleapis.com/books/v1/volumes"
BOOK_LOOKUP_MIN_SCORE = 0.56
VISION_MODEL_MARKERS = ("vision", "vl", "llava", "moondream", "minicpm", "gemma-3", "pixtral", "qwen2.5-vl", "qwen2-vl", "qwen-vl")

LOCAL_RUNTIME_SYSTEM_PROMPT = (
    "You are KnowledgeLab Chat, a local-first desktop assistant running inside the user's KnowledgeLab app. "
    "All model calls are routed through the user's configured local LM Studio OpenAI-compatible server. "
    "Do not claim you are running through Alibaba Cloud, OpenAI cloud, Anthropic cloud, or any other hosted API unless the user explicitly provides evidence of such a setup. "
    "If the prompt includes a 'KnowledgeLab runtime context' block, treat it as authoritative app state. "
    "If asked whether you are connected, where processing is happening, or what the app is doing, including LightRAG, queues, imports, DnD, local servers, book discovery, and video analysis, answer from that runtime context instead of model-provider biography. "
    "Answer normally and directly in Russian by default. "
    "Use another language only when the user clearly writes in that language or explicitly asks for it. "
    "Short ambiguous messages like 'ку', 'ого', '555', or mistyped Russian words must be treated as Russian conversation. "
    "Do not treat every message as a knowledge-base lookup. "
    "Do not show reasoning or analysis; provide only the final useful answer."
)

LAYER_ACTIVE = "active"
LAYER_FINISHED_PROJECTS = "finished-projects"
WARNING_PREFIX = "::knowledge-warning "
DND_SAFE_MODE_ENV = "KNOWLEDGELAB_ENABLE_EXPLORER_DND"
DND_DISABLE_ENV = "KNOWLEDGELAB_DISABLE_EXPLORER_DND"

CONTEXTS = {
    "General": ("general", ""),
    "Web Development": ("web", "web-development"),
    "My Game": ("game", "my-game"),
    "Finished Projects": ("all", ""),
}

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff"}
IMAGE_FILETYPES = [
    ("Images", "*.png *.jpg *.jpeg *.webp *.bmp *.gif *.tif *.tiff"),
    ("PNG", "*.png"),
    ("JPEG", "*.jpg *.jpeg"),
    ("All files", "*.*"),
]
TEXT_EXTENSIONS = {
    ".txt", ".md", ".markdown", ".csv", ".tsv", ".json", ".jsonl", ".yaml", ".yml", ".xml", ".html", ".htm",
    ".py", ".ps1", ".js", ".jsx", ".ts", ".tsx", ".css", ".scss", ".less", ".cs", ".cpp", ".h",
    ".hpp", ".java", ".kt", ".go", ".rs", ".php", ".rb", ".sql", ".log",
}
DOC_EXTENSIONS = {".docx", ".pdf", ".rtf", ".odt", ".epub"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".opus", ".flac", ".wma"}
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".m4v", ".wmv"}
ARCHIVE_EXTENSIONS = {".zip", ".rar", ".7z", ".tar", ".gz", ".tgz", ".bz2", ".xz"}
SUPPORTED_FILETYPES = [
    ("Knowledge sources", "*.png *.jpg *.jpeg *.webp *.bmp *.gif *.tif *.tiff *.txt *.md *.csv *.json *.docx *.pdf *.mp3 *.wav *.m4a *.mp4 *.mkv *.mov *.webm *.zip *.rar *.7z"),
    ("Images", "*.png *.jpg *.jpeg *.webp *.bmp *.gif *.tif *.tiff"),
    ("Documents", "*.txt *.md *.csv *.json *.docx *.pdf *.rtf *.odt *.epub"),
    ("Audio", "*.mp3 *.wav *.m4a *.aac *.ogg *.opus *.flac *.wma"),
    ("Video", "*.mp4 *.mkv *.mov *.avi *.webm *.m4v *.wmv"),
    ("Archives", "*.zip *.rar *.7z *.tar *.gz *.tgz *.bz2 *.xz"),
    ("All files", "*.*"),
]
TEXT_EXTRACTION_LIMIT = 90000
ARTICLE_TEXT_EXTRACTION_LIMIT = 60000
ARTICLE_FALLBACK_MIN_CHARS = 240
REFERENCE_LINK_LIMIT = 80
RLM_PROFILE_THRESHOLD_CHARS = 12000
FOLDER_TEXT_EXTRACTION_LIMIT = 12000
FOLDER_TOTAL_TEXT_LIMIT = 110000
FOLDER_TREE_LIMIT = 260
FOLDER_TEXT_FILE_LIMIT = 45
FOLDER_FILE_SCAN_LIMIT = 1800
VIDEO_FRAME_LIMIT = 8
VIDEO_FRAME_INTERVAL_SECONDS = 30
FOLDER_SKIP_DIRS = {
    ".git", ".hg", ".svn", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    ".venv", "venv", "env", "node_modules", "dist", "build", ".next", ".nuxt", ".turbo",
    "Library", "Temp", "obj", "bin", "target", ".gradle", ".idea", ".vscode",
}
FILE_CAPTURE_KINDS = {"text_file", "document_file", "audio_file", "video_file", "archive_file", "generic_file", "folder_source", "book_photo", "book_page_photo", "bookshelf_photo"}
URL_CAPTURE_KINDS = {"github_repository", "codepen_pen", "reference_link"}
VOICE_INPUT_SECONDS = 8

BUTTON_COLOR_PRESETS = {
    "Blue": "#476f9d",
    "Green": "#527b73",
    "Purple": "#76689a",
    "Graphite": "#5f6974",
}

UI_THEME = {
    "app_bg": "#f6f4ef",
    "top_bg": "#eef3f1",
    "sidebar_bg": "#edf1f3",
    "panel_bg": "#ffffff",
    "panel_border": "#d9e1e7",
    "panel_shadow": "#d8dde4",
    "chat_bg": "#fffdfa",
    "composer_bg": "#f6f4ef",
    "accent": "#476f9d",
    "accent_soft": "#dfeaf5",
    "accent_pulse_1": "#eaf3ff",
    "accent_pulse_2": "#dbeafd",
    "text": "#1f2933",
    "muted": "#4a5568",
    "warning": "#5a6370",
    "success": "#3f7a58",
    "danger": "#a34136",
    "focus_ring": "#476f9d",
}

DEFAULT_SETTINGS = {
    "send_on_enter": True,
    "use_lightrag": False,
    "button_color": BUTTON_COLOR_PRESETS["Blue"],
    "game_guard_enabled": True,
    "game_guard_delay_seconds": 5,
    "obsidian_path": "",
    "vault_path": str(DEFAULT_VAULT_DIR),
    "lmstudio_base_url": LMSTUDIO_API_URL,
    "llm_model": DEFAULT_LLM_MODEL,
    "vision_model": DEFAULT_VISION_MODEL,
    "embedding_model": DEFAULT_EMBEDDING_MODEL,
    "book_lookup_enabled": True,
    "auto_route_topics": True,
    "auto_create_topics": True,
    "response_language": "ru",
    "default_llm_mode_applied": True,
    "main_toolbar_lightrag_removed": True,
    "plain_chat_adapter_version": 1,
    "auto_process_links": True,
    "auto_detect_books_in_images": True,
    "web_search_enabled": False,
}

WEB_TERMS = {
    "web", "frontend", "front-end", "html", "css", "javascript", "typescript",
    "react", "next.js", "nextjs", "vue", "svelte", "vite", "tailwind", "dom",
    "browser", "layout", "responsive", "api", "fetch", "axios", "auth", "oauth",
    "jwt", "node", "npm", "верстка", "вёрстка", "фронтенд", "бекенд", "сайт",
    "страница", "лендинг", "landing", "landing page", "popup", "modal", "css",
}

GAME_TERMS = {
    "my-game", "my game", "моя игра", "моей игре", "мой проект игры",
    "геймплей", "game design", "игровой проект", "unity", "unreal",
}

FINISHED_PROJECT_TERMS = {
    "готовые проекты", "готовый проект", "готового проекта", "готовых проектов",
    "портфолио", "референс", "референсы", "пример проекта", "примеры проектов",
    "похожие проекты", "что уже сделано", "finished project", "finished projects",
    "portfolio", "reference project", "reference projects", "case study", "case studies",
}

BOOK_IMAGE_TERMS = {
    "book", "books", "library", "isbn", "cover", "spine", "page", "chapter",
    "книга", "книги", "обложка", "страница", "страницы", "корешок", "глава", "учебник",
}

BOOK_PAGE_TERMS = {"page", "pages", "chapter", "страница", "страницы", "глава", "разворот"}

BOOKSHELF_TERMS = {
    "bookshelf", "book shelf", "shelf", "shelves", "bookcase", "library shelf",
    "книжная полка", "полка с книгами", "книжные полки", "стеллаж", "стеллаж с книгами",
}

REFERENCE_LINK_HINTS = {
    "codepen", "github", "demo", "example", "sample", "snippet", "pen", "sandbox",
    "reference", "case", "preview", "live", "source", "сниппет", "пример", "демо",
    "референс", "исходник", "код", "анимация",
}

SAVE_PHRASES = {
    "вот ссылка", "сохрани", "сохранить", "запомни", "добавь в obsidian",
    "добавить в obsidian", "добавь в базу", "добавь в знания", "добавь материал",
    "сохрани ссылку", "занеси в vault", "вот материал", "полезная статья",
    "добавь заметку", "добавить заметку",
}

QUESTION_HINTS = {
    "что", "как", "почему", "зачем", "когда", "где", "кто", "какой", "какая",
    "какие", "можешь", "можно", "сделай", "напиши", "объясни", "расскажи",
    "найди", "поищи", "проверь", "why", "how", "what", "write", "make",
}

KNOWLEDGE_LOOKUP_TERMS = {
    "найди в базе", "поищи в базе", "ищи в базе", "из базы знаний", "по базе знаний",
    "из сохраненного", "из сохранённого", "из сохраненных", "из сохранённых",
    "из сохраненных материалов", "из сохранённых материалов", "по сохраненным материалам",
    "по сохранённым материалам", "что у меня сохранено", "что сохранено",
    "сделай из сохраненных", "сделай из сохранённых", "по материалам из obsidian",
}

KNOWLEDGE_HELP_TERMS = {
    "как узнать", "как достать", "как получить", "как спросить", "как найти",
    "как пользоваться", "как использовать", "доступ к lightrag", "доступ к базе",
}

RUSSIAN_LANGUAGE_TERMS = {
    "на русском", "по русски", "по-русски", "русский", "русском", "отвечай на русском",
    "говори на русском", "пиши на русском",
}

TOPICS = [
    ("React", {"react", "jsx", "tsx", "hooks", "component"}),
    ("TypeScript", {"typescript", " ts ", "types", "type-safe", "типизация"}),
    ("CSS Layout", {"css", "grid", "flex", "layout", "responsive", "media query", "верстка", "вёрстка", "popup", "modal"}),
    ("Accessibility", {"a11y", "accessibility", "aria", "screen reader", "доступность"}),
    ("Performance", {"performance", "perf", "lcp", "cls", "bundle", "оптимизация"}),
    ("API Integration", {"api", "fetch", "axios", "graphql", "rest", "websocket"}),
    ("Auth", {"auth", "oauth", "jwt", "session", "login", "авторизация"}),
    ("Deployment", {"deploy", "docker", "vercel", "netlify", "nginx", "hosting"}),
    ("Testing", {"test", "testing", "playwright", "vitest", "jest", "тест"}),
    ("Next.js", {"next.js", "nextjs", "app router", "server component"}),
    ("Node.js", {"node", "node.js", "express", "fastify", "npm"}),
    ("Tailwind", {"tailwind"}),
    ("Forms", {"form", "forms", "react-hook-form", "zod", "валидац"}),
    ("Animation", {"animation", "framer", "motion", "gsap", "анимац"}),
    ("Unity", {"unity", "c#", "csharp"}),
    ("Zenject", {"zenject", "dependency injection"}),
]
