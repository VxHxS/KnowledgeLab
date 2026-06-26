# KnowledgeLab — Итог сессии 26.06.2026

## Что сделано

### Web-поиск (исправлено)
- Системный промпт теперь знает про встроенный поиск и инструктирует LLM использовать результаты
- DuckDuckGo JSON API (стабильнее HTML) + HTML fallback
- Контекст для LLM: "USE THESE RESULTS, do NOT invent answers"

### Book reports (упрощён)
- Нумерованный список автор — название (как у ChatGPT)
- Проверка vault: книги уже в Obsidian помечаются ✓
- CTA: "Отправьте файлы книг (.epub, .pdf) отдельно"
- Vision-ошибки на русском языке

### Компактные сообщения
- Настройка `message_detail_level: compact/full`
- Форматы books/routing/video поддерживают оба режима

### Topic adaptation
- `build_topic_context()` добавляет в system prompt специализацию (web/game/general)
- LLM знает, что пользователь работает с React, Unity и т.д.

### Транскрипция
- `transcript_clean.py` — regex чистка (дубли, пунктуация, слова-паразиты)
- LLM постобработка (опционально) — исправление грамматики через LM Studio

### Vault sync
- `sync/vault_git.py` — auto-commit каждые N минут, push/pull
- `sync/syncthing.py` — проверка Syncthing, инструкция по настройке

### Code Review node
- `goal_nodes.py:CodeReviewNode` — анализ кода через LLM + Obsidian контекст
- Проверяет: названия, интерфейсы, запахи, модули, SOLID/DRY

### Node система
- `nodes/base.py` — протокол `KnowledgeNode`
- `nodes/registry.py` — реестр с `register()`, `get()`, `list_nodes()`, `run_node()`
- `nodes/builtin_nodes.py` — 4 встроенные ноды
- `nodes/goal_nodes.py` — 5 целевых нод (MakeWebsite, Refactor, LaunchServer, Analyze, CodeReview)

### Model manager
- `llm/model_manager.py` — автопереключение LLM/Vision/Embeddings через LM Studio API
- Настройки моделей в Settings

### Порт LM Studio
- Автодетект: env → common порты (5000 первый) → netstat → история → 1234
- История портов в `~/.knowledgelab/port_history.json`

### Keyboard shortcuts
- Ctrl+C — копирование выделенного текста
- Ctrl+V — вставка в поле ввода
- Ctrl+A — выделение всего текста

### Ярлык
- `Launch-KnowledgeLab.ps1` — обёртка, ищет последнюю папку staging
- Ярлык указывает на обёртку — не устаревает

### Анимация
- 4 цветные линии на thinking-пузыре (когда модель думает)
- Медленная (120ms), 7 ярких цветов
- Ответы и user-сообщения — без анимации

### Дедупликация чатов
- Макс. 25 чатов, убраны дубли по title+messages

### Дубликаты при drag-and-drop
- `frontmatter.py:find_existing_file_capture()` — проверка vault
- `dialogs.py:ask_duplicate_resolution()` — диалог "Пропустить/Сохранить/Отменить"

### SPA-сервер
- Статические проекты с `index.html` запускаются через Python HTTP server
- Projects без `index.html` — показывается ошибка

### Установщик
- Теперь создаёт ОДИН ярлык (LightRAG-Chat), а не два

---

## Что дальше (приоритет)

### Высокий приоритет
1. **Перенести русский текст в JSON** — 227 строк захардкожены в .py файлах
2. **UI для выбора моделей** — сейчас модели вводятся текстом, нужен выпадающий список с доступными моделями из LM Studio
3. **Тестирование на реальном железе** — проверить все фичи на 5060 Ti 16GB

### Средний приоритет
4. **Telegram sync improvements** — автоимпорт экспорта Telegram
5. **Video ASR** — интеграция Whisper/faster-whisper для транскрипции видео
6. **Book file import** — приём .epub/.pdf файлов книг и добавление в библиотеку
7. **Obsidian sync через Git** — авто-коммит vault каждые N минут

### Низкий приоритет
8. **Visual node editor** — визуальный редактор нод для создания workflow
9. **Multi-language support** — интерфейс на английском языке
10. **Plugin system** — расширяемость через плагины

---

## Технические детали

### Модели (для 5060 Ti 16GB + 32GB RAM)
- **LLM**: `Qwen2.5-Coder-14B-Uncensored` (8.5GB, без ограничений)
- **Vision**: `Qwen2.5-VL-7B-Instruct` (6.0GB, чтение книг)
- **Embeddings**: `text-embedding-nomic-embed-text-v1.5` (0.5GB, поиск)

### Структура проекта
```
scripts/
  main.py                          # Entry + KnowledgeChatApp
  knowledgelab/
    config.py, models.py
    utils/    (text, urls, colors, paths)
    routing/  (intent, topics, project_stack)
    vault/    (frontmatter, capture, capture_workflow)
    material/ (web, codepen, github, queue, youtube, video, workers, transcript_clean)
    vision/   (book_discovery, book_pipeline, book_downloads, book_sources, html_parsers)
    llm/      (lmstudio, runtime_context, diagnostics, web_search, voice, game_guard, model_manager, port_detector)
    ui/       (widgets, theme, tooltip, chat_store, settings, settings_dialog,
               game_guard_dialog, project_panel, chat_list, dialogs,
               message_bubble, animated_edges, obsidian)
    tasks/    (background, process, project_actions, static_server)
    nodes/    (base, registry, builtin_nodes, goal_nodes)
    sync/     (vault_git, syncthing)
    i18n/     (messages)
    resources/ (messages.ru.json)
```

### GitHub
- https://github.com/VxHxS/KnowledgeLab
- Последний коммит: `8713aea`
