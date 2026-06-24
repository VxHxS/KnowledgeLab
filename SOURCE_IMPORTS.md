# Source Imports

## Контексты

Vault остается одним, но заметки разделяются по контекстам:

- `scope: general` - общая база знаний, например Unity-ресурсы, статьи, курсы, Telegram-ссылки.
- `scope: game` + `project: my-game` - информация именно по твоей игре.
- `layer: finished-projects` - готовые проекты и портфолио-референсы; они хранятся как reference-only карточки в `40 Finished Projects/<section>/<project-slug>` и индексируются отдельно от активной базы.
- `project_section` - раздел/подтема готовых проектов, например `web`, `game`, `landing-pages`, `unity-tools`.
- При импорте Finished Project чат сначала сам выводит `project_title` и `project_section` из имени папки, GitHub `owner/repo` и подписи в сообщении; уточняющий вопрос нужен только для неоднозначных источников.
- Если тот же `source_url` уже сохранен в том же retrieval-слое/контексте, чат переиспользует существующую заметку вместо создания копии. Похожие по смыслу, но не идентичные источники не склеиваются автоматически, чтобы не терять контекст.
- Для SPA/Vite-страниц, где HTML содержит только пустой `#root`, importer пытается извлечь человекочитаемые строки из JS-бандла и сохранить их как `SPA Bundle Text Snapshot`.
- Explorer drag-and-drop включается через `tkinterdnd2`, если пакет доступен, и подсвечивает окно при наведении. Если на конкретной Windows/Tk-сборке DnD ведет себя нестабильно, его можно отключить через `KNOWLEDGELAB_DISABLE_EXPLORER_DND=1`; папки остаются доступными через отдельную кнопку папки, скрепку -> Folder или вставленный локальный путь.

LightRAG-скрипты читают эти поля из frontmatter. Если frontmatter нет, папки `10 Programming`, `10 General Knowledge` и `30 Sources` считаются `general`, а `20 Projects/<project>` считается `game`.
Если `layer` не указан, заметка считается `active`; обычные индексы не включают `finished-projects`.
При включенном `auto_route_topics` чат сам выбирает topic/project/layer и не открывает ручной диалог выбора. При включенном `auto_create_topics` новая тема создается как папка `Topics/<topic>/_Topic.md`; topic registry собирается из `TOPICS`, frontmatter (`topic`/`book_topic`) и уже существующих `Topics` папок.
При drag-and-drop папки KnowledgeLab не копирует исходную папку в vault и не хранит ее как отдельный материал: папка раскрывается в отдельные file-intake заметки по файлам. В каждой заметке сохраняются `source_path`, `source_root`, `source_relative_path`, topic/tags и легкий извлеченный текст, если это возможно.

Project action buttons are intentionally operational cache, not knowledge storage. `Получить результат` and `Запуск на локальном сервере` use `tmp/project-actions.json` plus isolated runtime copies/checkouts in `tmp/project-runtime/<project-id>/`; build artifacts, dependency installs, server logs, and process metadata stay there instead of being written into the original folder or the Obsidian vault.

RLM means Recursive Language Model here, following the MIT paper/workthrough: long context is treated as an external environment, then decomposed into snippets/subcalls instead of being pushed whole into the model context. KnowledgeLab stores the first operational hook in `tmp/rlm-processing-queue.jsonl`; parsed pages add an RLM profile when they are long or link-rich.

Recursive link capture is separate from RLM. When a parsed page contains CodePen/GitHub/demo/example links, KnowledgeLab creates canonical `reference_link` notes with `parent_note`, `parent_source_url`, `source_url`, `normalized_source_url`, `source_domain`, `link_context`, `link_role`, `capture_status`, and `content_hash`. CodePen URLs are recognized as `codepen_pen`; if CodePen blocks full parsing with a security check, the note remains useful with `capture_status: blocked` or `metadata`.

Book intake starts as photo OCR/vision intake: image files whose caption/name looks like a book, cover, spine, page, chapter, ISBN, or bookshelf become `book_photo`, `book_page_photo`, or `bookshelf_photo` under `50 Library/<book-slug>/`. Single-book/page notes store `source_image_path`, `book_title`, `page_number_guess`, `ocr_status`, and empty `ocr_text`. Bookshelf notes store `bookshelf_detection_status: pending` and `detected_books: []`, then a background LM Studio vision worker attempts to identify visible books, create/update canonical `type: book` notes, and append any unreadable spines/covers to `Unresolved / Not Found`. Catalog enrichment checks multiple public sources: Open Library (an open Internet Archive book catalog) and Google Books. Notes keep `catalog_sources`, `catalog_candidate_count`, best-match metadata, and a `Catalog Candidates` section for nearby matches. If the user later writes missing titles/authors, the chat links that list to the latest bookshelf report or creates a manual book-list parent note, saves user-confirmed `type: book` notes even when catalog lookup is weak, and appends `Resolved by user` to the parent note. Plain image attachments are also quietly checked for books when `auto_detect_books_in_images` is enabled; unrelated images are left alone. The chat also shows `Отчёт по книгам`, grouped into `Добавлено`, `Нужно уточнить`, and `Не найдено / не прочитано`, so the user sees what was added and what needs more title/author evidence.

