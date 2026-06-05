# Требования: YouTube-ссылка в Obsidian -> транскрипт -> LightRAG

## Цель

Пользователь добавляет YouTube-ссылку прямо в Obsidian. Система сама находит такую заметку, получает текст видео, сохраняет транскрипт как Markdown рядом с нужной темой или проектом и после переиндексации делает этот текст доступным для LightRAG-запросов.

Ключевая формулировка: "youtube достаточно взять ссылку и текст транскрибировать".

`LightRAG-Control` остается приложением для проверки и обслуживания системы. Через него не добавляются новые материалы в базу знаний.

## Пользовательский сценарий

1. Пользователь создает заметку в Obsidian с YouTube-ссылкой.
2. В frontmatter заметки указывает минимум `type: youtube_link` или `source: youtube_link`.
3. При необходимости задает `scope`, `project`, `area`, `topic` и теги.
4. Скрипт `scripts/sync-youtube-links.py` находит marked YouTube link notes.
5. Скрипт `scripts/import-youtube-transcript.py` получает captions или auto captions через `yt-dlp`.
6. Транскрипт сохраняется в правильную папку Obsidian.
7. `scripts/ingest-vault-scope-lmstudio.ps1` индексирует выбранный scope в LightRAG.
8. `scripts/query-vault-scope-lmstudio.ps1` или `scripts/chat-vault-lmstudio.ps1` отвечают по индексу через LM Studio.

## Формат заметки-ссылки

Минимальный пример:

```yaml
---
type: youtube_link
source: youtube_link
source_url: "https://www.youtube.com/watch?v=..."
scope: general
area: programming
topic: Zenject
tags: [source/youtube, topic/zenject, topic/unity]
---

# Zenject video

https://www.youtube.com/watch?v=...
```

Для проектного материала:

```yaml
---
type: youtube_link
source: youtube_link
scope: game
project: my-game
tags: [source/youtube, project/my-game]
---

https://www.youtube.com/watch?v=...
```

## Автоматическая сортировка

Для `scope: game` транскрипт сохраняется в:

```text
20 Projects/<project>/Sources/YouTube
```

Для общего знания транскрипт сохраняется по теме:

```text
10 Programming/<topic>/Sources/YouTube
20 Music/<topic>/Sources/YouTube
10 General Knowledge/<topic>/Sources/YouTube
```

`Sources` означает "исходные материалы": YouTube, Telegram, статьи, PDF, документация. Это не одна общая куча, а слой внутри темы или проекта, чтобы первоисточники оставались рядом с тем контекстом, к которому относятся.

## Выходной Markdown

Ожидаемый frontmatter транскрипта:

```yaml
---
source: youtube
source_url: "https://www.youtube.com/watch?v=..."
video_id: "..."
title: "Video title"
channel: "Channel name"
captured_at: "YYYY-MM-DD HH:mm:ss"
language: "ru-orig"
scope: "general"
project: ""
transcript_method: "captions|auto_captions|whisper"
---
```

Тело заметки:

```markdown
# Video title

Source: https://www.youtube.com/watch?v=...

## Transcript

Текст транскрипта...
```

## Логика получения текста

Приоритеты:

1. Сначала пробовать ручные subtitles/captions через `yt-dlp`.
2. Если ручных captions нет, пробовать auto captions.
3. Если captions нет или они плохие, позже добавить fallback через локальный STT (`faster-whisper` или `whisper.cpp`).

## Критерии готовности

- Пользователь добавляет только YouTube-ссылку в Obsidian note.
- Скрипт находит ссылку без ручного копирования transcript из браузера.
- Markdown-транскрипт появляется в правильной теме или проекте.
- Повторный sync не дублирует уже импортированное видео.
- Reindex строит LightRAG storage для нужного scope.
- Вопрос по содержанию видео возвращает ответ с reference на созданный transcript `.md`.

## Проверенный пример

Видео:

```text
https://www.youtube.com/watch?v=mbuzSrKHBHI&t=6802s
```

Заметка-ссылка:

```text
Obsidian-Test-Vault/00 Inbox/Zenject Favorite Video.md
```

Автоматический маршрут:

```text
10 Programming/Zenject/Sources/YouTube
```

Получен transcript через YouTube auto captions (`ru-orig`) и проверено, что LightRAG отвечает по нему с reference на transcript-файл.