Video intake is reference-only too. YouTube links keep the existing captions/transcript sync and also queue `video_analysis`; local video files store `transcript_status`, `frame_analysis_status`, and `video_processing_workspace`. Sampled frames live under `tmp/video-processing/<source-id>/`; the vision model extracts code, slides, diagrams, commands, and screen text into a `type: video_analysis` note. Missing FFmpeg, ASR, or vision support becomes a clear pending status instead of a crash.

Set `KNOWLEDGELAB_VISION_MODEL` to force a specific LM Studio vision model. Without it, the app prefers a loaded model whose id looks vision-capable (`vision`, `vl`, `llava`, `moondream`, `minicpm`, `pixtral`, `qwen*-vl`, etc.). It does not pretend a text-only chat model can read images; if no vision-capable model is available, the failure is written back to the parent book/shelf note and shown in chat instead of staying silent.

For phone sync without paid Obsidian Sync, use Syncthing for Windows + Android as the default. Sync the vault Markdown folder only; exclude runtime/cache folders such as `LightRAG/.venv`, `LightRAG/rag_storage*`, `tmp/project-runtime`, `tmp/project-action-logs`, and generated model/cache artifacts.

## Book Intake Flow

Book/page/shelf photos follow this intake path:

1. **Image intake**: Image files whose caption or filename looks like a book, cover, spine, page, chapter, ISBN, or bookshelf become `book_photo`, `book_page_photo`, or `bookshelf_photo` under `50 Library/<book-slug>/`.
2. **Reference-only storage**: Notes store `source_image_path`, `book_title`, `page_number_guess`, `ocr_status`, and empty `ocr_text`. Bookshelf notes additionally store `bookshelf_detection_status: pending` and `detected_books: []`.
3. **Background vision pass**: Book and bookshelf images start a background LM Studio vision worker. The worker asks the vision model for strict JSON with `detected_books` and `unresolved`.
4. **Catalog enrichment**: Readable books are looked up by ISBN first, then title/author, then visible spine evidence through Open Library Search API and Google Books volumes search.
5. **Canonical book notes**: Confidently matched books become `type: book` notes under `50 Library/<book-slug>/Book.md` with metadata from both the photo and catalog sources.
6. **Unresolved list**: Unreadable spines, weak catalog matches, lookup failures, and missing title/author cases go into the parent note under `Unresolved / Not Found`.
7. **Chat report**: The chat shows `Отчёт по книгам`, grouped into `Добавлено`, `Нужно уточнить`, and `Не найдено / не прочитано`.

Plain image attachments are also quietly checked for visible books when `auto_detect_books_in_images` is enabled; unrelated images are left alone.

## Video Analysis Flow

Video sources create `video_analysis` queue items for background processing:

1. **Intake**: YouTube links and local video files create reference-only intake notes plus a queued `video_analysis` note.
2. **Frame sampling**: Local videos sample frames into `tmp/video-processing/<source-id>/` using FFmpeg when available.
3. **Vision extraction**: The local vision model extracts visible code, slides, diagrams, commands, and screen text from sampled frames.
4. **YouTube caption sync**: YouTube links continue existing caption/transcript sync and also queue frame analysis.
5. **ASR queue**: Audio transcription remains `pending_asr` until a transcription worker is available.
6. **Note output**: Results are written into `type: video_analysis` notes. Missing FFmpeg, ASR, or vision support becomes a clear pending status.

## Book Resolution Flow

When the user writes missing book titles or authors after a bookshelf report:

1. **Detection**: The chat detects the follow-up as a manual book resolution attempt.
2. **Parent note update**: The chat links the list to the latest bookshelf report or creates a manual book-list parent note.
3. **Confirmed book notes**: User-confirmed `type: book` notes are saved even when catalog lookup is weak.
4. **Routing**: Each resolved book is routed to its own topic.
5. **Parent annotation**: `Resolved by user` is appended to the parent shelf note.

## Telegram

### Export mode

1. В Telegram Desktop открой канал или группу.
2. Меню -> Export chat history.
3. Выбери Machine-readable JSON.
4. Запусти `05 Import Telegram Export.cmd` из `C:\Users\Юрий\Desktop\LightRag`.
5. Укажи путь к `result.json`.

Импорт создаст Markdown-файлы в:

```text
Obsidian-Test-Vault\30 Sources\Telegram\<название канала>\
```

### Sync mode

Для живой синхронизации по ссылке используется отдельная иконка:

```text
C:\Users\Юрий\Desktop\Sync Telegram Unity.cmd
```

Первый запуск требует Telegram API credentials:

1. открой `https://my.telegram.org/apps`;
2. создай приложение;
3. скопируй `api_id` и `api_hash`;
4. введи их в окне синхронизации вместе с телефоном Telegram.

После первого входа локальная session сохраняется в:

```text
C:\MyFiles\KnowledgeLab\.telegram-sync
```

Синхронизация:

- открывает `https://t.me/+Ct9ip7LnMzNlN2M6`;
- получает темы Telegram-группы;
- пишет каждую тему отдельным Markdown-файлом;
- хранит `tg-msg:<id>` блоки и `last_id`, поэтому повторный запуск не дублирует сообщения.

## Scoped questions

- `06 Ask General Knowledge.cmd` спрашивает только по общей базе.
- `07 Ask My Game.cmd` спрашивает только по `scope: game`, `project: my-game`.
- `08 Reindex LightRAG Scope.cmd` строит отдельный LightRAG storage для выбранного scope.
